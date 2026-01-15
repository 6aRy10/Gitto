import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import models
import io
import hashlib
import json
import os

def debug_log(message, data=None, hypothesis_id=None, location=None):
    """
    Debug logging with environment-aware path handling.
    Uses DEBUG_LOG_PATH environment variable or defaults to relative path.
    """
    # Use environment variable or default to relative path
    log_path = os.getenv(
        "DEBUG_LOG_PATH",
        os.path.join(os.getcwd(), ".cursor", "debug.log")
    )
    
    # Ensure directory exists
    log_dir = os.path.dirname(log_path)
    if log_dir and not os.path.exists(log_dir):
        try:
            os.makedirs(log_dir, exist_ok=True)
        except OSError:
            # If we can't create the directory, skip logging
            return
    
    payload = {
        "sessionId": "debug-session",
        "timestamp": int(datetime.now().timestamp() * 1000),
        "message": message,
        "data": data or {},
        "hypothesisId": hypothesis_id,
        "location": location
    }
    try:
        with open(log_path, "a") as f:
            f.write(json.dumps(payload) + "\n")
    except (OSError, IOError, PermissionError):
        # Silently fail if logging is not possible (e.g., read-only filesystem)
        pass

def generate_canonical_id(row, source="Excel", entity_id=None):
    """
    Generates a high-fidelity fingerprint for idempotency.
    Identity = source_system + entity_id + doc_type + doc_number + counterparty_id + currency + amount + invoice_date + due_date + line_id
    """
    def clean(val):
        if pd.isna(val) or val is None: return ""
        return str(val).strip().lower()

    # Use existing external ID if explicitly provided (e.g. from Snowflake/ERP)
    if 'external_id' in row and pd.notna(row['external_id']):
        return f"{source}:{entity_id}:{clean(row['external_id'])}"

    # Deterministic fingerprinting components
    components = [
        str(source).upper(),
        str(entity_id or "GLOBAL"),
        clean(row.get('document_type', 'INV')),
        clean(row.get('document_number')),
        clean(row.get('customer') or row.get('counterparty_id', 'UNKNOWN')),
        clean(row.get('currency', 'EUR')),
        f"{float(row.get('amount', 0)):.2f}",
        clean(row.get('document_date') or row.get('invoice_date')),
        clean(row.get('expected_due_date') or row.get('due_date')),
        clean(row.get('line_id', '0')) # For multi-line invoices
    ]
    
    raw_str = "|".join(components)
    cid = hashlib.sha256(raw_str.encode()).hexdigest()
    
    # #region agent log
    debug_log("Generated Deterministic ID", {"cid": cid, "raw": raw_str}, "A", "utils.py:generate_canonical_id")
    # #endregion
    
    return cid

