# Testplan, feilrapport og forbedringsforslag

**Prosjekt:** income-inequality-welfare-analysis
**Repo:** https://github.com/torbjorc-web/income-inequality-welfare-analysis
**Revisjon testet:** `main` (siste push 2026-08-07)
**Dato:** 12. september 2026
**Testet av:** Torbjørn Carlsen (med AI-assistert kodegjennomgang)

## Sammendrag

| Måling | Resultat |
| --- | --- |
| Enhetstester | 170 passerte, 0 feilet (`pytest`) |
| Linting | `ruff check .` – ingen funn |
| Test-dekning `src/` | 99 % |
| Test-dekning totalt (inkl. `dashboard.py` og `scripts/`) | 95 % |
| Filer uten dekning | `scripts/make_charts.py` (518 linjer), `scripts/release_db_snapshot.py` (86 linjer) |
| Advarsler under testkjøring | 82 (hovedsakelig `ResourceWarning: unclosed database`) |
| Feil funnet | 12 (0 kritiske, 3 høye, 4 middels, 5 lave) |

Kodebasen er solid strukturert: tydelig lagdeling (`src/config.py`, `src/data/`, `src/services/`), ren separasjon mellom pipeline-skript og dashbord, og en reell testsuite som faktisk kjører i CI. Hovedfunnene handler ikke om at koden krasjer, men om **stille datatap i dashbordet** og at **CI-en måler null dekning uten å si det**.

---

## Del 1 – Testplan

### 1.1 Mål

Verifisere at pipelinen (rådata → SQLite → renset data → analyse → dashbord) gir korrekte, reproduserbare resultater, og at dashbordet behandler brukeropplastede land på samme måte som de tre innebygde landene.

### 1.2 Omfang

**Inkludert**

- Databaseoppsett og bootstrap (`setup_database.py`, `src/data/bootstrap.py`)
- Datavask og normalisering (`scripts/clean_data.py`)
- Analyse og aggregering (`scripts/analyze_data.py`)
- Figurer og tabeller (`scripts/make_charts.py`)
- Repository-laget (`src/data/repository.py`)
- Metrikk- og utvalgslogikk (`src/services/metrics.py`)
- CSV-opplasting og validering (`src/services/upload.py`)
- Prognosemodell og backtest (`src/services/forecasting.py`)
- Streamlit-UI (`dashboard.py`)
- CI-arbeidsflyt (`.github/workflows/tests.yml`)

**Utenfor omfang**

- Riktigheten i de offisielle kildedataene fra SSB, U.S. Census Bureau og PSA
- Ytelse/lastesting av Streamlit Cloud-instansen
- Notebookene i `notebooks/` (dokumentasjon, ikke produksjonskode)

### 1.3 Testmiljø

| Element | Verdi |
| --- | --- |
| Python | 3.13 i CI, verifisert lokalt på 3.14 |
| Avhengigheter | `requirements-dev.txt` (pandas ≥ 2.2, streamlit ≥ 1.37, scikit-learn ≥ 1.4, pytest ≥ 8, ruff ≥ 0.16) |
| Database | SQLite, `database/database.db` |
| Testdata | Fixtures i `tests/conftest.py` + reelle filer i `data/raw/` |
| Kommandoer | `ruff check .`, `pytest -q --cov=. --cov-report=term-missing` |

### 1.4 Testnivåer

1. **Enhetstest** – ren funksjonslogikk: `parse_number`, `validate_country_upload`, `pick_usa_value`, `_tidy_series`.
2. **Integrasjonstest** – SQLite-lesing/skriving, bootstrap som kjører skript i subprosess, pipeline-steg som leser hverandres output.
3. **Systemtest (UI)** – dashbordet kjørt via `streamlit.testing.v1.AppTest`, inkludert filter- og opplastingsflyt.
4. **Regresjonstest** – hele suiten kjøres i CI på push og pull request mot `main`.

### 1.5 Inngangs- og utgangskriterier

**Inngangskriterier:** repoet klones rent, `requirements-dev.txt` installeres uten feil, `python setup_database.py && python scripts/clean_data.py` fullfører.

**Utgangskriterier:** alle testtilfeller under er utført, ingen åpne feil med alvorsgrad Kritisk eller Høy, `ruff check .` er ren, og dekningen for `src/` er ≥ 90 % **målt** (ikke bare rapportert).

### 1.6 Risikoområder (prioritert testinnsats)

