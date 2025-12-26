import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import models
import io
import hashlib
import json
import os

def debug_log(message, data=None, hypothesis_id=None, location=None):
    log_path = r"c:\Users\AYUSH\OneDrive\Gitto\.cursor\debug.log"
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
    except:
        pass

def generate_canonical_id(row, source="Excel", entity_id=None):
    """
    Generates a rich fingerprint for idempotency.
    """
    # #region agent log
    debug_log("Generating Canonical ID", {"source": source, "entity_id": entity_id}, "A", "utils.py:generate_canonical_id")
    # #endregion
    def clean(val):
        if pd.isna(val) or val is None: return ""
        return str(val).strip().lower()

    if 'external_id' in row and pd.notna(row['external_id']):
        return f"{source}:{entity_id}:{clean(row['external_id'])}"

    components = [
        str(source),
        str(entity_id or "GLOBAL"),
        clean(row.get('document_number')),
        clean(row.get('document_type', 'INV')),
        clean(row.get('document_date')),
        clean(row.get('expected_due_date')),
        clean(row.get('currency', 'EUR')),
        f"{float(row.get('amount', 0)):.2f}",
        clean(row.get('customer', 'UNKNOWN'))
    ]
    
    raw_str = "|".join(components)
    cid = hashlib.sha256(raw_str.encode()).hexdigest()
    # #region agent log
    debug_log("Generated ID", {"cid": cid, "raw": raw_str}, "A", "utils.py:generate_canonical_id")
    # #endregion
    return cid

def parse_excel_to_df(file_content):
    # Load Excel
    xl = pd.ExcelFile(io.BytesIO(file_content))
    sheet_name = 'Data' if 'Data' in xl.sheet_names else xl.sheet_names[0]
    
    # Read raw with string dtype for ALL columns to prevent ANY automated transformation
    df = xl.parse(sheet_name, dtype=str)
    
    # Standardize column names (strip spaces)
    df.columns = [str(c).strip() for c in df.columns]
    
    print(f"DEBUG: Parsing sheet '{sheet_name}'")
    print(f"DEBUG: Found {len(df)} total rows")
    
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
    
    # Flexible mapping
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
            
    health = {
        "total_invoices": len(df),
        "paid_invoices": int(df['payment_date'].notna().sum()) if 'payment_date' in df.columns else 0,
        "open_invoices": int(df['payment_date'].isna().sum()) if 'payment_date' in df.columns else len(df),
        "missing_due_dates": int(df['expected_due_date'].isna().sum()),
        "weird_due_years": int((pd.to_numeric(df['due_year'], errors='coerce') > 2030).sum()) if 'due_year' in df.columns else 0
    }
    
    return df, health

def run_forecast_model(db, snapshot_id):
    # Load all invoices for this snapshot
    invoices = db.query(models.Invoice).filter(models.Invoice.snapshot_id == snapshot_id).all()
    df = pd.DataFrame([inv.__dict__ for inv in invoices])
    
    # Drop SQLAlchemy internal state
    if '_sa_instance_state' in df.columns:
        df = df.drop(columns=['_sa_instance_state'])

    # Separate paid and open
    paid_df = df[df['payment_date'].notna()].copy()
    open_df = df[df['payment_date'].isna()].copy()

    if paid_df.empty:
        # If no history, we can't do behavioral modeling, fall back to global 0
        global_median = 0
        global_p25 = 0
        global_p75 = 0
    else:
        # Calculate delay_days
        paid_df['delay_days'] = (paid_df['payment_date'] - paid_df['expected_due_date']).dt.days
        # Winsorize/Cap delays [-30, 180]
        paid_df['delay_days'] = paid_df['delay_days'].clip(-30, 180)

    # Define segments hierarchy
    hierarchies = [
        ['customer', 'country', 'terms_of_payment'],
        ['customer', 'country'],
        ['customer'],
        ['country', 'terms_of_payment'],
        ['country'],
        [] # Global
    ]

    segments_stats = {}

    def get_stats(data):
        if len(data) == 0: return None
        return {
            'count': len(data),
            'p25': float(data.quantile(0.25)),
            'p50': float(data.quantile(0.50)),
            'p75': float(data.quantile(0.75)),
            'p90': float(data.quantile(0.90)),
            'std': float(data.std()) if len(data) > 1 else 0
        }

    # Pre-calculate all segment stats from paid data
    for levels in hierarchies:
        seg_name = "+".join(levels) if levels else "Global"
        if not levels:
            stats = get_stats(paid_df['delay_days'])
            if stats:
                segments_stats[seg_name] = {"": stats}
        else:
            grouped = paid_df.groupby(levels)['delay_days']
            segments_stats[seg_name] = {}
            for name, group in grouped:
                key = str(name) if len(levels) > 1 else str(name)
                stats = get_stats(group)
                if stats:
                    segments_stats[seg_name][key] = stats

    # Save segments to DB
    for seg_type, keys in segments_stats.items():
        for key, stats in keys.items():
            db_seg = models.SegmentDelay(
                snapshot_id=snapshot_id,
                segment_type=seg_type,
                segment_key=key,
                count=stats['count'],
                median_delay=stats['p50'],
                p25_delay=stats['p25'],
                p75_delay=stats['p75'],
                p90_delay=stats['p90'],
                std_delay=stats['std']
            )
            db.add(db_seg)
    db.commit()

    # Predict for open invoices
    for inv in invoices:
        if inv.payment_date is not None:
            continue
        
        # Apply hierarchy
        pred_delay = 0
        chosen_seg = "Global"
        stats = segments_stats.get("Global", {}).get("", {"p25": 0, "p50": 0, "p75": 0})
        
        for levels in hierarchies:
            if not levels: continue
            seg_name = "+".join(levels)
            key = []
            for l in levels:
                val = getattr(inv, l, "")
                key.append(val)
            key_str = str(tuple(key)) if len(levels) > 1 else str(key[0])
            
            if key_str in segments_stats.get(seg_name, {}):
                stats = segments_stats[seg_name][key_str]
                chosen_seg = seg_name
                break
        
        inv.predicted_delay = int(stats['p50'])
        inv.prediction_segment = chosen_seg
        if inv.expected_due_date:
            inv.predicted_payment_date = inv.expected_due_date + timedelta(days=inv.predicted_delay)
            inv.confidence_p25 = inv.expected_due_date + timedelta(days=stats['p25'])
            inv.confidence_p75 = inv.expected_due_date + timedelta(days=stats['p75'])

    db.commit()