def parse_excel_to_df(file_content, mapping_config=None):
    # Load Excel
    xl = pd.ExcelFile(io.BytesIO(file_content))
    sheet_name = 'Data' if 'Data' in xl.sheet_names else xl.sheet_names[0]
    
    # Read raw with string dtype for ALL columns to prevent ANY automated transformation
    df = xl.parse(sheet_name, dtype=str)
    
    # Standardize column names (strip spaces)
    df.columns = [str(c).strip() for c in df.columns]
    
    print(f"DEBUG: Parsing sheet '{sheet_name}'")
    print(f"DEBUG: Found {len(df)} total rows")
    
    if mapping_config:
        # Use user-provided mapping from UI
        # mapping_config: { "canonical_field": "Source Column Name" }
        inv_mapping = {v: k for k, v in mapping_config.items() if v in df.columns}
        df = df.rename(columns=inv_mapping)
        mapping_diagnostics = {k: "OK" if k in df.columns else "MISSING" for k in mapping_config.keys()}
    else:
        # Default flexible mapping
        col_map = {
            'Project desc': 'project_desc',
            'Project description': 'project_desc',
            'Project': 'project',
            'Project number': 'project',
            'Country': 'country',
            'Customer': 'customer',
            'Customer name': 'customer',
            'Customer number': 'customer',
            'Document Number': 'document_number',
            'Invoice Number': 'document_number',
            'Terms of Payment': 'terms_of_payment',
            'Payment Terms': 'terms_of_payment',
            'Payment Terms (in days)': 'payment_terms_days',
            'Document Date': 'document_date',
            'Invoice Issue Date': 'invoice_issue_date',
            'Invoice Issue Date.1': 'invoice_issue_date_alt',
            'Expected Due Date': 'expected_due_date',
            'Due Date': 'expected_due_date',
            'Payment Date': 'payment_date',
            'Invoice Amount': 'amount',
            'Amount': 'amount',
            'Local Currency': 'currency',
            'Currency': 'currency',
            'Document Type': 'document_type',
            'Special G/L ind.': 'special_gl_ind',
            'Due Year': 'due_year'
        }
        
        mapped_cols = {}
        mapping_diagnostics = {}
        for target_label, internal_name in col_map.items():
            matched = False
            for actual_col in df.columns:
                if actual_col.lower() == target_label.lower():
                    mapped_cols[actual_col] = internal_name
                    mapping_diagnostics[internal_name] = "OK"
                    matched = True
                    break
            if not matched:
                mapping_diagnostics[internal_name] = "MISSING"
        
        df = df.rename(columns=mapped_cols)
    
    print(f"DEBUG: Column Mapping Results: {mapping_diagnostics}")
    
    # Deep clean the key columns - handle scientific notation, decimals, and nulls
    id_cols = ['project', 'country', 'customer', 'document_number', 'terms_of_payment', 'project_desc']
    for col in id_cols:
        if col in df.columns:
            # 1. Convert to string and strip spaces
            df[col] = df[col].astype(str).str.strip()
            # 2. Remove common Excel numeric artifacts like ".0" or scientific "1.23E+4"
            def clean_id_string(val):
                if not val or val.lower() in ['nan', 'none', 'null', '']: return np.nan
                
                # Handle scientific notation: 1.23E+4 -> 12300
                if 'E+' in val.upper() or 'E-' in val.upper():
                    try:
                        val = str(int(float(val)))
                    except:
                        pass
                
                # Remove .0 if it's at the end of a digit string
                if val.endswith('.0'): 
                    val = val[:-2]
                return val
            df[col] = df[col].apply(clean_id_string)

    print(f"DEBUG: Parsing sheet '{sheet_name}'")
    print(f"DEBUG: Found {len(df)} total rows")
    if 'project' in df.columns:
        unique_projs = df['project'].dropna().unique()
        print(f"DEBUG: Final Dataframe Unique Projects ({len(unique_projs)})")
    
    if 'country' in df.columns:
        unique_countries = df['country'].dropna().unique()
        print(f"DEBUG: Final Dataframe Unique Countries ({len(unique_countries)}): {unique_countries}")
    
    # Aggressive Amount Parsing
    if 'amount' in df.columns:
        def clean_amount(val):
            if pd.isna(val): return 0.0
            s = str(val).strip()
            # Handle European format: 1.234,56 -> 1234.56
            if ',' in s and '.' in s:
                if s.find(',') > s.find('.'): # 1.234,56
                    s = s.replace('.', '').replace(',', '.')
                else: # 1,234.56
                    s = s.replace(',', '')
            elif ',' in s and '.' not in s: # 1234,56
                s = s.replace(',', '.')
            # Remove currency symbols and anything not digit, dot, or minus
            s = "".join(c for c in s if c.isdigit() or c in '.-')
            try:
                return float(s)
            except:
                return 0.0
        
        df['amount'] = df['amount'].apply(clean_amount)
    
    # NEW: Forward-fill the key grouping columns to handle merged cells/blank rows
    fill_cols = ['country', 'customer', 'project', 'project_desc']
    for col in fill_cols:
        if col in df.columns:
            # Replace empty strings/nan with real NaN for ffill to work
            df[col] = df[col].replace('', np.nan)
            df[col] = df[col].ffill()

    date_cols = ['document_date', 'invoice_issue_date', 'expected_due_date', 'payment_date']
    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')
            
    # CFO-Grade Health Diagnostics
    total_rows = len(df)
    
    # Identify impossible values
    impossible_amounts = int((df['amount'] < 0).sum()) if 'amount' in df.columns else 0
    # Dates outside 2000-2100 are likely entry errors
    impossible_dates = 0
    if 'expected_due_date' in df.columns:
        valid_dates = df['expected_due_date'].dropna()
        impossible_dates = int(((valid_dates.dt.year < 2000) | (valid_dates.dt.year > 2100)).sum())

    health = {
        "total_invoices": total_rows,
        "completeness": {
            "missing_due_dates": int(df['expected_due_date'].isna().sum()) if 'expected_due_date' in df.columns else total_rows,
            "missing_customers": int(df['customer'].isna().sum()) if 'customer' in df.columns else total_rows,
            "missing_amounts": int((df['amount'] == 0).sum()) if 'amount' in df.columns else total_rows,
            "currency_mix": df['currency'].value_counts().to_dict() if 'currency' in df.columns else {}
        },
        "behavioral_blind_spots": {
            "no_history_customers": 0,
            "regime_shift_risk": int((pd.to_numeric(df['due_year'], errors='coerce') > (datetime.now().year + 1)).sum()) if 'due_year' in df.columns else 0,
            "future_anomaly_dates": int((df['expected_due_date'] > (datetime.now() + timedelta(days=365*2))).sum()) if 'expected_due_date' in df.columns else 0
        },
        "integrity": {
            "duplicate_keys": int(df.duplicated(subset=['document_number', 'customer']).sum()) if 'document_number' in df.columns and 'customer' in df.columns else 0,
            "backdated_invoices": int((df['document_date'] < (datetime.now() - timedelta(days=365))).sum()) if 'document_date' in df.columns else 0,
            "impossible_amounts": impossible_amounts,
            "impossible_dates": impossible_dates,
            "missing_fx": len(df['currency'].unique()) > 1 if 'currency' in df.columns else False
        }
    }
    
    return df, health