| Risiko | Begrunnelse |
| --- | --- |
| Stille filtrering i dashbordet | Hardkodede slidergrenser kan skjule gyldige rader uten feilmelding |
| Inkonsistent årsvalg per land | Ulik "as-of"-logikk gir sammenligninger på tvers av ulike år |
| Parsing av tallformater | Norske og engelske skilletegn blandes i rådata |
| Skjulte unntak | `except Exception` som returnerer tom DataFrame skjuler databasefeil |
| Falsk trygghet i CI | Dekningsmåling som ikke måler noe |

### 1.7 Testtilfeller

| ID | Område | Testtilfelle | Forventet resultat | Status |
| --- | --- | --- | --- | --- |
| TC-01 | Bootstrap | Kjør dashbordet mot en slettet `database.db` | Databasen bygges automatisk, alle `REQUIRED_TABLES` finnes | Bestått |
| TC-02 | Bootstrap | Kjør mot database der én påkrevd tabell mangler | `ensure_database_ready` kjører oppsett på nytt og kaster tydelig `RuntimeError` hvis noe fortsatt mangler | Bestått |
| TC-03 | Datavask | `scripts/clean_data.py` på rådataene | 4 rensede tabeller, ingen tomme kolonner, Norge 2001–2024 (24 rader) | Bestått |
| TC-04 | Parsing | `parse_number` med norsk format `"1 234,5"` | 1234.5 | Bestått |
| TC-05 | Parsing | `parse_number` med engelsk format `"1,234.5"` | 1234.5 | **Feilet – BUG-06** |
| TC-06 | Parsing | `parse_number` med `"n/a"`, `"-"`, `""`, `None` | `None` i alle tilfeller | Bestått |
| TC-07 | Repository | `load_core_data` mot manglende databasefil | `FileNotFoundError` med filbane | Bestått |
| TC-08 | Repository | `load_core_data` mot tom `usa_clean` | `ValueError` med tabellnavn | Bestått |
| TC-09 | Repository | Gjentatte kall til `load_core_data` | Ingen `ResourceWarning`, ingen åpne tilkoblinger | **Feilet – BUG-05** |
| TC-10 | Repository | `load_user_country_data` når tabellen ikke finnes | Tom DataFrame med korrekte kolonner, feilen logges | **Delvis – BUG-07** (feilen logges ikke) |
| TC-11 | Metrikk | Norsk verdi ved referanseår 2015 | Bruker 2015-raden (siste år ≤ valgt år) | Bestått |
| TC-12 | Metrikk | USA-verdi ved referanseår 2015 | Ingen verdi, eller verdi merket som utenfor perioden | **Feilet – BUG-03** (returnerer 2023-verdien) |
| TC-13 | Metrikk | Filippinsk Gini ved referanseår 2010 | 2009-verdien | Bestått |
| TC-14 | Opplasting | Importer prosjektets eget `country_upload_template.csv` | Alle rader importeres **og vises** i trendgrafen | **Feilet – BUG-02** (Gini 0,61–0,63 filtreres bort) |
| TC-15 | Opplasting | Last opp CSV med Gini = 1,4 | Valideringsfeil "Gini must be between 0 and 1" | Bestått |
| TC-16 | Opplasting | Last opp CSV med duplikat land/år | Valideringsfeil om duplikater | Bestått |
| TC-17 | Opplasting | Last opp gyldige rader for år 1995 og 2030 | Radene vises i grafen, eller brukeren varsles om at de er utenfor visningsperioden | **Feilet – BUG-04** |
| TC-18 | Opplasting | Importer samme land/år to ganger | `INSERT OR REPLACE` oppdaterer raden, ingen duplikat | Bestått |
| TC-19 | Prognose | Serie med færre enn 5 observasjoner | `ValueError`, vises som `st.warning` i UI | Bestått |
| TC-20 | Prognose | Norsk Gini-serie, lineær trend | Backtest med MAE, RMSE og baseline, forbehold vises | Bestått |
| TC-21 | Prognose | Filippinsk regionserie | Prognoseår følger undersøkelsens 3-årssyklus | **Feilet – BUG-09** (bruker 2-årssteg) |
| TC-22 | Prognose | Ukjent modellnavn | `ValueError: Unknown model` | Bestått |
| TC-23 | UI | Kjør hele appen uten unntak | Appen rendrer alle seksjoner | Bestått |
| TC-24 | UI | Filtre som ikke gir treff | Vennlig `st.warning`, ingen traceback | Bestått |
| TC-25 | Figurer | `scripts/make_charts.py` ende-til-ende | Alle filer i `outputs/figures/` og `outputs/tables/` regenereres | Ikke automatisert – 0 % dekning |
| TC-26 | CI | Push til `main` | Lint + tester + **reell** dekningsrapport | **Feilet – BUG-01** |

