import os
from dotenv import load_dotenv
load_dotenv()

from langchain_openai import ChatOpenAI
llm = ChatOpenAI(model="gpt-5.2", temperature=0, model_kwargs={"response_format": {"type": "json_object"}}) 
llm_alt = ChatOpenAI(model="gpt-5-mini", temperature=0, model_kwargs={"response_format": {"type": "json_object"}}) #11 march 2026: for summarization and parsing #26 march 2026 tune in model to reduce token output cost

import datetime
datetime.datetime.now().strftime('%Y-%m-%d %H:%M')

import datetime
end_date = datetime.datetime.now().date().strftime('%Y-%m-%d')
start_date = (datetime.datetime.now().date() - datetime.timedelta(days=30)).strftime('%Y-%m-%d')

# Web search tool, with Tavily
from langchain_tavily import TavilySearch
tavily_search = TavilySearch(max_results=5, search_depth='advanced', topic='general', start_date=start_date, end_date=end_date 
                            ,include_answer=False
                            ,country="indonesia" 
                            ,include_domain=["kompas.com","detik.com","kumparan.com","cnnindonesia.com"])

# Node preparation
import operator
from typing import Annotated
from langgraph.graph import MessagesState
from typing_extensions import TypedDict
from pydantic import BaseModel, Field
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from scraper.utils import safe_extract_item, normalize_url, parse_price, standardize_quantity, get_latest_exchange_rate #added 23 march 2026

import pandas as pd #added 23 march 2026
import numpy as np #added 23 march 2026

class SearchAnswers(BaseModel):
    answer: list[str] = Field(description= "Concise 5-10 words answer")
    url: list[str] = Field(description= "Source URL")
    source_published_date: list[str] = Field(description= "The published date/last update date of the source")    

class SearchState(TypedDict):
    answer_final: Annotated[list[str], operator.add] #Answer final
    answer: Annotated[list[str], operator.add] #Answers combined
    answer_tavily_original: Annotated[list[str], operator.add] #Answers from Tavily original
    answer_tavily: Annotated[list[str], operator.add] #Answers from Tavily, after summarised
    answer_gpt: Annotated[list[str], operator.add] #Answers from GPT
    question: str #questions
    country: str #country, 23 mar 2026
    url_final: Annotated[list[str], operator.add] #URL final
    url: Annotated[list[str], operator.add] #Url/Answer's source combined
    url_tavily_original: Annotated[list[str], operator.add] #Url/Answer's source from Tavily original
    url_tavily: Annotated[list[str], operator.add] #Url/Answer's source from Tavily, just the same as url_tavily_original
    url_gpt: Annotated[list[str], operator.add] #Url/Answer's source from GPT 
    source_date_final: Annotated[list[str], operator.add] #The source published date/last updated date final
    source_date: Annotated[list[str], operator.add] #The source's published date/last updated date combined 
    source_published_date_gpt : Annotated[list[str], operator.add] #The source's published date/last updated date from GPT
    source_published_date_tavily : Annotated[list[str], operator.add] #The source's published date/last updated date from Tavily
    product_name: Annotated[list[str], operator.add] #The product name
    price: Annotated[list[str], operator.add] #The product price
    quantity: Annotated[list[str], operator.add] #The product minimum quantity to be purchased
    measurement_scale: Annotated[list[str], operator.add] #The quantity scale
    place: Annotated[list[str], operator.add] #Where the product information is reported
    extract_date: Annotated[list[str], operator.add] #When the extraction is conducted
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
    #sections: list #Final key we duplicate in outer state for Send() API

