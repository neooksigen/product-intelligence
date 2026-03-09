#Google Shopping Scrapper
import os
from dotenv import load_dotenv
load_dotenv()

import operator
from typing import Annotated
from langgraph.graph import MessagesState
from typing_extensions import TypedDict
from pydantic import BaseModel, Field
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
import re
import http.client
import json
import requests
from urllib.parse import urlencode

from scraper.utils import safe_extract_item

from langchain_openai import ChatOpenAI
llm = ChatOpenAI(model="gpt-5.2", temperature=0) 

import datetime
end_date = datetime.datetime.now().date().strftime('%Y-%m-%d')
start_date = (datetime.datetime.now().date() - datetime.timedelta(days=30)).strftime('%Y-%m-%d')

class GoogleShoppingState(TypedDict):
    user_ask: str
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

#from app.config import settings

def s_extract(state: GoogleShoppingState):
    url = "https://google.serper.dev/shopping"
    payload = {
      "q": state['user_ask'],
      "gl": "id",
      "hl": "id",
      "num": 40
    }
    headers = {
      'X-API-KEY': os.getenv("SERPER_API_KEY"), #The argument name is X-API-KEY, don't change it
      'Content-Type': 'application/json'        
    }
    response = requests.request("POST", url, headers=headers, json=payload)
    serper_data_01 = json.loads(response.text) #json.loads to convert into json tidyly, good for extraction later
    serper_data_02 = serper_data_01.get('shopping')
    s_list_title = []
    s_list_source = []
    s_list_price = []
    s_list_rating = [] 
    s_list_ratingcount = []
    s_list_timestamp_extract = []
    s_list_method = []
    for item in serper_data_02:
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
    API_KEY = os.getenv("BRIGHTDATA_API_KEY") #need this exactly name API_KEY 9 mar 2026
    ZONE_NAME = "serp_api1" #need this exactly name ZONE_NAME 9 mar 2026

    query_params = {
        "q": state['user_ask'],
        "udm": '28',    
        #"hl": "id",   # language = Indonesian
        "gl": "id",   # country = Indonesia
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
    bd_list_title = []
    bd_list_price = []
    bd_list_shop = []
    bd_list_rating = []
    bd_list_reviews_cnt = []
    bd_list_timestamp_extract = []
    bd_list_method = []    
    for item in brightdata_results_02 :
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

title_processing_instructions = """ In this {title} you will find string with format :

PRODUCT NAME QUANTITY MEASUREMENT SCALE 

Example :
Mangga madu 1 kg
Jeruk california 5 buah
Daging ayam paha 1 ekor

PRODUCT NAME will be Mangga madu, Jeruk california, Daging ayam paha .
QUANTITY will be 1, 5, 1 .
MEASUREMENT SCALE will be kg, buah, ekor .

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
    state['all_title'] = state['s_title'] + state['bd_title'] 
    product_name_list = []
    quantity_list = []
    measurement_scale_list = []
    item_list = [] 
    for item in state['all_title']:
        prompt = title_processing_instructions.format(title=item)
        response = llm.with_structured_output(TitleParseResults).invoke(prompt)
        product_name_list.append(safe_extract_item(response.product_name))
        quantity_list.append(safe_extract_item(response.quantity))
        measurement_scale_list.append(safe_extract_item(response.measurement_scale)) 
        item_list.append(safe_extract_item(item))

    return {"product_name": product_name_list, 
        "quantity": quantity_list, 
        "measurement_scale": measurement_scale_list, 
           "price": state['s_price'] + state['bd_price'], 
           "source": state['s_source'] + state['bd_shop'], 
           "rating": state['s_rating'] + state['bd_rating'], 
           "review_count": state['s_ratingcount'] + state['bd_reviews_cnt'],
           "all_method": state['s_method'] + state['bd_method'], 
            "all_timestamp_extract": state['s_timestamp_extract'] + state['bd_timestamp_extract'],
            "all_title_final": item_list}

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
        place_list.append("Indonesia")
        source_date_list.append(None)
        question_list.append(safe_extract_item(state['user_ask']))
        owner_id_list.append(os.getenv("DB_OWNER_ID_00"))

    db = SessionLocal()
    try:
        for product_name, quantity, measurement_scale, price, source, rating, review_count, place, method, source_date, timestamp_extract, questions, nonparsed_response, owner_id in zip_longest(
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
            owner_id_list
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
                owner_id = owner_id
            )

            db.add(new_product)

        db.commit()
        print(">>> Commit Successful !")
    
    except Exception as e:
        db.rollback()
        print("Error:", e)
        raise
    
    finally:
        db.close()

    return state

from langgraph.graph import END, StateGraph, START

graph_gsc = StateGraph(GoogleShoppingState)
graph_gsc.add_node("s_extract", s_extract)
graph_gsc.add_node("bd_extract", bd_extract)
graph_gsc.add_node("gs_next_processing", gs_next_processing)
graph_gsc.add_node("insert_to_table", insert_to_table)
graph_gsc.add_edge(START, "s_extract")
graph_gsc.add_edge(START, "bd_extract")
graph_gsc.add_edge(["s_extract","bd_extract"], "gs_next_processing")
#graph_gsc.add_edge("s_extract","gs_next_processing")
graph_gsc.add_edge("gs_next_processing", "insert_to_table")
graph_gsc.add_edge("insert_to_table", END)

app_gsc = graph_gsc.compile()
