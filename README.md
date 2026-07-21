## Introduction

Maintelyd codebase are 2 :
1. product-intelligence : agentic workflow and automation pipeline. This is to build Maintelyd database.
2. product-intelligence-frontend : front end website and front end agent. This is to visualize the data from Maintelyd database,
   and deploy front end agent where user could ask custom product price analysis to Maintelyd database.

## Product-intelligence
### 1. Agentic Workflow
Agentic Workflow is important to orchestrate the line process to update database so new product price data keep coming & recorded.  We built with LangGraph.
The line process from beginning to the end are : 

A. product price discovery
B. data parsing
C. product name translation from local language to English 
D. product category mapping
E. measurement scale and quantity standardization
F. embed price currency conversion
G. final tabular data insertion to Supabase

Code : graph_search, graph_extract, graph_gsc, utils, database_sqlalchemy.

**ChatGPT has helped in :** 
1. in data parsing through JSON.load method introduction
2. 1st step cleaning long text by regex in graph_extract 
(it already didn't recommend to use llm because of expensive and takes too long time)
3. measurement scale and quantity standardization with custom Python function (it didn't recommend using llm with same reason point 2)
4. price currency conversion by recommending [ExchangeRate-API] (https://app.exchangerate-api.com/) and build custom Python function
   to convert raw text from API to JSON then to tabular data
5. recommending [Supabase](https://supabase.com/) for storing data , Python code function to insert data, and
    initial guide to connect to Supabase through SQL Alchemy.

**Model used :**
GPT-5.4 for web search (tool = web_search (not chat), user_location in local country). GPT-5-mini for data parsing, product name translation.
During OpenAI Build Week (specifically on 18 July 2026), I have committed on GitHub (6bb9dd7) to use GPT-5.6 for web search.
But I found the cost of 1x run graph_search jumped into 0.5 USD. Meanwhile the previous cost with GPT-5.4 is just 0.08 USD. 
As the this graph_search is running every day with monthly budget cap at 23 USD, using GPT-5.6 will incur monthly budget at 120 USD 
(= 0.5 x 8 runs per day x 30 day).
The web search result is still similar between GPT-5.4 and GPT-5.6.
Then I decided to commit GitHub again (aecd2e0) to use back GPT-5.4.

### 2. Product Price Topic Requests 
We prepared list of product price topic, to be executed by the agentic workflow.
**ChatGPT has helped in :** 
Translation 60 product price topics (topics mostly about raw foods/agricultural - garden - dairy - fisheries products) from English into : 
Portuguese, Spanish, Deutsch, France, Arabisch, Tanzanian, South African, Russian, Japanese, Mandarin (simplified), and Thai. 
Translation result was set in common local market context, and in tidy result ready to be imported to Supabase.

### 3. Automation Pipeline
Here are simplified automation pipeline from product price discovery until end-data storage : 
1. Check whether the money currency conversion rate is already latest. If only not, automatically download data from Exchange Rate API and store to Supabase.
2. One product price topics/URL is feed to agentic workflow.
3. The agentic workflow process it , as explained in section 1 from 1A until 1G.
4. That product price topic/URL marked as done. 
5. The pipeline stop for 180 minutes. 
6. Then next product price topics/URL is feed to agentic workflow. Begin again from 1-5. And so on.

Code : run_pipeline.py (custom Python code, no llm)

**ChatGPT has helped in :**
Built run_pipeline following those 6 steps in my prompt.