def run_forecast_model(db, snapshot_id):
    """
    CFO-Grade Distribution Forecast:
    1. Calculate delay distributions (P25/50/75/90) per segment.
    2. Apply hierarchy fallback with N >= 15 threshold.
    3. Project expected, upside, and downside dates.
    """
    invoices = db.query(models.Invoice).filter(models.Invoice.snapshot_id == snapshot_id).all()
    
    if not invoices:
        print(f"DEBUG: No invoices found for snapshot {snapshot_id}, skipping forecast")
        return
    
    df = pd.DataFrame([inv.__dict__ for inv in invoices])
    
    if '_sa_instance_state' in df.columns:
        df = df.drop(columns=['_sa_instance_state'])

    # Check for required columns
    if 'payment_date' not in df.columns:
        print(f"DEBUG: No payment_date column in snapshot {snapshot_id}, skipping forecast")
        return

    # Historical truth for learning
    paid_df = df[df['payment_date'].notna()].copy()
    if not paid_df.empty:
        # P1 Fix: Only calculate delay_days if we have both payment_date and expected_due_date
        paid_df = paid_df[paid_df['expected_due_date'].notna()].copy()
        if not paid_df.empty:
            paid_df['delay_days'] = (pd.to_datetime(paid_df['payment_date']) - pd.to_datetime(paid_df['expected_due_date'])).dt.days
            paid_df['delay_days'] = paid_df['delay_days'].clip(-30, 180)
            
            # Apply outlier handling (winsorization at P99)
            from forecast_enhancements import enhance_forecast_with_outliers_and_regime
            paid_df, regime_shifts = enhance_forecast_with_outliers_and_regime(paid_df, min_sample_size=15)
        else:
            paid_df = pd.DataFrame()  # No valid paid invoices with due dates
            regime_shifts = {}

    # Hierarchical segments (Full Benchmark Hierarchy)
    hierarchies = [
        ['customer', 'country', 'terms_of_payment'],
        ['customer', 'country'],
        ['customer'],
        ['country', 'terms_of_payment'],
        ['country'],
        [] # Global fallback
    ]

    segments_stats = {}
    MIN_SAMPLE_SIZE = 15

    def get_distribution_stats(data):
        if len(data) < 1: return None
        return {
            'count': len(data),
            'p25': float(np.percentile(data, 25)),
            'p50': float(np.percentile(data, 50)),
            'p75': float(np.percentile(data, 75)),
            'p90': float(np.percentile(data, 90)),
            'std': float(np.std(data))
        }

    # Pre-calculate stats for all hierarchy levels
    for levels in hierarchies:
        seg_name = "+".join(levels) if levels else "Global"
        segments_stats[seg_name] = {}
        
        if not levels:
            if not paid_df.empty and 'delay_days' in paid_df.columns:
                stats = get_distribution_stats(paid_df['delay_days'])
                if stats: segments_stats[seg_name][""] = stats
        else:
            # Only consider segments with enough data
            if not paid_df.empty and 'delay_days' in paid_df.columns:
                grouped = paid_df.groupby(levels)['delay_days']
                for name, group in grouped:
                    if len(group) >= MIN_SAMPLE_SIZE:
                        key = str(name) if len(levels) > 1 else str(name)
                        stats = get_distribution_stats(group)
                        if stats: segments_stats[seg_name][key] = stats

    # Save segment metadata to DB
    for seg_type, keys in segments_stats.items():
        for key, stats in keys.items():
            db.add(models.SegmentDelay(
                snapshot_id=snapshot_id,
                segment_type=seg_type,
                segment_key=key,
                count=stats['count'],
                median_delay=stats['p50'],
                p25_delay=stats['p25'],
                p75_delay=stats['p75'],
                p90_delay=stats['p90'],
                std_delay=stats['std']
            ))
    db.commit()

    # Apply predictions to open invoices
    # CRITICAL: Handle when ALL segments have N < MIN_SAMPLE_SIZE
    # In this case, compute global stats without the N threshold as last resort
    global_baseline = segments_stats.get("Global", {}).get("", None)
    
    # Fallback: If global baseline is None (all segments had N < 15), compute from ALL paid invoices
    if global_baseline is None:
        if not paid_df.empty and 'delay_days' in paid_df.columns:
            all_delays = paid_df['delay_days']
            if len(all_delays) >= 1:
                global_baseline = {
                    'count': len(all_delays),
                    'p25': float(np.percentile(all_delays, 25)) if len(all_delays) >= 1 else 0,
                    'p50': float(np.percentile(all_delays, 50)) if len(all_delays) >= 1 else 0,
                    'p75': float(np.percentile(all_delays, 75)) if len(all_delays) >= 1 else 0,
                    'p90': float(np.percentile(all_delays, 90)) if len(all_delays) >= 1 else 0,
                    'std': float(np.std(all_delays)) if len(all_delays) >= 1 else 0
                }
            else:
                # Absolute fallback: industry default (assume 30-day terms)
                global_baseline = {'count': 0, 'p25': -7, 'p50': 0, 'p75': 14, 'p90': 30, 'std': 15}
        else:
            # No paid invoices at all - use conservative industry default
            global_baseline = {'count': 0, 'p25': -7, 'p50': 0, 'p75': 14, 'p90': 30, 'std': 15}
    
    for inv in invoices:
        if inv.payment_date is not None: continue
        
        chosen_stats = global_baseline
        chosen_seg = "Global (Fallback)" if global_baseline.get('count', 0) < MIN_SAMPLE_SIZE else "Global"
        
        # Traverse hierarchy for best fit
        for levels in hierarchies:
            if not levels: continue
            seg_name = "+".join(levels)
            key_parts = [str(getattr(inv, l, "")).strip() for l in levels]
            key_str = str(tuple(key_parts)) if len(levels) > 1 else key_parts[0]
            
            if key_str in segments_stats.get(seg_name, {}):
                chosen_stats = segments_stats[seg_name][key_str]
                chosen_seg = seg_name
                break
        
        inv.predicted_delay = int(chosen_stats['p50'])
        inv.prediction_segment = chosen_seg
        
        if inv.expected_due_date:
            due = pd.to_datetime(inv.expected_due_date)
            inv.predicted_payment_date = due + timedelta(days=int(chosen_stats['p50']))
            inv.confidence_p25 = due + timedelta(days=int(chosen_stats['p25']))
            inv.confidence_p75 = due + timedelta(days=int(chosen_stats['p75']))
        else:
            # If no due date, set prediction to None (will be in Unknown bucket)
            inv.predicted_payment_date = None
            inv.confidence_p25 = None
            inv.confidence_p75 = None
            
    db.commit()

