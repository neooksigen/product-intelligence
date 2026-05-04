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
def parse_price(value: str):
    if not value:
        return None
    
    value = value.strip().lower()
    
    # Remove common currency symbols and codes
    value = re.sub(r'(rp|idr|usd|eur|jpy|sgd|aud|inr)', '', value)
    value = re.sub(r'[^\d,.\-]', '', value)  # keep only digits, comma, dot, minus
    value = value.rstrip(".") #29 mar 2026: cleaned again possible . at the end of string
    value_temp = value #29 mar 2026: value_temp to check cleaned value, if required
    
    # Check if value still contains non-numeric (excluding dot) (case of Arabian money value)
    has_non_numeric = bool(re.search(r"[^\d.]", value))

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
        if value.count('.') == 1 and len(value.split('.')[0]) == 0:
            value = value.replace('.', '.')
        elif value.count('.') == 1 and len(value.split('.')[-1]) <= 2: #enhanced 29 march 2026 so 12.99 will be treated as 12.99 (=no change).
            value = value.replace('.', '.')
        else:
            value = value.replace('.','')
    
    try:
        return {"fin":float(value), "value_temp":value_temp}
    except:
        return {"fin":None, "value_temp":None}

#new def 26 apr 2026
def safe_float(x):
    try:
        return float(x)
    except:
        return None

