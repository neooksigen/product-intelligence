#This function safe_extract_item will not be as Node. It is just helper function.
def safe_extract_item(response):
    if isinstance(response, str):
        # "'Rp 20000'" → 'Rp 20000'
        if response.startswith("'") and response.endswith("'"):
            return response[1:-1]
        return response
    
    elif isinstance(response, list) and len(response) > 0:
        # "['Rp 20000']" → 'Rp 20000'
        item = response[0]
        if isinstance(item, str) and item.startswith("'") and item.endswith("'"):
            return item[1:-1]
        return str(item)
    
    return str(response) 

from urllib.parse import urlsplit, urlunsplit, quote, unquote

def normalize_url(url): #edited 24 march 2026 to prevent double encoding
    parts = urlsplit(url)

    # Decode first to avoid double encoding
    path = quote(unquote(parts.path))
    query = quote(unquote(parts.query), safe="=&")

    return urlunsplit((parts.scheme, parts.netloc, path, query, parts.fragment))

import re 
#21 march 2026: new function parse_price to convert price text into price float
def parse_price(value: str) -> float:
    if not value:
        return None
    
    value = value.strip().lower()
    
    # Remove common currency symbols and codes
    value = re.sub(r'(rp|idr|usd|eur|jpy|sgd|aud|inr)', '', value)
    value = re.sub(r'[^\d,.\-]', '', value)  # keep only digits, comma, dot, minus
    
    # Case 1: Indonesian/European format → 1.234,56
    if ',' in value and '.' in value:
        if value.rfind(',') > value.rfind('.'):
            value = value.replace('.', '')
            value = value.replace(',', '.')
        else:
            value = value.replace(',', '')
    
    # Case 2: Only comma → could be decimal or thousand
    elif ',' in value:
        # assume comma is decimal if only one comma and at the end
        if value.count(',') == 1 and len(value.split(',')[-1]) <= 2:
            value = value.replace(',', '.')
        else:
            value = value.replace(',', '')
    
    # Case 3: Only dot → assume thousand separator
    elif '.' in value:
        value = value.replace('.', '')
    
    try:
        return float(value)
    except:
        return None

import re
#22 March 2026: new function to standardize quantity & measurement scale, deterministic without llm call
def standardize_quantity(quantity: str, measurement_scale: str):
    if not quantity:
        return None, None

    q = quantity.upper().strip()
    u = measurement_scale.upper().strip() if measurement_scale else ""

    # --- STEP 1: Clean quantity ---
    # Remove unwanted characters except digits, dot, X
    q = re.sub(r'[^0-9.X]', '', q)

    # --- STEP 2: Handle multiplication ---
    if 'X' in q:
        parts = q.split('X')
        numbers = [float(p) for p in parts if p]
        qty = 1
        for n in numbers:
            qty *= n
    else:
        qty = float(q) if q else 0

    # --- STEP 3: Normalize unit ---
    u = u.replace('.', '').strip()

    # Map units → standardized
    if u in ['ML']:
        return qty / 1000, "Liter"

    elif u in ['L', 'LT', 'LITER']:
        return qty, "Liter"

    elif u in ['G', 'GR', 'GRAM']:
        return qty / 1000, "Kilogram"

    elif u in ['KG', 'KILOGRAM']:
        return qty, "Kilogram"

    elif u in ['CM']:
        return qty / 100, "Meter"

    elif u in ['M', 'METER']:
        return qty, "Meter"

    elif u in ['PCS', 'S', 'BUTIR', 'PACK']:
        return qty, "Pcs"

    else:
        # fallback (unknown unit)
        return qty, u

import pandas as pd
import datetime
#22 mar 2026: new function to insert daily money exchange rates to Supabase table
def rates_to_dataframe(data:dict) -> pd.DataFrame:
    df = pd.DataFrame(
        list(data['conversion_rates'].items()),
        columns = ["to_currency","exchange_rate"]
    )
    df['from_base_code'] = data['base_code']
    df['time_last_update_utc'] = data['time_last_update_utc']
    df['timestamp_extract'] = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M')
    df_fin = df.loc[:,["from_base_code","to_currency","exchange_rate","time_last_update_utc","timestamp_extract"]]
    return df_fin

#22 mar 2026: new function completely insert daily money er to Supabase table (using rates_to_dataframe also)
#from scraper.utils import rates_to_dataframe
import os
from dotenv import load_dotenv
load_dotenv()

from app.database_sqlalchemy import SessionLocal
from app.tables import MoneyExchangeRate
from itertools import zip_longest

import requests

YOUR_API_KEY = os.getenv("EXCHANGERATE_API_KEY")
base_code_money = ['USD','BRL','ARS', 'CLP', 'GBP', 'EUR', 'DZD', 'TZS', 'ZAR', 'SAR', 'IQD', 'RUB', 'JPY', 'CNY', 'INR', 'THB', 'IDR', 'SGD', 'AUD', 'NZD']

def rates_to_dataframe_fin():
    for i in range(len(base_code_money)):
        er_url = 'https://v6.exchangerate-api.com/v6/{YOUR_API_KEY}/latest/{base}'.format(YOUR_API_KEY=YOUR_API_KEY, base=base_code_money[i])
        response = requests.get(er_url)
        data = response.json()
        output = rates_to_dataframe(data)
        owner_id_list = []
        for i in range(output.shape[0]):
            owner_id_list.append(os.getenv("DB_OWNER_ID_00"))

        db = SessionLocal()

        try:
            for from_base_code, to_currency, exchange_rate, time_last_update_utc, timestamp_extract, owner_id in zip_longest(
                output['from_base_code'].to_list(),
                output['to_currency'].to_list(),
                output['exchange_rate'].to_list(),
                output['time_last_update_utc'].to_list(),
                output['timestamp_extract'].to_list(),
                owner_id_list
                ) : 
            
                new_exchange_rate = MoneyExchangeRate(
                    from_base_code = from_base_code,
                    to_currency = to_currency,
                    exchange_rate = exchange_rate,
                    time_last_update_utc = time_last_update_utc,
                    timestamp_extract = timestamp_extract,
                    owner_id = owner_id 
                )

                db.add(new_exchange_rate)
        
            db.commit()
            print(">>> Insert data to money_exchange_rate table is successfull !")
            print(output)
    
        except Exception as e:
            db.rollback()
            print("Error: ", e)
            raise
    
        finally:
            db.close()

#23 March 2026: this function to retrieve latest money exchange rates
import time
import logging
import datetime

from sqlalchemy import select, asc, func, desc
from sqlalchemy.orm import Session

from app.database_sqlalchemy import engine
from app.tables import MoneyExchangeRate

from sqlalchemy.exc import OperationalError
import pandas as pd

def get_latest_exchange_rate():
    with Session(engine) as session_ex:

        subquery = (
            select(
                MoneyExchangeRate.from_base_code,
                MoneyExchangeRate.to_currency,
                MoneyExchangeRate.exchange_rate,
                MoneyExchangeRate.time_last_update_utc,
                MoneyExchangeRate.timestamp_extract,
                func.row_number().over(
                    partition_by=(
                        MoneyExchangeRate.from_base_code,
                        MoneyExchangeRate.to_currency
                    ),
                    order_by=MoneyExchangeRate.timestamp_extract.desc()
                ).label("rn")
            ).subquery()
        )
        query = select(subquery).where(subquery.c.rn == 1)        
        result = session_ex.execute(query).all()
    
    df = pd.DataFrame(result, columns=[
        "from_base_code",
        "to_currency",
        "exchange_rate",
        "time_last_update_utc",
        "timestamp_extract",
        "rn"
    ])
    
    return df