#GPT search is not compatible with date range start_date and end_date ! 
#If you put start_date and end_date, GPT search result will be "sorry I cannot search the web".
#Better you filter out the result just in the end.
search_instructions_gpt = """ Search the web for {search_query} to generate 8 concise results. 
For each result:
1. answer : Concise answer (5-10 words). Answer is containing product name, price per quantity, in where. For example: "Egg cost Rp 27,000-Rp 30,000 per kg in Bandung Indonesia". 
2. url : Source URL 
3. source_published_date : The published date/ last updated date of the source, in format yyyy-mm-dd.

Format as JSON list only.
"""
#Past additional prompt :
#Example: 
#- answer: "Eggs Rp 100 - Rp 150 per kg Jakarta", url: put source URL here
#- answer: "Market price Rp 28,000 per kg", url: put source URL here

search_instructions_tavily = """Generate answer from the user's questions: {search_query}. 
And include also the source's published date in format yyyy-mm-dd.
"""

def search_answer_gpt(state: SearchState):
    prompt = search_instructions_gpt.format(search_query=state['question'])
    response = llm.with_structured_output(SearchAnswers).invoke(prompt)
    #response_01 = response.answer
    #response_02 = [result for result in response_01[0]['search_answer']['answer']]
    return {"answer_gpt": response.answer or "No results found.",
           "url_gpt": response.url or "No results found.",
           "source_published_date_gpt": response.source_published_date or "No results found."}

def search_answer_tavily(state: SearchState):
    prompt = search_instructions_tavily.format(search_query=state['question'])  
    #try to remove this published date criteria in prompt
    #+ " The source's published date/last update date must be between {} and {} to have the current latest answer.".format(start_date,end_date)    
    data = tavily_search.invoke({"query": prompt}) #It is not possible to use with_structured_output because tavily_search actually doesn't have with_structured_output attribute.
    #results = data.get("results",data)
    #results = data.get("results",[])
    results = data["results"] #use this 7 mar 2026, perhaps update new in tavily 
    results_content_01 = [r['content'] for r in results]
    results_content_02 = results_content_01
    #url = [r['url'] for r in results if 'url' in r] 
    url = [r['url'] for r in results] #use this 7 mar 2026, perhaps update new in tavily
    return {"answer_tavily_original": results_content_02 or "No results found.",
           "url_tavily_original": url or "No results found."}

class SearchAnswersTavily(BaseModel):
    answer: list[str] = Field(description= "Concise 5-10 words answer")
    source_published_date: list[str] = Field(description= "The published date/ last updated date of the source, formatted in yyyy-mm-dd .")

summarise_instructions = """Summarise this search result to answer {question} in 5 - 10 words: 

{content} 

Keep it concise and directly answer the question. For example: "Egg cost Rp 27,000-Rp 30,000 per kg in Bandung Indonesia".  

For each search result:
1. answer: Concise answer (5-10 words). Answer is containing product name, price per quantity, in where.
2. source_published_date: The published date/ last updated date of the source, in format yyyy-mm-dd.
"""

def search_answer_tavily_summarise(state: SearchState):
    #LLM could not summarise at each answer, so it needs help by us to loop at each answer
    summarized_answers = [] 
    source_dates = []

    for content in state['answer_tavily_original']:
        if len(content.split()) > 10: #split to split sentence into words, then count how many words
            prompt = summarise_instructions.format(question=state['question'], content=content)
            #summary = llm.invoke(prompt).content.strip() #to make it raw text without any structure
            response = llm_alt.with_structured_output(SearchAnswersTavily).invoke(prompt) #edited 11 mar 2026 to use llm_alt for cheaper cost
            summarized_answer = response.answer[0]
            source_date = response.source_published_date[0]
        else: 
            #summary = content
            summarized_answer = content
            source_date = "The content is too short, or no content available."
        #summarized_answers.append(summary)
        summarized_answers.append(summarized_answer)
        source_dates.append(source_date)
        
    return {"answer_tavily": summarized_answers,
           "url_tavily": state['url_tavily_original'],
           "source_published_date_tavily": source_dates}

def search_answer_combined(state: SearchState):
    return {"answer": state['answer_gpt'], #+state['answer_tavily'], #11 mar 2026 due to not good result, tavily is set off.
           "url": state['url_gpt'], #+state['url_tavily'],
           "source_date": state['source_published_date_gpt'] #+state['source_published_date_tavily']
           }

