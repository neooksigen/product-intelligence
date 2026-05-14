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

from scraper.utils import safe_extract_item, normalize_url, parse_price, standardize_quantity, get_latest_exchange_rate

from langchain_openai import ChatOpenAI
llm = ChatOpenAI(model="gpt-5.2", temperature=0) 
llm_alt = ChatOpenAI(model="gpt-5-mini", temperature=0) #11 march 2026: for summarization and parsing

import datetime
end_date = datetime.datetime.now().date().strftime('%Y-%m-%d')
start_date = (datetime.datetime.now().date() - datetime.timedelta(days=30)).strftime('%Y-%m-%d')

import pandas as pd #added 23 march 2026
import numpy as np #added 23 march 2026

class ExtractState(TypedDict):
    urls: list[str]
    countries: list[str] #added 20 mar 2026
    content: Annotated[list[str], operator.add]
    url: Annotated[list[str], operator.add]
    country: Annotated[list[str], operator.add] #added 20 mar 2026
    clean_text_step_01: Annotated[list[str], operator.add]
    clean_text_step_02: Annotated[list[str], operator.add]
    product_name: Annotated[list[str], operator.add]
    quantity: Annotated[list[str], operator.add]
    measurement_scale: Annotated[list[str], operator.add]
    price: Annotated[list[str], operator.add]
    url_per_product: Annotated[list[str], operator.add]
    time_extracted: Annotated[list[str], operator.add]
    nonparsed_response: Annotated[list[str], operator.add] #added 7 mar 2026
    country_per_product: Annotated[list[str], operator.add] #added 20 mar 2026
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
    
from tavily import TavilyClient
#from app.config import settings

client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

import time 

def extract_tavily_v2(state: ExtractState):
    contents = [] 
    sources = []
    countries = [] 
    for url in state['urls']:
        url_mod = url.strip() 
        url_mod = normalize_url(url_mod) #24 march 2026: use url_mod for extraction. For idx, keep using original url.        
        try:
            data = client.extract(urls=url_mod, extract_depth='advanced', timeout=60) #14 mar 2026: allow waiting 60 seconds to extract URL.
            results = data["results"]
            content = [item['raw_content'] for item in results]
            source = [item['url'] for item in results]
            contents.append(content[0] if content else 'Failed')
            sources.append(source[0] if source else 'Failed to extract content on this {url} !'.format(url=url))
            idx = state['urls'].index(url)
            country = state['countries'][idx]
            countries.append(country)
            break 
        except Exception as e:
            contents.append('Failed')
            sources.append('Failed to extract content on this {url} !'.format(url=url))
            idx = state['urls'].index(url)
            country = state['countries'][idx] 
            countries.append(country)               
            #raise 
            time.sleep(10)

    return {"content": contents, 
            "url": sources,
            "country": countries}   #21 march 2026: return state will not generate output token cost. And this return state is important, otherwise the state will be blank !

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
        ct = llm_alt.invoke(prompt).content #the content will be raw text, because the prompt doesn't instruct to format as JSON list #14 mar 2026: use llm_alt for cheaper cost
        clean_text_step_02.append(ct)
      
    return {"clean_text_step_02": clean_text_step_02} 

