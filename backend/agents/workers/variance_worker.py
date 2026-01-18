"""
Variance Worker

Performs structured variance analysis using industry-standard categories:
Timing, Volume, Price/Rate, Mix, One-time, Error.
"""

from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any, Tuple
import logging
import uuid

from sqlalchemy.orm import Session
from sqlalchemy import func

import models
from ..models.variance import (
    VarianceItem, CategorizedVariance, RootCause, VarianceCategory,
    VarianceDirection, VarianceReport
)

logger = logging.getLogger(__name__)


class VarianceWorker:
    """
    Performs structured variance analysis.
    
    Categorizes variances into:
    - TIMING: Same transaction, different date
    - VOLUME: Count of transactions changed
    - PRICE_RATE: Same volume, different amount (FX, pricing)
    - MIX: Composition of sources changed
    - ONE_TIME: Non-recurring item
    - ERROR: Data quality issue
    """
    
    def __init__(self, db: Session, entity_id: int):
        self.db = db
        self.entity_id = entity_id
        self.materiality_threshold = Decimal("1000")  # € threshold for material variance
    
    def analyze_actual_vs_forecast(
        self,
        snapshot_id: int,
        compare_snapshot_id: int,
        period: str = "week",
    ) -> VarianceReport:
        """
        Analyze variance between actual results and forecast.
        
        Args:
            snapshot_id: Current snapshot with actuals
            compare_snapshot_id: Snapshot with forecast to compare
            period: "week" or "month"
        
        Returns:
            Complete variance report with categorized root causes
        """
        current = self.db.query(models.Snapshot).filter(
            models.Snapshot.id == snapshot_id
        ).first()
        
        compare = self.db.query(models.Snapshot).filter(
            models.Snapshot.id == compare_snapshot_id
        ).first()
        
        if not current or not compare:
            raise ValueError("Snapshots not found")
        
        # Get actual and forecast totals
        actual = Decimal(str(current.actual_total_amount or 0))
        forecast = Decimal(str(compare.forecast_total_amount or 0))
        
        variance = actual - forecast
        variance_pct = float(variance / forecast * 100) if forecast != 0 else 0
        
        # Create variance item
        variance_item = VarianceItem(
            id=str(uuid.uuid4()),
            variance_type="actual_vs_forecast",
            period=period,
            expected_amount=forecast,
            actual_amount=actual,
            variance_amount=variance,
            variance_pct=variance_pct,
            currency="EUR",
            direction=VarianceDirection.FAVORABLE if variance > 0 else VarianceDirection.UNFAVORABLE,
            is_material=abs(variance) >= self.materiality_threshold,
            materiality_threshold=self.materiality_threshold,
            entity_id=self.entity_id,
        )
        
        # Categorize the variance
        categorized = self._categorize_variance(variance_item, current, compare)
        
        # Create report
        report = VarianceReport(
            id=str(uuid.uuid4()),
            entity_id=self.entity_id,
            snapshot_id=snapshot_id,
            report_type=period,
            generated_at=datetime.utcnow(),
            period_start=current.start_date or date.today(),
            period_end=current.end_date or date.today(),
            variances=[categorized],
            total_favorable=variance if variance > 0 else Decimal("0"),
            total_unfavorable=abs(variance) if variance < 0 else Decimal("0"),
            net_variance=variance,
            by_category={
                "timing": str(categorized.timing_total),
                "volume": str(categorized.volume_total),
                "price_rate": str(categorized.price_rate_total),
                "mix": str(categorized.mix_total),
                "one_time": str(categorized.one_time_total),
                "error": str(categorized.error_total),
            },
            material_variances=[categorized] if categorized.variance_item.is_material else [],
        )
        
        return report
    
    def _categorize_variance(
        self,
        variance_item: VarianceItem,
        current_snapshot: models.Snapshot,
        compare_snapshot: models.Snapshot,
    ) -> CategorizedVariance:
        """
        Categorize a variance into root causes.
        
        This is the core logic that attributes variance to specific causes.
        """
        root_causes = []
        
        # 1. Check for TIMING variances (payments that shifted dates)
        timing_variance, timing_causes = self._analyze_timing_variance(
            current_snapshot, compare_snapshot
        )
        root_causes.extend(timing_causes)
        
        # 2. Check for VOLUME variances (different number of transactions)
        volume_variance, volume_causes = self._analyze_volume_variance(
            current_snapshot, compare_snapshot
        )
        root_causes.extend(volume_causes)
        
        # 3. Check for PRICE/RATE variances (FX movements, pricing changes)
        price_variance, price_causes = self._analyze_price_variance(
            current_snapshot, compare_snapshot
        )
        root_causes.extend(price_causes)
        
        # 4. Check for MIX variances (different composition)
        mix_variance, mix_causes = self._analyze_mix_variance(
            current_snapshot, compare_snapshot
        )
        root_causes.extend(mix_causes)
        
        # 5. Check for ONE_TIME items
        one_time_variance, one_time_causes = self._analyze_one_time_items(
            current_snapshot
        )
        root_causes.extend(one_time_causes)
        
        # 6. Remaining unexplained variance is potential ERROR
        total_explained = (
            timing_variance + volume_variance + price_variance +
            mix_variance + one_time_variance
        )
        unexplained = variance_item.variance_amount - total_explained
        
        error_variance = Decimal("0")
        if abs(unexplained) > Decimal("0.01"):
            error_variance = unexplained
            root_causes.append(RootCause(
                category=VarianceCategory.ERROR,
                amount=unexplained,
                currency="EUR",
                description="Unexplained variance - may require investigation",
            ))
        
        return CategorizedVariance(
            variance_item=variance_item,
            timing_total=timing_variance,
            volume_total=volume_variance,
            price_rate_total=price_variance,
            mix_total=mix_variance,
            one_time_total=one_time_variance,
            error_total=error_variance,
            unexplained=unexplained if abs(unexplained) > Decimal("0.01") else Decimal("0"),
            root_causes=root_causes,
        )
    
    def _analyze_timing_variance(
        self,
        current: models.Snapshot,
        compare: models.Snapshot,
    ) -> Tuple[Decimal, List[RootCause]]:
        """
        Analyze timing variances (payments that shifted dates).
        
        Looks for invoices/payments that were expected in one period
        but occurred in another.
        """
        timing_total = Decimal("0")
        causes = []
        
        # Find invoices that were expected but not received
        # (they shifted to a later period)
        expected_invoices = self.db.query(models.Invoice).filter(
            models.Invoice.snapshot_id == compare.id,
            models.Invoice.due_date <= compare.end_date,
            models.Invoice.status != 'paid',
        ).all()
        
        for inv in expected_invoices:
            # Check if this invoice was paid in current period
            current_inv = self.db.query(models.Invoice).filter(
                models.Invoice.snapshot_id == current.id,
                models.Invoice.invoice_number == inv.invoice_number,
            ).first()
            
            if current_inv and current_inv.status != 'paid':
                # Invoice shifted - timing variance
                amount = Decimal(str(inv.amount))
                timing_total -= amount  # Negative because expected but not received
                
                causes.append(RootCause(
                    category=VarianceCategory.TIMING,
                    amount=-amount,
                    currency=inv.currency or "EUR",
                    description=f"{inv.customer_name} payment shifted from expected date",
                    related_entity=inv.customer_name,
                    related_ids=[inv.id],
                    original_date=inv.due_date,
                ))
        
        return timing_total, causes
    
    def _analyze_volume_variance(
        self,
        current: models.Snapshot,
        compare: models.Snapshot,
    ) -> Tuple[Decimal, List[RootCause]]:
        """
        Analyze volume variances (different number of transactions).
        """
        volume_total = Decimal("0")
        causes = []
        
        # Count invoices in each period
        current_count = self.db.query(func.count(models.Invoice.id)).filter(
            models.Invoice.snapshot_id == current.id
        ).scalar() or 0
        
        compare_count = self.db.query(func.count(models.Invoice.id)).filter(
            models.Invoice.snapshot_id == compare.id
        ).scalar() or 0
        
        count_diff = current_count - compare_count
        
        if count_diff != 0:
            # Calculate average invoice value
            avg_value = self.db.query(func.avg(models.Invoice.amount)).filter(
                models.Invoice.snapshot_id == current.id
            ).scalar() or 0
            
            volume_impact = Decimal(str(avg_value)) * count_diff
            volume_total = volume_impact
            
            causes.append(RootCause(
                category=VarianceCategory.VOLUME,
                amount=volume_impact,
                currency="EUR",
                description=f"{'More' if count_diff > 0 else 'Fewer'} invoices than expected ({abs(count_diff)})",
                count_change=count_diff,
            ))
        
        return volume_total, causes
    
    def _analyze_price_variance(
        self,
        current: models.Snapshot,
        compare: models.Snapshot,
    ) -> Tuple[Decimal, List[RootCause]]:
        """
        Analyze price/rate variances (FX movements, pricing changes).
        """
        price_total = Decimal("0")
        causes = []
        
        # Check for FX rate changes
        current_rates = {
            r.currency_pair: Decimal(str(r.rate))
            for r in self.db.query(models.FXRate).filter(
                models.FXRate.snapshot_id == current.id
            ).all()
        }
        
        compare_rates = {
            r.currency_pair: Decimal(str(r.rate))
            for r in self.db.query(models.FXRate).filter(
                models.FXRate.snapshot_id == compare.id
            ).all()
        }
        
        for pair, current_rate in current_rates.items():
            compare_rate = compare_rates.get(pair)
            if compare_rate and current_rate != compare_rate:
                # FX rate changed
                rate_change = current_rate - compare_rate
                
                # Estimate impact (simplified - would need currency exposure data)
                # For now, flag as a cause without precise amount
                causes.append(RootCause(
                    category=VarianceCategory.PRICE_RATE,
                    amount=Decimal("0"),  # Would need exposure to calculate
                    currency="EUR",
                    description=f"FX rate change: {pair} moved from {compare_rate} to {current_rate}",
                    original_rate=float(compare_rate),
                    new_rate=float(current_rate),
                ))
        
        return price_total, causes
    
    def _analyze_mix_variance(
        self,
        current: models.Snapshot,
        compare: models.Snapshot,
    ) -> Tuple[Decimal, List[RootCause]]:
        """
        Analyze mix variances (different composition of sources).
        """
        mix_total = Decimal("0")
        causes = []
        
        # Group invoices by customer in each period
        current_by_customer = self.db.query(
            models.Invoice.customer_name,
            func.sum(models.Invoice.amount).label('total')
        ).filter(
            models.Invoice.snapshot_id == current.id
        ).group_by(models.Invoice.customer_name).all()
        
        compare_by_customer = self.db.query(
            models.Invoice.customer_name,
            func.sum(models.Invoice.amount).label('total')
        ).filter(
            models.Invoice.snapshot_id == compare.id
        ).group_by(models.Invoice.customer_name).all()
        
        current_dict = {c[0]: Decimal(str(c[1])) for c in current_by_customer}
        compare_dict = {c[0]: Decimal(str(c[1])) for c in compare_by_customer}
        
        # Find new customers (in current but not compare)
        new_customers = set(current_dict.keys()) - set(compare_dict.keys())
        for customer in new_customers:
            amount = current_dict[customer]
            mix_total += amount
            causes.append(RootCause(
                category=VarianceCategory.MIX,
                amount=amount,
                currency="EUR",
                description=f"New customer: {customer}",
                related_entity=customer,
            ))
        
        # Find lost customers (in compare but not current)
        lost_customers = set(compare_dict.keys()) - set(current_dict.keys())
        for customer in lost_customers:
            amount = compare_dict[customer]
            mix_total -= amount
            causes.append(RootCause(
                category=VarianceCategory.MIX,
                amount=-amount,
                currency="EUR",
                description=f"Lost customer: {customer}",
                related_entity=customer,
            ))
        
        return mix_total, causes
    
    def _analyze_one_time_items(
        self,
        current: models.Snapshot,
    ) -> Tuple[Decimal, List[RootCause]]:
        """
        Analyze one-time/non-recurring items.
        """
        one_time_total = Decimal("0")
        causes = []
        
        # Look for transactions tagged as one-time or unusual
        # This would typically be based on metadata or flags
        
        # For now, identify large outliers as potential one-time items
        avg_amount = self.db.query(func.avg(models.Invoice.amount)).filter(
            models.Invoice.snapshot_id == current.id
        ).scalar() or 0
        
        threshold = Decimal(str(avg_amount)) * 5  # 5x average is unusual
        
        large_invoices = self.db.query(models.Invoice).filter(
            models.Invoice.snapshot_id == current.id,
            models.Invoice.amount > float(threshold),
        ).all()
        
        for inv in large_invoices:
            amount = Decimal(str(inv.amount))
            one_time_total += amount
            causes.append(RootCause(
                category=VarianceCategory.ONE_TIME,
                amount=amount,
                currency=inv.currency or "EUR",
                description=f"Large invoice (potential one-time): {inv.invoice_number}",
                related_entity=inv.customer_name,
                related_ids=[inv.id],
                is_recurring=False,
            ))
        
        return one_time_total, causes
    
    def get_variance_summary(
        self,
        snapshot_id: int,
        compare_snapshot_id: int,
    ) -> Dict[str, Any]:
        """
        Get a summary of variance analysis.
        """
        report = self.analyze_actual_vs_forecast(snapshot_id, compare_snapshot_id)
        
        return {
            "period": report.report_type,
            "net_variance": str(report.net_variance),
            "favorable": str(report.total_favorable),
            "unfavorable": str(report.total_unfavorable),
            "by_category": report.by_category,
            "material_items": len(report.material_variances),
            "root_causes_count": sum(len(v.root_causes) for v in report.variances),
        }
