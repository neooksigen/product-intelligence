# Web Extract, with Tavily
import os
from dotenv import load_dotenv
load_dotenv()

from langchain_tavily import TavilyExtract

import operator
from typing import Annotated
from langgraph.graph import MessagesState
from typing_extensions import TypedDict
from pydantic import BaseModel, Field
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
import re

from scraper.utils import safe_extract_item, normalize_url

from langchain_openai import ChatOpenAI
llm = ChatOpenAI(model="gpt-5.2", temperature=0) 
llm_alt = ChatOpenAI(model="gpt-5-mini", temperature=0) #11 march 2026: for summarization and parsing

import datetime
end_date = datetime.datetime.now().date().strftime('%Y-%m-%d')
start_date = (datetime.datetime.now().date() - datetime.timedelta(days=30)).strftime('%Y-%m-%d')

class ExtractState(TypedDict):
    urls: list[str]
    content: Annotated[list[str], operator.add]
    url: Annotated[list[str], operator.add]
    clean_text_step_01: Annotated[list[str], operator.add]
    clean_text_step_02: Annotated[list[str], operator.add]
    product_name: Annotated[list[str], operator.add]
    quantity: Annotated[list[str], operator.add]
    measurement_scale: Annotated[list[str], operator.add]
    price: Annotated[list[str], operator.add]
    url_per_product: Annotated[list[str], operator.add]
    time_extracted: Annotated[list[str], operator.add]
    nonparsed_response: Annotated[list[str], operator.add] #added 7 mar 2026
    
from tavily import TavilyClient
#from app.config import settings

client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

def extract_tavily_v2(state: ExtractState):
    contents, sources = [], []
    for url in state['urls']:
        url = url.strip() 
        url = normalize_url(url)
        data = client.extract(urls=url, extract_depth='advanced')
        results = data["results"]
        content = [item['raw_content'] for item in results]
        source = [item['url'] for item in results]
        contents.append(content[0] if content else 'Failed')
        sources.append(source[0] if source else 'Failed to extract content on this {url} !'.format(url=url))
    return {"content": contents, 
            "url": sources}   

def tavily_clean_regex(state: ExtractState):
    clean_text_step_01 = []
    for content in state['content']:
        # Remove URLs
        text = re.sub(r'https?://[^\s\[\]]+', '', content)
        # Remove markdown images/links
        text = re.sub(r'!\[.*?\]\(.*?\)| \[.*?\]\(.*?\)', '', text)
        # Remove extra whitespace
        text = re.sub(r'\n\s*\n', '\n\n', text.strip())
        clean_text_step_01.append(text)
    return {"clean_text_step_01": clean_text_step_01}

clean_instructions = """
In this {text}, please find the string following this format : 
[product name] (any string) price
Example:
[SHARON CREAM MESSES 40GR](https://supermarket.yogyaonline.co.id/supermarket/detail/sharon/sharon-cream-messes-40gr/04124801)\n\nRp 4.000 

Please find also find the string following this alternative format : 
[product name] (any string) price (any string) quantity
Example:
Bawang Merah https://ubifresh.id/bawang-merah/19029232 Rp 18,000 img11230099-8989-766788 250 Gram

Then extract the product name and price, and put into this format :
(order sequence of the product for example z1., z2., z3., etc...) product name - price 
(order sequence of the product for example z1., z2., z3., etc...) product name quantity - price
Example:
z1. SHARON CREAM MESSES 40GR - Rp 4.000 (You must put z1. into the first product you find ! That is imperative !)
z2. Bawang Merah 250 Gram - Rp 18,000
Do not include those examples into the result. They are just example, not actual data !

You are just instructed to extract product name and price information from the {text}. 
You are not allowed to extract other kind of information from the {text}.
"""

def tavily_clean_remains(state: ExtractState):
    clean_text_step_02 = []
    for content in state['clean_text_step_01']:
        prompt = clean_instructions.format(text=content)
        ct = llm.invoke(prompt).content #the content will be raw text, because the prompt doesn't instruct to format as JSON list
        clean_text_step_02.append(ct)
    return {"clean_text_step_02": clean_text_step_02}

parse_instructions = """ 
In this {product_detail}, you will find string with the format: 

PRODUCT NAME QUANTITY MEASUREMENT SCALE - PRICE

Example:
ULTRA MILK CHOCOLATE MILK 1L - RP 20.000
AYAM HATI 250GR - RP 6.500
AYAM BROILER 1 EKOR - RP 30.000 (HARGA SPESIAL)
READY TO COOK PAKET CHICKEN STEAK - RP 35.500

PRODUCT NAME will be ULTRA MILK CHOCOLATE MILK, AYAM HATI, AYAM BROILER, READY TO COOK PAKET CHICKEN STEAK .
QUANTITY will be 1, 250, 1, None (don't have) .
MEASUREMENT SCALE will be L, GR, EKOR, None (don't have) .
PRICE will be RP 20.000, RP 6.500, RP 30.000, RP 35.500 .

Following example above (but please do not include the example into these product_name, quantity, measurement_scale, price variables below !), 
you have to parse the {product_detail} into PRODUCT NAME, QUANTITY, MEASUREMENT SCALE, PRICE:
1. product_name : PRODUCT NAME
2. quantity : QUANTITY
3. measurement_scale : MEASUREMENT SCALE
4. price : PRICE 

Format as JSON list only.
"""

