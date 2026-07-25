from datetime import datetime
from typing import Dict, Any
from sqlalchemy.orm import Session
from .models import RiskPredictionMonitoring

class RiskMonitoringService:
    @staticmethod
    def log_prediction(db: Session, session_id: str, risk_level: str) -> None:
        """Saves the initial automated risk prediction."""
        try:
            entry = RiskPredictionMonitoring(session_id=session_id, predicted_risk_level=risk_level)
            db.add(entry)
            db.commit()
        except Exception:
            db.rollback()  # Fails silently so it never breaks the live interview flow

    @staticmethod
    def log_recruiter_review(db: Session, session_id: str, action: str) -> None:
        """Updates the table when a recruiter submits a manual action ('CONFIRM' or 'OVERRIDE')."""
        try:
            entry = db.query(RiskPredictionMonitoring).filter(
                RiskPredictionMonitoring.session_id == session_id,
                RiskPredictionMonitoring.predicted_risk_level == "HIGH"
            ).order_by(RiskPredictionMonitoring.created_at.desc()).first()

            if entry:
                entry.recruiter_outcome = action
                # If predicted HIGH but recruiter overrides it -> It's a False Positive
                entry.is_false_positive = (action == "OVERRIDE")
                db.commit()
        except Exception:
            db.rollback()

    @staticmethod
    def get_metrics(db: Session) -> Dict[str, Any]:
        """Calculates the analytics requested in the issue."""
        query = db.query(RiskPredictionMonitoring).filter(RiskPredictionMonitoring.predicted_risk_level == "HIGH")
        
        total_high = query.count()
        confirmed = query.filter(RiskPredictionMonitoring.recruiter_outcome == "CONFIRM").count()
        false_positives = query.filter(RiskPredictionMonitoring.is_false_positive == True).count()
        
        reviewed = confirmed + false_positives
        fp_rate = (false_positives / reviewed * 100) if reviewed > 0 else 0.0

        return {
            "total_high_predictions": total_high,
            "confirmed_high_predictions": confirmed,
            "false_positive_count": false_positives,
            "false_positive_rate_percent": round(fp_rate, 2)
        }