def get_forecast_aggregation(db, snapshot_id, group_by="week"):
    invoices = db.query(models.Invoice).filter(models.Invoice.snapshot_id == snapshot_id).all()
    
    if not invoices:
        return []

    # Forward-looking forecast
    forecast_invoices = [inv for inv in invoices if inv.payment_date is None]
    if not forecast_invoices:
        return []

    # Convert all to EUR first
    temp_data = []
    for inv in forecast_invoices:
        amt_eur = convert_currency(db, snapshot_id, inv.amount, inv.currency, "EUR")
        temp_data.append({
            "amount": amt_eur,
            "target_date": pd.to_datetime(inv.predicted_payment_date),
            "p25_date": pd.to_datetime(inv.confidence_p25),
            "p75_date": pd.to_datetime(inv.confidence_p75)
        })

    forecast_df = pd.DataFrame(temp_data)

    if group_by == "week":
        # Adaptive timeline: Start from today, or if data is historical, start from the first predicted date
        today = datetime.now()
        first_date = forecast_df['target_date'].min()
        
        # If the earliest data point is more than 4 weeks in the past, center the chart on the data
        if pd.notna(first_date) and (today - first_date).days > 28:
            start_date = first_date - timedelta(days=first_date.weekday())
        else:
            start_date = today - timedelta(days=today.weekday())
            
        weeks = [start_date + timedelta(weeks=i) for i in range(14)]
        
        result = []
        for i in range(13):
            w_start = weeks[i]
            w_end = weeks[i+1]
            
            mask = (forecast_df['target_date'] >= w_start) & (forecast_df['target_date'] < w_end)
            mask_p25 = (forecast_df['p25_date'] >= w_start) & (forecast_df['p25_date'] < w_end)
            mask_p75 = (forecast_df['p75_date'] >= w_start) & (forecast_df['p75_date'] < w_end)
            
            result.append({
                "label": f"W{i+1} ({w_start.strftime('%m/%d')})",
                "start_date": w_start.isoformat(),
                "base": float(forecast_df.loc[mask, 'amount'].sum()),
                "downside": float(forecast_df.loc[mask_p75, 'amount'].sum()),
                "upside": float(forecast_df.loc[mask_p25, 'amount'].sum())
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

def get_snapshot_fx_rate(db, snapshot_id, from_curr, to_curr):
    """
    Fetches the FX rate locked for this specific snapshot.
    """
    if not from_curr or not to_curr: return 1.0
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
        
    return 1.0 # Default fallback

def convert_currency(db, snapshot_id, amount, from_curr, to_curr="EUR"):
    """
    Converts an amount based on snapshot-locked FX rates.
    """
    if from_curr == to_curr:
        return amount
    
    rate = get_snapshot_fx_rate(db, snapshot_id, from_curr, to_curr)
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
