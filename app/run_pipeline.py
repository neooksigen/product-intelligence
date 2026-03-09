import time
import logging
import datetime

from sqlalchemy import select, asc
from sqlalchemy.orm import Session

from app.database_sqlalchemy import engine
from app.tables import SearchQueries, ExtractUrls, GsQueries
from scraper.graph_search import app_search
from scraper.graph_extract import app_extract 
from scraper.graph_gsc import app_gsc

# --------------------------------------------------
# CONFIG
# --------------------------------------------------

INTERVAL_SECONDS = 40 * 60  # 40 minutes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --------------------------------------------------
# TASK FETCHERS
# --------------------------------------------------

def get_next_search_task(session: Session):
    stmt = (
        select(SearchQueries)
        .where(SearchQueries.active_status == True)
        .order_by(
            SearchQueries.last_run_at.asc().nullsfirst()
        )
        .limit(1)
    )
    return session.execute(stmt).scalars().first()

def get_next_extract_task(session: Session):
    stmt = (
        select(ExtractUrls)
        .where(ExtractUrls.active_status == True)
        .order_by(
            ExtractUrls.last_run_at.asc().nullsfirst()
        )
        .limit(1)
    )
    return session.execute(stmt).scalars().first()

def get_next_gsc_task(session: Session):
    stmt = (
        select(GsQueries)
        .where(GsQueries.active_status == True)
        .order_by(
            GsQueries.last_run_at.asc().nullsfirst()
        )
        .limit(1)
    )
    return session.execute(stmt).scalars().first()

# --------------------------------------------------
# EXECUTORS
# --------------------------------------------------

def run_search_task(session: Session, task: SearchQueries):
    logger.info(f"Running SEARCH task: {task.search_query_text}")

    for _ in app_search.stream({"question": task.search_query_text}):
        pass  # your graph handles DB insert internally

    task.last_run_at = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M')
    session.commit()

    logger.info("Search task completed.")

def run_extract_task(session: Session, task: ExtractUrls):
    logger.info(f"Running EXTRACT task: {task.url}")

    for _ in app_extract.stream({"urls": task.url}):
        pass

    task.last_run_at = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M')
    session.commit()

    logger.info("Extract task completed.")

def run_gsc_task(session: Session, task: GsQueries):
    logger.info(f"Running GSC task: {task.gs_query}")

    for _ in app_gsc.stream({"user_ask": task.gs_query}):
        pass
    
    task.last_run_at = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M')
    session.commit()

    logger.info("GSC task completed.")

# --------------------------------------------------
# MAIN LOOP
# --------------------------------------------------

def run_scheduler():
    logger.info("Pipeline scheduler started...")

    while True:
        with Session(engine) as session:

            # 1️⃣ Try SEARCH first
            search_task = get_next_search_task(session)

            if search_task:
                run_search_task(session, search_task)

            else:
                # 2️⃣ If no search task found → run EXTRACT
                extract_task = get_next_extract_task(session)

                if extract_task:
                    run_extract_task(session, extract_task)
                
                else:
                    # 3: If no extract task found → run GSC
                    gsc_task = get_next_gsc_task(session)

                    if gsc_task:
                        run_gsc_task(session, gsc_task)
                    
                    else:
                        logger.info("No active tasks found.")

        logger.info(f"Sleeping for {INTERVAL_SECONDS/60} minutes...\n")
        time.sleep(INTERVAL_SECONDS)


# --------------------------------------------------

if __name__ == "__main__":
    run_scheduler()


