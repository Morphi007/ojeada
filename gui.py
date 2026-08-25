"""
ojeada - graphical interface.

A Tkinter window around the same functions main.py uses from the terminal:
pick a file, see its info, sort it, see statistics and view charts live,
without needing to save any image to disk first.

Usage:
    python gui.py
"""

import contextlib
import ctypes
import io
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt

from main import (
    AXIS_COLOR,
    CHART_COLOR,
    MUTED_COLOR,
    SUPPORTED_FILE_TYPES,
    SURFACE_COLOR,
    TEXT_COLOR,
    build_chart_figure,
    chart_label,
    list_available_charts,
    read_dataset,
    show_basic_info,
    show_sorted_result,
    show_statistics,
    sort_dataset,
)

WINDOW_TITLE = "ojeada"
WINDOW_WIDTH = 1080
WINDOW_HEIGHT = 680
MIN_WIDTH = 760
MIN_HEIGHT = 480
SIDEBAR_WIDTH = 240
SIDEBAR_COLOR = "#f3f2ee"
OUTPUT_FONT = ("Consolas", 10)
DATA_FOLDER = Path(__file__).resolve().parent / "data"


def enable_high_dpi_awareness():
    """Tell Windows this app handles its own scaling, so it stops blurring the window on 4K/150%+ screens."""
    if sys.platform != "win32":
        return

    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except (AttributeError, OSError):
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except (AttributeError, OSError):
            pass


def get_dpi_scale(root):
    """1.0 at 100% Windows scaling, 1.5 at 150%, 2.0 on most 4K screens."""
    try:
        return root.winfo_fpixels("1i") / 96
    except tk.TclError:
        return 1.0


def run_captured(action, *args):
    """Run a main.py function and return what it printed instead of letting it reach the terminal."""
    buffer = io.StringIO()
    result = None

    try:
        with contextlib.redirect_stdout(buffer):
            result = action(*args)
    except SystemExit:
        pass  # main.py calls sys.exit(1) on error, which would otherwise close the window

    return buffer.getvalue(), result


def set_text(text_box, text):
    """Replace the contents of a read-only text box."""
    text_box.configure(state=tk.NORMAL)
    text_box.delete("1.0", tk.END)
    text_box.insert(tk.END, text)
    text_box.configure(state=tk.DISABLED)


def find_local_data_files():
    """List CSV, Excel and JSON files stored in the project's data/ folder."""
    if not DATA_FOLDER.is_dir():
        return []

    return sorted(
        path for path in DATA_FOLDER.iterdir()
        if path.suffix.lower() in SUPPORTED_FILE_TYPES
    )


def refresh_file_list(file_list):
    """Fill the sidebar list with the files auto-detected in data/."""
    file_list.delete(0, tk.END)
    for file_path in find_local_data_files():
        file_list.insert(tk.END, file_path.name)


def load_file(state, widgets, file_path):
    """Read a file and refresh every tab with its information."""
    text, dataset = run_captured(read_dataset, file_path)

    if dataset is None:
        messagebox.showerror("Could not open file", text.strip())
        return

    state["dataset"] = dataset
    state["file_path"] = file_path

    widgets["status_label"].configure(text=f"Loaded: {Path(file_path).name}")

    info_text, _ = run_captured(show_basic_info, dataset)
    set_text(widgets["info_box"], info_text.strip())

    stats_text, _ = run_captured(show_statistics, dataset)
    set_text(widgets["stats_box"], stats_text.strip())

    set_text(widgets["sort_box"], "")
    refresh_chart_menu(state, widgets)
    widgets["notebook"].select(widgets["info_tab"])


def browse_for_file(state, widgets):
    """Open the system file picker for a file outside data/."""
    file_path = filedialog.askopenfilename(
        title="Open a CSV, Excel or JSON file",
        filetypes=[
            ("Supported files", " ".join(f"*{ext}" for ext in SUPPORTED_FILE_TYPES)),
            ("All files", "*.*"),
        ],
    )
    if file_path:
        load_file(state, widgets, file_path)