#enhanced 5 may 2026: enhance title processing after found many cases multiple quantity & measurement scale (last 5 examples) in graph_gsc.
#enhanced 14 may 2026: to include case product without ms and quantity, to not include mangga madu to data !!!!
parse_instructions = """ 
In this {product_detail}, you will find string with the format: 

PRODUCT NAME QUANTITY MEASUREMENT SCALE - PRICE

Example:
ULTRA MILK CHOCOLATE MILK 1L - RP 20.000
AYAM HATI 250GR - RP 6.500
AYAM BROILER 1 EKOR - RP 30.000 (HARGA SPESIAL)
READY TO COOK PAKET CHICKEN STEAK - RP 35.500
HAAGENDAZS PISTACHIO VREAM MINT 420ML C8 - RP 40.000
WALLS OREO MINI STICK 6X48ML C6 - RP 37.888
NESTLE MILO KAW STICK 80ML C24 1 - RP 35.950
AICE FAMILY PACK MIKI MIKI DOUBLE CHOCO 6X35ML C4 1 - RP 27.750
PURI ORGANIC, TELUR KAMPUNG 8S 1 - RP 36.450
MITRA HEMAT TELUR BEBEK MENTAH 4'S 1 - RP 17.750
TEMPE KOTAK DAUN KECIL 1 - RP 4.650
ORGANA STEVIOL ORIGINAL 25S 1 - RP 35.100
TROPICANA SLIM SWEET DIAB 25X2.5GR 1 - RP 27.500
EQUAL STEVIA NO CALORIE SWEETENER 40SX2G 1 - RP 42.950
CHECKERS FINE GOLD 300G 1 - RP 104.950
CHA CHA PEANUT B2G1 3X20G_1C8B_1B8P 1 - RP 11.850
WET BRUSH DETANGLE BLACK 1 - RP 149.000
YADAH ALL DAY MASK PACK ALOE 1C_12 1 - RP 17.500
CHARM BF EXTRA MAXI NONWING 23CM 30S 1 - RP 17.900
HANSAPLAST ROL KAIN 1.25X5CM 1 - RP 15.600
DOODLE MINYAK TELON OIL 10ML ROLL ON 1 - RP 25.000
SO KLIN LIQ DET VIOLET BLOSSOM REF 1.6LT 1 - RP 27.900
RINSO LIQ DET ROSE REF 700GR _1C1P2P_67684285 1 - RP 14.900
VAPE ELECTRIC LIQUID SAKURA BLOSSOM 45 MALAM 1 - RP 18.950
TESSA TRAVEL PACK TP09 3PLY 50S 1 - RP 5.500
F CASTELL WAX CRAYON REGULAR 12C 1C6 R1018 1 - RP 22.500
GLADE AUTOMATIC SPRAY REFILL LAVENDER & VANILLA GLADE - RP 39.500
TELUR PRIMA LOW CHOLESTROL 10BUTIR - RP 38.180
Rice 1 bag (750G~1KG) - ¥2,720
Lemon Grass Leaves - 100 % Natural & Farm Fresh - 1 Bunch (100Gms) - €2.09
Watermelon (Tarbooz) - (Per Piece) (2.5Kg to 3Kg)From Kapil Fresh Vegetables - ₹330
Freshwater Prawns / రొయ్యలు - 50-60 Count/Kg - $20.56
Cauliflower - 1piece(800-1000gram) - SAR 3,865.00
Chocolate - $2.31

PRODUCT NAME will be ULTRA MILK CHOCOLATE MILK, AYAM HATI, AYAM BROILER, READY TO COOK PAKET CHICKEN STEAK, HAAGENDAZS PISTACHIO VREAM MINT, WALLS OREO MINI STICK, NESTLE MILO KAW STICK, AICE FAMILY PACK MIKI MIKI DOUBLE CHOCO, PURI ORGANIC - TELUR KAMPUNG, MITRA HEMAT TELUR BEBEK MENTAH, TEMPE KOTAK DAUN KECIL, ORGANA STEVIOL ORIGINAL, TROPICANA SLIM SWEET DIAB, EQUAL STEVIA NO CALORIE SWEETENER, CHECKERS FINE GOLD, CHA CHA PEANUT B2G1, WET BRUSH DETANGLE BLACK, YADAH ALL DAY MASK PACK ALOE 1C_12, CHARM BF EXTRA MAXI NONWING 23CM, HANSAPLAST ROL KAIN, DOODLE MINYAK TELON OIL, SO KLIN LIQ DET VIOLET BLOSSOM REF, RINSO LIQ DET ROSE REF, VAPE ELECTRIC LIQUID SAKURA BLOSSOM 45 MALAM, TESSA TRAVEL PACK TP09 3PLY, F CASTELL WAX CRAYON REGULAR, GLADE AUTOMATIC SPRAY REFILL LAVENDER & VANILLA GLADE, TELUR PRIMA LOW CHOLESTROL, Rice, Lemon Grass Leaves - 100 % Natural & Farm Fresh, Watermelon (Tarbooz), Freshwater Prawns, Cauliflower, Chocolate .
QUANTITY will be 1, 250, 1, 1, 420, 6x48, 80, 1, 8, 4, 1, 25, 25X2.5, 40SX2, 300, 3X20, 1, 1, 30, 1.25X5, 10, 1.6, 700, 1, 50, 1, 1, 10, 1 X 0.875, 1 X 0.1, 1 X 2.75, 1 X 1, 1 X 0.9, 0.
MEASUREMENT SCALE will be L, GR, EKOR, PCS, ML, ML, ML, ML, S, S, PCS, S, GR, G, G, G, PCS, PCS, S, CM, ML, LT, GR, PCS, S, PCS, PCS, BUTIR, kg, kg, kg, kg, kg, unknown.
PRICE will be RP 20.000, RP 6.500, RP 30.000, RP 35.500, RP 40.000, RP 37.888, RP 35.950, RP 27.750, RP 36.450, RP 17.750, RP 4.650, RP 35.100, RP 27.500, RP 42.950, RP 104.950, RP 11.850, RP 149.000, RP 17.500, RP 17.900, RP 15.000, RP 25.000, RP 27.900, RP 14.900, RP 18.950, RP 5.500, RP 22.500, RP 39.500, RP 38.100, ¥2,720, €2.09, ₹330, $20.56, SAR 3,865.00, $2.31.

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
    country_list = [] #added 20 mar 2026

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
    # 26 march 2026: reduce collecting total item to just 18 items to reduce token output cost, adapt from graph_gsc node s_extract/bd_extract
    if len(product_lines) >= 18:
        rand_i = np.random.choice(range(0,len(product_lines)), size=18, replace=False).tolist()
        product_lines_01 = [product_lines[i] for i in rand_i]        
        #product_lines_01 = product_lines[0:15]
    else : 
        product_lines_01 = product_lines

    for item in product_lines_01:
        product_details = item['content'].strip().upper()
        prompt = parse_instructions.format(product_detail=product_details)
        response = llm_alt.with_structured_output(ParseResults).invoke(prompt)
        a = safe_extract_item(response.product_name)
        b = safe_extract_item(response.quantity)
        c = safe_extract_item(response.measurement_scale)
        d = safe_extract_item(response.price)
        e = safe_extract_item(state['url'])
        f = safe_extract_item(state['country'])
        product_name_list.append(a)
        quantity_list.append(b)
        measurement_scale_list.append(c)
        price_list.append(d)
        url_per_product_list.append(e)
        time_extracted_list.append(datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M'))
        nonparsed_response_list.append(safe_extract_item(product_details))
        country_list.append(f)
    
    return {"product_name": product_name_list, "quantity": quantity_list, "measurement_scale": measurement_scale_list,
           "price": price_list, "url_per_product": url_per_product_list, "time_extracted": time_extracted_list,
           "nonparsed_response": nonparsed_response_list, "country_per_product": country_list}

translate_instructions = """ 

