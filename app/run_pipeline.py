import time
import logging
import datetime

from sqlalchemy import select, asc, func, desc
from sqlalchemy.orm import Session

from app.database_sqlalchemy import engine, SessionLocal
from app.tables import SearchQueries, ExtractUrls, GsQueries, MoneyExchangeRate
from scraper.graph_search import app_search
from scraper.graph_extract import app_extract 
from scraper.graph_gsc import app_gsc 

from sqlalchemy.exc import OperationalError

from scraper.utils import get_latest_exchange_rate, rates_to_dataframe, rates_to_dataframe_fin #added 23 mar 2026

# --------------------------------------------------
# CONFIG
# --------------------------------------------------

INTERVAL_SECONDS = 20 * 60  # 20 minutes 24 mar 2026 changed from 40 to 20 minutes

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

def get_next_search_task():
    with Session(engine) as session_g:
        stmt = (
            select(SearchQueries)
            .where(SearchQueries.active_status == True)
            .order_by(
                SearchQueries.last_run_at.asc().nullsfirst()
            )
            .limit(1)
        )
        return session_g.execute(stmt).scalars().first()

def get_next_search_task_2nd(session: Session):
    stmt = (
        select(SearchQueries)
        .where(SearchQueries.active_status == True)
        .order_by(
            SearchQueries.last_run_at.asc().nullsfirst()
        )
        .limit(1)
    )
    return session.execute(stmt).scalars().first()

def get_next_extract_task(): #16 mar 2026 : remove session argument
    with Session(engine) as session_g:        
        stmt = (
            select(ExtractUrls)
            .where(ExtractUrls.active_status == True)
            .order_by(
                ExtractUrls.last_run_at.asc().nullsfirst()
            )
            .limit(1)
        )
        return session_g.execute(stmt).scalars().first()

def get_next_extract_task_2nd(session: Session): #16 mar 2026 : 2nd time running to finally update table extract_url       
    stmt = (
        select(ExtractUrls)
        .where(ExtractUrls.active_status == True)
        .order_by(
            ExtractUrls.last_run_at.asc().nullsfirst()
        )
        .limit(1)
    )
    return session.execute(stmt).scalars().first()

def get_next_gsc_task():
    with Session(engine) as session_g:
        stmt = (
            select(GsQueries)
            .where(GsQueries.active_status == True)
            .order_by(
                GsQueries.last_run_at.asc().nullsfirst()
            )
            .limit(1)
        )
        return session_g.execute(stmt).scalars().first()

def get_next_gsc_task_2nd(session: Session):
    stmt = (
        select(GsQueries)
        .where(GsQueries.active_status == True)
        .order_by(
            GsQueries.last_run_at.asc().nullsfirst()
        )
        .limit(1)
    )
    return session.execute(stmt).scalars().first()

# ---------------------------------------------------------
# UPDATING TABLE SEARCH_QUERIES, EXTRACT_URLS, GS_QUERIES
# ---------------------------------------------------------

def update_search_queries(session: Session, task: SearchQueries):

    task.last_run_at = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M')        
    task.loop_order += 1

    session.commit()

def update_extract_urls(session: Session, task: ExtractUrls): #16 mar 2026 remove argument session
#    with Session(engine) as session_u:

        #task.last_run_at = datetime.datetime.now(datetime.timezone.utc)
    task.last_run_at = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M')        
    task.loop_order += 1

    session.commit() #16 mar 2026: session.commit() here, so the function do commit

    #print(">>> Update table extract_urls Successful !")
    #time.sleep(5)
    #logger.info("Extract task completed.")

def update_gs_queries(session: Session, task: GsQueries):

    task.last_run_at = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M')        
    task.loop_order += 1

    session.commit()

# --------------------------------------------------
# EXECUTORS
# --------------------------------------------------

def run_search_task(task: SearchQueries):
    logger.info(f"Running SEARCH task: {task.search_query_text} country {task.country}")
    try:
        for _ in app_search.stream({"question": task.search_query_text, "country": task.country}): #24 march 2026: add country
            pass  # your graph handles DB insert internally
    except Exception as e:
        logger.error("Search failed for {} {}: {}".format(task.search_query_text, task.country, e))
        pass

def run_extract_task(task: ExtractUrls): #16 mar 2026: remove argument session because it is not used...
    logger.info(f"Running EXTRACT task: {task.url} country {task.country}")
    try: 
        for _ in app_extract.stream({"urls": [task.url], "countries": [task.country]}): #14 mar 2026: add into list since graph_extract expect to receive url in list.
            pass 
    except Exception as e:
        logger.error(f"Extraction failed for {task.url} {task.country}: {e}")
        pass        

def run_gsc_task(task: GsQueries):
    logger.info(f"Running GSC task: {task.gs_query} country {task.country}")
    try:
        for _ in app_gsc.stream({"user_ask": task.gs_query, "country": task.country}):
            pass
    except Exception as e:
        logger.error("GSC failed for {} {}: {}".format(task.gs_query, task.country, e))
        pass

# --------------------------------------------------
# MAIN LOOP
# --------------------------------------------------

from sqlalchemy.exc import OperationalError
import time