def on_local_file_selected(state, widgets, file_list):
    """Load whichever file was just clicked in the sidebar list."""
    selection = file_list.curselection()
    if not selection:
        return

    file_name = file_list.get(selection[0])
    load_file(state, widgets, str(DATA_FOLDER / file_name))


def run_sort(state, widgets, columns_entry, descending_var):
    """Sort the currently loaded dataset by the columns typed in the entry."""
    if state["dataset"] is None:
        messagebox.showwarning("No file open", "Choose a file first.")
        return

    column_names = columns_entry.get().split()
    if not column_names:
        messagebox.showwarning("No columns", "Type one or more column names to sort by.")
        return

    text, sorted_dataset = run_captured(
        sort_dataset, state["dataset"], column_names, descending_var.get()
    )

    if sorted_dataset is None:
        set_text(widgets["sort_box"], text.strip())
        return

    state["dataset"] = sorted_dataset

    result_text, _ = run_captured(
        show_sorted_result, sorted_dataset, column_names, descending_var.get()
    )
    set_text(widgets["sort_box"], result_text.strip())
    refresh_chart_menu(state, widgets)


def refresh_chart_menu(state, widgets):
    """Refill the chart picker with the charts available for this dataset."""
    charts = list_available_charts(state["dataset"])
    state["charts"] = charts

    labels = [chart_label(kind, column_name) for kind, column_name in charts]
    chart_picker = widgets["chart_picker"]
    chart_picker.configure(values=labels)

    if labels:
        chart_picker.current(0)
        show_selected_chart(state, widgets)
    else:
        chart_picker.set("")
        clear_chart_canvas(widgets)


def clear_chart_canvas(widgets):
    """Remove whichever chart is currently drawn in the charts tab."""
    for child in widgets["chart_frame"].winfo_children():
        child.destroy()


def show_selected_chart(state, widgets):
    """Draw the chart chosen in the dropdown directly inside the window."""
    if state["dataset"] is None or not state["charts"]:
        return

    index = widgets["chart_picker"].current()
    if index < 0:
        return

    kind, column_name = state["charts"][index]
    figure = build_chart_figure(state["dataset"], kind, column_name)

    clear_chart_canvas(widgets)
    canvas = FigureCanvasTkAgg(figure, master=widgets["chart_frame"])
    canvas.draw()
    canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    plt.close(figure)  # already drawn on the canvas, no need to keep it open in pyplot


def configure_style(root):
    """Apply the same colors the charts use to the rest of the window."""
    style = ttk.Style(root)
    style.theme_use("clam")

    root.configure(background=SURFACE_COLOR)

    style.configure("TFrame", background=SURFACE_COLOR)
    style.configure("Sidebar.TFrame", background=SIDEBAR_COLOR)
    style.configure("TLabel", background=SURFACE_COLOR, foreground=TEXT_COLOR)
    style.configure("Sidebar.TLabel", background=SIDEBAR_COLOR, foreground=TEXT_COLOR)
    style.configure(
        "Title.TLabel",
        background=SIDEBAR_COLOR,
        foreground=TEXT_COLOR,
        font=("Segoe UI", 16, "bold"),
    )
    style.configure(
        "Subtitle.TLabel",
        background=SIDEBAR_COLOR,
        foreground=MUTED_COLOR,
        font=("Segoe UI", 9),
    )
    style.configure("Status.TLabel", foreground=MUTED_COLOR, padding=(10, 6))

    style.configure(
        "TButton",
        background=CHART_COLOR,
        foreground="#ffffff",
        font=("Segoe UI", 10),
        padding=8,
        borderwidth=0,
    )
    style.map("TButton", background=[("active", "#1f5fac")])

    style.configure(
        "Secondary.TButton",
        background=SIDEBAR_COLOR,
        foreground=TEXT_COLOR,
        font=("Segoe UI", 9),
        padding=6,
        borderwidth=1,
        bordercolor=AXIS_COLOR,
    )

    style.configure("TNotebook", background=SURFACE_COLOR, borderwidth=0)
    style.configure(
        "TNotebook.Tab",
        background=SIDEBAR_COLOR,
        foreground=TEXT_COLOR,
        padding=(16, 10),
        font=("Segoe UI", 10),
    )
    style.map("TNotebook.Tab", background=[("selected", SURFACE_COLOR)])

    style.configure("TEntry", padding=6)
    style.configure("TCheckbutton", background=SURFACE_COLOR)
    style.configure("TCombobox", padding=6)


