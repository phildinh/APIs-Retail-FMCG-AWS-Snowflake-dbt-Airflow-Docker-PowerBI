# Retail FMCG Data Pipeline

A production-grade data pipeline that pulls retail data from an API,
stores it in AWS, transforms it in Snowflake, and delivers business
insights through a Power BI dashboard — fully automated and scheduled
with Apache Airflow.

**AWS S3 · Snowflake · dbt · Airflow · Docker · Power BI · Python**

---

## What does this project do?

Imagine you are running an online retail store. Every day you have
products being viewed, customers placing orders, and prices changing.
All of that data is valuable — but only if you can collect it reliably,
clean it up, and turn it into something a business person can actually
use to make decisions.

That is exactly what this pipeline does.

It automatically:
1. Pulls fresh product, customer, and order data from a retail API
2. Stores the raw data safely in AWS cloud storage
3. Cleans and organises it in Snowflake data warehouse
4. Builds analytics-ready tables that answer real business questions
5. Runs everything on a schedule so the data is always up to date

The end result is a Power BI dashboard where a business analyst can
open their laptop and immediately see revenue trends, top-selling
products, and customer behaviour — without waiting for anyone to
manually pull a report.

---

## Why did I build this?

I have spent five years working in FMCG and retail analytics. I have
seen firsthand how much time analysts waste manually downloading data,
cleaning it in Excel, and rebuilding the same reports every week.

This project is my answer to that problem. I wanted to build the kind
of automated, reliable data pipeline that a real business would use —
not a toy example, but something that handles the messy realities of
production data: API failures, duplicate records, changing prices, and
pipelines that need to run correctly every single time.

Every decision in this project came from asking one question:
"How would a real data team build this?"

---

## What business questions does it answer?

Once the pipeline runs, a business analyst can immediately answer:

- **Revenue** — How much did we sell this month vs last month?
- **Products** — Which products are our top performers by revenue?
- **Customers** — Who are our highest-value customers?
- **Trends** — What does our seasonal demand pattern look like?
- **Pricing** — How have product prices changed over time?

These are the questions that drive real business decisions in retail
and FMCG — inventory planning, pricing strategy, marketing spend,
and customer retention.

---

## How it works — in plain English

The pipeline runs in six steps, fully automated:

**Step 1 — Collect**
Python code calls a retail API and pulls down product listings,
customer profiles, and order data. If the API is slow or briefly
unavailable, the pipeline automatically retries before giving up.

**Step 2 — Store raw data**
The raw data is saved to AWS S3 exactly as it came from the API —
nothing changed, nothing deleted. Think of this as a safety net.
If anything goes wrong downstream, the original data is always there.

**Step 3 — Load into the warehouse**
The raw files are loaded into Snowflake, our cloud data warehouse.
Each pipeline run adds new data without overwriting what is already
there — so we build up a complete history over time.

**Step 4 — Clean and organise**
dbt (a SQL transformation tool) takes the raw data and cleans it up —
fixing data types, flattening nested fields, removing duplicates.
The cleaned data sits in a separate layer so analysts always have a
reliable, consistent version to work from.

**Step 5 — Build the analytics layer**
dbt builds the final analytics tables — a star schema with one central
fact table surrounded by dimension tables for products, customers, and
dates. This is the structure that makes Power BI fast and intuitive.

**Step 6 — Track history**
When a product price changes or a customer updates their address,
the pipeline does not overwrite the old record. It keeps both versions
with timestamps — so you can always answer "what was the price at
the time of this order?" This is called SCD Type 2 and it is how
professional data teams handle changing data.

---

## The tech stack — and why each tool was chosen

| Tool | What it does | Why I chose it |
|---|---|---|
| **Python** | Pulls data from the API | Industry standard for data pipelines |
| **AWS S3** | Stores raw data files | Cheap, reliable, scales to any size |
| **Snowflake** | Cloud data warehouse | Best-in-class performance for analytics |
| **dbt** | Transforms and tests data | Version-controlled SQL with built-in testing |
| **Airflow** | Schedules and monitors the pipeline | Standard orchestration tool at most data teams |
| **Docker** | Packages Airflow for consistent local setup | Runs the same way on any machine |
| **Power BI** | Business intelligence dashboards | Connects natively to Snowflake |
| **GitHub Actions** | Runs automated tests on every code change | Catches bugs before they reach production |

