#Google Shopping Scrapper
import os
from dotenv import load_dotenv
load_dotenv()

import operator
from typing import Annotated
from langgraph.graph import MessagesState
from typing_extensions import TypedDict
from pydantic import BaseModel, Field
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, trim_messages #added 26 march 2026 but not sure if this works to reduce output token cost
import re
import http.client
import json
import requests
from urllib.parse import urlencode

from scraper.utils import safe_extract_item, normalize_url, parse_price, standardize_quantity, get_latest_exchange_rate #added 24 march 2026

import pandas as pd #added 24 march 2026
import numpy as np #added 24 march 2026

from langchain_openai import ChatOpenAI
llm = ChatOpenAI(model="gpt-5.2", temperature=0, model_kwargs={"response_format": {"type": "json_object"}})
llm_alt = ChatOpenAI(model="gpt-5-mini", temperature=0, model_kwargs={"response_format": {"type": "json_object"}}) #11 march 2026: for summarization and parsing #26 march 2026: model tune up to further reduce output token cost

import datetime
end_date = datetime.datetime.now().date().strftime('%Y-%m-%d')
start_date = (datetime.datetime.now().date() - datetime.timedelta(days=30)).strftime('%Y-%m-%d')

class GoogleShoppingState(TypedDict):
    user_ask: str
    country: str #country, added 24 mar 2026    
    s_title: Annotated[list[str], operator.add]
    s_source: Annotated[list[str], operator.add]
    s_price: Annotated[list[str], operator.add]
    s_rating: Annotated[list[str], operator.add]
    s_ratingcount: Annotated[list[str], operator.add]
    s_timestamp_extract: Annotated[list[str], operator.add]
    s_method: Annotated[list[str], operator.add]
    bd_title: Annotated[list[str], operator.add]
    bd_shop: Annotated[list[str], operator.add]
    bd_price: Annotated[list[str], operator.add]
    bd_rating: Annotated[list[str], operator.add]
    bd_reviews_cnt: Annotated[list[str], operator.add]
    bd_timestamp_extract: Annotated[list[str], operator.add]
    bd_method: Annotated[list[str], operator.add] 
    all_title_final: Annotated[list[str], operator.add]
    all_title: Annotated[list[str], operator.add]
    product_name: Annotated[list[str], operator.add]
    quantity: Annotated[list[str], operator.add]
    measurement_scale: Annotated[list[str], operator.add]
    price: Annotated[list[str], operator.add]
    source: Annotated[list[str], operator.add]
    rating: Annotated[list[str], operator.add]
    review_count: Annotated[list[str], operator.add]
    all_method: Annotated[list[str], operator.add]
    all_timestamp_extract: Annotated[list[str], operator.add]
    country_per_product: Annotated[list[str], operator.add] #added 23 march 2026
    product_name_en: Annotated[list[str], operator.add] #added 20 mar 2026
    measurement_scale_standardized: Annotated[list[str], operator.add] #added 20 mar 2026
    quantity_standardized: Annotated[list[float], operator.add] #added 20 mar 2026
    price_local: Annotated[list[float], operator.add] #added 20 mar 2026
    price_usd: Annotated[list[float], operator.add] #added 20 mar 2026
    price_eur: Annotated[list[float], operator.add] #added 20 mar 2026
    price_chf: Annotated[list[float], operator.add] #added 20 mar 2026
    price_jpy: Annotated[list[float], operator.add] #added 20 mar 2026
    price_cny: Annotated[list[float], operator.add] #added 20 mar 2026
    price_aud: Annotated[list[float], operator.add] #added 20 mar 2026
    price_sgd: Annotated[list[float], operator.add] #added 20 mar 2026                        
    product_category: Annotated[list[str], operator.add] #added 20 mar 2026          

#from app.config import settings

