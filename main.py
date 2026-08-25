"""
ojeada - a quick look at any CSV file.

Reads a CSV file, shows basic information about it, sorts it and draws charts.

Usage:
    python main.py --file data/sample_sales.csv
    python main.py --file data/sample_sales.csv --sort units_sold --desc
    python main.py --file data/sample_sales.csv --plot
"""

import argparse
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # no display needed, must be set before importing pyplot

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.ticker import MaxNLocator

# Same color everywhere, one series per chart.
CHART_COLOR = "#2a78d6"
SURFACE_COLOR = "#fcfcfb"
GRID_COLOR = "#e1e0d9"
AXIS_COLOR = "#c3c2b7"
TEXT_COLOR = "#0b0b0b"
MUTED_COLOR = "#898781"

MAX_CATEGORIES_IN_CHART = 10


SUPPORTED_FILE_TYPES = (".csv", ".xlsx", ".xls", ".json")


def read_dataset(file_path):
    """Read a CSV, Excel or JSON file and return it as a DataFrame."""
    extension = Path(file_path).suffix.lower()

    if extension not in SUPPORTED_FILE_TYPES:
        print(f"Error: unsupported file type '{extension}'.")
        print(f"Supported formats: {', '.join(SUPPORTED_FILE_TYPES)}")
        sys.exit(1)

    try:
        if extension == ".csv":
            dataset = pd.read_csv(file_path)
        elif extension in (".xlsx", ".xls"):
            dataset = pd.read_excel(file_path)
        else:
            dataset = pd.read_json(file_path)

    except FileNotFoundError:
        print(f"Error: could not find the file '{file_path}'.")
        print("Check that the path is spelled correctly and that the file exists.")
        sys.exit(1)

    except PermissionError:
        print(f"Error: you do not have permission to read the file '{file_path}'.")
        sys.exit(1)

    except pd.errors.EmptyDataError:
        print(f"Error: the file '{file_path}' is empty.")
        sys.exit(1)

    except pd.errors.ParserError:
        print(f"Error: the file '{file_path}' is not a valid CSV.")
        print("Some commas may be missing, quotes unbalanced, or rows may not line up.")
        sys.exit(1)

    except ValueError:
        print(f"Error: the file '{file_path}' is not a valid {extension} file.")
        sys.exit(1)

    return dataset


def show_dataset_size(dataset):
    """Show how many rows and columns the dataset has."""
    print("DATASET SIZE")
    print(f"  Rows:    {len(dataset)}")
    print(f"  Columns: {len(dataset.columns)}")
    print()


def show_columns_detail(dataset):
    """Show the name, type and number of missing values of every column."""
    total_rows = len(dataset)

    print("COLUMNS")
    print(f"  {'NAME':<15} {'TYPE':<12} {'MISSING':>8}  PERCENTAGE")
    print("  " + "-" * 50)

    for column_name in dataset.columns:
        column = dataset[column_name]
        missing_count = column.isna().sum()

        # A CSV can have a header row and no data rows at all.
        if total_rows > 0:
            missing_percentage = (missing_count / total_rows) * 100
        else:
            missing_percentage = 0

        print(
            f"  {column_name:<15} {str(column.dtype):<12} "
            f"{missing_count:>8}  {missing_percentage:>6.1f}%"
        )

    print()


def show_missing_summary(dataset):
    """Show the total number of missing values in the dataset."""
    total_missing = dataset.isna().sum().sum()

    print("MISSING VALUES")

    if total_missing == 0:
        print("  The dataset has no missing values.")
    else:
        print(f"  The dataset has {total_missing} missing values in total.")

    print()


def show_statistics(dataset):
    """Show mean, median, standard deviation and correlations for numeric columns."""
    numeric_columns = dataset.select_dtypes(include="number")

    print("=" * 54)
    print("BASIC STATISTICS")
    print("=" * 54)
    print()

    if numeric_columns.empty:
        print("  The dataset has no numeric columns to analyze.")
        print()
        return

    print("SUMMARY (numeric columns)")
    summary = pd.DataFrame({
        "mean": numeric_columns.mean(),
        "median": numeric_columns.median(),
        "std_dev": numeric_columns.std(),
    })
    print(summary)
    print()

    if len(numeric_columns.columns) > 1:
        print("CORRELATIONS")
        print(numeric_columns.corr())
        print()


def show_first_rows(dataset, how_many=5):
    """Show the first rows of the dataset."""
    print(f"FIRST {how_many} ROWS")
    print(dataset.head(how_many))
    print()


def show_basic_info(dataset):
    """Show all the basic information about the dataset."""
    print()
    print("=" * 54)
    print("BASIC DATASET INFORMATION")
    print("=" * 54)
    print()

    show_dataset_size(dataset)
    show_columns_detail(dataset)
    show_missing_summary(dataset)
    show_first_rows(dataset)


