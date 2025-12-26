import models
from sqlalchemy.orm import Session
from utils import debug_log, convert_currency
import datetime
from dateutil.relativedelta import relativedelta
import pandas as pd

def project_recurring_outflows(db: Session, entity_id: int, snapshot_id: int):
    """
    Takes all recurring outflows for an entity and projects them into OutflowItem 
    entries for the next 13 weeks in a snapshot.
    """
    recurring = db.query(models.RecurringOutflow).filter(models.RecurringOutflow.entity_id == entity_id).all()
    
    # Define the 13-week window starting from now
    today = datetime.datetime.now()
    end_date = today + datetime.timedelta(weeks=14) # A bit extra to ensure coverage
    
    outflows_to_create = []
    
    for rec in recurring:
        current = today
        
        while current < end_date:
            target_date = None
            
            if rec.frequency == "Weekly":
                # Find next occurrence of day_of_week
                days_ahead = (rec.day_of_week - current.weekday()) % 7
                target_date = current + datetime.timedelta(days=days_ahead)
                current = target_date + datetime.timedelta(days=1)
                
            elif rec.frequency == "Monthly":
                if rec.is_last_day:
                    # Last day of current month
                    target_date = (current + relativedelta(day=31))
                else:
                    # Specific day of month
                    try:
                        target_date = current.replace(day=rec.day_of_month)
                    except ValueError:
                        # Month doesn't have that many days, use last day
                        target_date = (current + relativedelta(day=31))
                
                # If target date is in the past for this month, move to next month
                if target_date < current:
                    target_date = target_date + relativedelta(months=1)
                
                current = target_date + relativedelta(days=1)

            if target_date and target_date < end_date:
                # Create OutflowItem
                item = models.OutflowItem(
                    snapshot_id=snapshot_id,
                    entity_id=entity_id,
                    category=rec.category,
                    description=rec.description,
                    amount=rec.amount,
                    currency=rec.currency,
                    expected_date=target_date,
                    is_discretionary=rec.is_discretionary,
                    source="Calendar",
                    status="Planned"
                )
                outflows_to_create.append(item)
            else:
                break
                
    if outflows_to_create:
        db.bulk_save_objects(outflows_to_create)
        db.commit()
    
    return len(outflows_to_create)

def get_outflow_summary(db: Session, snapshot_id: int):
    """
    Aggregates both OutflowItems (Templates) and VendorBills (Actuals) 
    by week for the 13-week view, applying precedence and timing rules.
    """
    snapshot = db.query(models.Snapshot).filter(models.Snapshot.id == snapshot_id).first()
    entity = snapshot.entity if snapshot else None
    
    # #region agent log
    debug_log("Outflow Summary Start", {"snapshot_id": snapshot_id, "entity_found": entity is not None}, "B", "cash_calendar_service.py:get_outflow_summary")
    # #endregion
    
    payment_run_day = entity.payment_run_day if entity else 3 # Default Thu
    
    # 1. Fetch Template-generated items
    outflow_items = db.query(models.OutflowItem).filter(models.OutflowItem.snapshot_id == snapshot_id).all()
    
    # 2. Fetch Actual Vendor Bills
    vendor_bills = db.query(models.VendorBill).filter(models.VendorBill.snapshot_id == snapshot_id).all()
    
    # 3. Apply Timing Logic to Vendor Bills
    bill_data = []
    actual_categories_by_week = {} # To track where actuals exist for gap-filling
    
    today = datetime.datetime.now().date()
    
    for bill in vendor_bills:
        if bill.hold_status:
            continue # Exclude from forecast, effectively move to "Held" bucket
            
        # Convert to reporting currency (EUR)
        amount_eur = convert_currency(db, snapshot_id, bill.amount, bill.currency, "EUR")

        # Determine Cash Out Date
        if bill.scheduled_payment_date:
            cash_out_date = bill.scheduled_payment_date.date()
        else:
            # Payment Run Logic
            base_date = bill.due_date.date() if bill.due_date else today
            if bill.approval_date and bill.approval_date.date() > base_date:
                base_date = bill.approval_date.date()
            
            # Find next payment run day after base_date
            days_until_run = (payment_run_day - base_date.weekday()) % 7
            cash_out_date = base_date + datetime.timedelta(days=days_until_run)
            
        week_start = cash_out_date - datetime.timedelta(days=cash_out_date.weekday())
        
        bill_data.append({
            "week_start": week_start,
            "category": bill.category,
            "amount": amount_eur
        })
        
        # Track that we have actuals for this category in this week
        cat_key = (week_start, bill.category)
        actual_categories_by_week[cat_key] = True

    # 4. Filter Templates (Gap-Filling Rule)
    # Rule: If actual bills exist for a category in a week, don't use templates for that category in that week.
    template_data = []
    for item in outflow_items:
        week_start = item.expected_date.date() - datetime.timedelta(days=item.expected_date.weekday())
        if (week_start, item.category) in actual_categories_by_week:
            continue # Precedence to actual VendorBills
        
        # Convert to reporting currency (EUR)
        amount_eur = convert_currency(db, snapshot_id, item.amount, item.currency, "EUR")

        template_data.append({
            "week_start": week_start,
            "category": item.category,
            "amount": amount_eur
        })
    
    # Combined Data
    all_data = bill_data + template_data
    if not all_data:
        return {}
        
    df = pd.DataFrame(all_data)
    
    # Priority sorting for categories
    # Payroll and Taxes should always be visible/prioritized in the summary
    summary = df.groupby(['week_start', 'category'])['amount'].sum().unstack(fill_value=0).to_dict('index')
    
    # Ensure key categories are at least present in keys if we want to force them (optional)
    return summary

