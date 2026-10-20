# CricketData Pro — DSA Project 1

A desktop application that downloads real cricket match data from [Cricsheet](https://cricsheet.org),
stores it locally, and lets you sort, search, benchmark and edit it with hand-written
data-structure and algorithm implementations.

Built with Python and PyQt5. The interface is designed in Qt Designer (`App.ui`) and loaded at run time.



## Features

| Area | What it does |
|---|---|
| **Scraper** | Downloads Cricsheet yearly archives (2001–2026) and parses each match into 17 attributes. Target is 15,000 matches by default. Start / Pause / Resume / Stop buttons, progress bar and live log. Duplicates are skipped by Match ID. |
| **URL input (bonus)** | Paste a single Cricsheet zip link, e.g. `https://cricsheet.org/downloads/2024_json.zip`, to scrape only that archive. Leave it empty to scrape everything. |
| **Sorting** | Sort by any of the 17 columns, ascending or descending, with the algorithm you choose. Shows time (ms), comparisons, swaps/moves, complexity and stable/unstable. |
| **Multi-level sort** | Add several columns as sort levels (e.g. Match Type ↑ then Margin ↓). |
| **Sort scope** | Sort the full dataset or only the currently filtered rows. |
| **Benchmark** | Runs every applicable algorithm on the same sample (rows set by the user) and shows a comparison table. |
| **Search / filter** | Per-condition column, operator, value and search algorithm (Linear, Binary, Jump). Conditions combine with AND / OR and can be negated with NOT. |
| **CRUD** | Add, edit and delete matches. Every change is saved to the CSV immediately. |
| **Persistence** | Data lives in `cricket_matches.csv` next to the program and is loaded on start. |

## Attributes (17 columns)

Match ID, Date, Match Type, Gender, Event, Venue, City, Team 1, Team 2, Toss Winner, Toss Decision,
Winner, Margin, Margin Type, Player of Match, Season, Overs.

`Margin` and `Overs` are integers; all others are text.

## Algorithms

All algorithms are written by hand. No sorting library is used, and no built-in `sorted()` or `.sort()`
appears inside any sorting algorithm.

### Sorting (10)

| Algorithm | Complexity | Stable | Works on |
|---|---|---|---|
| Bubble Sort | O(n²) | Yes | any column |
| Selection Sort | O(n²) | No | any column |
| Insertion Sort | O(n²) | Yes | any column |
| Merge Sort | O(n log n) | Yes | any column |
| Quick Sort (random pivot, 3-way) | O(n log n) avg | No | any column |
| Counting Sort | O(n + k) | Yes | integer columns |
| Radix Sort | O(d·(n + b)) | Yes | integer columns |
| Bucket Sort | O(n + k) avg, O(n²) worst | Yes | numeric columns |
| **Cocktail Shaker Sort** (extra) | O(n²) | Yes | any column |
| **Hybrid Sort** (extra: Insertion + Merge) | O(n log n) | Yes | any column |

Counting, Radix and Bucket are offered only when the selected column suits them and only for a
single-column sort. Multi-level sorting needs a comparison-based algorithm.

### Searching (3)

Linear Search, Binary Search and Jump Search. Binary and Jump search work on a sorted copy of the
column (built with the built-in `sorted()` as preparation only; this step is not counted).
They are used for `equals`, `starts with` and numeric comparisons. Other operators
(`contains`, `ends with`, `!=`) fall back to Linear Search.

## How sorting works

1. Each row becomes a `(key, row)` tuple. The key is the column value (text is lower-cased;
   descending order negates numbers or wraps text in a reversing class). Multi-level sorts use a tuple key.
2. The algorithm sorts the list in place by comparing only the key and returns
   `(comparisons, swaps)`. For algorithms that move elements instead of swapping, "swaps" counts moves.
3. `run_sort` times the call with `time.perf_counter()` and returns the sorted rows plus the statistics.

## Project structure

```
App.ui           Qt Designer layout and stylesheet (do not modify)
app.py           Main window: loads App.ui, connects buttons, sorting / search / CRUD / scraper controls
scraper.py       Cricsheet downloader running in a QThread (pause / resume / stop)
data.py          Column definitions, type conversion, CSV load / save
sorting.py       Sorting algorithms, counters, benchmark
searching.py     Linear / Binary / Jump search and AND / OR / NOT conditions
test_app.py      Offscreen automated checks
screenshots/     Pictures used in this README
requirements.txt Python dependencies
```

`cricket_matches.csv` is created on the first run.

## Setup and run

Requires Python 3.9 or newer.

```bash
pip install -r requirements.txt
python app.py
```

### First use

1. Open the **Scraper** tab.
2. Leave the URL empty (or paste one Cricsheet zip link) and set the target (default 15,000).
3. Click **Start**. Use **Pause**, **Resume** and **Stop** as needed. Stopping saves everything scraped so far.
4. Go back to the **Cricket** tab to sort, search, benchmark and edit the data.

Scraping happens once; later runs load the saved CSV and only add new matches.

## Tests

```bash
python test_app.py
```

Runs the app offscreen and checks every widget binding, all sorting algorithms, search conditions,
sort scope, multi-level sort, benchmark, add / edit / delete with CSV saving, and the scraper
(target, stop without lost rows or duplicates, pause / resume, bad URL) using a fake archive.

## Data source

Match data comes from [Cricsheet](https://cricsheet.org), published under the
Open Data Commons Attribution License. The scraper waits briefly between downloads to be polite to the server.