---

## Del 2 – Feilrapport

Alvorsgrad: **Kritisk** = blokkerer bruk · **Høy** = feil resultat eller falsk trygghet · **Middels** = robusthet/vedlikehold · **Lav** = kosmetisk eller lav risiko.

### BUG-01 · Høy · CI måler null test-dekning

**Fil:** `.github/workflows/tests.yml`
**Steg:** `pytest -q --cov=app --cov-report=term-missing`
**Problem:** Prosjektet har ingen pakke som heter `app`. Coverage finner ingenting å måle.
**Faktisk:** `CovReportWarning: Failed to generate report: No data to report.` – og jobben blir grønn likevel.
**Forventet:** Dekning måles for `src`, `scripts` og `dashboard.py`, og bygget feiler under en definert terskel.
**Reproduksjon:** `pytest -q --cov=app tests/test_metrics.py` → 20 tester passerer, ingen dekningsdata.

### BUG-02 · Høy · Prosjektets eget CSV-eksempel forsvinner fra grafen

**Fil:** `dashboard.py` (Gini-slider), `src/config.py` (`CSV_TEMPLATE`)
**Problem:** Gini-slideren har maksverdi `0.60` og standardintervall `(0.20, 0.50)`, mens malen som brukeren laster ned inneholder Sør-Afrika med Gini 0,610–0,630. Valideringen godtar alt mellom 0 og 1.
**Faktisk:** Importen melder "Imported 3 rows", men radene kan ikke vises i trendgrafen uansett hvordan slideren settes.
**Forventet:** Slidergrensene beregnes fra faktiske data, eventuelt med varsel om at rader ligger utenfor valgt intervall.
**Reproduksjon:** Last ned CSV-malen i sidepanelet, importer den uendret, velg Sør-Afrika i landfilteret.

### BUG-03 · Høy · USA-tall ignorerer valgt referanseår

**Fil:** `src/services/metrics.py`, `pick_usa_value`
**Problem:** Funksjonen returnerer 2024-verdien når `year >= 2024`, ellers **alltid** 2023-verdien – uavhengig av hvor langt tilbake referanseåret er. Norge bruker `choose_latest_not_after` og Filippinene bruker `y <= year`, så de tre landene følger ulik logikk.
**Faktisk:** `pick_usa_value(usa_df, "Gini index of income inequality", 2005)` → `(0.485, 2023)`
**Forventet:** `(None, None)`, eller en tydelig UI-merking av at USA-serien bare dekker 2023–2024.
**Konsekvens:** Sammenligningskortene kan vise Norge 2005 ved siden av USA 2023 og Filippinene 2009 samtidig. Årstallet står i hjelpeteksten, men rangeringen "higher = more inequality" blir likevel misvisende.

### BUG-04 · Middels · Hardkodede årsgrenser klipper opplastede data

**Fil:** `dashboard.py`
**Kode:** `min_year = int(min(norway_df["year"].min(), 2009))`, `max_year = int(max(norway_df["year"].max(), 2024))`
**Problem:** Grensene tar ikke hensyn til `user_country_df`, mens valideringen godtar årstall fra 1900 til 2100.
**Faktisk:** Opplastede rader for f.eks. 1995 eller 2030 lagres i databasen, men kan aldri komme innenfor årsslideren.
**Forventet:** Grensene utvides til å dekke alle serier som faktisk er lastet.

### BUG-05 · Middels · SQLite-tilkoblinger lukkes aldri

**Fil:** `src/data/repository.py` (4 steder), `src/data/bootstrap.py` (2 steder)
**Problem:** `with sqlite3.connect(...) as conn:` avslutter kun transaksjonen – den lukker **ikke** tilkoblingen. Ingen av kallene bruker `conn.close()` eller `contextlib.closing`.
**Faktisk:** 82 advarsler i testkjøringen, hovedsakelig `ResourceWarning: unclosed database in <sqlite3.Connection object>`. Reprodusert direkte med `warnings.simplefilter("error", ResourceWarning)`.
**Forventet:** Ingen advarsler; filhåndtak frigis. I en langlivet Streamlit-prosess akkumulerer disse for hver rerun.

### BUG-06 · Middels · `parse_number` feiler på engelsk tallformat