def get_13_week_workspace(db: Session, snapshot_id: int):
    snapshot = db.query(models.Snapshot).filter(models.Snapshot.id == snapshot_id).first()
    if not snapshot:
        return None
    
    # 1. Setup Timeframe (Adaptive)
    from utils import get_forecast_aggregation
    inflow_data = get_forecast_aggregation(db, snapshot_id, group_by="week")
    
    if not inflow_data:
        today = datetime.datetime.now().date()
        start_of_week = today - datetime.timedelta(days=today.weekday())
    else:
        # Use the start date from the first week of the ACTUAL forecast results
        # This ensures the grid matches the chart
        start_of_week = datetime.datetime.fromisoformat(inflow_data[0]['start_date']).date()

    weeks = [(start_of_week + datetime.timedelta(weeks=i)) for i in range(14)]
    
    # 2. Map Inflows by their start date string to avoid TZ/Format mismatches
    inflow_map = {item['start_date'].split('T')[0]: item['base'] for item in inflow_data}
    
    # 3. Get Outflows (Categorized)
    outflow_map = get_outflow_summary(db, snapshot_id)
    
    # 4. Opening Balance
    opening_balance = snapshot.opening_bank_balance
    min_threshold = snapshot.min_cash_threshold
    
    grid = []
    current_cash = opening_balance
    
    for i in range(13):
        w_start = weeks[i]
        w_start_str = w_start.isoformat()
        
        inflow = inflow_map.get(w_start_str, 0.0)
        
        # Breakdown outflows
        outflows_cat = outflow_map.get(w_start, {})
        total_outflow = sum(outflows_cat.values())
        
        net_change = inflow - total_outflow
        closing_cash = current_cash + net_change
        
        grid.append({
            "week_label": f"W{i+1}",
            "start_date": w_start_str,
            "opening_cash": current_cash,
            "inflows": inflow,
            "outflows": total_outflow,
            "outflow_details": outflows_cat,
            "net_change": net_change,
            "closing_cash": closing_cash,
            "is_red": closing_cash < min_threshold
        })
        
        current_cash = closing_cash
        
    # 5. Risks & Drivers
    from utils import predict_dispute_risk
    top_risks = predict_dispute_risk(db, snapshot_id)
    
    return {
        "summary": {
            "opening_cash": opening_balance,
            "min_cash_threshold": min_threshold,
            "min_projected_cash": min([g['closing_cash'] for g in grid]) if grid else 0,
            "total_inflows_4w": sum([g['inflows'] for g in grid[:4]]),
            "total_outflows_4w": sum([g['outflows'] for g in grid[:4]]),
        },
        "grid": grid,
        "top_risks": top_risks[:5]
    }

def get_week_drilldown_data(db: Session, snapshot_id: int, week_index: int, type: str):
    """
    Returns the specific invoices or outflows for a selected week in the 13-week view.
    """
    # 1. Determine Week Range
    from utils import get_forecast_aggregation
    inflow_data = get_forecast_aggregation(db, snapshot_id, group_by="week")
    
    if not inflow_data:
        today = datetime.datetime.now().date()
        start_of_week = today - datetime.timedelta(days=today.weekday())
    else:
        start_of_week = datetime.datetime.fromisoformat(inflow_data[0]['start_date']).date()

    target_week_start = start_of_week + datetime.timedelta(weeks=week_index)
    target_week_end = target_week_start + datetime.timedelta(days=7)

    if type == 'inflow':
        # Find open invoices predicted to land in this week
        invoices = db.query(models.Invoice).filter(
            models.Invoice.snapshot_id == snapshot_id,
            models.Invoice.payment_date == None,
            models.Invoice.predicted_payment_date >= target_week_start,
            models.Invoice.predicted_payment_date < target_week_end
        ).order_by(models.Invoice.amount.desc()).all()
        
        return [{
            "customer": inv.customer,
            "amount": inv.amount,
            "date": inv.predicted_payment_date.isoformat(),
            "confidence": inv.prediction_segment
        } for inv in invoices]

    else:
        # Find vendor bills and outflow items scheduled for this week
        bills = db.query(models.VendorBill).filter(
            models.VendorBill.snapshot_id == snapshot_id,
            models.VendorBill.due_date >= target_week_start,
            models.VendorBill.due_date < target_week_end
        ).all()
        
        outflows = db.query(models.OutflowItem).filter(
            models.OutflowItem.snapshot_id == snapshot_id,
            models.OutflowItem.expected_date >= target_week_start,
            models.OutflowItem.expected_date < target_week_end
        ).all()
        
        res = []
        for b in bills:
            res.append({
                "description": f"Vendor: {b.vendor_name}",
                "amount": b.amount,
                "date": b.due_date.isoformat(),
                "is_discretionary": b.is_discretionary == 1
            })
        for o in outflows:
            res.append({
                "description": o.description,
                "amount": o.amount,
                "date": o.expected_date.isoformat(),
                "is_discretionary": o.is_discretionary == 1
            })
        return sorted(res, key=lambda x: x['amount'], reverse=True)