import re
import numpy as np
#22 March 2026: new function to standardize quantity & measurement scale, deterministic without llm call
#22 March 2026: new function to standardize quantity & measurement scale, deterministic without llm call
def standardize_quantity(quantity: str, measurement_scale: str):
    if not quantity:
        return None, None

    q = quantity.upper().strip().replace(' ', '') #26 april 2026: add replace space to remove space
    u = measurement_scale.upper().strip() if measurement_scale else ""

    #2 May 2026: add this to convert certain unicode characters into ASCII.
    q = q.replace('×', 'X')       # Unicode multiplication sign → X
    q = q.replace('〜', '~')       # Fullwidth tilde → regular tilde
    q = q.replace('～', '~')       # Another fullwidth tilde variant → regular tilde
    q = q.replace('＊', '*')       # Fullwidth asterisk → regular asterisk

    # --- STEP 1: Clean quantity ---
    # Remove unwanted characters except digits, dot, comma, strip, X, *, +
    q = re.sub(r'[^0-9.,xX\-\*\+\~\T\O]', '', q) #26 april 2026 add x little, 1 may 2026 add ~ due to finding in JP, 5 may 2026: add 'to' case found in IN.

    # --- STEP 2: Handle multiplication ---
    # enhanced 19 april 2026 to handle comma and -
    # 26 apr 2026 add this if , if digit not detected, simply return qty = 0..
    if not re.search(r'\d', q):
        print(f"[WARNING] No digits in quantity: {quantity} → cleaned: {q}")
        qty = 0
        
    elif 'X' in q or 'x' in q :
        parts = q.upper().split('X') #enhanced 1 may 2026 to handle both x and X
        numbers = []
        for p in parts:
            if p.count(',') > 0:
                p = p.replace(',','.')
            cal = safe_float(p)
            if cal is not None:
                numbers.append(cal)
        ###numbers = [float(p) for p in parts if p]
        qty = 1
        for n in numbers:
            qty *= n

    elif 'TO' in q.upper() or 'O' in q.upper() : #added 5 may 2026 to handle 'to' case found in IN. 
        q = q.upper().replace('T','')
        parts = q.upper().split('O') 
        numbers = []
        for p in parts:
            if p.count(',') > 0:
                p = p.replace(',','.')
            cal = safe_float(p)
            if cal is not None:
                numbers.append(cal)
        ###numbers = [float(p) for p in parts if p]
        qty = 1
        for n in numbers:
            qty *= n
    
    elif '-' in q or '~' in q : #enhanced 1 may 2026 to handle - and ~ (case of JP)
        parts = re.split(r'[-~]', q)
        numbers = []
        for p in parts[0:2]:
            if p.count(',') > 0:
                p = p.replace(',','.')
            cal = safe_float(p)
            if cal is not None:                
                numbers.append(cal)
        ###numbers = [float(p) for p in parts if p]
        qty = float(np.mean(numbers))

    elif '*' in q : #added 26 apr 2026
        parts = q.split('*')
        numbers = []
        for p in parts:
            if p.count(',') > 0:
                p = p.replace(',','.')
            cal = safe_float(p)
            if cal is not None: 
                numbers.append(cal)
        ###numbers = [float(p) for p in parts if p]
        qty = 1
        for n in numbers:
            qty *= n    

    elif '+' in q : #added 26 apr 2026
        parts = q.split('+')
        numbers = []
        for p in parts:
            if p.count(',') > 0:
                p = p.replace(',','.')
            cal = safe_float(p)
            if cal is not None: 
                numbers.append(cal)
        ###numbers = [float(p) for p in parts if p]
        qty = 1
        for n in numbers:
            qty = qty + n
        qty = qty - 1
    
    elif ',' in q:
        qty = q.replace(',','.')
        qty = safe_float(qty)
            
    else:
        cal = safe_float(q)
        if cal is not None:
            qty = cal
        else :
            qty = 0

    # --- STEP 3: Normalize unit ---
    u = u.replace('.', '').strip()

    # Map units → standardized
    if u in ['ML']:
        return qty / 1000, "Liter"

    elif u in ['L', 'LT', 'LITER','L POUCH','LITRE','LTR']:
        return qty, "Liter"

    elif u in ['G', 'GR', 'GRAM']:
        return qty / 1000, "Kilogram"

    elif u in ['KG', 'KILOGRAM', 'K','KGMS','KGS','KILOGRAMS']:
        return qty, "Kilogram"

    elif u in ['CM']:
        return qty / 100, "Meter"

    elif u in ['M', 'METER']:
        return qty, "Meter"

    elif u in ['PCS', 'S', 'BUTIR', 'PACK','BIG SIZEPICES','BOTTLE','BOX','BUAH','BUNCH','CLOVE','COUNT','EGG','EGGS','PC','PCS/TRAY','PIECE','POUCH','WHOLE','PACKET','PS','PICES']:
        return qty, "Pcs"
    
    elif u in ['INCHES','INCH']:
        return qty * 0.0254, "Meter"
    
    elif u in ['COUNT/KG','PCS/KG']: #new 4 may 2026
        qty = 1
        return qty, "Kilogram"
    
    elif u in ['PC / 500G TO 700G']: #new 4 may 2026
        return qty * 0.6, "Kilogram"
    
    elif u in ['PIECE(800-1000GRAM)']: #new 4 may 2026
        return qty * 0.9, "Kilogram"
    
    #25 April 2026: Arabic measurement scale standardized
    elif u in ['بوصة','م','متر']:
        return qty * 0.0254, "Meter" 

    elif u in ['بيضة','حب','حبة','حزمة','ربطة','فخذين','كبسولة','علب','اكياس','كيس','حقنة','قطعة','بذرة','العلبة','قطع','BUAH','GK','HEADS','PASANG','PIECE','أشهر','الحبة','جوهرة','جيجا','حبه','حزمه','حقنه','درج','درجات','ذبيحة','ذهبي هرمي','ربطه','رقم','سلة','صحن','صندوق','صينية','طقم','عبوات','عبوة','علبة','علبه','في','في 1','قرص','قرصاً','كرتون','كيسة مغلفة','مقاعد']: #8th 9th added 26 april 2026, 10th 11th 12th 13th 14th 15th added 27 april 2026
        return qty, "Pcs" 

    elif u in ['طبق','طبق حجم كبير','كيس كبير']:
        return qty, "Carton" 

    elif u in ['ك 10x حبات']:
        return qty / 10, "Pcs" 

    elif u in ['لتر','عبوات 1 لتر','ليتر']:
        return qty, "Liter" 
    
    elif u in ['مليلتر','مل','ملى','ملل','ملليلتر','ملى','مم']: #3rd added on 26 april 2026
        return qty / 1000, "Liter"

    elif u in ['ج','جرام','جم','غ','غرام','غم','ملغ']:
        return qty / 1000, "Kilogram" 

    elif u in ['ريال','ك','كج','كجم','كغ','كغم','كيلو','كيلو (حبة)','كيلو جرام','كيلوجرام','K','ادراج','كليو','كيلوغرام']:
        return qty, "Kilogram" 

    elif u in ['واط']:
        return qty, "Watt"  

    elif u in ['أونصة','أوقية','أونز','أونصات','اونصة']: #new 27 apr 2026
        return qty * 0.02835, "Kilogram"

    elif u in ['مجم']: #new 27 apr 2026
        return qty / 1000, "Kilogram" 
    
    elif u in ['أونصة سائلة']: #new 4 may 2026
        return qty * 0.0295735, "Liter" 
    
    elif u in ['جالون']: #new 4 may 2026
        return qty * 3.78541, "Liter" 
    
    elif u in ['رطل']: #new 4 may 2026
        return qty * 0.453592, "Kilogram"
    
    elif u in ['سم']: #new 4 may 2026
        return qty / 100, "Meter" 
    
    elif u in ['كوارت']: #new 4 may 2026
        return qty * 0.946353, "Liter" 

    elif u in ['كيلو وات']: #new 4 may 2026
        return qty * 1000, "Watt"     
    

    #25 April 2026: Russia measurement scale standardized, on 4 may 2025 added some more units
    elif u in ['кг','КГ','1 КГ','KILO']:
        return qty, "Kilogram" 

    elif u in ['грамм','г','гр','ГРАММ','ГР','Г']:        
        return qty / 1000, "Kilogram" 
    
    elif u in ['л','Л','литр','ЛИТР','LTR','УПАКОВКИ ПО 1 Л']:
        return qty, "Liter" 

    elif u in ['мл','МЛ','ЛИТРА']:
        return qty / 1000, "Liter"

    elif u in ['шт','ШТ','БУТ','ГОД','ЕВРО','ИНДИЯ','КЛАСС','ПОРЦИЯ','ПЭТ','С','С/М','СЕМ','СМ','УПАКОВКА','ШТ/УП','ШТУКА']:
        return qty, "Pcs"
    
    elif u in ['Г /10','ГР/10']:
        return qty / 10, "Kilogram" 
    
    elif u in ['ГРР']:
        return qty * 0.001, "Kilogram"
        
    #25 April 2026: Japan measurement scale standardized, 1 may 2026: edited to add more units found in JP
    elif u in ['リットル','LITRE','LTR']:
        return qty, "Liter" 

    elif u in ['ミリリットル','本(1L)']:
        return qty / 1000, "Liter"
    
    elif u in ['キロ','KG X 袋','KG/袋','KG×6P','KG以上','KG袋','キロ/玉','キロ以上']: #added some on 4 may 2026
        return qty, "Kilogram" 
    
    elif u in ['タイプ','パック','玉','房','P','QUẢ','ケース','セット','タイプ','パック','ボール']: #2 may 2026: added 3rd, 4th
        return qty, "Pcs" 
    
    elif u in ['セット']:
        return qty, "Pcs" 
    
    elif u in ['個','分上','匹','尾','本','束','枚','点','箱','袋']:
        return qty, "Pcs" 
    
    elif u.upper().startswith('G'): #added 2 may 2026
        return qty / 1000, "Kilogram"
    
    elif u in ['250G']: #added 4 may 2026
        return qty * 0.25, "Kilogram"
    
    elif u in ['ポンド']: #added 4 may 2026
        return qty * 0.453592, "Kilogram"

    elif u in ['玉(750G~1KG)']: #added 4 may 2026
        return qty * 0.875, "Kilogram"
    
    elif u in ['箱6〜8本入']: #added 4 may 2026
        return qty * 7, "Pcs"


    #25 April 2026: China measurement scale standardized
    elif u in ['公斤']:
        return qty, "Kilogram" 

    elif u in ['升']:
        return qty, "Liter" 

    elif u in ['克']:
        return qty / 1000, "Kilogram"

    elif u in ['毫升']:
        return qty / 1000, "Liter"       

    #25 April 2026: Thailand measurement scale standardized
    elif u in ['กิโลกรัม','กิโล']:
        return qty, "Kilogram" 
    
    elif u in ['ขีด']:
        return qty * 100 / 1000, "Kilogram" 
    
    elif u in ['กรัม']:
        return qty / 1000, "Kilogram" 
    
    elif u in ['ลิตร','ล','ล.','ทะนาน']:
        return qty, "Liter" 

    elif u in ['มิลลิลิตร','มล','มล.']:
        return qty / 1000, "Liter" 
    
    elif u in ['ถัง']:
        return qty / 20, "Liter"

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

