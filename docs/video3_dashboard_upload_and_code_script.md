# Video 3 Script: Dashboard Demo, Upload Feature, and Code Walkthrough

## Working Title

Behind the Code: Building a Streamlit Inequality Dashboard with Python and SQLite

## Target Length

3 to 5 minutes

## Recording Style

- Keep the pace steady and practical.
- Show the working product first, then explain implementation.
- Only show code sections that support the story.

## Script

### Opening Hook

"In this video, I want to show how the dashboard works behind the scenes, from the data pipeline to the interactive app structure, and then demonstrate the custom CSV upload feature."

### Repository Overview

"The repository is organized into raw data, processed data, analysis scripts, notebooks, outputs, and a modular Streamlit app. The goal was to keep the project readable and maintainable instead of putting everything into one long dashboard file."

### Data Pipeline Overview

"The project starts with raw CSV files, loads them into SQLite, then cleans and normalizes country-specific tables with Python scripts. That makes it possible to reuse the same cleaned data across notebooks, summary outputs, and the dashboard."

### App Structure

"The dashboard itself is modular. Configuration, bootstrap logic, repository functions, metrics, and upload services are separated into their own files. That structure makes it easier to extend the app without breaking unrelated parts."

### Upload Feature Intro

"One feature I added is a CSV upload pipeline for new country data. Instead of hardcoding every dataset, a user can upload a CSV, map the columns, validate the data, and import it into the database."

### Upload Demo Steps

"The workflow is simple: upload a CSV, choose whether the country comes from a fixed name or a column, map the year and Gini fields, optionally map extra fields like P90 over P10 or welfare proxy values, then run validation and import."

### Validation Logic

"Before import, the app checks that year is numeric and in a reasonable range, that Gini is numeric and in a 0 to 1 scale, and that there are no duplicate country and year rows in the upload. That keeps the feature practical without pretending to do full statistical quality assurance."

### What To Show On Screen

- Show the repository structure on GitHub.
- Show the live dashboard.
- Open the CSV upload expander.
- Show the template and mapping options.
- Demonstrate import flow if you want a live example.
- Point to where the new country appears in the charts.

### Why This Feature Matters

"This upload feature makes the project more than a static dashboard. It turns it into a small analytical tool that can be extended with new country data without rewriting the application."

### Closing

"So this project is not only about visualizing inequality. It is also about building a reusable workflow from raw public data to a deployed interactive app with room for future extension."

## Suggested Video Description

This video shows how I structured the code behind my inequality dashboard and how the custom CSV upload feature works.

It matters because a good data project should be reproducible, extensible, and understandable beyond the final charts.

The project uses Python, pandas, SQLite, and Streamlit, with public data from Norway, the USA, and the Philippines.

Key takeaway: the dashboard is backed by a modular pipeline and can be extended with validated country uploads.

Links:

- Live app: [Inequality & Welfare Dashboard](https://income-inequality-welfare-analysis-a9ngzr4evattkxng7oaxup.streamlit.app/)
- GitHub repo: [income-inequality-welfare-analysis](https://github.com/torbjorc-web/income-inequality-welfare-analysis)
- Presentation: [PowerPoint walkthrough](https://1drv.ms/p/c/4246acc26547a1fc/IQD3jhAcVuRPSYF4dYweL2VpAVFl818193NJHlZWpirrwmc?e=aM2McJ)
- YouTube channel: [Channel link](https://www.youtube.com/channel/UCY4HNGfLRSIcls_4h6oq_PA)