def get_forecast_aggregation(db, snapshot_id, group_by="week"):
    invoices = db.query(models.Invoice).filter(models.Invoice.snapshot_id == snapshot_id).all()
    
    if not invoices:
        return []

    # Forward-looking forecast
    forecast_invoices = [inv for inv in invoices if inv.payment_date is None]
    if not forecast_invoices:
        return []

    # Weighted Probabilistic Allocation (Benchmark Specification)
    # 20% Upside (P25), 50% Expected (P50), 30% Downside (P75)
    temp_data = []
    for inv in forecast_invoices:
        # P0 Fix: Handle missing FX rates gracefully - skip invoices without rates
        try:
            amt_eur = convert_currency(db, snapshot_id, inv.amount, inv.currency, "EUR", raise_on_missing=True)
        except ValueError:
            # Missing FX rate - this invoice is tracked in Unknown bucket, skip from forecast
            continue
        temp_data.append({
            "amount": amt_eur,
            "target_date": pd.to_datetime(inv.predicted_payment_date),
            "p25_date": pd.to_datetime(inv.confidence_p25),
            "p75_date": pd.to_datetime(inv.confidence_p75)
        })

    forecast_df = pd.DataFrame(temp_data)

    if group_by == "week":
        # Handle empty dataframe (all invoices skipped due to missing FX)
        if forecast_df.empty or 'target_date' not in forecast_df.columns:
            # Return empty weeks structure
            today = datetime.now()
            start_date = today - timedelta(days=today.weekday())
            weeks = [start_date + timedelta(weeks=i) for i in range(14)]
            result = []
            for i in range(13):
                w_start = weeks[i]
                result.append({
                    "label": f"W{i+1} ({w_start.strftime('%m/%d')})",
                    "start_date": w_start.isoformat(),
                    "base": 0.0,
                    "inflow_p50": 0.0
                })
            return result
        
        today = datetime.now()
        first_date = forecast_df[['target_date', 'p25_date', 'p75_date']].min().min()
        
        if pd.notna(first_date) and (today - first_date).days > 28:
            start_date = first_date - timedelta(days=first_date.weekday())
        else:
            start_date = today - timedelta(days=today.weekday())
            
        weeks = [start_date + timedelta(weeks=i) for i in range(14)]
        
        result = []
        for i in range(13):
            w_start = weeks[i]
            w_end = weeks[i+1]
            
            # CFO-Grade Probabilistic Allocation
            # Each invoice contributes to different weeks based on its distribution
            mask_p25 = (forecast_df['p25_date'] >= w_start) & (forecast_df['p25_date'] < w_end)
            mask_p50 = (forecast_df['target_date'] >= w_start) & (forecast_df['target_date'] < w_end)
            mask_p75 = (forecast_df['p75_date'] >= w_start) & (forecast_df['p75_date'] < w_end)
            
            # Weighted Sum: 20% of its amount lands in its P25 week, 50% in P50, 30% in P75
            # Note: This means a single invoice's value can be spread across 1-3 different weeks
            weighted_total = (
                (forecast_df.loc[mask_p25, 'amount'].sum() * 0.2) +
                (forecast_df.loc[mask_p50, 'amount'].sum() * 0.5) +
                (forecast_df.loc[mask_p75, 'amount'].sum() * 0.3)
            )
            
            result.append({
                "label": f"W{i+1} ({w_start.strftime('%m/%d')})",
                "start_date": w_start.isoformat(),
                "base": float(weighted_total),
                "inflow_p50": float(forecast_df.loc[mask_p50, 'amount'].sum()), # For grid detail
                "upside": float(forecast_df.loc[mask_p25, 'amount'].sum()),
                "downside": float(forecast_df.loc[mask_p75, 'amount'].sum())
            })
        return result
    
    elif group_by == "month":
        today = datetime.now()
        result = []
        for i in range(12):
            month_date = (today + pd.DateOffset(months=i))
            m_start = month_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            m_end = (m_start + pd.DateOffset(months=1))
            
            mask = (forecast_df['target_date'] >= m_start) & (forecast_df['target_date'] < m_end)
            
            result.append({
                "label": m_start.strftime('%b %Y'),
                "start_date": m_start.isoformat(),
                "amount": float(forecast_df.loc[mask, 'amount'].sum())
            })
        return result
    
    return []

def apply_scenario_to_forecast(db, snapshot_id, scenario_config):
    # scenario_config: {"global_shock": int, "customer_shocks": {name: int}, "collections_improvement": int}
    invoices = db.query(models.Invoice).filter(models.Invoice.snapshot_id == snapshot_id).all()
    
    forecast_data = []
    global_shock = scenario_config.get("global_shock", 0)
    customer_shocks = scenario_config.get("customer_shocks", {})
    improvement = scenario_config.get("collections_improvement", 0)
    
    today = datetime.now()
    start_of_week = today - timedelta(days=today.weekday())
    weeks = [start_of_week + timedelta(weeks=i) for i in range(14)]
    
    temp_forecast = []
    for inv in invoices:
        if inv.payment_date is not None: continue
        
        base_date = pd.to_datetime(inv.predicted_payment_date)
        if pd.isna(base_date): continue
        
        shock = global_shock + customer_shocks.get(inv.customer, 0) - improvement
        shifted_date = base_date + timedelta(days=shock)
        
        p25_shifted = pd.to_datetime(inv.confidence_p25) + timedelta(days=shock)
        p75_shifted = pd.to_datetime(inv.confidence_p75) + timedelta(days=shock)
        
        temp_forecast.append({
            "amount": inv.amount,
            "target_date": shifted_date,
            "p25_date": p25_shifted,
            "p75_date": p75_shifted
        })
        
    df = pd.DataFrame(temp_forecast)
    if df.empty: return []
    
    result = []
    for i in range(13):
        w_start = weeks[i]
        w_end = weeks[i+1]
        
        mask = (df['target_date'] >= w_start) & (df['target_date'] < w_end)
        mask_p25 = (df['p25_date'] >= w_start) & (df['p25_date'] < w_end)
        mask_p75 = (df['p75_date'] >= w_start) & (df['p75_date'] < w_end)
        
        result.append({
            "label": f"W{i+1} ({w_start.strftime('%m/%d')})",
            "base": float(df.loc[mask, 'amount'].sum()),
            "downside": float(df.loc[mask_p75, 'amount'].sum()),
            "upside": float(df.loc[mask_p25, 'amount'].sum())
        })
    return result

