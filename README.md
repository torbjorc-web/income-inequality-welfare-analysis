# Income Inequality, Poverty and Welfare Analysis

![Project Cover](assets/cover.png)

![Status](https://img.shields.io/badge/status-in%20progress-orange?style=for-the-badge)
![Data](https://img.shields.io/badge/data-official%20statistics-blue?style=for-the-badge)
![Focus](https://img.shields.io/badge/focus-data%20analysis%20%26%20visualization-green?style=for-the-badge)
![Countries](https://img.shields.io/badge/countries-Norway%20%7C%20USA%20%7C%20Philippines-purple?style=for-the-badge)

## Overview

This project compares income inequality, poverty, and welfare systems across Norway, the United States, and the Philippines.

It uses official statistics and supporting research to show how public services, redistribution, and welfare policy shape the gap between rich and poor.

It examines how public services and equivalence scales change the interpretation of inequality and poverty, and uses SQL, pandas, and visualization tools to turn raw CSV data into portfolio-ready analysis.

For a short explanation of **SNA vs EU-skala** and why equivalence-scale choice matters, see `docs/methodology.md`.

## Why this project

I wanted to build a portfolio project that shows real data analysis skills, not just charts.

The project combines data collection, cleaning, comparison, visualization, and interpretation in a social and economic context.

## Problem Statement

Official inequality and poverty indicators are often presented separately and are hard to compare across countries with different welfare systems.
This project builds a repeatable pipeline to compare Norway, the USA, and the Philippines using transparent data cleaning, database storage, and clear visual outputs.

## Data Sources

- Statistics Norway (SSB)
- U.S. Census Bureau
- Philippine Statistics Authority (PSA)
- Supporting research on public services, inequality, and welfare effects

## Main Questions

- How does income distribution differ between the three countries?
- What do the data say about the gap between rich and poor?
- How do welfare systems and public services affect poverty and inequality?

## Method

1. Load raw source files into SQLite with `setup_database.py`.
2. Clean and normalize country-specific datasets with `scripts/clean_data.py`.
3. Generate analysis summaries and comparison metrics with `scripts/analyze_data.py`.
4. Generate publication-ready charts/tables with `scripts/make_charts.py`.

## Run the project (end-to-end)

```bash
python setup_database.py
python scripts/clean_data.py
python scripts/analyze_data.py
python scripts/make_charts.py
```

Outputs are written to:

- `outputs/figures/` (charts)
- `outputs/tables/` (summary tables and text outputs)

## Repository Structure

- `data/raw/` — original source files.
- `data/processed/` — cleaned and combined datasets.
- `notebooks/` — exploration and analysis notebooks.
- `scripts/` — reusable Python scripts for cleaning and analysis.
- `outputs/` — charts, tables, and screenshots.
- `docs/` — project description, methodology, and references.
- `assets/` — cover image and badge notes.

## What I Am Building

- Cleaned datasets.
- Comparison tables.
- Charts and dashboards.
- A short portfolio-ready explanation of the findings.

## Current Status

Early development stage.

## Findings (current snapshot)

- **Norway:** lower inequality level overall, but a gradual increase over time.
- **USA:** higher inequality, with a more market-driven distribution pattern.
- **Philippines:** a stronger poverty challenge and a different welfare context than Norway/USA.

## Chart and table interpretation (short)

- `gini_usa_norway_philippines*.png`: compares headline national inequality levels (Gini) across the three countries.
- `norway_gini_p90p10_s80s20.png`: shows that different inequality indicators in Norway move together over time.
- `usa_norway_comparison.png`: highlights the gap between Norway and USA on latest available Gini and P90/P10 ratios.
- `country_headline_comparison.md`: compact, portfolio-ready comparison table with key context indicators.
