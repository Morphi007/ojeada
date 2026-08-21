<p align="center">
  <img src="assets/logo-512.png" alt="ojeada" width="120">
</p>

<h1 align="center">ojeada</h1>

<p align="center">
  A quick look at any CSV: what columns it has, what type they are,
  how many values are missing, and a chart for each one.
</p>

---

The whole point of this project is that the code stays **easy to read**. Every function
does one thing and its name says exactly what that thing is. No tricks, no clever
one-liners.

## Requirements

- Python 3.11 or newer (tested on Python 3.14)
- pandas 3.0
- matplotlib 3.11

## Installation

**1. Clone the repo and create a virtual environment:**

```bash
git clone https://github.com/Morphi007/ojeada.git
cd ojeada
python -m venv .venv
```

**2. Activate the virtual environment.** Copy ONLY the line for your operating system:

Windows (PowerShell):

```powershell
.venv\Scripts\Activate.ps1
```

Linux or macOS:

```bash
source .venv/bin/activate
```

You know it worked because your terminal prompt now starts with `(.venv)`.

**3. Install the dependencies:**

```bash
pip install -r requirements.txt
```

## Usage

```bash
python main.py --file data/sample_sales.csv
python main.py --file data/sample_sales.csv --sort units_sold --desc
python main.py --file data/sample_sales.csv --sort category units_sold
python main.py --file data/sample_sales.csv --plot
```

| Argument | Required | What it does |
|----------|----------|--------------|
| `--file` | Yes      | Path to the CSV file you want to explore |
| `--sort` | No       | One or more columns to sort by |
| `--desc` | No       | Sort from highest to lowest (default: lowest to highest) |
| `--plot` | No       | Generate charts and save them into `output/` |

## Example output

Running the script against the sample CSV shipped in `data/`:

```
======================================================
BASIC DATASET INFORMATION
======================================================

DATASET SIZE
  Rows:    20
  Columns: 5

COLUMNS
  NAME            TYPE          MISSING  PERCENTAGE
  --------------------------------------------------
  date            str                 0     0.0%
  product         str                 0     0.0%
  category        str                 0     0.0%
  units_sold      int64               0     0.0%
  unit_price      float64             3    15.0%

MISSING VALUES
  The dataset has 3 missing values in total.

FIRST 5 ROWS
         date   product     category  units_sold  unit_price
0  2026-01-05  Keyboard  Peripherals          12        45.5
1  2026-01-06   Monitor     Displays           3       220.0
2  2026-01-07     Mouse  Peripherals          25        18.9
3  2026-01-08    Laptop    Computers           2       950.0
4  2026-01-09  Keyboard  Peripherals           8        45.5
```

The output reads in four blocks:

1. **Size**: how many rows and columns the dataset has.
2. **Columns**: the detail of each column, its type and how many holes it has.
   In this example, `unit_price` is missing 3 values (15% of the rows).
3. **Missing values**: the total number of holes across the whole dataset.
4. **First rows**: a sample of the real data, to confirm it was read correctly.

### One important detail about types

Notice that the `date` column shows up as type `str`, **not** as a date. That is correct:
pandas does not guess that a text column holds dates unless you ask it to. The conversion
happens inside `--plot`, when it actually needs to draw the time series.

And a note for anyone coming from older tutorials: in pandas 3.0 text columns are of type
`str`, not `object`. If you see code detecting text with `df[col].dtype == object`, it is
out of date. The correct check today is `pd.api.types.is_string_dtype(df[col])`.

## Sorting the dataset

`--sort` reorders the rows based on the values of one or more columns:

```bash
python main.py --file data/sample_sales.csv --sort units_sold --desc
```

```
======================================================
SORTED BY: units_sold (descending)
======================================================

          date     product     category  units_sold  unit_price
7   2026-01-14       Mouse  Peripherals          30       18.90
2   2026-01-07       Mouse  Peripherals          25       18.90
10  2026-01-19  Headphones        Audio          22       35.75
14  2026-01-23       Mouse  Peripherals          18       18.90
5   2026-01-12  Headphones        Audio          15         NaN
```