#24 march 2026: add mapping country and gl to automatically select correct gl based on country. To be used in node s_extract & bd_extract.
dummy_country_gl_mapping = pd.DataFrame({
    "country": ["United States", "Brazil", "Argentina", "Chile", "United Kingdom", "France", "Germany", "Algeria", "Tanzania", "South Africa", "Saudi Arabia",
    "Iraq","Russia","Japan","China","India","Thailand","Indonesia","Singapore","Australia","New Zealand"],
    "gl": ["us", "br", "ar", "cl", "gb", "fr", "de", "dz", "tz", "za", "sa", 
    "iq", "ru", "jp", "cn", "in", "th", "id", "sg", "au", "nz"]
})

def s_extract(state: GoogleShoppingState):
    gl_selected = dummy_country_gl_mapping[dummy_country_gl_mapping["country"] == safe_extract_item(state["country"])].loc[:,"gl"].values[0]
    url = "https://google.serper.dev/shopping"
    payload = {
      "q": state['user_ask'],
      "gl": gl_selected, #enhanced 24 mar 2026
      #"hl": "id", #inactivate this 19 mar 2026
      "num": 40
    }
    headers = {
      'X-API-KEY': os.getenv("SERPER_API_KEY"), #The argument name is X-API-KEY, don't change it
      'Content-Type': 'application/json'        
    }
    response = requests.request("POST", url, headers=headers, json=payload)
    serper_data_01 = json.loads(response.text) #json.loads to convert into json tidyly, good for extraction later
    serper_data_02 = serper_data_01.get('shopping')
    #25 march 2026: take just 15 results from Google Shopping, to reduce cost on llm
    #3 april 2026: increase to 20, because BD is deactivated
    if len(serper_data_02) >= 20 :
        rand_i = np.random.choice(range(0,len(serper_data_02)), size=20, replace=False).tolist()
        serper_data_03 = [serper_data_02[i] for i in rand_i]
        #serper_data_03 = serper_data_02[0:15]
    else : 
        serper_data_03 = serper_data_02
    #serper_data_03 = serper_data_02 #for testing only, use all crawl GS result 26 apr 2026
    s_list_title = []
    s_list_source = []
    s_list_price = []
    s_list_rating = [] 
    s_list_ratingcount = []
    s_list_timestamp_extract = []
    s_list_method = []
    for item in serper_data_03:
        s_list_title.append(item.get('title')) 
        s_list_source.append(item.get('source'))
        pie = item.get('price')
        pie_nxt = pie.replace("\xa0", " ")
        s_list_price.append(pie_nxt)
        s_list_rating.append(item.get('rating'))
        s_list_ratingcount.append(item.get('ratingCount')) 
        s_list_timestamp_extract.append(datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M'))
        s_list_method.append('Serper API, extract Google Shopping')
    return {"s_title": s_list_title, "s_source": s_list_source, "s_price": s_list_price, 
            "s_rating": s_list_rating, "s_ratingcount": s_list_ratingcount, "s_timestamp_extract": s_list_timestamp_extract,
            "s_method": s_list_method}

def bd_extract(state: GoogleShoppingState):
    gl_selected = dummy_country_gl_mapping[dummy_country_gl_mapping["country"] == safe_extract_item(state["country"])].loc[:,"gl"].values[0]    
    API_KEY = os.getenv("BRIGHTDATA_API_KEY") #need this exactly name API_KEY 9 mar 2026
    ZONE_NAME = "serp_api1" #need this exactly name ZONE_NAME 9 mar 2026

    query_params = {
        "q": state['user_ask'],
        "udm": '28',    
        #"hl": "id",   # language = Indonesian
        "gl": gl_selected,   # country = Indonesia
        #"tbm": "shop" # inactivate 9 Mar 2026, there was change on Google side informed by Bright Data agent
        "brd_json": '1' # advised by Bright Data agent 9 Mar 2026
    }
    google_url = "https://www.google.com/search?" + urlencode(query_params)
    endpoint = "https://api.brightdata.com/request"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "zone": ZONE_NAME,  # your SERP API name
        "url": google_url,
        "format": "raw",    # 9 mar 2026 change from json to raw
        "data_format": "parsed_light" # as suggested by Bright Data agent 9 mar 2026
    }
    response = requests.post(endpoint, headers=headers, json=payload, timeout=120)
    response.raise_for_status()
    brightdata_data = response.json()
    brightdata_results_02 = brightdata_data.get('shopping')
    # 26 mar 2026: take just 15 results from Google Shopping, to reduce llm output cost later
    if len(brightdata_results_02) >= 15:
        rand_i = np.random.choice(range(0,len(brightdata_results_02)), size=15, replace=False).tolist()
        brightdata_results_03 = [brightdata_results_02[i] for i in rand_i]        
        #brightdata_results_03 = brightdata_results_02[0:15]
    else : 
        brightdata_results_03 = brightdata_results_02
    bd_list_title = []
    bd_list_price = []
    bd_list_shop = []
    bd_list_rating = []
    bd_list_reviews_cnt = []
    bd_list_timestamp_extract = []
    bd_list_method = []    
    for item in brightdata_results_03 :
        bd_list_title.append(item.get('title'))
        pie_bd = item.get('price')
        pie_bd_nxt = pie_bd.replace("\xa0", " ")        
        bd_list_price.append(pie_bd_nxt)
        bd_list_shop.append(item.get('shop'))
        bd_list_rating.append(item.get('rating'))
        bd_list_reviews_cnt.append(item.get('reviews_cnt'))
        bd_list_timestamp_extract.append(datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M'))
        bd_list_method.append('Bright Data API, extract Google Shopping')
    return {"bd_title": bd_list_title, "bd_price": bd_list_price, "bd_shop": bd_list_shop, "bd_rating": bd_list_rating, 
           "bd_reviews_cnt": bd_list_reviews_cnt, "bd_timestamp_extract": bd_list_timestamp_extract, "bd_method": bd_list_method}

#enhanced 5 may 2026: enhance title processing after found many cases multiple quantity & measurement scale (last 5 examples)
#enhanced 14 may 2026: to include case product without ms and quantity, to not include mangga madu to data !!!!
title_processing_instructions = """ In this {title} you will find string with format :

PRODUCT NAME QUANTITY MEASUREMENT SCALE 

Example :
Mangga madu 1 kg
Jeruk california 5 buah
Daging ayam paha 1 ekor
Rice 1 bag (750G~1KG)
Lemon Grass Leaves - 100 % Natural & Farm Fresh - 1 Bunch (100Gms)
Watermelon (Tarbooz) - (Per Piece) (2.5Kg to 3Kg)From Kapil Fresh Vegetables
Freshwater Prawns / రొయ్యలు - 50-60 Count/Kg
Cauliflower - 1piece(800-1000gram)
Chocolate

PRODUCT NAME will be Mangga madu, Jeruk california, Daging ayam paha, Rice, Lemon Grass Leaves - 100 % Natural & Farm Fresh, Watermelon (Tarbooz), Freshwater Prawns, Cauliflower, Chocolate .
QUANTITY will be 1, 5, 1, 1 X 0.875, 1 X 0.1, 1 X 2.75, 1 X 1, 1 X 0.9, 0 .
MEASUREMENT SCALE will be kg, buah, ekor, kg, kg, kg, kg, kg, unknown.

Following example above (but please do not include the example into these product_name, quantity, measurement_scale variables below !), 
you have to parse the {title} into PRODUCT NAME, QUANTITY, MEASUREMENT SCALE :
1. product_name : PRODUCT NAME
2. quantity : QUANTITY 
3. measurement_scale : MEASUREMENT SCALE 

Format as JSON list only.
"""

class TitleParseResults(BaseModel):
    product_name: list[str] = Field(description= "Product name.")
    quantity: list[str] = Field(description= "Minimum quantity per product to be purchased.")
    measurement_scale: list[str] = Field(description= "Scale of quantity such as GR, L, EKOR, BUAH, ML, etc.")

def gs_next_processing(state: GoogleShoppingState):
    state['all_title'] = state['s_title'] #+ state['bd_title'] #3 april 2026: BD is not available on certain countries. Also to reduce cost, then BD will be deactivated.
    product_name_list = []
    quantity_list = []
    measurement_scale_list = []
    item_list = []
    country_per_product_list = [] #24 march 2026: added 
    for item in state['all_title']:
        prompt = title_processing_instructions.format(title=item)
        response = llm_alt.with_structured_output(TitleParseResults).invoke(prompt) #24 march 2026: use llm_alt for cheaper & faster result !
        product_name_list.append(safe_extract_item(response.product_name))
        quantity_list.append(safe_extract_item(response.quantity))
        measurement_scale_list.append(safe_extract_item(response.measurement_scale)) 
        item_list.append(safe_extract_item(item))
        country_per_product_list.append(state['country']) #added 24 march 2026

    return {"product_name": product_name_list, 
        "quantity": quantity_list, 
        "measurement_scale": measurement_scale_list, 
           "price": state['s_price'], #+ state['bd_price'], 
           "source": state['s_source'], #+ state['bd_shop'], 
           "rating": state['s_rating'], #+ state['bd_rating'], 
           "review_count": state['s_ratingcount'], #+ state['bd_reviews_cnt'],
           "all_method": state['s_method'], #+ state['bd_method'], 
            "all_timestamp_extract": state['s_timestamp_extract'], #+ state['bd_timestamp_extract'],
            "all_title_final": item_list, 
            "country_per_product": country_per_product_list}

#new 24 march 2026: translate - categorize - standardize - price conversion, similar to graph_extract
translate_instructions = """ 

You will receive {product_name} .

Please help to translate this {product_name} into English version appropriately. 
Brand name inside {product_name} should not be translated.

Output into: 
1. product_name_en: translation result

Format as JSON list only.

"""

categorize_instructions = """
You will receive {product_name}.
Based on {product_name}, please help to categorize the product into well known product category. 
Well known product category example: rice, egg, chicken meat, beef, vegetable, fruit, seasoning, crackers, drinks, sweets, soap, shampoo, kitchen cleaner, etc.

Output into:
1. product_category : product categorization result

Format as JSON list only.

"""

class TranslateResults(BaseModel):
    product_name_en: list[str] = Field(description= "Product name English version.") 

class ProductCategoryResults(BaseModel):
    product_category : list[str] = Field(description= "Product category determined based on product name and url. Example product category: rice, egg, chicken meat, beef, vegetable, fruit, seasoning, crackers, drinks, sweets, soap, shampoo, kitchen cleaner, etc.")


def next_translate(state: GoogleShoppingState):
    product_name_en_list = []
    for item in state['product_name']:
        prompt_a = translate_instructions.format(product_name=item) #21 mar 2026 1:26 AM -> revise this to product_name=item !!!
        response_a = llm_alt.with_structured_output(TranslateResults).invoke(prompt_a)
        product_name_en_list.append(safe_extract_item(response_a.product_name_en))

    return {"product_name_en": product_name_en_list}

def next_productcategorization(state: GoogleShoppingState):
    product_category_list = []
    for a in state['product_name']:
        prompt = categorize_instructions.format(product_name=a)
        response = llm_alt.with_structured_output(ProductCategoryResults).invoke(prompt)
        product_category_list.append(safe_extract_item(response.product_category))

    return {"product_category": product_category_list}

def next_quantity_standardize(state: GoogleShoppingState):
    results = [
        standardize_quantity(q, u) for q, u in zip(state['quantity'], state['measurement_scale'])
    ]
    quantity_std = [r[0] for r in results]
    measurement_scale_std = [r[1] for r in results]

    return {"quantity_standardized": quantity_std, "measurement_scale_standardized": measurement_scale_std}

def next_price_currency_conversion(state: GoogleShoppingState):
    price_usd_list = []
    price_eur_list = []
    price_chf_list = []
    price_jpy_list = []
    price_cny_list = []
    price_aud_list = []
    price_sgd_list = []
    exchange_rate_table = get_latest_exchange_rate()
    price_local = [
        parse_price(m)["fin"] for m in state['price'] #29 mar 2026: parse_price def was just edited, use fin to get final value
    ]
    dummy_country_fbc_mapping = pd.DataFrame({
        "country":["United States", "Brazil", "Argentina", "Chile", "United Kingdom", "France", "Germany", "Algeria", "Tanzania", "South Africa", "Saudi Arabia",
        "Iraq","Russia","Japan","China","India","Thailand","Indonesia","Singapore","Australia","New Zealand"],
        "from_base_code":['USD','BRL','ARS', 'CLP', 'GBP', 'EUR','EUR', 'DZD', 'TZS', 'ZAR', 'SAR', 
        'IQD', 'RUB', 'JPY', 'CNY', 'INR', 'THB', 'IDR', 'SGD', 'AUD', 'NZD']
    })
    for x, y in zip(price_local, state['country_per_product']):
        fbc = dummy_country_fbc_mapping[dummy_country_fbc_mapping['country'] == safe_extract_item(y)].loc[:,"from_base_code"].values[0]
        er_usd = exchange_rate_table[(exchange_rate_table["from_base_code"] == fbc) & (exchange_rate_table["to_currency"] == "USD")].loc[:,"exchange_rate"].values[0]
        price_usd = er_usd * x
        price_usd_list.append(round(float(price_usd),3)) #23 mar 2026: need to use this round & float to convert np.float64 to float 3 decimals
        er_eur = exchange_rate_table[(exchange_rate_table["from_base_code"] == fbc) & (exchange_rate_table["to_currency"] == "EUR")].loc[:,"exchange_rate"].values[0]
        price_eur = er_eur * x
        price_eur_list.append(round(float(price_eur),3))
        er_chf = exchange_rate_table[(exchange_rate_table["from_base_code"] == fbc) & (exchange_rate_table["to_currency"] == "CHF")].loc[:,"exchange_rate"].values[0]
        price_chf = er_chf * x
        price_chf_list.append(round(float(price_chf),3))            
        er_jpy = exchange_rate_table[(exchange_rate_table["from_base_code"] == fbc) & (exchange_rate_table["to_currency"] == "JPY")].loc[:,"exchange_rate"].values[0]
        price_jpy = er_jpy * x
        price_jpy_list.append(round(float(price_jpy),3))
        er_cny = exchange_rate_table[(exchange_rate_table["from_base_code"] == fbc) & (exchange_rate_table["to_currency"] == "CNY")].loc[:,"exchange_rate"].values[0]
        price_cny = er_cny * x
        price_cny_list.append(round(float(price_cny),3))  
        er_aud = exchange_rate_table[(exchange_rate_table["from_base_code"] == fbc) & (exchange_rate_table["to_currency"] == "AUD")].loc[:,"exchange_rate"].values[0]
        price_aud = er_aud * x
        price_aud_list.append(round(float(price_aud),3))
        er_sgd = exchange_rate_table[(exchange_rate_table["from_base_code"] == fbc) & (exchange_rate_table["to_currency"] == "SGD")].loc[:,"exchange_rate"].values[0]
        price_sgd = er_sgd * x
        price_sgd_list.append(round(float(price_sgd),3))
    
    return {"price_local": price_local, "price_usd": price_usd_list, "price_eur": price_eur_list, "price_chf": price_chf_list, "price_jpy": price_jpy_list,
            "price_cny": price_cny_list, "price_aud": price_aud_list, "price_sgd": price_sgd_list}


from app.database_sqlalchemy import SessionLocal
from app.tables import Product
from itertools import zip_longest

def insert_to_table(state: GoogleShoppingState):
    #remaining columns to be filled in --->
    place_list = []
    source_date_list = []
    question_list = [] 
    owner_id_list = []
    for i in range(len(state['product_name'])):
        place_list.append(state['country']) #edited on 3 april 2026
        source_date_list.append(None)
        question_list.append(safe_extract_item(state['user_ask']))
        owner_id_list.append(os.getenv("DB_OWNER_ID_00"))

    db = SessionLocal()
    try:
        for product_name, quantity, measurement_scale, price, source, rating, review_count, place, method, source_date, timestamp_extract, questions, nonparsed_response, product_name_en, measurement_scale_standardized, quantity_standardized, price_local, price_usd, price_eur, price_chf, price_jpy, price_cny, price_aud, price_sgd, product_category, owner_id, country in zip_longest(
            state['product_name'], 
            state['quantity'],
            state['measurement_scale'],
            state['price'],
            state['source'],
            state['rating'],
            state['review_count'],
            place_list,
            state['all_method'],
            source_date_list,
            state['all_timestamp_extract'],
            question_list,
            state['all_title_final'],
            state['product_name_en'],
            state['measurement_scale_standardized'],
            state['quantity_standardized'],
            state['price_local'],
            state['price_usd'],
            state['price_eur'],
            state['price_chf'],
            state['price_jpy'],
            state['price_cny'],
            state['price_aud'],
            state['price_sgd'],                        
            state['product_category'],              
            owner_id_list,
            state['country_per_product']
            ) : 

            new_product = Product(
                product_name = product_name,
                quantity = quantity,
                measurement_scale = measurement_scale,
                price = price,
                source = source,
                rating = rating,
                review_count = review_count,
                place = place,
                method = method,
                source_date = source_date,
                timestamp_extract = timestamp_extract,
                questions = questions,
                nonparsed_response = nonparsed_response, #added 7 mar 2026 
                product_name_en = product_name_en,
                measurement_scale_standardized = measurement_scale_standardized,
                quantity_standardized = quantity_standardized,
                price_local = price_local,
                price_usd = price_usd,
                price_eur = price_eur,
                price_chf = price_chf,
                price_jpy = price_jpy,
                price_cny = price_cny,
                price_aud = price_aud,
                price_sgd = price_sgd,
                product_category = product_category,                  
                owner_id = owner_id,
                country = country #added 3 apr 2026
            )

            db.add(new_product)

        db.commit()
        print(">>> Insert data to table products using app_gsc is successful !")
    
    except Exception as e:
        db.rollback()
        print("Error:", e)
        raise
    
    finally:
        db.close()

    #return state #24 march 2026 no need to return state as this node is to insert data !

from langgraph.graph import END, StateGraph, START

graph_gsc = StateGraph(GoogleShoppingState)
graph_gsc.add_node("s_extract", s_extract)
#graph_gsc.add_node("bd_extract", bd_extract)
graph_gsc.add_node("gs_next_processing", gs_next_processing)
graph_gsc.add_node("next_translate", next_translate)
graph_gsc.add_node("next_productcategorization", next_productcategorization)
graph_gsc.add_node("next_quantity_standardize", next_quantity_standardize)
graph_gsc.add_node("next_price_currency_conversion", next_price_currency_conversion)
graph_gsc.add_node("insert_to_table", insert_to_table)
graph_gsc.add_edge(START, "s_extract")
#graph_gsc.add_edge(START, "bd_extract")
#graph_gsc.add_edge(["s_extract","bd_extract"], "gs_next_processing")
graph_gsc.add_edge("s_extract","gs_next_processing")
graph_gsc.add_edge("gs_next_processing", "next_translate")
graph_gsc.add_edge("next_translate", "next_productcategorization")
graph_gsc.add_edge("next_productcategorization", "next_quantity_standardize")
graph_gsc.add_edge("next_quantity_standardize", "next_price_currency_conversion")
graph_gsc.add_edge("next_price_currency_conversion", "insert_to_table")
graph_gsc.add_edge("insert_to_table", END)

app_gsc = graph_gsc.compile()