from scraper.utils import safe_extract_item 

class SearchAnswersParsed(BaseModel):
    product_name: list[str] = Field(description="Product name.")
    price: list[str] = Field(description="Product price preceeded by money currency such as Rp, $, etc.")
    quantity: list[str] = Field(description="Minimum quantity of product to be purchased.")
    measurement_scale: list[str] = Field(description="The quantity scale such as gr, kg, bungkus, etc.")
    place: list[str] = Field(description="The place where the product information is reported.")

search_answer_parsed_instructions = """In this {answer_detail}, you will find string with the format:

PRODUCT NAME PRICE QUANTITY MEASUREMENT SCALE PLACE

Example:
Apel Malang Rp 25.000/kg di Jakarta (Harga Spesial)
Alpukat Rp 5.750/100gr di Surabaya
Madu Rp 40.000 - Rp 50.000/500 ml di Bandung

PRODUCT NAME will be Apel Malang, Apel Fuji .
PRICE will be Rp 25.000, Rp 5.750, Rp 40.000 - Rp 50.000 . 
QUANTITY will be 1, 100, 500 .
MEASUREMENT SCALE will be kg, gr, ml .
PLACE will be Jakarta, Surabaya, Bandung .

Following example above (but please do not include the example into these product_name, quantity, measurement_scale, price, place variables below !),
you have to parse the {answer_detail} into PRODUCT NAME, PRICE, QUANTITY, MEASUREMENT SCALE, PLACE: 
1. product_name : PRODUCT NAME
2. price : PRICE
3. quantity: QUANTITY
4. measurement_scale: MEASUREMENT SCALE
5. place: PLACE

Format as JSON list only.
"""