**Fil:** `src/data/repository.py`
**Problem:** Funksjonen erstatter komma med punktum uten å skille mellom desimaltegn og tusenskille, og stopper ved første ugyldige tegn. `"1,234.5"` blir `"1.234.5"` → `float()` feiler → `None`.
**Faktisk:** `parse_number("1,234.5")` → `None`
**Forventet:** `1234.5`
**Konsekvens:** `get_norway_welfare_total` returnerer `None` så snart én av de fire kolonnene ikke kan tolkes, og Norge droppes stille ut av velferds-scatteret via `dropna`. Brukeren får ingen forklaring.

### BUG-07 · Middels · Databasefeil skjules bak tom DataFrame

**Fil:** `src/data/repository.py`, `load_user_country_data`
**Problem:** `except Exception` returnerer en tom DataFrame for alle feiltyper – ikke bare "tabellen finnes ikke", som kommentaren antyder. Korrupt database, låst fil eller endret skjema gir samme stille resultat.
**Forventet:** Fang `sqlite3.OperationalError` spesifikt, logg unntaket, og la uventede feil boble opp til UI-grensen.

### BUG-08 · Lav · Tabellnavn interpoleres inn i SQL

**Fil:** `src/data/repository.py` (`load_user_country_data`, `save_user_country_data`), `src/data/bootstrap.py` (`ensure_user_country_table`)
**Problem:** Tabellnavn settes inn med f-string. Verdien er i dag konstanten `USER_COUNTRY_TABLE`, så det er ikke utnyttbart nå, men mønsteret er en SQL-injeksjonsrisiko så snart navnet blir konfigurerbart.
**Forventet:** Valider mot en hviteliste av tillatte tabellnavn før interpolering.

### BUG-09 · Lav · Prognosesteg matcher ikke undersøkelsessyklusen

**Fil:** `dashboard.py`, `render_forecast_section`
**Problem:** Filippinene bruker `step = 2`, men `PH_GINI_YEARS` er 2009, 2012, 2015, 2018, 2021, 2023 – altså i praksis 3-årssteg.
**Faktisk:** Prognoseår blir 2025, 2027, 2029.
**Forventet:** 2026, 2029, 2032 – eller steg utledet fra medianavstanden i serien.

### BUG-10 · Lav · Ubeskyttet `raise` i UI-laget

**Fil:** `dashboard.py`
**Kode:** `raise ValueError("No Norway rows available for selected year.")`
**Problem:** Denne ligger utenfor `try/except`-grensen rundt datalastingen, så den vises som rå traceback i stedet for `st.error`. Lav sannsynlighet i dag (norsk serie starter i 2001 = `min_year`), men den blir reell hvis årsgrensene gjøres dynamiske (se BUG-04).

### BUG-11 · Lav · Genererte artefakter er sjekket inn

**Filer:** `.coverage`, `database/database.db`, `income_inequality_welfare_analysis_presentation_polished.pptx`, `outputs/**`
**Problem:** `.gitignore` dekker ikke `.coverage` eller `*.db`. Repoet er ~3,4 MB med binærfiler som endrer seg ved hver kjøring, og databasen kan komme ut av synk med skriptene som bygger den.
**Forventet:** Ignorer `.coverage` og `database/*.db`; distribuer databasen via `scripts/release_db_snapshot.py` som en release-ressurs.

### BUG-12 · Lav · Cache-nøkkel ignorerer argumentet sitt

**Fil:** `dashboard.py`
**Kode:** `@st.cache_data def load_data(_db_path: str)`
**Problem:** Understrek-prefiks betyr at Streamlit **ikke** hasher argumentet, så `str(DB_PATH)` har ingen effekt på cache-nøkkelen. Signaturen antyder noe annet enn den gjør.
**Forventet:** Fjern argumentet, eller la det være med i nøkkelen hvis flere databaser skal støttes.

---

## Del 3 – Forbedringsforslag

### Prioritet 1 – gjør CI ærlig

1. **Rett dekningsmålet og sett en terskel:**
   `pytest -q --cov=src --cov=scripts --cov=dashboard.py --cov-report=term-missing --cov-fail-under=90`
2. **Legg `ruff format --check .` i lint-steget** slik at formatering også er en gate, ikke bare regler.
3. **Test på flere Python-versjoner** med `strategy.matrix` (3.12 og 3.13), siden `requirements.txt` ikke låser noe.
4. **Last opp dekningsrapport som artefakt** og legg et coverage-merke i README ved siden av test-merket.

### Prioritet 2 – reproduserbarhet

