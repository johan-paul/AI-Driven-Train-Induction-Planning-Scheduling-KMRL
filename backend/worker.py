# backend/worker.py
"""
Simple scheduler using APScheduler to run nightly ingestion + induction.
You can start this module separately or import the `schedule_nightly_job()` function in main.py.
"""
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, time, timedelta
import logging
from .ingestion import build_combined_snapshot
from .database import SessionLocal
from . import crud
from .core_import_helper import run_induction_from_rows  # we will create a tiny helper that runs induction

logger = logging.getLogger(__name__)

def nightly_job():
    logger.info("Nightly job start: fetching snapshots")
    rows = build_combined_snapshot()
    db = SessionLocal()
    try:
        n = crud.bulk_save_snapshots(db, rows)
        logger.info(f"Saved {n} train snapshots")
        # Run induction immediately (example defaults)
        plan = run_induction_from_rows(rows, service_count=8, lambda_risk=1.5, use_ml=True)
        # persist plan in DB (crud.create_induction_plan expects summary and plan json)
        crud.create_induction_plan(db, service_count=8, lambda_risk=1.5, use_ml=True, summary=plan['summary'], plan_json=plan['results'])
        logger.info("Induction completed and saved")
    finally:
        db.close()

def schedule_nightly_job(hour=21, minute=0):
    sched = BackgroundScheduler()
    # schedule daily at hour:minute
    sched.add_job(nightly_job, 'cron', hour=hour, minute=minute)
    sched.start()
    logger.info(f"Scheduled nightly_job at {hour:02d}:{minute:02d}")
    return sched
