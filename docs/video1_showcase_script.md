# Video 1 Script: Project Walkthrough

## Working Title

Income Inequality Dashboard: Norway vs USA vs Philippines

## Target Length

2 to 4 minutes

## Recording Style

- Speak clearly and a little slower than normal conversation.
- Keep the screen moving every 10 to 20 seconds.
- Prioritize the live dashboard and key visuals over code.

## Script

### Opening Hook

"In this project, I built an interactive dashboard that compares income inequality and welfare context across Norway, the United States, and the Philippines. The goal was to turn public data into a clear, reproducible analysis that is both visual and easy to explore."

### Why The Project Matters

"Income inequality is often discussed in headlines, but it is much harder to compare meaningfully across countries with very different welfare systems. I wanted to build a project that not only compares the numbers, but also adds enough context to interpret them more responsibly."

### Data Sources

"The project uses public data from Statistics Norway, the U.S. Census Bureau, and the Philippine Statistics Authority, together with supporting material on public services and welfare effects."

### Method And Pipeline

"The workflow starts with raw CSV files, which are loaded into SQLite. From there, I clean and normalize the data with Python and pandas, generate analysis tables and charts, and then serve the final result through a Streamlit dashboard. That gives the project a full pipeline from raw data to interactive presentation."

### Dashboard Demo Intro

"The live dashboard lets the user compare the three countries using filters for year range, country selection, and inequality range. It also includes headline metrics, trend charts, comparison panels, and a welfare-context view."

### What To Show On Screen

- Show the dashboard landing view.
- Point to the About section.
- Point to the sidebar filters.
- Show the Gini trend chart.
- Show the country comparison panel.
- Show the welfare-context scatter.

### Explain Main Findings

"At the current snapshot in the project data, Norway has the lowest headline inequality, the USA has the highest, and the Philippines sits in between but shows improvement over time. The dashboard is designed to make those differences visible while also reminding the viewer that country comparisons need careful interpretation."

### Explain What Makes The Project Strong

"What makes this project valuable is that it combines data cleaning, SQL storage, analysis, visualization, deployment, and explanation in one complete workflow. It is not just a chart collection. It is a small analytical product built around a real question."

### Optional Mention Of Upload Feature

"I also added a CSV upload pipeline so new country data can be validated and added through the dashboard interface, which makes the project more extensible than a static comparison app."

### Closing

"Overall, this project helped me practice end-to-end data work: collecting public data, structuring it, analyzing it, and presenting it through a deployed dashboard. If you want to explore it yourself, the live app, GitHub repository, and presentation are all linked below."

## Shorter 60-Second Version

"This project is an interactive dashboard comparing income inequality and welfare context across Norway, the USA, and the Philippines. I used public data, loaded it into SQLite, cleaned and analyzed it with Python and pandas, and deployed the final result with Streamlit. The dashboard highlights major differences in Gini levels, trend direction, and welfare context, while also showing the limits of direct cross-country comparison. The project is designed as a full portfolio piece, combining data engineering, analysis, visualization, and communication in one workflow."

## Suggested Video Description

This video gives a short walkthrough of my income inequality and welfare dashboard comparing Norway, the USA, and the Philippines.

The project matters because inequality figures are easy to quote but much harder to compare responsibly across different welfare systems.

Data sources include Statistics Norway (SSB), the U.S. Census Bureau, and the Philippine Statistics Authority.

Key takeaway: the dashboard shows both headline inequality differences and why welfare context matters when interpreting them.

Links:

- Live app: [Inequality & Welfare Dashboard](https://income-inequality-welfare-analysis-a9ngzr4evattkxng7oaxup.streamlit.app/)
- GitHub repo: [income-inequality-welfare-analysis](https://github.com/torbjorc-web/income-inequality-welfare-analysis)
- Presentation: [PowerPoint walkthrough](https://1drv.ms/p/c/4246acc26547a1fc/IQD3jhAcVuRPSYF4dYweL2VpAVFl818193NJHlZWpirrwmc?e=aM2McJ)
- YouTube channel: [Channel link](https://www.youtube.com/channel/UCY4HNGfLRSIcls_4h6oq_PA)