5. **Lås avhengigheter.** `pandas>=2.2` betyr at bygget kan knekke av en oppstrøms utgivelse. Legg til en `requirements.lock` (pip-compile) eller pinn eksakte versjoner, og skru på Dependabot.
6. **Ta databasen ut av Git** og bygg den i CI som en smoke-test: `setup_database.py → clean_data.py → analyze_data.py` på et lite fixture-utvalg. Da testes hele pipelinen i praksis, ikke bare funksjonene hver for seg.
7. **Dokumentér datauttrekkene** med nedlastingsdato og kildeversjon per fil i `data/raw/sources.md`, slik at analysen kan gjenskapes eksakt.

### Prioritet 3 – korrekthet og datakvalitet

8. **Én felles "as-of"-funksjon** for alle land, slik at Norge, USA, Filippinene og opplastede land velger år etter samme regel (fikser BUG-03). La den returnere både verdi og år, og vis "n/a (utenfor dekning)" når serien ikke rekker tilbake til referanseåret.
9. **Utled UI-grenser fra data** – både årsintervall og Gini-intervall (fikser BUG-02 og BUG-04). Vis en `st.info` når rader faller utenfor gjeldende filter, i stedet for å skjule dem.
10. **Skjemavalidering av datarammer** med f.eks. `pandera`: kolonnetyper, verdiintervall og obligatoriske kolonner sjekkes ved lasting, ikke bare ved opplasting.
11. **Robust tallparsing:** skill mellom desimaltegn og tusenskille, og bruk `pandas.to_numeric` der det er mulig (fikser BUG-06). Sett gjerne parsing i en egen `src/data/parsing.py` med parametriserte tester.

### Prioritet 4 – arkitektur og robusthet

12. **Sentraliser databasetilgangen** i én `get_connection()` context manager som garanterer `close()` (fikser BUG-05), og la repository-funksjonene ta imot en tilkobling i stedet for en filbane. Det gjør dem også lettere å teste in-memory.
13. **Innfør logging** (`logging.getLogger(__name__)`) i stedet for stille `except Exception` (fikser BUG-07), og fang spesifikke unntakstyper.
14. **Fjern duplisert kolonnedefinisjon** – lista over de ni brukerkolonnene finnes tre ganger i `repository.py`. Flytt den til `src/config.py` som `USER_COUNTRY_COLUMNS`.
15. **Legg til type hints og `mypy`** i CI. `src/services/forecasting.py` er allerede annotert; resten av `src/` er delvis.

### Prioritet 5 – testdekning der den mangler

16. **`scripts/make_charts.py` (518 linjer) og `scripts/release_db_snapshot.py` har 0 % dekning.** Legg til en test som kjører dem mot en fixture-database i `tmp_path` og verifiserer at forventede filer opprettes og ikke er tomme.
17. **UI-test av opplastingsflyten** med `streamlit.testing.v1.AppTest`: last opp mal-CSV, mapp kolonner, importer, og bekreft at landet dukker opp i både landvelger og trendgraf. Det ville avdekket BUG-02 automatisk.
18. **Egenskapsbaserte tester** (Hypothesis) for `parse_number` og `validate_country_upload` – disse er rene funksjoner med et stort inputrom og er ideelle kandidater.
19. **Gjør advarsler til feil** i `pytest.ini`: `filterwarnings = error::ResourceWarning`. Da blir lekkasjer som BUG-05 fanget av CI i stedet for å drukne i 82 advarsler.

### Prioritet 6 – produkt og presentasjon

20. **Dokumentér at opplastede data er flyktige** på Streamlit Cloud: SQLite-skrivingen forsvinner når containeren restartes. Skriv det i UI-teksten så ingen tror dataene lagres permanent.
21. **Legg til `docs/` -lenke fra README til denne testplanen**, og gjerne en kort "Kvalitetssikring"-seksjon. For en portefølje er dokumentert testarbeid ofte mer overbevisende enn én ekstra graf.
22. **CHANGELOG.md** med versjoner knyttet til databasesnapshot, slik at figurer i presentasjonen kan spores til et bestemt datauttrekk.

---

## Kilder og verktøy brukt

- Kodegjennomgang av `main`-grenen, hentet via GitHub CLI
- `pytest 8` med `pytest-cov` og `ruff` fra `requirements-dev.txt`
- Streamlit-caching-semantikk for understrek-prefiksede argumenter: [Streamlit caching-dokumentasjon](https://docs.streamlit.io/develop/concepts/architecture/caching)
- SQLite-tilkoblinger som context manager avslutter transaksjon, ikke tilkobling: [Python sqlite3-dokumentasjon](https://docs.python.org/3/library/sqlite3.html#sqlite3-connection-context-manager)
- UI-testing av Streamlit-apper: [streamlit.testing.v1.AppTest](https://docs.streamlit.io/develop/api-reference/app-testing/st.testing.v1.apptest)