def check_columns_exist(dataset, column_names):
    """Stop the program if any of the requested columns is not in the dataset."""
    for column_name in column_names:
        if column_name not in dataset.columns:
            print(f"Error: the column '{column_name}' does not exist in the dataset.")
            print(f"Available columns: {', '.join(dataset.columns)}")
            sys.exit(1)


def sort_dataset(dataset, column_names, descending):
    """Return a copy of the dataset sorted by the given columns."""
    check_columns_exist(dataset, column_names)

    # no inplace=, keep the original dataset untouched
    return dataset.sort_values(by=column_names, ascending=not descending)


def show_sorted_result(dataset, column_names, descending):
    """Show the dataset once it has been sorted."""
    if descending:
        order = "descending"
    else:
        order = "ascending"

    print("=" * 54)
    print(f"SORTED BY: {', '.join(column_names)} ({order})")
    print("=" * 54)
    print()
    print(dataset.head(10))
    print()


def is_number_column(dataset, column_name):
    """Tell whether the column holds numbers."""
    return pd.api.types.is_numeric_dtype(dataset[column_name])


def is_text_column(dataset, column_name):
    """Tell whether the column holds text."""
    return pd.api.types.is_string_dtype(dataset[column_name])


def is_date_column(dataset, column_name):
    """Tell whether the column holds dates. Only text is tried, numbers convert too easily."""
    if pd.api.types.is_datetime64_any_dtype(dataset[column_name]):
        return True

    if not is_text_column(dataset, column_name):
        return False

    try:
        pd.to_datetime(dataset[column_name])
        return True
    except (ValueError, TypeError):
        return False


def find_date_column(dataset):
    """Return the name of the first date column, or None if there is none."""
    for column_name in dataset.columns:
        if is_date_column(dataset, column_name):
            return column_name

    return None


def build_file_name(prefix, column_name):
    """Build a safe file name out of a column name."""
    safe_name = "".join(
        character if character.isalnum() else "_"
        for character in column_name
    )
    return f"{prefix}_{safe_name}.png"


def apply_chart_style(axes, title, x_label, y_label, grid_axis="both"):
    """Apply the same visual style to every chart."""
    axes.set_title(title, color=TEXT_COLOR, fontsize=13, pad=15)
    axes.set_xlabel(x_label, color=MUTED_COLOR, fontsize=10)
    axes.set_ylabel(y_label, color=MUTED_COLOR, fontsize=10)

    # grid_axis is only set here — a second axes.grid() call would override it
    axes.grid(axis=grid_axis, color=GRID_COLOR, linewidth=0.8)
    axes.set_axisbelow(True)

    axes.spines["top"].set_visible(False)
    axes.spines["right"].set_visible(False)
    axes.spines["left"].set_color(AXIS_COLOR)
    axes.spines["bottom"].set_color(AXIS_COLOR)

    axes.tick_params(colors=MUTED_COLOR, labelsize=9)


def save_chart(figure, output_folder, file_name):
    """Save the chart as a PNG file and release the memory it was using."""
    file_path = output_folder / file_name

    # bbox_inches="tight" so long labels don't get cut off
    figure.savefig(file_path, dpi=150, bbox_inches="tight", facecolor=SURFACE_COLOR)
    plt.close(figure)

    print(f"  Saved: {file_path}")


def build_histogram_figure(dataset, column_name):
    """Build a histogram figure: how many values fall into each range."""
    values = dataset[column_name].dropna()

    figure, axes = plt.subplots(figsize=(8, 5), facecolor=SURFACE_COLOR)
    axes.set_facecolor(SURFACE_COLOR)

    # rwidth leaves a gap between bars so they read apart without a border.
    axes.hist(values, bins=10, color=CHART_COLOR, rwidth=0.95)

    axes.yaxis.set_major_locator(MaxNLocator(integer=True))  # whole numbers only

    apply_chart_style(
        axes,
        title=f"Distribution of {column_name}",
        x_label=column_name,
        y_label="Number of rows",
        grid_axis="y",
    )

    return figure


def plot_histogram(dataset, column_name, output_folder):
    """Draw a histogram and save it as a PNG file."""
    figure = build_histogram_figure(dataset, column_name)
    save_chart(figure, output_folder, build_file_name("histogram", column_name))


def build_bars_figure(dataset, column_name):
    """Build a bar chart figure: how many times each category shows up."""
    counts = dataset[column_name].value_counts().head(MAX_CATEGORIES_IN_CHART)

    counts = counts.sort_values()  # so the most frequent one ends up on top

    figure, axes = plt.subplots(figsize=(8, 5), facecolor=SURFACE_COLOR)
    axes.set_facecolor(SURFACE_COLOR)

    axes.barh(counts.index, counts.to_numpy(), color=CHART_COLOR, height=0.7)

    axes.xaxis.set_major_locator(MaxNLocator(integer=True))  # whole numbers only

    apply_chart_style(
        axes,
        title=f"Frequency of {column_name}",
        x_label="Number of rows",
        y_label="",
        grid_axis="x",
    )

    return figure