def get_top_movers_logic(db, current_id, previous_id):
    curr_invoices = db.query(models.Invoice).filter(models.Invoice.snapshot_id == current_id).all()
    prev_invoices = db.query(models.Invoice).filter(models.Invoice.snapshot_id == previous_id).all()
    
    # Map by canonical_id
    curr_map = {inv.canonical_id: inv for inv in curr_invoices}
    prev_map = {inv.canonical_id: inv for inv in prev_invoices}
    
    movers = []
    
    for cid, curr_inv in curr_map.items():
        if cid in prev_map:
            prev_inv = prev_map[cid]
            
            # Check for date shifts
            curr_date = curr_inv.predicted_payment_date
            prev_date = prev_inv.predicted_payment_date
            
            if curr_date and prev_date and (curr_date != prev_date):
                shift_days = (curr_date - prev_date).days
                if abs(shift_days) >= 1:
                    movers.append({
                        "invoice_number": curr_inv.document_number,
                        "customer": curr_inv.customer,
                        "amount": curr_inv.amount,
                        "shift_days": shift_days,
                        "reason": f"Behavioral shift: {curr_inv.prediction_segment}" if curr_inv.prediction_segment != prev_inv.prediction_segment else "Updated terms"
                    })

    # Sort by amount to get "Top Movers"
    movers.sort(key=lambda x: abs(x['amount']), reverse=True)
    
    return movers[:10]

def compare_snapshots(db, current_id, previous_id):
    curr_forecast = get_forecast_aggregation(db, current_id, "week")
    prev_forecast = get_forecast_aggregation(db, previous_id, "week")
    
    # Map by label
    prev_map = {item['label']: item['base'] for item in prev_forecast}
    
    comparison = []
    for item in curr_forecast:
        label = item['label']
        curr_val = item['base']
        prev_val = prev_map.get(label, 0)
        comparison.append({
            "label": label,
            "current": curr_val,
            "previous": prev_val,
            "change": curr_val - prev_val
        })
    return comparison