def search_answer_parsed(state: SearchState):
    product_name_list = []
    price_list = []
    quantity_list = []
    measurement_scale_list = []
    place_list = []
    extract_date_list = []
    country_per_product_list = [] #added 23 march 2026

    for answer_detail in state['answer']:
        prompt = search_answer_parsed_instructions.format(answer_detail=answer_detail)
        response = llm_alt.with_structured_output(SearchAnswersParsed).invoke(prompt) #edited 11 mar 2026 to use cheaper model
        product_name_list.append(safe_extract_item(response.product_name))
        price_list.append(safe_extract_item(response.price))
        quantity_list.append(safe_extract_item(response.quantity))
        measurement_scale_list.append(safe_extract_item(response.measurement_scale))
        place_list.append(safe_extract_item(response.place))
        extract_date_list.append(datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M'))
        country_per_product_list.append(state['country']) #added 23 march 2026

    return {"product_name": product_name_list, "price": price_list, "quantity": quantity_list, "measurement_scale": measurement_scale_list,
           "place": place_list, 
           "answer_final": state['answer'],
           "url_final": state['url'],
           "source_date_final": state['source_date'],
           "extract_date": extract_date_list,
           "country_per_product": country_per_product_list}

#new 23 march 2026: translate - categorize - standardize - price conversion, similar to graph_extract
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

def next_translate(state: SearchState):
    product_name_en_list = []
    for item in state['product_name']:
        prompt_a = translate_instructions.format(product_name=item) #21 mar 2026 1:26 AM -> revise this to product_name=item !!!
        response_a = llm_alt.with_structured_output(TranslateResults).invoke(prompt_a)
        product_name_en_list.append(safe_extract_item(response_a.product_name_en))

    return {"product_name_en": product_name_en_list}

def next_productcategorization(state: SearchState):
    product_category_list = []
    for a in state['product_name']:
        prompt = categorize_instructions.format(product_name=a)
        response = llm_alt.with_structured_output(ProductCategoryResults).invoke(prompt)
        product_category_list.append(safe_extract_item(response.product_category))

    return {"product_category": product_category_list}

def next_quantity_standardize(state: SearchState):
    results = [
        standardize_quantity(q, u) for q, u in zip(state['quantity'], state['measurement_scale'])
    ]
    quantity_std = [r[0] for r in results]
    measurement_scale_std = [r[1] for r in results]

    return {"quantity_standardized": quantity_std, "measurement_scale_standardized": measurement_scale_std}

def next_price_currency_conversion(state: SearchState):
    price_usd_list = []
    price_eur_list = []
    price_chf_list = []
    price_jpy_list = []
    price_cny_list = []
    price_aud_list = []
    price_sgd_list = []
    exchange_rate_table = get_latest_exchange_rate()
    price_local = [
        parse_price(m) for m in state['price']
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

def insert_to_table(state: SearchState):
    #remaining columns to be filled in --->
    question_list = []
    rating_list = []
    review_count_list = []
    method_list = []
    owner_id_list = []
    question = safe_extract_item(state['question'])
    for i in range(len(state["product_name"])):
        question_list.append(question)
        rating_list.append(None)
        review_count_list.append(None)
        method_list.append("web search")
        owner_id_list.append(os.getenv("DB_OWNER_ID_00"))
    
    db = SessionLocal()
    try:
        for product_name, quantity, measurement_scale, price, source, rating, review_count, place, method, source_date, timestamp_extract, questions, nonparsed_response, product_name_en, measurement_scale_standardized, quantity_standardized, price_local, price_usd, price_eur, price_chf, price_jpy, price_cny, price_aud, price_sgd, product_category, owner_id in zip_longest(
            state['product_name'], 
            state['quantity'],
            state['measurement_scale'],
            state['price'],
            state['url_final'],
            rating_list,
            review_count_list,
            state['place'],
            method_list,
            state['source_date_final'],
            state['extract_date'],
            question_list,
            state['answer_final'],
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
                owner_id = owner_id
            )

            db.add(new_product)

        db.commit()
        print(">>> Insert data to table products using app_search is successful !")
    
    except Exception as e:
        db.rollback()
        print("Error:", e)
        raise
    
    finally:
        db.close()

    #return state #24 march 2026 no need to return state as this node is to insert data !

from langgraph.graph import END, StateGraph, START

graph_search = StateGraph(SearchState)
#graph_search.add_node("search_answer_tavily", search_answer_tavily)
graph_search.add_node("search_answer_gpt", search_answer_gpt)
#graph_search.add_node("search_answer_tavily_summarise", search_answer_tavily_summarise) 
graph_search.add_node("search_answer_combined", search_answer_combined)
graph_search.add_node("search_answer_parsed", search_answer_parsed)
graph_search.add_node("next_translate", next_translate)
graph_search.add_node("next_productcategorization", next_productcategorization)
graph_search.add_node("next_quantity_standardize", next_quantity_standardize)
graph_search.add_node("next_price_currency_conversion", next_price_currency_conversion)
graph_search.add_node("insert_to_table", insert_to_table)
#graph_search.add_edge(START, "search_answer_tavily")
graph_search.add_edge(START, "search_answer_gpt")
#graph_search.add_edge("search_answer_tavily", "search_answer_tavily_summarise")
#graph_search.add_edge(["search_answer_tavily_summarise", "search_answer_gpt"], "search_answer_combined")
graph_search.add_edge("search_answer_gpt","search_answer_combined")
graph_search.add_edge("search_answer_combined", "search_answer_parsed")
graph_search.add_edge("search_answer_parsed","next_translate")
graph_search.add_edge("next_translate","next_productcategorization")
graph_search.add_edge("next_productcategorization", "next_quantity_standardize")
graph_search.add_edge("next_quantity_standardize", "next_price_currency_conversion")
graph_search.add_edge("next_price_currency_conversion", "insert_to_table")
graph_search.add_edge("insert_to_table", END)

app_search = graph_search.compile()    