def plot_bars(dataset, column_name, output_folder):
    """Draw a bar chart and save it as a PNG file."""
    figure = build_bars_figure(dataset, column_name)
    save_chart(figure, output_folder, build_file_name("bars", column_name))


def build_time_series_figure(dataset, date_column, value_column):
    """Build a line figure with the total of a numeric column over time."""
    dates = pd.to_datetime(dataset[date_column])

    # Group by date so every date shows up only once along the line.
    totals = dataset.groupby(dates)[value_column].sum().sort_index()

    figure, axes = plt.subplots(figsize=(9, 5), facecolor=SURFACE_COLOR)
    axes.set_facecolor(SURFACE_COLOR)

    axes.plot(
        totals.index,
        totals.to_numpy(),
        color=CHART_COLOR,
        linewidth=2,
        marker="o",
        markersize=5,
    )

    apply_chart_style(
        axes,
        title=f"{value_column} over time",
        x_label=date_column,
        y_label=f"Total {value_column}",
        grid_axis="y",
    )

    figure.autofmt_xdate()

    return figure


def plot_time_series(dataset, date_column, value_column, output_folder):
    """Draw a line chart and save it as a PNG file."""
    figure = build_time_series_figure(dataset, date_column, value_column)
    file_name = build_file_name("line", f"{value_column}_by_{date_column}")
    save_chart(figure, output_folder, file_name)


def list_available_charts(dataset):
    """List (kind, column_name) pairs; kind is "histogram", "bars" or "time_series"."""
    date_column = find_date_column(dataset)
    charts = []

    for column_name in dataset.columns:
        if column_name == date_column:
            continue

        if is_number_column(dataset, column_name):
            charts.append(("histogram", column_name))
        elif is_text_column(dataset, column_name):
            charts.append(("bars", column_name))

    if date_column is not None:
        for column_name in dataset.columns:
            if is_number_column(dataset, column_name):
                charts.append(("time_series", column_name))

    return charts


def chart_label(kind, column_name):
    """Build a human-readable label for a chart, for menus and lists."""
    if kind == "histogram":
        return f"Distribution of {column_name}"
    if kind == "bars":
        return f"Frequency of {column_name}"
    return f"{column_name} over time"


def build_chart_figure(dataset, kind, column_name):
    """Build the figure for one chart (identified by list_available_charts)."""
    if kind == "histogram":
        return build_histogram_figure(dataset, column_name)
    if kind == "bars":
        return build_bars_figure(dataset, column_name)
    return build_time_series_figure(dataset, find_date_column(dataset), column_name)


def create_output_folder(folder_name="output"):
    """Create the folder where charts are saved, if it is not there yet."""
    output_folder = Path(folder_name)
    output_folder.mkdir(exist_ok=True)
    return output_folder


def generate_all_plots(dataset):
    """Draw one chart per column, picking the type that fits its data."""
    output_folder = create_output_folder()
    date_column = find_date_column(dataset)

    print("=" * 54)
    print("GENERATING CHARTS")
    print("=" * 54)
    print()

    for column_name in dataset.columns:
        if column_name == date_column:
            continue

        if is_number_column(dataset, column_name):
            plot_histogram(dataset, column_name, output_folder)
        elif is_text_column(dataset, column_name):
            plot_bars(dataset, column_name, output_folder)

    if date_column is not None:
        for column_name in dataset.columns:
            if is_number_column(dataset, column_name):
                plot_time_series(dataset, date_column, column_name, output_folder)

    print()


def create_argument_parser():
    """Define the arguments the script accepts from the terminal."""
    parser = argparse.ArgumentParser(
        description="Read a CSV file, describe it, sort it and draw charts.",
    )

    parser.add_argument(
        "--file",
        required=True,
        help="Path to the CSV file you want to explore.",
    )

    parser.add_argument(
        "--sort",
        nargs="+",
        help="One or more columns to sort by. Example: --sort category units_sold",
    )

    parser.add_argument(
        "--desc",
        action="store_true",
        help="Sort from highest to lowest. Sorts from lowest to highest by default.",
    )

    parser.add_argument(
        "--plot",
        action="store_true",
        help="Generate charts and save them into the output/ folder.",
    )

    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show mean, median, standard deviation and correlations for numeric columns.",
    )

    return parser


def main():
    """Read the arguments and run whatever was asked for."""
    parser = create_argument_parser()
    arguments = parser.parse_args()

    dataset = read_dataset(arguments.file)
    show_basic_info(dataset)

    if arguments.sort:
        dataset = sort_dataset(dataset, arguments.sort, arguments.desc)
        show_sorted_result(dataset, arguments.sort, arguments.desc)

    if arguments.stats:
        show_statistics(dataset)

    if arguments.plot:
        generate_all_plots(dataset)


if __name__ == "__main__":
    main()
