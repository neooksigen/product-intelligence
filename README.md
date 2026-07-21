## Introduction

[Maintelyd](https://maintelyd.com)'s Global Product Price Discoveries codebase are 2 :
1. repo [product-intelligence](https://github.com/neooksigen/product-intelligence) : agentic workflow and automation pipeline. This is to build and refresh Maintelyd database.
2. repo [product-intelligence-frontend](https://github.com/neooksigen/product-intelligence-frontend) : front end website and front end agent. This is to visualize the data from Maintelyd database, and deploy front end agent where user could ask custom product price analysis to Maintelyd database.
Both repo 1 and repo 2 will be described together in this README product-intelligence.

## Product Price Discoveries Components
### 1. Agentic Workflow
Agentic Workflow is important to orchestrate the line process to update database so new product price data keep coming & recorded.  We built with LangGraph.
The line process from beginning to the end are : 

* A. product price discovery
* B. data parsing
* C. product name translation from local language to English 
* D. product category mapping
* E. measurement scale and quantity standardization
* F. embed price currency conversion
* G. final tabular data insertion to Supabase

Code : graph_search, graph_extract, graph_gsc, utils, database_sqlalchemy.

**ChatGPT has helped in :** 
1. in data parsing through JSON.load method introduction
2. 1st step cleaning long text by regex in graph_extract 
(it already didn't recommend to use llm because of expensive and takes too long time)
3. measurement scale and quantity standardization with custom Python function (it didn't recommend using llm with same reason point 2)
4. price currency conversion by recommending [ExchangeRate-API](https://app.exchangerate-api.com/) and build custom Python function
   to convert raw text from API to JSON then to tabular data
5. recommending [Supabase](https://supabase.com/) for storing data , Python code function to insert data, and
    initial guide to connect to Supabase through SQL Alchemy.

**Model used :**
GPT-5.4 for web search (tool = web_search (not chat), user_location in local country). GPT-5-mini for data parsing, product name translation.
During OpenAI Build Week (specifically on 18 July 2026), I have committed on GitHub (6bb9dd7) to use **GPT-5.6** for web search.
But I found the cost of 1x run graph_search jumped into 0.5 USD. Meanwhile the previous cost with GPT-5.4 is just 0.08 USD. 
As this graph_search is running every day with monthly budget cap at 23 USD, using GPT-5.6 will incur monthly budget at 120 USD 
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

### 4. Front End Maintelyd Website

We developed the web front end with TypeScript framework in Vercel platform. We purchased maintelyd domain in Cloudflare with cost 10.46 USD.

**ChatGPT has helped in :**
1. recommended Vercel as platform to deploy website, and guide to install Vercel folders in VS Code through npm install.
2. built web structure following my prompt, which consist of homepage, daily-chart, monthly-chart, daily-table, monthly-table, country, raw.
3. built those 6 pages in point 2 one-by-one. So I prepared the screenshot "the data visualization that I want", then ask ChatGPT to build page.tsx and dashboard.tsx to implement that screenshot.
4. guide initially in how to connect to Supabase within Typescript environment.
5. recommended Cloudflare to buy domain and setups.

## During Open AI Build Week 13 - 21 July 2026 (more specifically on 18-20 July 2026)

I truly never used **Codex** before. But actually I am quite overwhelmed by this old practice : 

ChatGPT recommends code changes ---> 
I find the problematic code lines (guided by ChatGPT), then apply that change in VS Code ---> 
Copy paste full code to GitHub repo ---> 
Commit changes 

After we know that Codex could apply code change directly to GitHub, I give it a try and finally **Codex solve these 2 problems** : 

a. bad UI appearance in mobile browser view, chart are "compressed" by large filters. On desktop browser view, the huge tooltip shadowed the chart dots and line. I taught Codex the GitHub [product-price-intelligence](https://github.com/neooksigen/product-intelligence-frontend) repo structure. Meanwhile I didn't taught  Codex about deep page.tsx and dashboard.tsx TypeScript code structure (I really don't have this knowledge, those were previously from ChatGPT). But Codex intelligently acknowledged folder structure, edited the TypeScript code, by creating additional TypeScript code for mobile view specific, and edit the tooltip from long vertical shape to be  n row x 3 columns. 

b. No front end agent on Maintelyd website, where user could ask customized product price analysis. The first version agent that Codex built was not "an agent", but merely just reporting templates even with many weird product categories. That feature also was repeatedly created by Codex. This is because Codex was still scary of SQL code generated that could update/insert/delete data wrongly on Supabase table. After I ensured that only Read access was given to the public/anon role in Supabase RLS policy and schema end_data exposed to public is just secondary (primary schema is secret and not exposed to public), then finally the Codex build the real front end agent :-)))) . Even in the instruction , Codex has written to prevent any SQL code that Update/Write/Delete data.

This front end agent could understand human language and do SQL coding dynamically to finally answer user's custom price analysis. **Agent is the next gen of data visualization**. We keep charts and tables as for regular monitoring and reporting. But for custom data analysis , we cannot always rely manually to our data analyst team. Instead, we ask agent to do that. Our front end agent in Maintelyd, [Product Price Master Agent](https://maintelyd.com/price-agent), for now capable to generate analysis result in table form. Next, we will add capabilities to create charts to it !

I also discover "**incremental knowledge agent**". Because our front end agent is exposed to the database that is always updated every day, with new price data that keep coming every day.  The agent is able to give answer about the latest price trend, and also the past historical price trend. No need manual training setup periodically, the agent is already exposed to the regularly-refreshed database !

Although unfortunately I could not continue utilizing GPT-5.6 due to daily cost constraint (this Maintelyd automation is already running every day since March 2026) , **our Maintelyd project is fully powered by OpenAI**. The agentic workflows, automation pipeline, frontend website were developed by ChatGPT. The website UI enhancement and front end agent were developed by Codex during this OpenAI Build Week Submission Period. And models inside agentic workflows and inside front end agent are 100 % OpenAI (GPT-5.4 and GPT-5-mini). No gemini, claude, deepseek etc models inside this Maintelyd project. **I don't want to lie that I utilize GPT-5.6 in the demo video**, so this explanation is very important ground truth.

## How to Test
Go to Maintelyd's Global Product Price Discoveries website https://maintelyd.com and try out these 7 pages one-by-one (accessible also in menu bar on top right) in desktop and/or mobile browser : 
1. [Daily Price Comparison](https://maintelyd.com/daily-chart)
2. [Monthly Price Comparison](https://maintelyd.com/monthly-chart)
3. [Daily Price Comparison - Table](https://maintelyd.com/daily-table)
4. [Monthly Price Comparison - Table](https://maintelyd.com/monthly-table)
5. [Price Monitoring per Country](https://maintelyd.com/country)
6. [Raw Data Price](https://maintelyd.com/raw)
7. [Product Price Master Agent](https://maintelyd.com/price-agent) ---> 100 % Built with Codex during OpenAI Build Week Submission Period. Try to put any custom product price analysis topic to our agent ! For example (copy paste to the input box inside the page) : What are average and median USD price of product fish (per kilogram), butter (per kilogram), vegetable (per kilogram), and cooking oil (per liter) in China, Russia, France, Brazil in June-July 2026 ? Provide me the result in table with column name : product (fish/butter/vegetable/cooking oil), measurement scale, country, average USD price, median USD price, count product names !





