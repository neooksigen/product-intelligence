import os
from dotenv import load_dotenv
load_dotenv()

from langchain_openai import ChatOpenAI
llm = ChatOpenAI(model="gpt-5.2", temperature=0) 

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
            response = llm.with_structured_output(SearchAnswersTavily).invoke(prompt)
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
    return {"answer": state['answer_gpt']+state['answer_tavily'],
           "url": state['url_gpt']+state['url_tavily'],
           "source_date": state['source_published_date_gpt']+state['source_published_date_tavily']}

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

    for answer_detail in state['answer']:
        prompt = search_answer_parsed_instructions.format(answer_detail=answer_detail)
        response = llm.with_structured_output(SearchAnswersParsed).invoke(prompt)
        product_name_list.append(safe_extract_item(response.product_name))
        price_list.append(safe_extract_item(response.price))
        quantity_list.append(safe_extract_item(response.quantity))
        measurement_scale_list.append(safe_extract_item(response.measurement_scale))
        place_list.append(safe_extract_item(response.place))
        extract_date_list.append(datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M'))

    return {"product_name": product_name_list, "price": price_list, "quantity": quantity_list, "measurement_scale": measurement_scale_list,
           "place": place_list, 
           "answer_final": state['answer'],
           "url_final": state['url'],
           "source_date_final": state['source_date'],
           "extract_date": extract_date_list}

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
        for product_name, quantity, measurement_scale, price, source, rating, review_count, place, method, source_date, timestamp_extract, questions, nonparsed_response, owner_id in zip_longest(
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

graph_search = StateGraph(SearchState)
graph_search.add_node("search_answer_tavily", search_answer_tavily)
graph_search.add_node("search_answer_gpt", search_answer_gpt)
graph_search.add_node("search_answer_tavily_summarise", search_answer_tavily_summarise) 
graph_search.add_node("search_answer_combined", search_answer_combined)
graph_search.add_node("search_answer_parsed", search_answer_parsed)
graph_search.add_node("insert_to_table", insert_to_table)
graph_search.add_edge(START, "search_answer_tavily")
graph_search.add_edge(START, "search_answer_gpt")
graph_search.add_edge("search_answer_tavily", "search_answer_tavily_summarise")
graph_search.add_edge(["search_answer_tavily_summarise", "search_answer_gpt"], "search_answer_combined")
graph_search.add_edge("search_answer_combined", "search_answer_parsed")
graph_search.add_edge("search_answer_parsed", "insert_to_table")
graph_search.add_edge("insert_to_table", END)

app_search = graph_search.compile()    