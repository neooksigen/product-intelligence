import time
import logging
import datetime

from sqlalchemy import select, asc, func
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

# -----------New 14 March 2026----------------------
# CHECK CONDITION
# --------------------------------------------------

#use session_s (do not use session) so the engine will not be confused. This CHECK CONDITION is just checking current loop order in table, not committing data.
def check_condition_search_queries():

    with Session(engine) as session_s:

        all_rows = (
            select(func.count())
            .select_from(SearchQueries)
            .where(SearchQueries.active_status == True)
        )
        all_rows_number = session_s.execute(all_rows).scalar()

        latest_loop_order = (
            select(func.max(SearchQueries.loop_order))
            .select_from(SearchQueries)
            .where(SearchQueries.active_status == True)
        )
        latest_loop_order_number = session_s.execute(latest_loop_order).scalar()

        rows_with_latest_loop_order = (
            select(func.count())
            .select_from(SearchQueries)
            .where(
                SearchQueries.active_status == True,
                SearchQueries.loop_order == latest_loop_order_number
            )
        )
        rows_with_latest_loop_order_number = session_s.execute(rows_with_latest_loop_order).scalar()
        
        check_condition = (all_rows_number == rows_with_latest_loop_order_number)

        return {"all_rows_number": all_rows_number, 
        "latest_loop_order_number": latest_loop_order_number,
        "rows_with_latest_loop_order_number": rows_with_latest_loop_order_number,
        "check_condition": check_condition}

def check_condition_extract_urls():

    with Session(engine) as session_s:

        all_rows = (
            select(func.count())
            .select_from(ExtractUrls)
            .where(ExtractUrls.active_status == True)
        )
        all_rows_number = session_s.execute(all_rows).scalar()

        latest_loop_order = (
            select(func.max(ExtractUrls.loop_order))
            .select_from(ExtractUrls)
            .where(ExtractUrls.active_status == True)
        )
        latest_loop_order_number = session_s.execute(latest_loop_order).scalar()

        rows_with_latest_loop_order = (
            select(func.count())
            .select_from(ExtractUrls)
            .where(
                ExtractUrls.active_status == True,
                ExtractUrls.loop_order == latest_loop_order_number
            )
        )
        rows_with_latest_loop_order_number = session_s.execute(rows_with_latest_loop_order).scalar()
        
        check_condition = (all_rows_number == rows_with_latest_loop_order_number)

        return {"all_rows_number": all_rows_number, 
        "latest_loop_order_number": latest_loop_order_number,
        "rows_with_latest_loop_order_number": rows_with_latest_loop_order_number,
        "check_condition": check_condition}

def check_condition_gs_queries():

    with Session(engine) as session_s:

        all_rows = (
            select(func.count())
            .select_from(GsQueries)
            .where(GsQueries.active_status == True)
        )
        all_rows_number = session_s.execute(all_rows).scalar()

        latest_loop_order = (
            select(func.max(GsQueries.loop_order))
            .select_from(GsQueries)
            .where(GsQueries.active_status == True)
        )
        latest_loop_order_number = session_s.execute(latest_loop_order).scalar()

        rows_with_latest_loop_order = (
            select(func.count())
            .select_from(GsQueries)
            .where(
                GsQueries.active_status == True,
                GsQueries.loop_order == latest_loop_order_number
            )
        )
        rows_with_latest_loop_order_number = session_s.execute(rows_with_latest_loop_order).scalar()
        
        check_condition = (all_rows_number == rows_with_latest_loop_order_number)

        return {"all_rows_number": all_rows_number, 
        "latest_loop_order_number": latest_loop_order_number,
        "rows_with_latest_loop_order_number": rows_with_latest_loop_order_number,
        "check_condition": check_condition}

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
    #all_rows_number = check_condition_search_queries()['all_rows_number']
    #latest_loop_order_number = check_condition_search_queries()['latest_loop_order_number']    
    #rows_with_latest_loop_order_number = check_condition_search_queries()['rows_with_latest_loop_order_number']
    #if all_rows_number == rows_with_latest_loop_order_number : 
    task.loop_order = task.loop_order + 1
    #else : 
    #    task.loop_order = latest_loop_order_number

    session.commit()
    print(">>> Update table search_queries Successful !")
    logger.info("Search task completed.")

