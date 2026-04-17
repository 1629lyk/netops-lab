"""
compliance.py — GET /compliance, POST /compliance/run
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from src.api.dependencies import get_db
from src.database.models import ComplianceResult
from src.core.engine import get_nornir_managed
from src.tasks.compliance import check_compliance

router = APIRouter(prefix="/compliance", tags=["compliance"])


@router.get("")
def list_compliance(db: Session = Depends(get_db)):
    """Return latest compliance result per host per policy."""
    records = db.query(ComplianceResult)\
                .order_by(ComplianceResult.checked_at.desc())\
                .all()

    return {
        "results": [
            {
                "id": r.id,
                "hostname": r.hostname,
                "policy": r.policy,
                "passed": r.passed,
                "detail": r.detail,
                "checked_at": r.checked_at.isoformat()
            }
            for r in records
        ],
        "total": len(records)
    }


@router.post("/run")
def run_compliance():
    """Run compliance checks against all devices synchronously."""
    nr = get_nornir_managed()
    results = nr.run(task=check_compliance)

    summary = []
    for host, result in results.items():
        if result.failed:
            summary.append({
                "hostname": host,
                "success": False,
                "error": str(result.exception)
            })
        else:
            policy_results = result[0].result
            summary.append({
                "hostname": host,
                "success": True,
                "policies": policy_results
            })

    return {"results": summary}