def build_output_box(parent):
    """Build a read-only, monospaced text area for showing tabular output."""
    text_box = ScrolledText(
        parent,
        wrap=tk.NONE,
        font=OUTPUT_FONT,
        background="#ffffff",
        foreground=TEXT_COLOR,
        borderwidth=0,
        padx=12,
        pady=12,
    )
    text_box.configure(state=tk.DISABLED)
    return text_box


def build_sidebar(root, state, widgets, sidebar_width, dpi_scale):
    """Build the left panel: logo, file picker and the auto-detected files."""
    sidebar = ttk.Frame(root, style="Sidebar.TFrame", padding=16, width=sidebar_width)
    sidebar.pack(side=tk.LEFT, fill=tk.Y)
    sidebar.pack_propagate(False)

    # subsample only takes whole numbers, so the shrink factor is rounded;
    # the logo just ends up a little bigger on very high DPI screens.
    logo_shrink = max(round(8 / dpi_scale), 1)
    logo_path = Path(__file__).resolve().parent / "assets" / "logo-512.png"
    if logo_path.exists():
        logo_image = tk.PhotoImage(file=logo_path).subsample(logo_shrink, logo_shrink)
        widgets["logo_image"] = logo_image  # kept alive, or Tk would drop it
        ttk.Label(sidebar, image=logo_image, style="Sidebar.TLabel").pack(anchor=tk.W)

    ttk.Label(sidebar, text="ojeada", style="Title.TLabel").pack(anchor=tk.W, pady=(8, 0))
    ttk.Label(
        sidebar, text="A quick look at any dataset", style="Subtitle.TLabel"
    ).pack(anchor=tk.W, pady=(0, 16))

    ttk.Button(
        sidebar, text="Browse for a file...", command=lambda: browse_for_file(state, widgets)
    ).pack(fill=tk.X)

    ttk.Label(
        sidebar, text="FILES FOUND IN data/", style="Subtitle.TLabel"
    ).pack(anchor=tk.W, pady=(20, 6))

    file_list = tk.Listbox(
        sidebar,
        background="#ffffff",
        foreground=TEXT_COLOR,
        selectbackground=CHART_COLOR,
        selectforeground="#ffffff",
        borderwidth=0,
        highlightthickness=1,
        highlightbackground=AXIS_COLOR,
        activestyle="none",
    )
    file_list.pack(fill=tk.BOTH, expand=True)
    file_list.bind(
        "<<ListboxSelect>>", lambda event: on_local_file_selected(state, widgets, file_list)
    )
    refresh_file_list(file_list)

    ttk.Button(
        sidebar,
        text="Refresh list",
        style="Secondary.TButton",
        command=lambda: refresh_file_list(file_list),
    ).pack(fill=tk.X, pady=(8, 0))


def build_info_tab(notebook, widgets):
    """Build the tab that shows the basic information of the dataset."""
    tab = ttk.Frame(notebook, padding=16)
    widgets["info_box"] = build_output_box(tab)
    widgets["info_box"].pack(fill=tk.BOTH, expand=True)
    widgets["info_tab"] = tab
    notebook.add(tab, text="Info")