def run_extract_task(session: Session, task: ExtractUrls):
    logger.info(f"Running EXTRACT task: {task.url}")
    try: 
        for _ in app_extract.stream({"urls": [task.url]}): #14 mar 2026: add into list since graph_extract expect to receive url in list.
            pass 
    except Exception as e:
        logger.error(f"Extraction failed for {task.url}: {e}")        

    task.last_run_at = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M')
    #check_result = check_condition_extract_urls()
    #all_rows_number =  check_result['all_rows_number']
    #latest_loop_order_number = check_result['latest_loop_order_number']    
    #rows_with_latest_loop_order_number = check_result['rows_with_latest_loop_order_number']
    #if all_rows_number == rows_with_latest_loop_order_number : 
    task.loop_order = task.loop_order + 1
    #else : 
    #    task.loop_order = latest_loop_order_number  
  
    session.commit()
    print(">>> Update table extract_urls Successful !")

# safe commit 15 mar 2026 to mitigate DB connection drop
    #from sqlalchemy.exc import OperationalError
    #import time

    #for attempt in range(2):
    #try:
    #    session.commit()
    #    print(">>> Update table extract_urls Successful !")
        #break
    #except OperationalError as e:
    #except Exception as e:
        #logger.error(f"Commit retry {attempt+1}: {e}")
    #    session.rollback()
    #    print("Error:",e)
    #    time.sleep(5)

    logger.info("Extract task completed.")

def run_gsc_task(session: Session, task: GsQueries):
    logger.info(f"Running GSC task: {task.gs_query}")

    for _ in app_gsc.stream({"user_ask": task.gs_query}):
        pass
    
    task.last_run_at = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M')
    #all_rows_number = check_condition_gs_queries()['all_rows_number']
    #latest_loop_order_number = check_condition_gs_queries()['latest_loop_order_number']    
    #rows_with_latest_loop_order_number = check_condition_gs_queries()['rows_with_latest_loop_order_number']
    #if all_rows_number == rows_with_latest_loop_order_number : 
    task.loop_order = task.loop_order + 1
    #else : 
    #    task.loop_order = latest_loop_order_number  
    
    session.commit()
    print(">>> Update table gs_queries Successful !")
    logger.info("GSC task completed.")

# --------------------------------------------------
# MAIN LOOP
# --------------------------------------------------

def run_scheduler():

    logger.info("Pipeline scheduler started...")

    stage = "SEARCH"

    while True:

        with Session(engine) as session:

            # --------------------------------------
            # SEARCH STAGE
            # --------------------------------------
            if stage == "SEARCH" :

                gate_search_queries = check_condition_search_queries()
                if (gate_search_queries['all_rows_number'] != gate_search_queries['rows_with_latest_loop_order_number']) or (gate_search_queries['latest_loop_order_number'] == 0) : 

                    search_task = get_next_search_task(session)
                    run_search_task(session, search_task) 
                
                else :
                    logger.info("All SEARCH tasks completed. Moving to EXTRACT.")
                    stage = "EXTRACT" 
                    continue   

            # -------------------------------------
            # EXTRACT STAGE 
            # -------------------------------------
            elif stage == "EXTRACT" :

                gate_extract_urls = check_condition_extract_urls() 
                if (gate_extract_urls['all_rows_number'] != gate_extract_urls['rows_with_latest_loop_order_number']) or (gate_extract_urls['latest_loop_order_number'] == 0) : 

                    extract_task = get_next_extract_task(session) 
                    run_extract_task(session, extract_task)

                else : 
                    logger.info("All EXTRACT tasks completed. Moving to GSC.") 
                    stage = "GSC" 
                    continue 

            # -------------------------------------
            # GSC STAGE 
            # -------------------------------------
            elif stage == "GSC" : 

                gate_gs_queries = check_condition_gs_queries()
                if (gate_gs_queries['all_rows_number'] != gate_gs_queries['rows_with_latest_loop_order_number']) or (gate_gs_queries['latest_loop_order_number'] == 0) : 

                    gsc_task = get_next_gsc_task(session) 
                    run_gsc_task(session, gsc_task) 
                
                else : 
                    logger.info("All GSC tasks completed. Restarting pipeline.")
                    stage = "SEARCH" 
                    continue 

        logger.info(f"Sleeping for {INTERVAL_SECONDS/60} minutes...\n")
        time.sleep(INTERVAL_SECONDS)


# --------------------------------------------------

if __name__ == "__main__":
    run_scheduler()