def get_ar_prioritization(db, snapshot_id):
    # Rank invoices by: Amount, Predicted Landing (soon), Lateness Risk (P75-P50)
    invoices = db.query(models.Invoice).filter(models.Invoice.snapshot_id == snapshot_id, models.Invoice.payment_date == None).all()
    
    today = datetime.now()
    four_weeks_later = today + timedelta(weeks=4)
    
    priorities = []
    for inv in invoices:
        if not inv.predicted_payment_date: continue
        
        pred_date = pd.to_datetime(inv.predicted_payment_date)
        
        if pred_date <= four_weeks_later:
            lateness_risk = (pd.to_datetime(inv.confidence_p75) - pd.to_datetime(inv.predicted_payment_date)).days
            
            priorities.append({
                "invoice_number": inv.document_number,
                "customer": inv.customer,
                "amount": inv.amount,
                "predicted_date": inv.predicted_payment_date.isoformat(),
                "lateness_risk_days": lateness_risk,
                "impact_week": ((pred_date - (today - timedelta(days=today.weekday()))).days // 7) + 1
            })
            
    priorities.sort(key=lambda x: x['amount'], reverse=True)
    return priorities[:20]

def predict_dispute_risk(db, snapshot_id):
    # Fetch all open invoices
    invoices = db.query(models.Invoice).filter(models.Invoice.snapshot_id == snapshot_id, models.Invoice.payment_date == None).all()
    
    # 1. Identify segments with high blockage history
    # (In real app, we'd query historical blocked invoices)
    
    risk_flags = []
    for inv in invoices:
        # Heuristic rules for risk flagging
        risk_score = 0
        reasons = []
        
        # Rule 1: Large amount + missing PO indicator in description
        if inv.amount > 50000 and (not inv.project_desc or 'PO' not in inv.project_desc.upper()):
            risk_score += 30
            reasons.append("High value + Missing PO pattern")
            
        # Rule 2: Country risk (e.g. certain countries have higher approval delays)
        # (Example: assume Germany O11 projects often have pricing mismatches)
        if inv.country == 'Germany' and inv.project == 'O11':
            risk_score += 20
            reasons.append("Project O11 specific approval friction")
            
        if risk_score > 0:
            risk_flags.append({
                "invoice_number": inv.document_number,
                "customer": inv.customer,
                "amount": inv.amount,
                "predicted_date": inv.predicted_payment_date.isoformat() if inv.predicted_payment_date else None,
                "risk_score": risk_score,
                "potential_blockage_reasons": reasons
            })
            
    return sorted(risk_flags, key=lambda x: x['risk_score'], reverse=True)

def get_fx_exposure(db, snapshot_id):
    # Group open invoices by currency
    invoices = db.query(models.Invoice).filter(models.Invoice.snapshot_id == snapshot_id, models.Invoice.payment_date == None).all()
    
    exposure = {}
    for inv in invoices:
        currency = inv.currency or "EUR"
        if currency not in exposure:
            exposure[currency] = {"amount": 0, "count": 0}
        exposure[currency]["amount"] += inv.amount
        exposure[currency]["count"] += 1
        
    # Calculate implied risk (simplistic EUR baseline)
    baseline_currency = "EUR"
    result = []
    for curr, data in exposure.items():
        # Example volatility weights
        volatility = 0.05 if curr != baseline_currency else 0.0
        result.append({
            "currency": curr,
            "total_amount": data["amount"],
            "invoice_count": data["count"],
            "implied_fx_risk": data["amount"] * volatility
        })
        
    return result

def record_audit_log(db: models.Session, user: str, action: str, resource_type: str, resource_id: int = None, changes: dict = None):
    """
    Records a high-level audit trail for CFO sign-offs and overrides.
    """
    log = models.AuditLog(
        user=user,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        changes=changes
    )
    db.add(log)
    db.commit()

def get_snapshot_fx_rate(db, snapshot_id, from_curr, to_curr, raise_on_missing=False):
    """
    Fetches the FX rate locked for this specific snapshot.
    
    P0 Fix: Explicit handling of missing FX rates to prevent silent errors.
    
    Args:
        raise_on_missing: If True, raises ValueError when rate not found. 
                         If False, returns None (caller must handle).
    """
    if not from_curr or not to_curr: 
        if raise_on_missing:
            raise ValueError(f"Invalid currency pair: {from_curr} -> {to_curr}")
        return None
    
    from_curr = from_curr.upper()
    to_curr = to_curr.upper()
    
    if from_curr == to_curr:
        return 1.0
        
    rate = db.query(models.WeeklyFXRate).filter(
        models.WeeklyFXRate.snapshot_id == snapshot_id,
        models.WeeklyFXRate.from_currency == from_curr,
        models.WeeklyFXRate.to_currency == to_curr
    ).first()
    
    if rate:
        return rate.rate
    
    # Fallback to inverse if available
    inv_rate = db.query(models.WeeklyFXRate).filter(
        models.WeeklyFXRate.snapshot_id == snapshot_id,
        models.WeeklyFXRate.from_currency == to_curr,
        models.WeeklyFXRate.to_currency == from_curr
    ).first()
    
    if inv_rate and inv_rate.rate > 0:
        return 1.0 / inv_rate.rate
    
    # P0 Fix: Explicit handling instead of silent fallback
    if raise_on_missing:
        raise ValueError(
            f"FX rate not found: {from_curr} -> {to_curr} for snapshot {snapshot_id}. "
            f"Please set FX rates via /snapshots/{snapshot_id}/fx-rates endpoint."
        )
    
    return None  # Explicit None instead of silent 1.0 fallback

def calculate_forecast_accuracy(db, snapshot_id):
    """
    Backtesting Engine:
    Compares prior forecast to actual bank receipt dates.
    Calculates MAE, Bias, and P75 Calibration.
    """
    invoices = db.query(models.Invoice).filter(models.Invoice.snapshot_id == snapshot_id).all()
    
    # Only consider invoices that have both a prediction and a real payment date
    valid_data = []
    for inv in invoices:
        if inv.payment_date and inv.predicted_payment_date:
            actual = pd.to_datetime(inv.payment_date)
            predicted = pd.to_datetime(inv.predicted_payment_date)
            p25 = pd.to_datetime(inv.confidence_p25)
            p75 = pd.to_datetime(inv.confidence_p75)
            
            error = (actual - predicted).days
            valid_data.append({
                "error": error,
                "abs_error": abs(error),
                "in_range": p25 <= actual <= p75
            })
            
    if not valid_data:
        return {"mae": 0, "bias": 0, "confidence_calibration": 0, "n": 0}
        
    df = pd.DataFrame(valid_data)
    return {
        "mae": float(df['abs_error'].mean()),
        "bias": float(df['error'].mean()), # Negative means pessimistic, positive means optimistic
        "confidence_calibration": float(df['in_range'].mean()), # % of items landing in P25-P75
        "n": len(df)
    }

def convert_currency(db, snapshot_id, amount, from_curr, to_curr="EUR", raise_on_missing=True):
    """
    Converts an amount based on snapshot-locked FX rates.
    
    P0 Fix: Explicit error handling for missing FX rates to prevent incorrect forecasts.
    
    Args:
        raise_on_missing: If True, raises ValueError when FX rate is missing.
                         If False, returns None to indicate conversion failed.
    """
    if from_curr == to_curr:
        return amount
    
    rate = get_snapshot_fx_rate(db, snapshot_id, from_curr, to_curr, raise_on_missing=raise_on_missing)
    
    if rate is None:
        if raise_on_missing:
            raise ValueError(
                f"Cannot convert {amount} {from_curr} to {to_curr}: FX rate not found for snapshot {snapshot_id}. "
                f"This invoice will be tracked in the Unknown bucket."
            )
        return None  # Explicit failure indicator
    
    return amount * rate

def detect_intercompany_washes_logic(db, snapshot_id):
    # Detect invoices where customer name matches another entity name
    entities = db.query(models.Entity).all()
    entity_names = [e.name.lower() for e in entities]
    
    invoices = db.query(models.Invoice).filter(models.Invoice.snapshot_id == snapshot_id).all()
    
    intercompany = []
    for inv in invoices:
        if inv.customer and inv.customer.lower() in entity_names:
            intercompany.append({
                "invoice_number": inv.document_number,
                "from_entity": inv.entity.name if inv.entity else "Source",
                "to_entity": inv.customer,
                "amount": inv.amount,
                "currency": inv.currency
            })
            
    return intercompany

def calculate_unknown_bucket(db, snapshot_id):
    """
    CFO Trust Feature: Explicitly tracks items that cannot be forecasted confidently.
    Categories:
    - Missing due dates
    - Held AP bills
    - Unmatched bank cash
    - Missing FX rates for non-EUR invoices
    
    Returns: {
        total_unknown_amount: float,
        total_unknown_count: int,
        unknown_pct: float,  # % of total portfolio
        categories: { ... },
        kpi_target_met: bool  # <5% unknown
    }
    """
    snapshot = db.query(models.Snapshot).filter(models.Snapshot.id == snapshot_id).first()
    if not snapshot:
        return {"total_unknown_amount": 0, "total_unknown_count": 0, "unknown_pct": 0, "categories": {}, "kpi_target_met": True}
    
    # 1. Invoices with missing due dates
    invoices = db.query(models.Invoice).filter(models.Invoice.snapshot_id == snapshot_id).all()
    missing_due_dates = [inv for inv in invoices if inv.expected_due_date is None and inv.payment_date is None]
    missing_due_amount = sum(inv.amount for inv in missing_due_dates)
    
    # 2. Held AP bills (not forecastable until released)
    vendor_bills = db.query(models.VendorBill).filter(models.VendorBill.snapshot_id == snapshot_id).all()
    held_bills = [b for b in vendor_bills if b.hold_status == 1]
    held_bills_amount = sum(b.amount for b in held_bills)
    
    # 3. Unmatched bank cash (unexplained movements)
    unmatched_txns = []
    unmatched_amount = 0.0
    if snapshot.entity_id:
        bank_accounts = db.query(models.BankAccount).filter(models.BankAccount.entity_id == snapshot.entity_id).all()
        for acct in bank_accounts:
            unmatched = db.query(models.BankTransaction).filter(
                models.BankTransaction.bank_account_id == acct.id,
                models.BankTransaction.is_reconciled == 0
            ).all()
            unmatched_txns.extend(unmatched)
            unmatched_amount += sum(abs(t.amount) for t in unmatched)
    
    # 4. Non-EUR invoices without FX rates
    fx_rates = db.query(models.WeeklyFXRate).filter(models.WeeklyFXRate.snapshot_id == snapshot_id).all()
    fx_pairs = {(r.from_currency, r.to_currency) for r in fx_rates}
    
    missing_fx = []
    for inv in invoices:
        if inv.currency and inv.currency != "EUR":
            if (inv.currency, "EUR") not in fx_pairs and ("EUR", inv.currency) not in fx_pairs:
                missing_fx.append(inv)
    missing_fx_amount = sum(inv.amount for inv in missing_fx)
    
    # Calculate totals
    total_unknown_count = len(missing_due_dates) + len(held_bills) + len(unmatched_txns) + len(missing_fx)
    total_unknown_amount = missing_due_amount + held_bills_amount + unmatched_amount + missing_fx_amount
    
    # Calculate portfolio total for percentage
    total_portfolio = sum(inv.amount for inv in invoices if inv.payment_date is None) + sum(b.amount for b in vendor_bills)
    unknown_pct = (total_unknown_amount / total_portfolio * 100) if total_portfolio > 0 else 0.0
    
    return {
        "total_unknown_amount": float(total_unknown_amount),
        "total_unknown_count": total_unknown_count,
        "unknown_pct": round(unknown_pct, 2),
        "kpi_target_met": unknown_pct < 5.0,
        "categories": {
            "missing_due_dates": {
                "count": len(missing_due_dates),
                "amount": float(missing_due_amount),
                "items": [{"id": inv.id, "customer": inv.customer, "amount": inv.amount} for inv in missing_due_dates[:10]]
            },
            "held_ap_bills": {
                "count": len(held_bills),
                "amount": float(held_bills_amount),
                "items": [{"id": b.id, "vendor": b.vendor_name, "amount": b.amount} for b in held_bills[:10]]
            },
            "unmatched_bank_cash": {
                "count": len(unmatched_txns),
                "amount": float(unmatched_amount),
                "items": [{"id": t.id, "counterparty": t.counterparty, "amount": t.amount} for t in unmatched_txns[:10]]
            },
            "missing_fx_rates": {
                "count": len(missing_fx),
                "amount": float(missing_fx_amount),
                "currencies": list(set(inv.currency for inv in missing_fx))
            }
        }
    }

    inv_rate = db.query(models.WeeklyFXRate).filter(
        models.WeeklyFXRate.snapshot_id == snapshot_id,
        models.WeeklyFXRate.from_currency == to_curr,
        models.WeeklyFXRate.to_currency == from_curr
    ).first()
    
    if inv_rate and inv_rate.rate > 0:
        return 1.0 / inv_rate.rate
        
    return 1.0 # Default fallback

def calculate_forecast_accuracy(db, snapshot_id):
    """
    Backtesting Engine:
    Compares prior forecast to actual bank receipt dates.
    Calculates MAE, Bias, and P75 Calibration.
    """
    invoices = db.query(models.Invoice).filter(models.Invoice.snapshot_id == snapshot_id).all()
    
    # Only consider invoices that have both a prediction and a real payment date
    valid_data = []
    for inv in invoices:
        if inv.payment_date and inv.predicted_payment_date:
            actual = pd.to_datetime(inv.payment_date)
            predicted = pd.to_datetime(inv.predicted_payment_date)
            p25 = pd.to_datetime(inv.confidence_p25)
            p75 = pd.to_datetime(inv.confidence_p75)
            
            error = (actual - predicted).days
            valid_data.append({
                "error": error,
                "abs_error": abs(error),
                "in_range": p25 <= actual <= p75
            })
            
    if not valid_data:
        return {"mae": 0, "bias": 0, "confidence_calibration": 0, "n": 0}
        
    df = pd.DataFrame(valid_data)
    return {
        "mae": float(df['abs_error'].mean()),
        "bias": float(df['error'].mean()), # Negative means pessimistic, positive means optimistic
        "confidence_calibration": float(df['in_range'].mean()), # % of items landing in P25-P75
        "n": len(df)
    }

def convert_currency(db, snapshot_id, amount, from_curr, to_curr="EUR", raise_on_missing=True):
    """
    Converts an amount based on snapshot-locked FX rates.
    
    P0 Fix: Explicit error handling for missing FX rates to prevent incorrect forecasts.
    
    Args:
        raise_on_missing: If True, raises ValueError when FX rate is missing.
                         If False, returns None to indicate conversion failed.
    """
    if from_curr == to_curr:
        return amount
    
    rate = get_snapshot_fx_rate(db, snapshot_id, from_curr, to_curr, raise_on_missing=raise_on_missing)
    
    if rate is None:
        if raise_on_missing:
            raise ValueError(
                f"Cannot convert {amount} {from_curr} to {to_curr}: FX rate not found for snapshot {snapshot_id}. "
                f"This invoice will be tracked in the Unknown bucket."
            )
        return None  # Explicit failure indicator
    
    return amount * rate

def detect_intercompany_washes_logic(db, snapshot_id):
    # Detect invoices where customer name matches another entity name
    entities = db.query(models.Entity).all()
    entity_names = [e.name.lower() for e in entities]
    
    invoices = db.query(models.Invoice).filter(models.Invoice.snapshot_id == snapshot_id).all()
    
    intercompany = []
    for inv in invoices:
        if inv.customer and inv.customer.lower() in entity_names:
            intercompany.append({
                "invoice_number": inv.document_number,
                "from_entity": inv.entity.name if inv.entity else "Source",
                "to_entity": inv.customer,
                "amount": inv.amount,
                "currency": inv.currency
            })
            
    return intercompany

def calculate_unknown_bucket(db, snapshot_id):
    """
    CFO Trust Feature: Explicitly tracks items that cannot be forecasted confidently.
    Categories:
    - Missing due dates
    - Held AP bills
    - Unmatched bank cash
    - Missing FX rates for non-EUR invoices
    
    Returns: {
        total_unknown_amount: float,
        total_unknown_count: int,
        unknown_pct: float,  # % of total portfolio
        categories: { ... },
        kpi_target_met: bool  # <5% unknown
    }
    """
    snapshot = db.query(models.Snapshot).filter(models.Snapshot.id == snapshot_id).first()
    if not snapshot:
        return {"total_unknown_amount": 0, "total_unknown_count": 0, "unknown_pct": 0, "categories": {}, "kpi_target_met": True}
    
    # 1. Invoices with missing due dates
    invoices = db.query(models.Invoice).filter(models.Invoice.snapshot_id == snapshot_id).all()
    missing_due_dates = [inv for inv in invoices if inv.expected_due_date is None and inv.payment_date is None]
    missing_due_amount = sum(inv.amount for inv in missing_due_dates)
    
    # 2. Held AP bills (not forecastable until released)
    vendor_bills = db.query(models.VendorBill).filter(models.VendorBill.snapshot_id == snapshot_id).all()
    held_bills = [b for b in vendor_bills if b.hold_status == 1]
    held_bills_amount = sum(b.amount for b in held_bills)
    
    # 3. Unmatched bank cash (unexplained movements)
    unmatched_txns = []
    unmatched_amount = 0.0
    if snapshot.entity_id:
        bank_accounts = db.query(models.BankAccount).filter(models.BankAccount.entity_id == snapshot.entity_id).all()
        for acct in bank_accounts:
            unmatched = db.query(models.BankTransaction).filter(
                models.BankTransaction.bank_account_id == acct.id,
                models.BankTransaction.is_reconciled == 0
            ).all()
            unmatched_txns.extend(unmatched)
            unmatched_amount += sum(abs(t.amount) for t in unmatched)
    
    # 4. Non-EUR invoices without FX rates
    fx_rates = db.query(models.WeeklyFXRate).filter(models.WeeklyFXRate.snapshot_id == snapshot_id).all()
    fx_pairs = {(r.from_currency, r.to_currency) for r in fx_rates}
    
    missing_fx = []
    for inv in invoices:
        if inv.currency and inv.currency != "EUR":
            if (inv.currency, "EUR") not in fx_pairs and ("EUR", inv.currency) not in fx_pairs:
                missing_fx.append(inv)
    missing_fx_amount = sum(inv.amount for inv in missing_fx)
    
    # Calculate totals
    total_unknown_count = len(missing_due_dates) + len(held_bills) + len(unmatched_txns) + len(missing_fx)
    total_unknown_amount = missing_due_amount + held_bills_amount + unmatched_amount + missing_fx_amount
    
    # Calculate portfolio total for percentage
    total_portfolio = sum(inv.amount for inv in invoices if inv.payment_date is None) + sum(b.amount for b in vendor_bills)
    unknown_pct = (total_unknown_amount / total_portfolio * 100) if total_portfolio > 0 else 0.0
    
    return {
        "total_unknown_amount": float(total_unknown_amount),
        "total_unknown_count": total_unknown_count,
        "unknown_pct": round(unknown_pct, 2),
        "kpi_target_met": unknown_pct < 5.0,
        "categories": {
            "missing_due_dates": {
                "count": len(missing_due_dates),
                "amount": float(missing_due_amount),
                "items": [{"id": inv.id, "customer": inv.customer, "amount": inv.amount} for inv in missing_due_dates[:10]]
            },
            "held_ap_bills": {
                "count": len(held_bills),
                "amount": float(held_bills_amount),
                "items": [{"id": b.id, "vendor": b.vendor_name, "amount": b.amount} for b in held_bills[:10]]
            },
            "unmatched_bank_cash": {
                "count": len(unmatched_txns),
                "amount": float(unmatched_amount),
                "items": [{"id": t.id, "counterparty": t.counterparty, "amount": t.amount} for t in unmatched_txns[:10]]
            },
            "missing_fx_rates": {
                "count": len(missing_fx),
                "amount": float(missing_fx_amount),
                "currencies": list(set(inv.currency for inv in missing_fx))
            }
        }
    }