class ParseResults(BaseModel):
    product_name: list[str] = Field(description= "Product name.")
    quantity: list[str] = Field(description= "Minimum quantity per product to be purchased.")
    measurement_scale: list[str] = Field(description= "Scale of quantity such as GR, L, EKOR, ML, etc.")
    price: list[str] = Field(description= "Product price.")

def tavily_parse(state: ExtractState):
    product_name_list = [] 
    quantity_list = []
    measurement_scale_list = []
    price_list = []
    url_per_product_list = []
    time_extracted_list = []
    nonparsed_response_list = [] #added 7 mar 2026

    # Find positions of \n1, \n2, \n3, etc.
    product_lines = []
    for ind_text in state['clean_text_step_02']:
        for i in range(1, 1000):  # Check up to 999 products
            marker = f'z{i}.' #previous: f'\n{i}.'
            pos = ind_text.find(marker)
            if pos != -1:
                # Find end position (next \n or end of text)
                end_pos = ind_text.find('\n', pos + len(marker))
                if end_pos == -1:
                    end_pos = len(ind_text)
        
                product_lines.append({
                    'number': i,
                    'marker': marker,
                    'start_pos': pos,
                    'end_pos': end_pos,
                    'content': ind_text[pos:end_pos].strip()
                })
    
    # Extract product name, quantity, measurement scale, price
    for item in product_lines:
        product_details = item['content'].strip().upper()
        prompt = parse_instructions.format(product_detail=product_details)
        response = llm_alt.with_structured_output(ParseResults).invoke(prompt)
        a = safe_extract_item(response.product_name)
        b = safe_extract_item(response.quantity)
        c = safe_extract_item(response.measurement_scale)
        d = safe_extract_item(response.price)
        e = safe_extract_item(state['url'])
        product_name_list.append(a)
        quantity_list.append(b)
        measurement_scale_list.append(c)
        price_list.append(d)
        url_per_product_list.append(e)
        time_extracted_list.append(datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M'))
        nonparsed_response_list.append(safe_extract_item(product_details))

    return {"product_name": product_name_list, "quantity": quantity_list, "measurement_scale": measurement_scale_list,
           "price": price_list, "url_per_product": url_per_product_list, "time_extracted": time_extracted_list,
           "nonparsed_response": nonparsed_response_list}

from app.database_sqlalchemy import SessionLocal
from app.tables import Product
from itertools import zip_longest

def insert_to_table(state: ExtractState):
    #remaining columns to be filled in --->
    rating_list = []
    review_count_list = []
    place_list = []
    method_list = []
    source_date_list = []
    question_list = []
    owner_id_list = []
    for i in range(len(state["product_name"])):
        rating_list.append(None)
        review_count_list.append(None)
        place_list.append('Indonesia')
        method_list.append('Tavily extracts target URL')
        source_date_list.append(None)
        question_list.append(None)
        owner_id_list.append(os.getenv("DB_OWNER_ID_00"))

    db = SessionLocal()
    try:
        for product_name, quantity, measurement_scale, price, source, rating, review_count, place, method, source_date, timestamp_extract, questions, nonparsed_response, owner_id in zip_longest(
            state['product_name'], 
            state['quantity'],
            state['measurement_scale'],
            state['price'],
            state['url_per_product'],
            rating_list,
            review_count_list,
            place_list,
            method_list,
            source_date_list,
            state['time_extracted'],
            question_list,
            state['nonparsed_response'],
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
                nonparsed_response = nonparsed_response,
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

graph_extract = StateGraph(ExtractState)
graph_extract.add_node("extract_tavily", extract_tavily_v2)
graph_extract.add_node("tavily_clean_regex", tavily_clean_regex)
graph_extract.add_node("tavily_clean_remains", tavily_clean_remains)
graph_extract.add_node("tavily_parse", tavily_parse)
graph_extract.add_node("insert_to_table", insert_to_table)
graph_extract.add_edge(START, "extract_tavily")
graph_extract.add_edge("extract_tavily", "tavily_clean_regex")
graph_extract.add_edge("tavily_clean_regex", "tavily_clean_remains")
graph_extract.add_edge("tavily_clean_remains", "tavily_parse")
graph_extract.add_edge("tavily_parse", "insert_to_table")
graph_extract.add_edge("insert_to_table", END)

app_extract = graph_extract.compile()
