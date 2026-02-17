# Sales Analytics Dashboard

A simple Streamlit web app that uses an Excel file as its datasource to display interactive sales data analysis and reporting.

## Features

- 📊 **Overview tab** — key metrics (revenue, profit, units sold, top product & region)
- 📈 **Charts tab** — monthly revenue trend, revenue by region & product, units sold breakdown
- 📋 **Data tab** — full filtered table with CSV download
- 🔍 **Sidebar filters** — filter by Region and Product; all views update live
- 📁 **File upload** — bring your own `.xlsx` file or use the included sample data

## Tech Stack

Python · Streamlit · pandas · openpyxl · Plotly

## Run Locally

```bash
pip install -r requirements.txt
python sample_data.py   # generate sample data (run once)
streamlit run app.py
```

## Deploy

Deployed on [Streamlit Community Cloud](https://share.streamlit.io).