def build_sort_tab(notebook, state, widgets):
    """Build the tab that sorts the dataset by one or more columns."""
    tab = ttk.Frame(notebook, padding=16)

    controls = ttk.Frame(tab)
    controls.pack(fill=tk.X, pady=(0, 12))

    ttk.Label(controls, text="Columns:").pack(side=tk.LEFT)
    columns_entry = ttk.Entry(controls, width=30)
    columns_entry.pack(side=tk.LEFT, padx=(8, 12))

    descending_var = tk.BooleanVar(value=False)
    ttk.Checkbutton(controls, text="Descending", variable=descending_var).pack(side=tk.LEFT)

    ttk.Button(
        controls,
        text="Sort",
        command=lambda: run_sort(state, widgets, columns_entry, descending_var),
    ).pack(side=tk.LEFT, padx=(12, 0))

    widgets["sort_box"] = build_output_box(tab)
    widgets["sort_box"].pack(fill=tk.BOTH, expand=True)
    notebook.add(tab, text="Sort")


def build_stats_tab(notebook, widgets):
    """Build the tab that shows mean, median, standard deviation and correlations."""
    tab = ttk.Frame(notebook, padding=16)
    widgets["stats_box"] = build_output_box(tab)
    widgets["stats_box"].pack(fill=tk.BOTH, expand=True)
    notebook.add(tab, text="Statistics")


def build_charts_tab(notebook, state, widgets):
    """Build the tab that shows a chosen chart drawn live inside the window."""
    tab = ttk.Frame(notebook, padding=16)

    controls = ttk.Frame(tab)
    controls.pack(fill=tk.X, pady=(0, 12))

    ttk.Label(controls, text="Chart:").pack(side=tk.LEFT)
    chart_picker = ttk.Combobox(controls, state="readonly", width=40)
    chart_picker.pack(side=tk.LEFT, padx=(8, 0))
    chart_picker.bind(
        "<<ComboboxSelected>>", lambda event: show_selected_chart(state, widgets)
    )
    widgets["chart_picker"] = chart_picker

    chart_frame = ttk.Frame(tab)
    chart_frame.pack(fill=tk.BOTH, expand=True)
    widgets["chart_frame"] = chart_frame

    notebook.add(tab, text="Charts")


def build_gui():
    """Build and run the ojeada window."""
    enable_high_dpi_awareness()

    state = {"dataset": None, "file_path": None, "charts": []}
    widgets = {}

    root = tk.Tk()
    root.title(WINDOW_TITLE)

    dpi_scale = get_dpi_scale(root)
    root.tk.call("tk", "scaling", root.winfo_fpixels("1i") / 72)  # keeps point-sized fonts correct

    root.geometry(f"{round(WINDOW_WIDTH * dpi_scale)}x{round(WINDOW_HEIGHT * dpi_scale)}")
    root.minsize(round(MIN_WIDTH * dpi_scale), round(MIN_HEIGHT * dpi_scale))

    icon_path = Path(__file__).resolve().parent / "assets" / "favicon.png"
    if icon_path.exists():
        widgets["icon_image"] = tk.PhotoImage(file=icon_path)
        root.iconphoto(True, widgets["icon_image"])

    configure_style(root)

    build_sidebar(root, state, widgets, round(SIDEBAR_WIDTH * dpi_scale), dpi_scale)

    main_area = ttk.Frame(root)
    main_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    notebook = ttk.Notebook(main_area)
    notebook.pack(fill=tk.BOTH, expand=True)
    widgets["notebook"] = notebook

    build_info_tab(notebook, widgets)
    build_sort_tab(notebook, state, widgets)
    build_stats_tab(notebook, widgets)
    build_charts_tab(notebook, state, widgets)

    status_label = ttk.Label(main_area, text="Choose a file to get started.", style="Status.TLabel")
    status_label.pack(fill=tk.X, side=tk.BOTTOM)
    widgets["status_label"] = status_label

    root.mainloop()


if __name__ == "__main__":
    build_gui()