You will receive {product_name} .

Please help to translate this {product_name} into English version appropriately. 
Brand name inside {product_name} should not be translated.

Output into: 
1. product_name_en: translation result

Format as JSON list only.

"""

#26 march 2026: remove url to reduce token output cost , the product categorization still works well on graph_gsc and graph_search without url...
categorize_instructions = """
You will receive {product_name} .
Based on {product_name} , please help to categorize the product into well known product category. 
Well known product category example: rice, egg, chicken meat, beef, vegetable, fruit, seasoning, crackers, drinks, sweets, soap, shampoo, kitchen cleaner, etc.

Output into:
1. product_category : product categorization result

Format as JSON list only.

"""

class TranslateResults(BaseModel):
    product_name_en: list[str] = Field(description= "Product name English version.") 

class ProductCategoryResults(BaseModel):
    product_category : list[str] = Field(description= "Product category determined based on product name. Example product category: rice, egg, chicken meat, beef, vegetable, fruit, seasoning, crackers, drinks, sweets, soap, shampoo, kitchen cleaner, etc.")

def next_translate(state: ExtractState):
    product_name_en_list = []
    for item in state['product_name']:
        prompt_a = translate_instructions.format(product_name=item) #21 mar 2026 1:26 AM -> revise this to product_name=item !!!
        response_a = llm_alt.with_structured_output(TranslateResults).invoke(prompt_a)
        product_name_en_list.append(safe_extract_item(response_a.product_name_en))

    return {"product_name_en": product_name_en_list}

def next_productcategorization(state: ExtractState):
    product_category_list = []
    for a in state['product_name']:
        prompt = categorize_instructions.format(product_name=a)
        response = llm_alt.with_structured_output(ProductCategoryResults).invoke(prompt)
        product_category_list.append(safe_extract_item(response.product_category))

    return {"product_category": product_category_list}

def next_quantity_standardize(state: ExtractState):
    results = [
        standardize_quantity(q, u) for q, u in zip(state['quantity'], state['measurement_scale'])
    ]
    quantity_std = [r[0] for r in results]
    measurement_scale_std = [r[1] for r in results]

    return {"quantity_standardized": quantity_std, "measurement_scale_standardized": measurement_scale_std}

def next_price_currency_conversion(state: ExtractState):
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

def insert_to_table(state: ExtractState):
    #remaining columns to be filled in --->
    rating_list = []
    review_count_list = []
    method_list = []
    source_date_list = []
    question_list = []
    owner_id_list = []
    for i in range(len(state["product_name"])):
        rating_list.append(None)
        review_count_list.append(None)
        method_list.append('Tavily extracts target URL')
        source_date_list.append(None)
        question_list.append(None)
        owner_id_list.append(os.getenv("DB_OWNER_ID_00"))

    db = SessionLocal()
    try:
        for product_name, quantity, measurement_scale, price, source, rating, review_count, place, method, source_date, timestamp_extract, questions, nonparsed_response, product_name_en, measurement_scale_standardized, quantity_standardized, price_local, price_usd, price_eur, price_chf, price_jpy, price_cny, price_aud, price_sgd, product_category, owner_id, country in zip_longest(
            state['product_name'], 
            state['quantity'],
            state['measurement_scale'],
            state['price'],
            state['url_per_product'],
            rating_list,
            review_count_list,
            state['country_per_product'],
            method_list,
            source_date_list,
            state['time_extracted'],
            question_list,
            state['nonparsed_response'],
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
                nonparsed_response = nonparsed_response,
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
                country = country #added 3 april 2026
            )

            db.add(new_product)

        db.commit()
        print(">>> Insert data to table products using app_extract is successful !") #15 mar 2026: clearer message
    
    except Exception as e:
        db.rollback()
        print("Error:", e)
        raise
    
    finally:
        db.close()

    #return state #14 March 2026: to reduce cost by not generating output token

from langgraph.graph import END, StateGraph, START

graph_extract = StateGraph(ExtractState)
graph_extract.add_node("extract_tavily", extract_tavily_v2)
graph_extract.add_node("tavily_clean_regex", tavily_clean_regex)
graph_extract.add_node("tavily_clean_remains", tavily_clean_remains)
graph_extract.add_node("tavily_parse", tavily_parse)
graph_extract.add_node("next_translate", next_translate)
graph_extract.add_node("next_productcategorization", next_productcategorization)
graph_extract.add_node("next_quantity_standardize", next_quantity_standardize)
graph_extract.add_node("next_price_currency_conversion", next_price_currency_conversion)
graph_extract.add_node("insert_to_table", insert_to_table)
graph_extract.add_edge(START, "extract_tavily")
graph_extract.add_edge("extract_tavily", "tavily_clean_regex")
graph_extract.add_edge("tavily_clean_regex", "tavily_clean_remains")
graph_extract.add_edge("tavily_clean_remains", "tavily_parse")
graph_extract.add_edge("tavily_parse", "next_translate")
graph_extract.add_edge("next_translate", "next_productcategorization")
graph_extract.add_edge("next_productcategorization","next_quantity_standardize")
graph_extract.add_edge("next_quantity_standardize", "next_price_currency_conversion")
graph_extract.add_edge("next_price_currency_conversion", "insert_to_table")
graph_extract.add_edge("insert_to_table", END)

app_extract = graph_extract.compile()