The numbers on the left are the original index: row 7 was the eighth row in the CSV, but
sorting moved it to the top. Sorting never deletes or changes data — it only rearranges it.

### Sorting by several columns

When you pass more than one column, sorting cascades: the second column only breaks ties
where the first one is equal.

```bash
python main.py --file data/sample_sales.csv --sort category units_sold
```

```
          date     product   category  units_sold  unit_price
12  2026-01-21  Microphone      Audio           4         NaN
17  2026-01-28  Headphones      Audio          11       35.75
5   2026-01-12  Headphones      Audio          15         NaN
10  2026-01-19  Headphones      Audio          22       35.75
9   2026-01-16      Laptop  Computers           1      950.00
3   2026-01-08      Laptop  Computers           2      950.00
```

First it groups by `category` alphabetically (Audio, Computers, ...) and inside each
category it sorts by `units_sold` from lowest to highest.

If you ask for a column that does not exist, the script tells you which ones are available:

```bash
$ python main.py --file data/sample_sales.csv --sort price
Error: the column 'price' does not exist in the dataset.
Available columns: date, product, category, units_sold, unit_price
```

## Generating charts

```bash
python main.py --file data/sample_sales.csv --plot
```

The script looks at the type of each column and picks the chart that fits:

| Column type | Chart | What it shows |
|-------------|-------|---------------|
| Numeric | Histogram | How values spread across ranges |
| Text | Horizontal bars | How often each category appears (top 10) |
| Date | Line | How each numeric column evolves over time |

Files are saved into `output/`, with the chart type in the name:

```
  Saved: output\bars_product.png
  Saved: output\bars_category.png
  Saved: output\histogram_units_sold.png
  Saved: output\histogram_unit_price.png
  Saved: output\line_units_sold_by_date.png
  Saved: output\line_unit_price_by_date.png
```

### What they look like

**`bars_category.png`** — horizontal bars, most frequent category on top.
Peripherals appears 7 times, Displays and Audio 4 each, Computers 3 and Video 2.
They are horizontal so category names read without rotating the text.

**`histogram_units_sold.png`** — the X axis holds ranges of units sold and the Y axis
how many rows fall into each range. Most sales turn out to be of just a few units.

**`line_units_sold_by_date.png`** — a line with the total units per date, one dot for
every day that has data.

### Chart design decisions

Every bar in a chart uses the **same color**. Painting each bar differently is tempting,
but it adds nothing: the length of the bar already tells you which one is bigger. Coloring
them differently repeats that information and burns color, the one free channel left to
show something new.

The grid is a thin, light line — never black, never dashed. It is there to help read
values, not to compete with the data.

On axes that count rows, the ticks are whole numbers. There is no such thing as half a row.

### How dates are detected

A column counts as a date if it already has a date type, or if it is **text** and pandas
manages to convert it. Restricting this to text is deliberate: any number can be read as a
date (seconds since 1970), so a column like `units_sold` would be misdetected as one.

## Error handling

The script does not throw a stack trace in your face. It translates the common failures
into clear messages and exits with code 1:

```bash
$ python main.py --file missing.csv
Error: could not find the file 'missing.csv'.
Check that the path is spelled correctly and that the file exists.
```

Cases covered: missing file, no read permission, empty file, and malformed CSV.

## Project structure

```
.
├── main.py             # The whole script
├── requirements.txt    # Dependencies
├── README.md
├── LICENSE
├── assets/             # Project logo
├── data/               # Sample CSV to try it out
│   └── sample_sales.csv
└── output/             # Generated charts land here
```

## Roadmap

- [x] Read a CSV and show basic information
- [x] Sort by one or more columns (`--sort`, ascending and descending)
- [x] Generate charts based on column type (`--plot`) and save them into `output/`
- [ ] Support more input formats (Excel, JSON)
- [ ] Basic statistical analysis (mean, median, correlations)
- [ ] Graphical interface

## License

MIT — use it, copy it and modify it freely. See [LICENSE](LICENSE).