def run_scheduler():

    logger.info("Pipeline scheduler started...")

    stage = "SEARCH"
    last_stage = "FIRST TIME RUN"

    while True:

        # with Session(engine) as session: deactivated on 16 mar 2026
        
        # ---------------------------------------------------------------------------------------------
        # 23 March 2026: Check table money_exchange_rate whether there is newest exchange rates or not
        # ---------------------------------------------------------------------------------------------
        exchange_rate_table = get_latest_exchange_rate()
        latest_timestamp_extract = exchange_rate_table["timestamp_extract"].max()
        lte_datetime = datetime.datetime.strptime(latest_timestamp_extract, '%Y-%m-%d %H:%M')
        lte_datetime = lte_datetime.replace(tzinfo=datetime.timezone.utc)
        if lte_datetime > (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=24)) :
            print("The money exchange rates is already newest !") 
        else:
            print("Start collect newest money exchange rates from API.")
            rates_to_dataframe_fin()
            print("Collection is finished !")        


        # --------------------------------------
        # SEARCH STAGE
        # --------------------------------------
        if stage == "SEARCH" :

            gate_search_queries = check_condition_search_queries()
            if (gate_search_queries['all_rows_number'] != gate_search_queries['rows_with_latest_loop_order_number']) or (gate_search_queries['latest_loop_order_number'] == 0) or (last_stage == "GSC") : 

                search_task = get_next_search_task()
                run_search_task(search_task) 
                with Session(engine) as session_u:
                    for attempt in range(2):
                        try:
                            search_task_u = get_next_search_task_2nd(session_u)
                            update_search_queries(session_u, search_task_u)
                            print(">>> Update table search_queries Successful !")
                            time.sleep(2)
                            print(">>> Search task completed.")
                            logger.info("Search task completed.")
                            break
                        except OperationalError as e:
                            logger.error("Update table search_queries retry {}: {}".format(attempt+1, e))
                            session_u.rollback()
                            print("Error:",e)
                            time.sleep(2)
                last_stage = "SEARCH"
                time.sleep(2)
                logger.info("Sleeping for {} minutes...\n".format(INTERVAL_SECONDS/60))
                time.sleep(INTERVAL_SECONDS)
                
            else :
                logger.info("All SEARCH tasks completed. Moving to EXTRACT.")
                stage = "EXTRACT"
                last_stage = "SEARCH" 
                continue   

        # -------------------------------------
        # EXTRACT STAGE 
        # -------------------------------------
        elif stage == "EXTRACT" :

            gate_extract_urls = check_condition_extract_urls() 
            if (gate_extract_urls['all_rows_number'] != gate_extract_urls['rows_with_latest_loop_order_number']) or (gate_extract_urls['latest_loop_order_number'] == 0) or (last_stage == "SEARCH") : 

                extract_task = get_next_extract_task() 
                run_extract_task(extract_task) #sessionlocal was already created in last node of graph_extract long time ago 16 mar 2026
                with Session(engine) as session_u:
                    for attempt in range(2):
                        try:
                            extract_task_u = get_next_extract_task_2nd(session_u)
                            update_extract_urls(session_u, extract_task_u) #need sesion because updating table 16 mar 2026, session.commit inside this function                                                        
                            print(">>> Update table extract_urls Successful !")
                            time.sleep(2)
                            print(">>> Extract task completed.") #16 march 2026: replace logger.info with print
                            logger.info("Extract task completed.")
                            break
                        except OperationalError as e:
                            logger.error(f"Update table extract_urls retry {attempt+1}: {e}")
                            session_u.rollback()
                            print("Error:",e)
                            time.sleep(2)
                last_stage = "EXTRACT"
                time.sleep(2)
                logger.info(f"Sleeping for {INTERVAL_SECONDS/60} minutes...\n") # 16 march 2026 sleeping 
                time.sleep(INTERVAL_SECONDS)                            
             
            else : 
                logger.info("All EXTRACT tasks completed. Moving to GSC.") 
                stage = "GSC" 
                last_stage = "EXTRACT"
                continue #meaning: continue to the next elif 17 march 2026

        # -------------------------------------
        # GSC STAGE 
        # -------------------------------------
        elif stage == "GSC" : 

            gate_gs_queries = check_condition_gs_queries()
            if (gate_gs_queries['all_rows_number'] != gate_gs_queries['rows_with_latest_loop_order_number']) or (gate_gs_queries['latest_loop_order_number'] == 0) or (last_stage == "EXTRACT") : 

                gsc_task = get_next_gsc_task() 
                run_gsc_task(gsc_task)
                with Session(engine) as session_u:
                    for attempt in range(2):
                        try:
                            gsc_task_u = get_next_gsc_task_2nd(session_u)
                            update_gs_queries(session_u, gsc_task_u)
                            print(">>> Update table gs_queries Successfull !")
                            time.sleep(2)
                            print(">>> GSC task completed.")
                            logger.info("GSC task completed.")
                            break
                        except OperationalError as e:
                            logger.error("Update table gs_queries retry {}: {}".format(attempt+1, e))
                            session_u.rollback()
                            print("Error:",e)
                            time.sleep(2)
                last_stage = "GSC"
                time.sleep(2)
                logger.info("Sleeping for {} minutes...\n".format(INTERVAL_SECONDS/60))
                time.sleep(INTERVAL_SECONDS)
                
            else : 
                logger.info("All GSC tasks completed. Restarting pipeline.")
                #logger.info("Restarting for {} hours...\n".format(86400/3600))
                logger.info("Restarting for {} minutes...\n".format(INTERVAL_SECONDS/60/2))
                time.sleep(INTERVAL_SECONDS/2)                
                stage = "SEARCH" 
                last_stage = "GSC"
                continue 

    #Deactivated 17 march 2026 because it is actually not executed inside while True
    #logger.info(f"Sleeping for {INTERVAL_SECONDS/60} minutes...\n")
    #time.sleep(INTERVAL_SECONDS)


# --------------------------------------------------

if __name__ == "__main__":
    run_scheduler()


