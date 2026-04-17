"""
configs.py — GET /configs, POST /configs/backup
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from src.api.dependencies import get_db
from src.database.models import ConfigBackup
from src.core.engine import get_nornir_managed
from src.tasks.backup import backup_config

router = APIRouter(prefix="/configs", tags=["configs"])


@router.get("")
def list_configs(db: Session = Depends(get_db)):
    """Return all backup records from DB, most recent first."""
    records = db.query(ConfigBackup)\
                .order_by(ConfigBackup.backed_up_at.desc())\
                .all()

    return {
        "backups": [
            {
                "id": r.id,
                "hostname": r.hostname,
                "filepath": r.filepath,
                "backed_up_at": r.backed_up_at.isoformat(),
                "success": r.success,
                "lines": r.lines
            }
            for r in records
        ],
        "total": len(records)
    }


@router.post("/backup")
def run_backup():
    """Run config backup against all devices synchronously."""
    nr = get_nornir_managed()
    results = nr.run(task=backup_config)

    summary = []
    for host, result in results.items():
        if result.failed:
            summary.append({
                "hostname": host,
                "success": False,
                "error": str(result.exception)
            })
        else:
            data = result[0].result
            summary.append({
                "hostname": host,
                "success": data["success"],
                "lines": data["lines"],
                "filepath": data["filepath"]
            })

    return {"results": summary}