---

## What makes this project stand out?

### It handles real-world data problems
Raw data from APIs is messy — nested JSON structures, duplicate
records across pipeline runs, fields that change over time. This
pipeline handles all of that properly rather than ignoring it.

### It is built for reliability
If the pipeline runs twice on the same day it produces the same
result — not double the data. Every run is tracked with a unique
ID so anything that goes wrong can be traced back to its source.

### It keeps history
Most simple pipelines just overwrite data when something changes.
This pipeline keeps a full history of every product price and
customer detail change using industry-standard SCD Type 2 tracking.
That history is what makes time-based analysis possible.

### It is fully tested
The ingestion layer has 15 automated tests that run on every code
change. The data warehouse layer has 12 dbt tests that verify data
quality directly in Snowflake. Both layers fail loudly if something
is wrong — rather than silently producing bad data.

### It is production-ready
The same patterns used here — medallion architecture, incremental
loading, environment-based configuration, structured logging,
containerised orchestration — are used by data engineering teams
at companies of all sizes.

---

## The data model

The final analytics layer is a star schema — the industry standard
structure for business intelligence. It is designed so Power BI
queries run fast and analysts can slice data any way they need.
```
                 ┌───────────┐
                 │ dim_date  │
                 └─────┬─────┘
                       │
┌──────────────┐  ┌────┴──────────────┐  ┌─────────────┐
│ dim_customer │  │ fact_order_items  │  │ dim_product │
│              ├──┤                   ├──┤             │
│ Who bought   │  │ What was ordered  │  │ What it was │
│ Full history │  │ How much revenue  │  │ Price history│
└──────────────┘  └───────────────────┘  └─────────────┘
```

The fact table combines real order data from the API with 50,000
rows of synthetic historical orders — giving Power BI two full years
of data to visualise trends, seasonality, and growth patterns.

---

## How to run it

### You will need
- Python 3.11 or higher
- Docker Desktop
- A Snowflake account (free trial works)
- An AWS account with an S3 bucket

### Getting started
```bash
# clone the repo
git clone https://github.com/phildinh/APIs-Retail-FMCG-AWS-Snowflake-dbt-Airflow-Docker.git
cd APIs-Retail-FMCG-AWS-Snowflake-dbt-Airflow-Docker

# set up Python environment
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
pip install dbt-snowflake==1.7.2

# add your credentials
Copy-Item .env.example .env
# open .env and fill in your Snowflake and AWS details
```

### Run the pipeline once
```bash
python -m ingestion.pipeline
```

### Run the full transformation layer
```bash
cd dbt
dbt snapshot
dbt run
dbt test
```

### Run with Airflow on a schedule
```bash
docker-compose up -d
# open http://localhost:8080
# enable and trigger the ecommerce_pipeline DAG
```

### Run the test suite
```bash
pytest tests/ -v
```

---

## Project structure
```
ecommerce-pipeline/
│
├── ingestion/          ← pulls data from API and loads to S3 + Snowflake
├── dbt/                ← cleans and models data in Snowflake
├── dags/               ← Airflow schedule and task definitions
├── tests/              ← automated test suite
├── snowflake/          ← one-time setup scripts
├── scripts/            ← utility scripts
├── docs/               ← architecture diagram
├── docker-compose.yml  ← local Airflow setup
└── .github/            ← CI/CD pipeline
```

---

## What I learned

Building this project taught me that good data engineering is mostly
about handling failure gracefully. The happy path — API works, data
is clean, everything loads — is the easy part. The interesting
engineering happens when you ask: what if the API is down? What if
the same pipeline runs twice? What if a product price changes mid-month?

Every one of those scenarios has a deliberate answer in this project.
That is what I am most proud of.

I also learned that the separation between collecting data, cleaning
data, and serving data is not just a nice pattern — it is what makes
a pipeline debuggable, testable, and maintainable over time. When
something breaks, you know exactly which layer to look at.

---
[GitHub](https://github.com/phildinh) ·
[LinkedIn](https://www.linkedin.com/in/phil-dinh)
