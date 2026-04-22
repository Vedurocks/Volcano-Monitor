"""
VolcanoEruptionMonitor.pyw  v5.0
Vedurocks Ltd 2026
Pure-black minimalistic dark UI.
Dual sensor: Ultrasonic + Seismic.
Tabs: Connection | Settings | Shell | AI
Serial format: distance,seismic,dist_alert,seis_alert,dual_alert,kill_state,sys_state,min_ultra,min_seis
Commands: on | off | kill | reset | 456 | min ult X | min sei X
"""
import os, sys, re, json, csv, threading, queue, time
from datetime import datetime
from pathlib import Path
from collections import deque

import tkinter as tk
from tkinter import ttk

try:
    import serial, serial.tools.list_ports
    HAS_SERIAL = True
except ImportError:
    HAS_SERIAL = False

try:
    from PIL import Image, ImageTk
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

try:
    import matplotlib
    matplotlib.use("TkAgg")
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    HAS_MPL = True
except Exception as e:
    HAS_MPL = False
    MPL_ERROR = str(e)
    print(f"matplotlib import failed: {e}")

try:
    import requests as _requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

try:
    import winsound
    HAS_SOUND = True
except ImportError:
    HAS_SOUND = False

# ════════════════════════════════════════════════════════════
#  THEMES
# ════════════════════════════════════════════════════════════
THEMES = {
    "dark": {
        "bg":        "#000000",
        "surface":   "#080808",
        "panel":     "#0e0e0e",
        "panel2":    "#141414",
        "border":    "#1e1e1e",
        "accent":    "#f97316",
        "blue":      "#3b82f6",
        "bluehov":   "#60a5fa",
        "green":     "#22c55e",
        "greenhov":  "#4ade80",
        "red":       "#ef4444",
        "redhov":    "#f87171",
        "orange":    "#f97316",
        "orangehov": "#fb923c",
        "white":     "#ffffff",
        "text":      "#f5f5f5",
        "textdim":   "#3a3a3a",
        "textsub":   "#6b6b6b",
        "btn":       "#111111",
        "btnbord":   "#252525",
        "btnhov":    "#1a1a1a",
        "entry":     "#050505",
        "entbord":   "#252525",
        "logbg":     "#000000",
        "logfg":     "#22c55e",
        "graphbg":   "#000000",
        "graphfg":   "#3b82f6",
        "graphfg2":  "#f97316",
        "graphgrid": "#111111",
        "aibg":      "#000000",
        "aiuser":    "#0a1628",
        "aibot":     "#0a1a0a",
        "banner":    "#000000",
        "scrollbg":  "#000000",
        "scrollfg":  "#1e1e1e",
        "yellow":    "#eab308",
    },
    "light": {
        "bg":        "#f8fafc",
        "surface":   "#ffffff",
        "panel":     "#f1f5f9",
        "panel2":    "#e2e8f0",
        "border":    "#cbd5e1",
        "accent":    "#ea580c",
        "blue":      "#2563eb",
        "bluehov":   "#1d4ed8",
        "green":     "#16a34a",
        "greenhov":  "#15803d",
        "red":       "#dc2626",
        "redhov":    "#b91c1c",
        "orange":    "#ea580c",
        "orangehov": "#c2410c",
        "white":     "#ffffff",
        "text":      "#0f172a",
        "textdim":   "#94a3b8",
        "textsub":   "#64748b",
        "btn":       "#e2e8f0",
        "btnbord":   "#cbd5e1",
        "btnhov":    "#cbd5e1",
        "entry":     "#ffffff",
        "entbord":   "#94a3b8",
        "logbg":     "#f8fafc",
        "logfg":     "#16a34a",
        "graphbg":   "#ffffff",
        "graphfg":   "#2563eb",
        "graphfg2":  "#ea580c",
        "graphgrid": "#e2e8f0",
        "aibg":      "#f8fafc",
        "aiuser":    "#dbeafe",
        "aibot":     "#dcfce7",
        "banner":    "#0f172a",
        "scrollbg":  "#e2e8f0",
        "scrollfg":  "#94a3b8",
        "yellow":    "#ca8a04",
    },
}

C: dict = dict(THEMES["dark"])

# ════════════════════════════════════════════════════════════
#  CONSTANTS
# ════════════════════════════════════════════════════════════
BASE         = Path(sys.executable).parent if getattr(sys, "frozen", False) \
               else Path(__file__).parent
CONFIG_FILE  = BASE / "volcano_config.json"
LOG_DIR      = BASE / "logs"
LOG_DIR.mkdir(exist_ok=True)
SARVAM_URL   = "https://api.sarvam.ai/v1/chat/completions"
SARVAM_MODEL = "sarvam-105b"
SARVAM_KEY   = "sk_r23iydgh_dw0vMbf5zUDob7Koc7oIClYi"
VOLCANO_API  = "https://volcano-monitor-sandy.vercel.app/api/volcano"
COMMAND_POLL_INTERVAL = 1.0  # seconds between GET requests for commands
GRAPH_POINTS = 120

# ════════════════════════════════════════════════════════════
#  HELPERS
# ════════════════════════════════════════════════════════════
def ts()  -> str: return datetime.now().strftime("%H:%M:%S")
def dts() -> str: return datetime.now().strftime("%Y%m%d")
def resource(r: str) -> str: return str(BASE / r)

def _lighten(h: str, a: int = 40) -> str:
    return "#{:02x}{:02x}{:02x}".format(
        min(255, int(h[1:3], 16) + a),
        min(255, int(h[3:5], 16) + a),
        min(255, int(h[5:7], 16) + a))

def sep(parent, color=None, pady=(4, 0)):
    tk.Frame(parent, bg=color or C["border"], height=1).pack(
        fill="x", padx=0, pady=pady)

# ════════════════════════════════════════════════════════════
#  TTK DARK STYLE
# ════════════════════════════════════════════════════════════
def _apply_ttk(root):
    s = ttk.Style(root)
    s.theme_use("default")

    s.configure("TNotebook",
        background=C["bg"], borderwidth=0, tabmargins=[0, 0, 0, 0])
    s.configure("TNotebook.Tab",
        background=C["panel"], foreground=C["textsub"],
        padding=[16, 7], borderwidth=0, font=("Segoe UI", 9, "bold"))
    s.map("TNotebook.Tab",
        background=[("selected", C["accent"]), ("active", C["btnhov"])],
        foreground=[("selected", "#ffffff"),   ("active", C["text"])])

    s.configure("TCombobox",
        fieldbackground=C["entry"], background=C["btn"],
        foreground=C["text"], selectbackground=C["btn"],
        selectforeground=C["text"], arrowcolor=C["textsub"],
        bordercolor=C["entbord"], lightcolor=C["entbord"],
        darkcolor=C["entbord"], relief=tk.FLAT)
    s.map("TCombobox",
        fieldbackground=[("readonly", C["entry"]), ("disabled", C["panel"])],
        foreground=[("disabled", C["textdim"])],
        background=[("active", C["btnhov"])])
    root.option_add("*TCombobox*Listbox.background",       C["panel2"])
    root.option_add("*TCombobox*Listbox.foreground",       C["text"])
    root.option_add("*TCombobox*Listbox.selectBackground", C["accent"])
    root.option_add("*TCombobox*Listbox.selectForeground", "#ffffff")

    for o in ("Vertical", "Horizontal"):
        n = f"V.{o}.TScrollbar"
        s.configure(n,
            background=C["scrollfg"], troughcolor=C["scrollbg"],
            bordercolor=C["scrollbg"], arrowcolor=C["textsub"],
            relief=tk.FLAT)
        s.map(n, background=[
            ("active", C["textsub"]), ("pressed", C["accent"])])

# ════════════════════════════════════════════════════════════
#  BUTTON WIDGET
# ════════════════════════════════════════════════════════════
class Btn(tk.Frame):
    _MAPS = {
        "blue":   ("blue",   "bluehov",   "#ffffff"),
        "green":  ("green",  "greenhov",  "#ffffff"),
        "orange": ("orange", "orangehov", "#ffffff"),
        "red":    ("red",    "redhov",    "#ffffff"),
        "white":  ("btn",    "btnhov",    "text"),
        "dim":    ("panel2", "btnhov",    "textsub"),
    }

    def __init__(self, master, text="", command=None,
                 color="white", variant="outline",
                 width=None, font_size=9, **kw):
        super().__init__(master, bg=C["bg"], cursor="hand2")
        self._cmd     = command
        self._color   = color
        self._variant = variant
        self._enabled = True

        base_c, hov_c, fg_key = self._MAPS.get(color, self._MAPS["white"])

        if variant == "solid":
            self._bg_rest = C[base_c]
            self._bg_hov  = C[hov_c]
            self._fg_rest = "#ffffff" if fg_key == "#ffffff" else C.get(fg_key, C["text"])
            self._fg_hov  = "#ffffff"
            self._bd_rest = C[base_c]
            self._bd_hov  = C[hov_c]
        elif variant == "outline":
            self._bg_rest = C["btn"]
            self._bg_hov  = C[base_c]
            self._fg_rest = C[base_c]
            self._fg_hov  = "#ffffff"
            self._bd_rest = C[base_c]
            self._bd_hov  = C[base_c]
        else:  # ghost
            self._bg_rest = C["bg"]
            self._bg_hov  = C["btnhov"]
            self._fg_rest = C.get(base_c, C["text"])
            self._fg_hov  = C.get(hov_c,  C["text"])
            self._bd_rest = C["bg"]
            self._bd_hov  = C["btnhov"]

        self._border = tk.Frame(self, bg=self._bd_rest, padx=1, pady=1)
        self._border.pack(fill="both", expand=True)

        btn_kw = dict(
            text=text, relief=tk.FLAT, bd=0, cursor="hand2",
            bg=self._bg_rest, fg=self._fg_rest,
            activebackground=self._bg_hov, activeforeground=self._fg_hov,
            disabledforeground=C["textdim"],
            font=("Segoe UI", font_size),
            padx=14, pady=6)
        if width:
            btn_kw["width"] = width
        self._btn = tk.Button(self._border, **btn_kw, command=self._click)
        self._btn.pack(fill="both", expand=True)

        for w in (self, self._border, self._btn):
            w.bind("<Enter>", self._on_enter, "+")
            w.bind("<Leave>", self._on_leave, "+")

    def _click(self):
        if self._enabled and self._cmd:
            self._cmd()

    def _on_enter(self, _=None):
        if not self._enabled: return
        self._border.config(bg=self._bd_hov)
        self._btn.config(bg=self._bg_hov, fg=self._fg_hov)

    def _on_leave(self, _=None):
        self._border.config(bg=self._bd_rest)
        self._btn.config(bg=self._bg_rest, fg=self._fg_rest)

    def configure_state(self, enabled: bool):
        self._enabled = enabled
        self._btn.config(state="normal" if enabled else "disabled")
        self._on_leave()

    def set_active(self, active: bool):
        if active:
            self._border.config(bg=C["red"])
            self._btn.config(bg=C["red"], fg="#ffffff")
        else:
            self._on_leave()

    def config_text(self, text: str):
        self._btn.config(text=text)

    def config_color(self, color: str):
        base_c, hov_c, _ = self._MAPS.get(color, self._MAPS["white"])
        if self._variant == "outline":
            self._bg_hov  = C[base_c]
            self._fg_rest = C[base_c]
            self._bd_rest = C[base_c]
            self._bd_hov  = C[base_c]
        elif self._variant == "solid":
            self._bg_rest = C[base_c]
            self._bg_hov  = C[hov_c]
            self._bd_rest = C[base_c]
            self._bd_hov  = C[hov_c]
        self._on_leave()

# ════════════════════════════════════════════════════════════
#  PROGRESS BAR
# ════════════════════════════════════════════════════════════
class CBar(tk.Canvas):
    def __init__(self, master, **kw):
        kw.setdefault("height", 18)
        kw.setdefault("bg", C["surface"])
        kw.setdefault("bd", 0)
        kw.setdefault("highlightthickness", 1)
        kw.setdefault("highlightbackground", C["border"])
        super().__init__(master, **kw)
        self._p     = 0.0
        self._alert = False
        self.bind("<Configure>", lambda _: self._draw())

    def set(self, pct: float, alert: bool = False):
        self._p     = max(0.0, min(1.0, pct))
        self._alert = alert
        self._draw()

    def _draw(self):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        self.create_rectangle(0, 0, w, h, fill=C["surface"], outline="")
        fw = int(w * self._p)
        if fw <= 0:
            return
        col = (C["red"]    if self._alert or self._p < 0.22 else
               C["yellow"] if self._p < 0.55 else C["green"])
        self.create_rectangle(0, 0, fw, h,  fill=col,              outline="")
        self.create_rectangle(0, 0, fw, 2,  fill=_lighten(col, 50), outline="")
        self.create_text(w // 2, h // 2,
                         text=f"{int(self._p * 100)}%",
                         fill=C["text"], font=("Segoe UI", 7, "bold"))

# ════════════════════════════════════════════════════════════
#  DUAL GRAPH  (ultrasonic top, seismic bottom)
# ════════════════════════════════════════════════════════════
class Graph:
    """Two stacked subplots: ultrasonic distance (top) + seismic (bottom)."""
    def __init__(self, parent):
        self._ud    = deque([0.0] * GRAPH_POINTS, maxlen=GRAPH_POINTS)
        self._sd    = deque([0.0] * GRAPH_POINTS, maxlen=GRAPH_POINTS)
        self._times = deque(range(GRAPH_POINTS),   maxlen=GRAPH_POINTS)
        self._t     = 0
        self.canvas_widget = None

        if not HAS_MPL:
            err_msg = f"matplotlib error:\n{MPL_ERROR}" if 'MPL_ERROR' in globals() else "pip install matplotlib"
            tk.Label(parent, text=err_msg,
                     bg=C["graphbg"], fg=C["textsub"],
                     font=("Consolas", 8), justify="left").pack(expand=True, padx=10)
            return

        self._fig  = Figure(figsize=(6, 3.8), dpi=96, facecolor=C["graphbg"])
        self._ax_u = self._fig.add_subplot(211)
        self._ax_s = self._fig.add_subplot(212)
        self._style_u()
        self._style_s()

        # Ultrasonic line + threshold
        self._u_line,  = self._ax_u.plot([], [], color=C["graphfg"], lw=1.5,
                                          solid_capstyle="round")
        self._u_fill   = None
        self._u_thresh = self._ax_u.axhline(y=100, color=C["red"],
                                             lw=0.8, linestyle="--", alpha=0.5)
        # Seismic line + threshold
        self._s_line,  = self._ax_s.plot([], [], color=C["graphfg2"], lw=1.5,
                                          solid_capstyle="round")
        self._s_fill   = None
        self._s_thresh = self._ax_s.axhline(y=50, color=C["red"],
                                             lw=0.8, linestyle="--", alpha=0.5)

        self._fig.tight_layout(pad=0.6, h_pad=0.8)
        self._cv = FigureCanvasTkAgg(self._fig, master=parent)
        self.canvas_widget = self._cv.get_tk_widget()
        self.canvas_widget.configure(bg=C["graphbg"], highlightthickness=0)
        self.canvas_widget.pack(fill="both", expand=True)

    def _style_ax(self, ax, ylabel, title):
        ax.set_facecolor(C["graphbg"])
        ax.tick_params(colors=C["textsub"], labelsize=6)
        for sp in ax.spines.values():
            sp.set_color(C["border"])
        ax.set_ylabel(ylabel, color=C["textsub"], fontsize=7)
        ax.set_title(title,   color=C["textsub"], fontsize=7, pad=2)
        ax.grid(True, color=C["graphgrid"], ls="--", lw=0.4, alpha=0.7)

    def _style_u(self):
        self._style_ax(self._ax_u, "cm",  "Ultrasonic Distance")
        self._ax_u.set_ylim(0, 520)

    def _style_s(self):
        self._style_ax(self._ax_s, "raw", "Seismic Activity")
        self._ax_s.set_ylim(0, 1024)

    def push(self, dist: float, seis: float,
             dist_alert: bool = False, seis_alert: bool = False,
             min_ultra: float = 100, min_seis: float = 50):
        if not HAS_MPL:
            return
        self._t += 1
        self._ud.append(dist)
        self._sd.append(seis)
        self._times.append(self._t)
        xs = list(self._times)
        ud = list(self._ud)
        sd = list(self._sd)

        self._ax_u.set_xlim(xs[0], xs[-1] + 1)
        self._ax_s.set_xlim(xs[0], xs[-1] + 1)

        uc = C["red"] if dist_alert else C["graphfg"]
        self._u_line.set_data(xs, ud)
        self._u_line.set_color(uc)
        if self._u_fill:
            self._u_fill.remove()
        self._u_fill = self._ax_u.fill_between(xs, ud, alpha=0.08, color=uc)
        self._u_thresh.set_ydata([min_ultra, min_ultra])

        sc = C["red"] if seis_alert else C["graphfg2"]
        self._s_line.set_data(xs, sd)
        self._s_line.set_color(sc)
        if self._s_fill:
            self._s_fill.remove()
        self._s_fill = self._ax_s.fill_between(xs, sd, alpha=0.08, color=sc)
        self._s_thresh.set_ydata([min_seis, min_seis])

        try:
            self._cv.draw_idle()
        except Exception:
            pass

    def clear(self):
        if not HAS_MPL:
            return
        self._ud    = deque([0.0] * GRAPH_POINTS, maxlen=GRAPH_POINTS)
        self._sd    = deque([0.0] * GRAPH_POINTS, maxlen=GRAPH_POINTS)
        self._times = deque(range(GRAPH_POINTS),   maxlen=GRAPH_POINTS)
        self._ax_u.cla()
        self._ax_s.cla()
        self._style_u()
        self._style_s()
        self._u_line, = self._ax_u.plot([], [], color=C["graphfg"],  lw=1.5)
        self._s_line, = self._ax_s.plot([], [], color=C["graphfg2"], lw=1.5)
        self._u_fill  = self._s_fill = None
        self._u_thresh = self._ax_u.axhline(y=100, color=C["red"],
                                             lw=0.8, linestyle="--", alpha=0.5)
        self._s_thresh = self._ax_s.axhline(y=50,  color=C["red"],
                                             lw=0.8, linestyle="--", alpha=0.5)
        try:
            self._cv.draw_idle()
        except Exception:
            pass

    def restyle(self):
        if not HAS_MPL:
            return
        self._fig.set_facecolor(C["graphbg"])
        for ax in (self._ax_u, self._ax_s):
            ax.set_facecolor(C["graphbg"])
            ax.tick_params(colors=C["textsub"])
            for sp in ax.spines.values():
                sp.set_color(C["border"])
            ax.grid(True, color=C["graphgrid"], ls="--", lw=0.4, alpha=0.7)
        try:
            self._cv.draw_idle()
        except Exception:
            pass

# ════════════════════════════════════════════════════════════
#  ALARM
# ════════════════════════════════════════════════════════════
class Alarm:
    def __init__(self):
        self._active = False

    def start(self):
        if self._active:
            return
        self._active = True
        threading.Thread(target=self._loop, daemon=True).start()

    def stop(self):
        self._active = False

    def _loop(self):
        while self._active:
            if HAS_SOUND:
                try:
                    winsound.Beep(1000, 200)
                except Exception:
                    pass
            else:
                print("\a", end="", flush=True)
            time.sleep(0.7)

# ════════════════════════════════════════════════════════════
#  DATA LOGGER
# ════════════════════════════════════════════════════════════
class DataLogger:
    def __init__(self):
        self._file   = None
        self._writer = None
        self._day    = None
        self._open()

    def _open(self):
        today = dts()
        if self._day == today:
            return
        if self._file:
            try:
                self._file.close()
            except Exception:
                pass
        self._day   = today
        path        = LOG_DIR / f"volcano_{today}.csv"
        new         = not path.exists()
        self._file  = open(path, "a", newline="", encoding="utf-8")
        self._writer = csv.writer(self._file)
        if new:
            self._writer.writerow([
                "timestamp", "dist_cm", "seismic",
                "dist_alert", "seis_alert", "dual_alert",
                "kill", "sys_on", "min_ultra", "min_seis"])

    def log(self, dist, seis, dist_alert, seis_alert,
            dual_alert, kill, sys_on, min_ultra, min_seis):
        try:
            self._open()
            self._writer.writerow([
                datetime.now().isoformat(timespec="seconds"),
                round(dist, 2),  round(seis, 2),
                int(dist_alert), int(seis_alert), int(dual_alert),
                int(kill),       int(sys_on),
                round(min_ultra, 1), round(min_seis, 1)])
            self._file.flush()
        except Exception:
            pass

    def close(self):
        if self._file:
            try:
                self._file.close()
            except Exception:
                pass

# ════════════════════════════════════════════════════════════
#  MAIN APP
# ════════════════════════════════════════════════════════════
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Volcano Eruption Monitor")
        self.geometry("1100x780")
        self.minsize(960, 700)
        self.configure(bg=C["bg"])
        _apply_ttk(self)

        ico = resource("volcano.ico")
        if os.path.exists(ico):
            try:
                self.iconbitmap(ico)
            except Exception:
                pass

        # ── state ────────────────────────────────────────
        self._port          = None
        self._connected     = False
        self._min_received  = False
        self._alarm_dist    = 100.0
        self._alarm_seis    = 50.0
        self._q             = queue.Queue()
        self._alarm         = Alarm()
        self._logger        = DataLogger()
        self._local_sys     = False
        self._local_kill    = False
        self._ai_history    = []
        self._shell_history = []
        self._shell_hist_idx = -1

        self._api_key    = SARVAM_KEY
        self._ai_model   = SARVAM_MODEL
        self._theme_name = "dark"
        
        # Cloud sync state
        self._last_command_poll = 0  # timestamp of last command GET request
        self._command_poll_active = False  # command polling loop running
        
        self._load_config()

        self._build_ui()
        if self._theme_name != "dark":
            self._apply_theme(self._theme_name)
        self._poll_queue()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ════════════════════════════════════════════════════════
    #  BUILD UI
    # ════════════════════════════════════════════════════════
    def _build_ui(self):
        self._build_banner()
        self._nb = ttk.Notebook(self, style="TNotebook")
        self._nb.pack(fill="both", expand=True)
        self._tab_conn = tk.Frame(self._nb, bg=C["bg"])
        self._tab_set  = tk.Frame(self._nb, bg=C["bg"])
        self._tab_sh   = tk.Frame(self._nb, bg=C["bg"])
        self._tab_ai   = tk.Frame(self._nb, bg=C["bg"])
        self._nb.add(self._tab_conn, text="  Connection  ")
        self._nb.add(self._tab_set,  text="  Settings  ")
        self._nb.add(self._tab_sh,   text="  Shell  ")
        self._nb.add(self._tab_ai,   text="  AI  ")
        self._build_connection()
        self._build_settings()
        self._build_shell()
        self._build_ai()
        self._build_statusbar()

    # ── Banner ──────────────────────────────────────────
    def _build_banner(self):
        f = tk.Frame(self, bg=C["banner"], height=60)
        f.pack(fill="x")
        f.pack_propagate(False)
        if HAS_PIL:
            p = resource("logo.png")
            if os.path.exists(p):
                img = Image.open(p).resize((280, 56), Image.LANCZOS)
                self._logo_img = ImageTk.PhotoImage(img)
                tk.Label(f, image=self._logo_img, bg=C["banner"]).pack(
                    side="left", padx=10, pady=2)
                return
        tk.Label(f, text="🌋  VOLCANO ERUPTION MONITOR",
                 bg=C["banner"], fg=C["accent"],
                 font=("Segoe UI", 16, "bold")).pack(side="left", padx=16, pady=14)

    # ════════════════════════════════════════════════════════
    #  TAB: CONNECTION
    # ════════════════════════════════════════════════════════
    def _build_connection(self):
        p = self._tab_conn

        # ── top row: readout card | dual graph ───────────
        top = tk.Frame(p, bg=C["bg"])
        top.pack(fill="x", padx=10, pady=8)

        # Readout card
        rc = tk.Frame(top, bg=C["surface"])
        rc.pack(side="left", fill="y", padx=(0, 8))

        def _lbl_section(parent, title):
            tk.Label(parent, text=title, bg=C["surface"], fg=C["textsub"],
                     font=("Segoe UI", 8, "bold")).pack(
                         anchor="w", padx=14, pady=(10, 0))

        # Ultrasonic
        _lbl_section(rc, "ULTRASONIC")
        self._lbl_dist = tk.Label(rc, text="---", bg=C["surface"],
                                  fg=C["blue"], font=("Segoe UI", 42, "bold"))
        self._lbl_dist.pack(anchor="w", padx=12)
        tk.Label(rc, text="cm", bg=C["surface"], fg=C["textsub"],
                 font=("Segoe UI", 10)).pack(anchor="w", padx=14)

        _lbl_section(rc, "DIST STATUS")
        self._lbl_alert = tk.Label(rc, text="---", bg=C["surface"],
                                   fg=C["textdim"], font=("Segoe UI", 14, "bold"))
        self._lbl_alert.pack(anchor="w", padx=14, pady=(2, 0))

        sep(rc, color=C["border"], pady=(8, 8))

        # Seismic
        _lbl_section(rc, "SEISMIC")
        self._lbl_seis = tk.Label(rc, text="---", bg=C["surface"],
                                  fg=C["orange"], font=("Segoe UI", 42, "bold"))
        self._lbl_seis.pack(anchor="w", padx=12)
        tk.Label(rc, text="raw", bg=C["surface"], fg=C["textsub"],
                 font=("Segoe UI", 10)).pack(anchor="w", padx=14)

        _lbl_section(rc, "SEIS STATUS")
        self._lbl_seis_alert = tk.Label(rc, text="---", bg=C["surface"],
                                        fg=C["textdim"], font=("Segoe UI", 14, "bold"))
        self._lbl_seis_alert.pack(anchor="w", padx=14, pady=(2, 0))

        sep(rc, color=C["border"], pady=(8, 8))

        # System
        _lbl_section(rc, "SYSTEM")
        self._lbl_sys = tk.Label(rc, text="---", bg=C["surface"],
                                 fg=C["textdim"], font=("Segoe UI", 11))
        self._lbl_sys.pack(anchor="w", padx=14, pady=(2, 12))

        # Dual graph card
        gc = tk.Frame(top, bg=C["graphbg"])
        gc.pack(side="left", fill="both", expand=True)
        self._graph = Graph(gc)

        # ── dual progress bars ────────────────────────────
        bf = tk.Frame(p, bg=C["bg"])
        bf.pack(fill="x", padx=10, pady=(0, 2))

        tk.Label(bf, text="Ultrasonic", bg=C["bg"], fg=C["blue"],
                 font=("Segoe UI", 7, "bold")).pack(anchor="w")
        self._bar = CBar(bf, height=16)
        self._bar.pack(fill="x")
        sl1 = tk.Frame(bf, bg=C["bg"])
        sl1.pack(fill="x")
        tk.Label(sl1, text="0 cm",   bg=C["bg"], fg=C["textdim"],
                 font=("Segoe UI", 7)).pack(side="left")
        tk.Label(sl1, text="500 cm", bg=C["bg"], fg=C["textdim"],
                 font=("Segoe UI", 7)).pack(side="right")

        tk.Label(bf, text="Seismic", bg=C["bg"], fg=C["orange"],
                 font=("Segoe UI", 7, "bold")).pack(anchor="w", pady=(4, 0))
        self._sbar = CBar(bf, height=16)
        self._sbar.pack(fill="x")
        sl2 = tk.Frame(bf, bg=C["bg"])
        sl2.pack(fill="x")
        tk.Label(sl2, text="0",    bg=C["bg"], fg=C["textdim"],
                 font=("Segoe UI", 7)).pack(side="left")
        tk.Label(sl2, text="1023", bg=C["bg"], fg=C["textdim"],
                 font=("Segoe UI", 7)).pack(side="right")

        sep(p, pady=(6, 0))

        # ── data log ──────────────────────────────────────
        lf = tk.Frame(p, bg=C["logbg"])
        lf.pack(fill="both", expand=True, padx=10, pady=(4, 8))

        hdr = tk.Frame(lf, bg=C["logbg"])
        hdr.pack(fill="x", padx=4, pady=(3, 0))
        tk.Label(hdr, text="DATA LOG", bg=C["logbg"], fg=C["textsub"],
                 font=("Segoe UI", 8, "bold")).pack(side="left")
        Btn(hdr, text="Clear", color="dim", variant="ghost", font_size=8,
            command=lambda: self._clear_text(self._conn_log)
            ).pack(side="right", padx=2)

        inner = tk.Frame(lf, bg=C["logbg"])
        inner.pack(fill="both", expand=True, padx=2, pady=(2, 2))
        self._conn_log = tk.Text(
            inner, state="disabled", wrap="none",
            bg=C["logbg"], fg=C["logfg"],
            font=("Consolas", 9), relief=tk.FLAT, bd=0,
            selectbackground=C["blue"], selectforeground="#ffffff",
            insertbackground=C["text"])
        vsb = ttk.Scrollbar(inner, orient="vertical",
                            style="V.Vertical.TScrollbar",
                            command=self._conn_log.yview)
        hsb = ttk.Scrollbar(inner, orient="horizontal",
                            style="V.Horizontal.TScrollbar",
                            command=self._conn_log.xview)
        self._conn_log.config(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.pack(side="right",  fill="y")
        hsb.pack(side="bottom", fill="x")
        self._conn_log.pack(side="left", fill="both", expand=True)

    # ════════════════════════════════════════════════════════
    #  TAB: SETTINGS
    # ════════════════════════════════════════════════════════
    def _build_settings(self):
        p = self._tab_set

        def section(title):
            tk.Label(p, text=title, bg=C["bg"], fg=C["textsub"],
                     font=("Segoe UI", 8, "bold")).pack(
                         anchor="w", padx=14, pady=(14, 3))
            sep(p, pady=(0, 0))

        # ── Appearance ─────────────────────────────────────
        section("APPEARANCE")
        ar = tk.Frame(p, bg=C["surface"], pady=10)
        ar.pack(fill="x", padx=10, pady=(4, 0))
        tk.Label(ar, text="Theme", bg=C["surface"], fg=C["textsub"],
                 font=("Segoe UI", 9)).pack(side="left", padx=(14, 12))
        self._theme_var = tk.StringVar(value=self._theme_name)
        for lbl, val in [("● Dark", "dark"), ("● Light", "light")]:
            tk.Radiobutton(ar, text=lbl, variable=self._theme_var, value=val,
                           bg=C["surface"], fg=C["text"],
                           activebackground=C["surface"],
                           activeforeground=C["accent"],
                           selectcolor=C["panel2"],
                           font=("Segoe UI", 9),
                           command=lambda v=val: self._apply_theme(v)
                           ).pack(side="left", padx=10)

        # ── Serial ─────────────────────────────────────────
        section("SERIAL CONNECTION")
        sr = tk.Frame(p, bg=C["surface"], pady=10)
        sr.pack(fill="x", padx=10, pady=(4, 0))

        tk.Label(sr, text="Port", bg=C["surface"], fg=C["textsub"],
                 font=("Segoe UI", 9)).pack(side="left", padx=(14, 8))
        self._port_var = tk.StringVar()
        self._cmb = ttk.Combobox(sr, textvariable=self._port_var,
                                  width=11, state="readonly")
        self._cmb.pack(side="left", padx=(0, 10))
        self._cmb.bind("<ButtonPress>", lambda _: self._refresh_ports())
        self._refresh_ports()

        self._btn_conn = Btn(sr, text="Connect", color="green", variant="solid",
                             command=self._toggle_connect)
        self._btn_conn.pack(side="left", padx=4)

        tk.Frame(sr, bg=C["border"], width=1).pack(
            side="left", fill="y", padx=14, pady=2)
        self._lbl_status = tk.Label(sr, text="● Disconnected",
                                    bg=C["surface"], fg=C["textdim"],
                                    font=("Segoe UI", 9, "italic"))
        self._lbl_status.pack(side="left")

        # ── Alarm thresholds ───────────────────────────────
        section("ALARM THRESHOLDS")
        tf = tk.Frame(p, bg=C["surface"], pady=10)
        tf.pack(fill="x", padx=10, pady=(4, 0))

        def thresh_row(parent, label, var_attr, ent_attr, btn_attr,
                       ard_cmd, local_cmd, default, unit):
            r = tk.Frame(parent, bg=C["surface"])
            r.pack(fill="x", padx=14, pady=(0, 8))
            tk.Label(r, text=label, bg=C["surface"], fg=C["textsub"],
                     font=("Segoe UI", 9), width=22, anchor="w").pack(side="left")
            var = tk.StringVar(value=str(int(default)))
            setattr(self, var_attr, var)
            ent = tk.Entry(r, textvariable=var, width=7,
                           bg=C["entry"], fg=C["text"],
                           insertbackground=C["text"],
                           disabledbackground=C["panel"],
                           disabledforeground=C["textdim"],
                           relief=tk.FLAT, bd=6,
                           highlightthickness=1,
                           highlightbackground=C["entbord"],
                           highlightcolor=C["blue"],
                           font=("Segoe UI", 10), state="disabled")
            setattr(self, ent_attr, ent)
            ent.pack(side="left", padx=(0, 4))
            tk.Label(r, text=unit, bg=C["surface"], fg=C["textdim"],
                     font=("Segoe UI", 8)).pack(side="left", padx=(0, 8))
            btn_a = Btn(r, text="→ Arduino", color="blue", variant="outline",
                        command=ard_cmd)
            btn_a.pack(side="left", padx=(0, 4))
            btn_a.configure_state(False)
            setattr(self, btn_attr, btn_a)
            Btn(r, text="Save local", color="white", variant="ghost",
                command=local_cmd).pack(side="left", padx=(0, 4))

        thresh_row(tf,
            "Ultrasonic MIN (cm)",
            "_min_var", "_ent_min", "_btn_setmin",
            self._send_min_ult, self._save_min_ult,
            self._alarm_dist, "cm")

        thresh_row(tf,
            "Seismic MIN (raw)",
            "_min_seis_var", "_ent_seis", "_btn_setseis",
            self._send_min_sei, self._save_min_sei,
            self._alarm_seis, "raw")

        # ── Commands ───────────────────────────────────────
        section("ARDUINO COMMANDS")
        cr = tk.Frame(p, bg=C["surface"], pady=10)
        cr.pack(fill="x", padx=10, pady=(4, 0))
        bf = tk.Frame(cr, bg=C["surface"])
        bf.pack(padx=10, anchor="w")

        def cbtn(text, cmd, col="white"):
            b = Btn(bf, text=text, color=col, variant="outline",
                    command=lambda c=cmd: self._send(c))
            b.pack(side="left", padx=(0, 6))
            b.configure_state(False)
            return b

        self._btn_on    = cbtn("▶  ON",    "on",    "green")
        self._btn_off   = cbtn("■  OFF",   "off",   "white")
        self._btn_kill  = cbtn("☠  KILL",  "kill",  "red")
        self._btn_reset = cbtn("↺  RESET", "reset", "orange")
        self._btn_test  = cbtn("⚡ TEST",  "456",   "blue")
        self._cmd_btns  = [self._btn_on, self._btn_off,
                           self._btn_kill, self._btn_reset, self._btn_test]

        # ── Sarvam AI ──────────────────────────────────────
        section("SARVAM AI")
        aif = tk.Frame(p, bg=C["surface"], pady=10)
        aif.pack(fill="x", padx=10, pady=(4, 0))

        tk.Label(aif, text="API Key", bg=C["surface"], fg=C["textsub"],
                 font=("Segoe UI", 9)).pack(side="left", padx=(14, 8))
        self._apikey_var = tk.StringVar(value=self._api_key)
        ek = tk.Entry(aif, textvariable=self._apikey_var, width=34,
                      bg=C["entry"], fg=C["text"], insertbackground=C["text"],
                      show="•", relief=tk.FLAT, bd=6,
                      highlightthickness=1, highlightbackground=C["entbord"],
                      highlightcolor=C["blue"], font=("Consolas", 9))
        ek.pack(side="left", padx=(0, 10))

        tk.Label(aif, text="Model", bg=C["surface"], fg=C["textsub"],
                 font=("Segoe UI", 9)).pack(side="left", padx=(0, 6))
        self._model_var = tk.StringVar(value=self._ai_model)
        em = tk.Entry(aif, textvariable=self._model_var, width=14,
                      bg=C["entry"], fg=C["text"], insertbackground=C["text"],
                      relief=tk.FLAT, bd=6,
                      highlightthickness=1, highlightbackground=C["entbord"],
                      highlightcolor=C["blue"], font=("Segoe UI", 9))
        em.pack(side="left", padx=(0, 10))
        Btn(aif, text="Save", color="blue", variant="solid",
            command=self._save_ai).pack(side="left")

        # ── Logging ────────────────────────────────────────
        section("DATA LOGGING")
        lf = tk.Frame(p, bg=C["surface"], pady=8)
        lf.pack(fill="x", padx=10, pady=(4, 0))
        tk.Label(lf, text=f"CSV → {LOG_DIR}",
                 bg=C["surface"], fg=C["textsub"],
                 font=("Consolas", 8)).pack(side="left", padx=14)
        Btn(lf, text="Open folder", color="white", variant="ghost",
            command=lambda: os.startfile(str(LOG_DIR))
            if sys.platform == "win32" else None
            ).pack(side="left", padx=8)

    # ════════════════════════════════════════════════════════
    #  TAB: SHELL
    # ════════════════════════════════════════════════════════
    def _build_shell(self):
        p = self._tab_sh

        hdr = tk.Frame(p, bg=C["bg"])
        hdr.pack(fill="x", padx=10, pady=(8, 0))
        tk.Label(hdr, text="SERIAL SHELL", bg=C["bg"], fg=C["textsub"],
                 font=("Segoe UI", 8, "bold")).pack(side="left")
        tk.Label(hdr, text="↑↓ history  •  type help",
                 bg=C["bg"], fg=C["textdim"],
                 font=("Segoe UI", 8, "italic")).pack(side="left", padx=12)
        Btn(hdr, text="Clear", color="dim", variant="ghost", font_size=8,
            command=lambda: self._clear_text(self._shell_out)
            ).pack(side="right", padx=2)

        sep(p, pady=(4, 0))

        out_f = tk.Frame(p, bg=C["logbg"])
        out_f.pack(fill="both", expand=True, padx=10, pady=(4, 0))
        self._shell_out = tk.Text(
            out_f, state="disabled", wrap="none",
            bg=C["logbg"], fg=C["logfg"],
            font=("Consolas", 10), relief=tk.FLAT, bd=0,
            selectbackground=C["blue"], selectforeground="#ffffff",
            insertbackground=C["text"])
        vsb = ttk.Scrollbar(out_f, orient="vertical",
                            style="V.Vertical.TScrollbar",
                            command=self._shell_out.yview)
        self._shell_out.config(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self._shell_out.pack(side="left", fill="both", expand=True)

        inp = tk.Frame(p, bg=C["surface"], pady=8)
        inp.pack(fill="x", padx=10, pady=(4, 8))
        tk.Label(inp, text="›", bg=C["surface"], fg=C["accent"],
                 font=("Consolas", 13, "bold")).pack(side="left", padx=(10, 6))
        self._shell_inp = tk.Entry(
            inp, bg=C["entry"], fg=C["text"],
            insertbackground=C["text"],
            relief=tk.FLAT, bd=0,
            highlightthickness=1,
            highlightbackground=C["entbord"],
            highlightcolor=C["blue"],
            font=("Consolas", 10))
        self._shell_inp.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self._shell_inp.bind("<Return>", self._shell_enter)
        self._shell_inp.bind("<Up>",     self._shell_up)
        self._shell_inp.bind("<Down>",   self._shell_dn)
        Btn(inp, text="Send", color="orange", variant="solid",
            command=self._shell_enter).pack(side="left", padx=(0, 8))

        self._shell_write(
            f"[{ts()}]  Volcano Eruption Monitor Shell  —  Vedurocks Ltd 2026\n"
            f"[{ts()}]  Commands  : on | off | kill | reset | 456\n"
            f"[{ts()}]  Threshold : min ult X  (ultrasonic cm) | min sei X  (seismic raw)\n"
            f"[{ts()}]  Aliases   : system on | system off | sys on | sys off\n"
            f"[{ts()}]  Internal  : help | status | clear\n\n")

    # ════════════════════════════════════════════════════════
    #  TAB: AI
    # ════════════════════════════════════════════════════════
    def _build_ai(self):
        p = self._tab_ai

        hdr = tk.Frame(p, bg=C["aibg"])
        hdr.pack(fill="x", padx=10, pady=(8, 0))
        tk.Label(hdr, text="🤖  SARVAM AI", bg=C["aibg"], fg=C["blue"],
                 font=("Segoe UI", 11, "bold")).pack(side="left")
        tk.Label(hdr, text="AI controls Arduino via [CMD:on] syntax",
                 bg=C["aibg"], fg=C["textdim"],
                 font=("Segoe UI", 8, "italic")).pack(side="left", padx=10)
        Btn(hdr, text="New session", color="dim", variant="ghost", font_size=8,
            command=self._ai_new).pack(side="right", padx=2)
        Btn(hdr, text="Clear", color="dim", variant="ghost", font_size=8,
            command=self._ai_clear).pack(side="right", padx=2)

        sep(p, pady=(4, 0))

        cf = tk.Frame(p, bg=C["aibg"])
        cf.pack(fill="both", expand=True, padx=10, pady=(4, 0))
        self._ai_chat = tk.Text(
            cf, state="disabled", wrap="word",
            bg=C["aibg"], fg=C["text"],
            font=("Segoe UI", 10), relief=tk.FLAT, bd=0,
            selectbackground=C["blue"], selectforeground="#ffffff",
            spacing1=2, spacing3=4)
        vsb = ttk.Scrollbar(cf, orient="vertical",
                            style="V.Vertical.TScrollbar",
                            command=self._ai_chat.yview)
        self._ai_chat.config(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self._ai_chat.pack(side="left", fill="both", expand=True, padx=(4, 0))

        self._ai_chat.tag_configure("user",  background=C["aiuser"],
                                    foreground=C["white"],
                                    lmargin1=8, lmargin2=8, rmargin=8)
        self._ai_chat.tag_configure("bot",   background=C["aibot"],
                                    foreground=C["white"],
                                    lmargin1=8, lmargin2=8, rmargin=8)
        self._ai_chat.tag_configure("cmd",   foreground=C["orange"],
                                    font=("Consolas", 9, "bold"))
        self._ai_chat.tag_configure("label", foreground=C["textsub"],
                                    font=("Segoe UI", 8, "bold"))
        self._ai_chat.tag_configure("err",   foreground=C["red"])
        self._ai_chat.tag_configure("sys",   foreground=C["textdim"],
                                    font=("Segoe UI", 8, "italic"))

        inf = tk.Frame(p, bg=C["surface"], pady=8)
        inf.pack(fill="x", padx=10, pady=(4, 8))
        self._ai_inp = tk.Text(
            inf, height=2, bg=C["entry"], fg=C["text"],
            insertbackground=C["text"],
            relief=tk.FLAT, bd=0,
            highlightthickness=1,
            highlightbackground=C["entbord"],
            highlightcolor=C["blue"],
            font=("Segoe UI", 10), wrap="word")
        self._ai_inp.pack(side="left", fill="x", expand=True, padx=(8, 8))
        self._ai_inp.bind("<Return>",       self._ai_enter)
        self._ai_inp.bind("<Shift-Return>", lambda e: None)
        Btn(inf, text="Send\n(Enter)", color="blue", variant="solid",
            font_size=9, command=self._ai_send).pack(side="left", padx=(0, 8))

        self._ai_write("sys", "Sarvam AI ready. Set API key in Settings.\n")

    # ── Status bar ──────────────────────────────────────
    def _build_statusbar(self):
        bar = tk.Frame(self, bg=C["surface"], height=24)
        bar.pack(fill="x", side="bottom")
        bar.pack_propagate(False)
        sep(bar, color=C["border"], pady=(0, 0))
        tk.Label(bar, text="Vedurocks Ltd  2026©",
                 bg=C["surface"], fg=C["textdim"],
                 font=("Segoe UI", 8)).pack(side="left", padx=12)
        self._sb_alarm = tk.Label(bar, text="", bg=C["surface"],
                                  fg=C["red"], font=("Segoe UI", 8, "bold"))
        self._sb_alarm.pack(side="left", padx=10)
        tk.Label(bar, text=f"Logs → {LOG_DIR}",
                 bg=C["surface"], fg=C["textdim"],
                 font=("Segoe UI", 8)).pack(side="right", padx=12)

    # ════════════════════════════════════════════════════════
    #  PORT
    # ════════════════════════════════════════════════════════
    def _refresh_ports(self):
        if not HAS_SERIAL:
            self._cmb["values"] = ["(install pyserial)"]
            return
        ports = [p.device for p in serial.tools.list_ports.comports()]
        self._cmb["values"] = ports or ["(none)"]
        if ports and not self._port_var.get():
            self._port_var.set(ports[0])

    # ════════════════════════════════════════════════════════
    #  CONNECT / DISCONNECT
    # ════════════════════════════════════════════════════════
    def _toggle_connect(self):
        (self._disconnect if self._connected else self._connect)()

    def _connect(self):
        if not HAS_SERIAL:
            self._log("pyserial missing — pip install pyserial")
            return
        pn = self._port_var.get()
        if not pn or pn.startswith("("):
            self._log("Select a valid COM port.")
            return
        try:
            self._port         = serial.Serial(pn, 9600, timeout=1)
            self._connected    = True
            self._min_received = False
            self._btn_conn.config_text("Disconnect")
            self._btn_conn.config_color("red")
            self._lbl_status.config(text=f"● {pn} @ 9600", fg=C["green"])
            self._cmb.config(state="disabled")
            self._set_cmd_state(True)
            self._log(f"Connected → {pn}")
            self._shell_write(f"[{ts()}]  ✔  Connected to {pn}\n")
            threading.Thread(target=self._read_loop, daemon=True).start()
            
            # Start command polling loop
            self._start_command_polling()
        except Exception as e:
            self._log(f"Connection failed: {e}")

    def _disconnect(self):
        self._connected = False
        self._alarm.stop()
        
        # Stop command polling
        self._stop_command_polling()
        
        try:
            if self._port and self._port.is_open:
                self._port.close()
        except Exception:
            pass
        self._port         = None
        self._min_received = False
        self._local_sys    = False
        self._local_kill   = False
        self._btn_conn.config_text("Connect")
        self._btn_conn.config_color("green")
        self._lbl_status.config(text="● Disconnected", fg=C["textdim"])
        self._cmb.config(state="readonly")
        self._set_cmd_state(False)
        self._lbl_dist.config(text="---", fg=C["blue"])
        self._lbl_alert.config(text="---", fg=C["textdim"],
                               font=("Segoe UI", 14, "bold"))
        self._lbl_seis.config(text="---", fg=C["orange"])
        self._lbl_seis_alert.config(text="---", fg=C["textdim"],
                                    font=("Segoe UI", 14, "bold"))
        self._lbl_sys.config(text="---", fg=C["textdim"])
        self._bar.set(0)
        self._sbar.set(0)
        self._sb_alarm.config(text="")
        self._log("Disconnected.")
        self._shell_write(f"[{ts()}]  ✖  Disconnected\n")
        self._graph.clear()

    # ════════════════════════════════════════════════════════
    #  SERIAL THREAD
    # ════════════════════════════════════════════════════════
    def _read_loop(self):
        while self._connected and self._port and self._port.is_open:
            try:
                raw = self._port.readline().decode("utf-8", errors="ignore").strip()
                if raw:
                    self._q.put(raw)
            except Exception:
                break
        if self._connected:
            self._q.put("__DROPPED__")

    def _poll_queue(self):
        try:
            while True:
                item = self._q.get_nowait()
                if item == "__DROPPED__":
                    self._log("⚠ Serial connection lost.")
                    self._shell_write(f"[{ts()}]  ⚠  Connection lost\n")
                    self._disconnect()
                else:
                    self._parse(item)
        except queue.Empty:
            pass
        self.after(50, self._poll_queue)

    # ════════════════════════════════════════════════════════
    #  PARSE
    # Format: distance,seismic,dist_alert,seis_alert,dual_alert,
    #         kill_state,sys_state,min_ultra,min_seis
    # ════════════════════════════════════════════════════════
    def _parse(self, line: str):
        parts = line.split(",")
        if len(parts) < 9:
            self._log(f"← (unknown) {line}")
            return
        try:
            dist       = float(parts[0])
            seis       = float(parts[1])
            dist_alert = parts[2].strip() == "1"
            seis_alert = parts[3].strip() == "1"
            dual_alert = parts[4].strip() == "1"
            kill       = parts[5].strip() == "1"
            sys_on     = parts[6].strip() == "1"
            min_ultra  = float(parts[7].strip())
            min_seis   = float(parts[8].strip())
        except ValueError:
            self._log(f"← (bad) {line}")
            return

        # Sync thresholds from Arduino on first packet
        if not self._min_received:
            self._min_received = True
            self._alarm_dist   = min_ultra
            self._alarm_seis   = min_seis
            self._min_var.set(str(int(min_ultra)))
            self._min_seis_var.set(str(int(min_seis)))
            self._log(f"Arduino MIN  ultra={min_ultra} cm  seis={min_seis}")

        # Local threshold checks
        local_dist_alert = dist < self._alarm_dist
        local_seis_alert = seis > self._alarm_seis
        any_alert = (local_dist_alert or local_seis_alert
                     or dist_alert or seis_alert or dual_alert)

        # Alarm sound
        if any_alert:
            self._alarm.start()
            if dual_alert:
                alarm_txt = "⚠  DUAL ALERT"
            elif dist_alert or local_dist_alert:
                alarm_txt = "⚠  DIST ALERT"
            else:
                alarm_txt = "⚠  SEIS ALERT"
            self._sb_alarm.config(text=alarm_txt)
        else:
            self._alarm.stop()
            self._sb_alarm.config(text="")

        # Ultrasonic display
        da = dist_alert or local_dist_alert
        self._lbl_dist.config(
            text=f"{dist:.1f}",
            fg=C["red"] if da else C["blue"])
        self._bar.set(dist / 500.0, da)
        if da:
            self._lbl_alert.config(text="⚠  ALERT", fg=C["red"],
                                   font=("Segoe UI", 14, "bold"))
        else:
            self._lbl_alert.config(text="✔  OK", fg=C["green"],
                                   font=("Segoe UI", 14, "bold"))

        # Seismic display
        sa = seis_alert or local_seis_alert
        self._lbl_seis.config(
            text=f"{seis:.0f}",
            fg=C["red"] if sa else C["orange"])
        self._sbar.set(seis / 1023.0, sa)
        if sa:
            self._lbl_seis_alert.config(text="⚠  ALERT", fg=C["red"],
                                        font=("Segoe UI", 14, "bold"))
        else:
            self._lbl_seis_alert.config(text="✔  OK", fg=C["green"],
                                        font=("Segoe UI", 14, "bold"))

        # System / kill
        self._local_sys  = sys_on
        self._local_kill = kill
        self._refresh_sys_ui()

        sc = C["red"] if kill else C["yellow"] if any_alert else C["green"]
        self._lbl_status.config(
            text=f"● {self._port.port if self._port else '?'}  "
                 f"dist={dist:.1f}cm  seis={seis:.0f}",
            fg=sc)

        self._graph.push(dist, seis, da, sa, self._alarm_dist, self._alarm_seis)
        self._logger.log(dist, seis, da, sa, dual_alert,
                         kill, sys_on, min_ultra, min_seis)
        self._log(
            f"← dist={dist:.1f}cm  seis={seis:.0f}  "
            f"da={int(dist_alert)} sa={int(seis_alert)} "
            f"dual={int(dual_alert)} kill={int(kill)} "
            f"sys={int(sys_on)} mU={int(min_ultra)} mS={int(min_seis)}")
        
        # Send to cloud API (async, non-blocking)
        self._send_to_cloud(dist, seis, da, sa, dual_alert, kill, sys_on, 
                           min_ultra, min_seis)

    def _send_to_cloud(self, dist, seis, dist_alert, seis_alert, 
                       dual_alert, kill, sys_on, min_ultra, min_seis):
        """Send sensor data to cloud as JSON (non-blocking)"""
        if not HAS_REQUESTS:
            return
        
        def _post():
            try:
                # Build JSON payload
                payload = {
                    "distance": float(f"{dist:.2f}"),
                    "vibration": int(seis),
                    "dist_alert": bool(dist_alert),
                    "vib_alert": bool(seis_alert),
                    "dual_alert": bool(dual_alert),
                    "kill_state": bool(kill),
                    "sys_state": bool(sys_on),
                    "min_ultra": int(min_ultra),
                    "min_vib": int(min_seis)
                }
                
                # POST JSON to API
                response = _requests.post(
                    VOLCANO_API,
                    json=payload,
                    headers={'Content-Type': 'application/json'},
                    timeout=3
                )
                
                # Log for debugging (optional - uncomment if needed)
                # if 200 <= response.status_code < 300:
                #     print(f"✓ Data sent: {response.status_code}")
                # else:
                #     print(f"✗ POST error: {response.status_code}")
                    
            except Exception as e:
                # Silent fail - don't interrupt main app
                # print(f"✗ POST exception: {e}")
                pass
        
        # Send in background thread
        threading.Thread(target=_post, daemon=True).start()
    
    def _start_command_polling(self):
        """Start background thread to poll for commands every 1 second"""
        if not HAS_REQUESTS or self._command_poll_active:
            return
        
        self._command_poll_active = True
        threading.Thread(target=self._command_poll_loop, daemon=True).start()
    
    def _stop_command_polling(self):
        """Stop command polling loop"""
        self._command_poll_active = False
    
    def _command_poll_loop(self):
        """Background loop: GET commands from API every 1 second"""
        while self._command_poll_active and self._connected:
            try:
                # GET request to fetch pending commands
                response = _requests.get(
                    VOLCANO_API,
                    timeout=3
                )
                
                if 200 <= response.status_code < 300:
                    data = response.json()
                    
                    # Check for pending commands
                    # Expected format: {"data": {...}, "commands": [{"id": 12, "command": "on"}]}
                    commands = data.get('commands', [])
                    
                    if commands:
                        # Process each command
                        for cmd_obj in commands:
                            cmd_id = cmd_obj.get('id')
                            command = cmd_obj.get('command', '').strip()
                            
                            if cmd_id and command:
                                # Execute command on Arduino
                                self._execute_remote_command(command, cmd_id)
                
            except Exception as e:
                # Silent fail - polling continues
                # print(f"✗ Command poll error: {e}")
                pass
            
            # Wait 1 second before next poll
            time.sleep(COMMAND_POLL_INTERVAL)
    
    def _execute_remote_command(self, command, cmd_id):
        """Execute command from cloud and mark as executed"""
        if not self._connected or not self._port:
            return
        
        try:
            # Send command to Arduino
            self._send(command)
            
            # Log to UI
            self._log(f"☁ Remote command: {command}")
            self._shell_write(f"[{ts()}]  ☁  Remote: {command}\n")
            
            # Mark command as executed in database
            def _mark_executed():
                try:
                    payload = {"executed_id": cmd_id}
                    _requests.post(
                        VOLCANO_API,
                        json=payload,
                        headers={'Content-Type': 'application/json'},
                        timeout=3
                    )
                    # print(f"✓ Marked executed: {cmd_id}")
                except Exception:
                    # print(f"✗ Failed to mark executed: {cmd_id}")
                    pass
            
            # Send executed confirmation in background
            threading.Thread(target=_mark_executed, daemon=True).start()
            
        except Exception as e:
            self._log(f"✗ Remote command failed: {e}")

    # ════════════════════════════════════════════════════════
    #  SYS / KILL STATE
    # ════════════════════════════════════════════════════════
    def _apply_cmd_state(self, cmd: str):
        c = cmd.strip().lower()
        if   c == "on":    self._local_sys = True;  self._local_kill = False
        elif c == "off":   self._local_sys = False
        elif c == "kill":  self._local_kill = not self._local_kill
        elif c == "reset": self._local_sys = True;  self._local_kill = False
        self._refresh_sys_ui()

    def _refresh_sys_ui(self):
        sys_str  = "ACTIVE"  if self._local_sys  else "STANDBY"
        kill_str = "  KILL"  if self._local_kill else ""
        self._lbl_sys.config(
            text=f"{sys_str}{kill_str}",
            fg=C["red"]     if self._local_kill
               else C["green"] if self._local_sys
               else C["textdim"])
        self._btn_kill.set_active(self._local_kill)

    # ════════════════════════════════════════════════════════
    #  SEND
    # ════════════════════════════════════════════════════════
    def _send(self, cmd: str):
        if not self._connected or not self._port:
            self._log("Not connected.")
            return
        try:
            self._port.write((cmd + "\n").encode())
            self._apply_cmd_state(cmd)
            self._log(f"→ {cmd}")
            self._shell_write(f"[{ts()}]  → {cmd}\n")
        except Exception as e:
            self._log(f"Send error: {e}")
            self._shell_write(f"[{ts()}]  ✖  Send error: {e}\n")

    def _send_shell(self, cmd: str):
        try:
            self._port.write((cmd + "\n").encode())
            self._apply_cmd_state(cmd)
            sys_s = f"sys={'1 (ACTIVE)' if self._local_sys else '0 (STANDBY)'}"
            kil_s = f"  kill={'1' if self._local_kill else '0'}"
            self._shell_write(f"[{ts()}]  ✔  {cmd}  →  {sys_s}{kil_s}\n")
            self._log(f"→ {cmd}")
        except Exception as e:
            self._shell_write(f"[{ts()}]  ✖  Send error: {e}\n")
            self._log(f"Send error: {e}")

    def _send_min_ult(self):
        try:
            val = float(self._min_var.get())
            if val <= 0: raise ValueError
        except ValueError:
            self._log("Invalid ultrasonic MIN.")
            return
        self._alarm_dist = val
        self._send(f"min ult {int(val)}")

    def _save_min_ult(self):
        try:
            val = float(self._min_var.get())
            if val <= 0: raise ValueError
            self._alarm_dist = val
            self._save_config()
            self._log(f"Ultrasonic threshold saved: {val} cm")
        except ValueError:
            self._log("Invalid ultrasonic MIN.")

    def _send_min_sei(self):
        try:
            val = float(self._min_seis_var.get())
            if val < 0: raise ValueError
        except ValueError:
            self._log("Invalid seismic MIN.")
            return
        self._alarm_seis = val
        self._send(f"min sei {int(val)}")

    def _save_min_sei(self):
        try:
            val = float(self._min_seis_var.get())
            if val < 0: raise ValueError
            self._alarm_seis = val
            self._save_config()
            self._log(f"Seismic threshold saved: {val}")
        except ValueError:
            self._log("Invalid seismic MIN.")

    # ════════════════════════════════════════════════════════
    #  SHELL
    # ════════════════════════════════════════════════════════
    def _shell_enter(self, event=None):
        cmd = self._shell_inp.get().strip()
        if not cmd:
            return "break"
        self._shell_inp.delete(0, "end")
        self._shell_history.insert(0, cmd)
        self._shell_hist_idx = -1

        aliases = {
            "system on":   "on",   "sys on":   "on",
            "system off":  "off",  "sys off":  "off",
            "system kill": "kill", "sys kill": "kill",
        }
        cmd = aliases.get(cmd.lower(), cmd)
        self._shell_write(f"[{ts()}]  › {cmd}\n")

        cl = cmd.lower()
        if cl == "help":
            self._shell_write(
                "  Commands  : on | off | kill | reset | 456\n"
                "  Threshold : min ult X  |  min sei X\n"
                "  Aliases   : system on | system off | sys on | sys off\n"
                "  Internal  : help | status | clear\n")
        elif cl == "status":
            pn = self._port.port if self._port else "none"
            self._shell_write(
                f"  Connected   : {self._connected} ({pn})\n"
                f"  sys         : {'1 (ACTIVE)' if self._local_sys else '0 (STANDBY)'}\n"
                f"  kill        : {'1' if self._local_kill else '0'}\n"
                f"  MIN ultra   : {self._alarm_dist} cm\n"
                f"  MIN seismic : {self._alarm_seis} raw\n"
                f"  Alarm       : {'YES' if self._alarm._active else 'no'}\n")
        elif cl == "clear":
            self._clear_text(self._shell_out)
        else:
            if not self._connected or not self._port:
                self._shell_write(
                    f"[{ts()}]  ✖  Not connected — use Settings to connect\n")
                return "break"
            self._send_shell(cmd)
        return "break"

    def _shell_up(self, _=None):
        if not self._shell_history:
            return
        self._shell_hist_idx = min(self._shell_hist_idx + 1,
                                    len(self._shell_history) - 1)
        self._shell_inp.delete(0, "end")
        self._shell_inp.insert(0, self._shell_history[self._shell_hist_idx])

    def _shell_dn(self, _=None):
        self._shell_hist_idx = max(self._shell_hist_idx - 1, -1)
        self._shell_inp.delete(0, "end")
        if self._shell_hist_idx >= 0:
            self._shell_inp.insert(0, self._shell_history[self._shell_hist_idx])

    def _shell_write(self, msg: str):
        self._shell_out.config(state="normal")
        self._shell_out.insert("end", msg)
        n = int(self._shell_out.index("end-1c").split(".")[0])
        if n > 600:
            self._shell_out.delete("1.0", f"{n - 600}.0")
        self._shell_out.see("end")
        self._shell_out.config(state="disabled")

    # ════════════════════════════════════════════════════════
    #  AI
    # ════════════════════════════════════════════════════════
    def _ai_system_prompt(self):
        return (
            "You are the AI controller for the Volcano Eruption Monitor by Vedurocks Ltd (2026).\n"
            "Connected to HC-SR04 ultrasonic + seismic sensor via Arduino.\n\n"
            f"Ultrasonic MIN threshold : {self._alarm_dist} cm\n"
            f"Seismic MIN threshold    : {self._alarm_seis} (raw)\n"
            f"Alarm active   : {self._alarm._active}\n"
            f"Arduino connected : {self._connected}\n"
            f"System state : {'ACTIVE' if self._local_sys else 'STANDBY'}\n"
            f"Kill mode    : {self._local_kill}\n\n"
            "DATA FORMAT (Arduino → PC, comma separated):\n"
            "  distance, seismic, dist_alert, seis_alert, dual_alert,\n"
            "  kill_state, sys_state, min_ultra, min_seis\n\n"
            "COMMANDS YOU CAN EXECUTE (embed exactly in reply):\n"
            "  [CMD:on]           — Activate system\n"
            "  [CMD:off]          — Deactivate system\n"
            "  [CMD:kill]         — Toggle kill mode\n"
            "  [CMD:reset]        — Reset to safe state\n"
            "  [CMD:456]          — Test signal\n"
            "  [CMD:min ult X]    — Set ultrasonic threshold to X cm\n"
            "  [CMD:min sei X]    — Set seismic threshold to X raw\n\n"
            "Be concise and technical. Explain what you are doing."
        )

    def _ai_enter(self, event):
        if event.state & 0x1:
            return
        self._ai_send()
        return "break"

    def _ai_send(self):
        msg = self._ai_inp.get("1.0", "end").strip()
        if not msg:
            return
        self._ai_inp.delete("1.0", "end")
        if not HAS_REQUESTS:
            self._ai_write("err", "⚠ requests not installed — pip install requests\n")
            return
        self._ai_write("user", f"You\n{msg}\n")
        threading.Thread(target=self._ai_call, args=(msg,), daemon=True).start()

    def _ai_call(self, user_msg: str):
        self._ai_history.append({"role": "user", "content": user_msg})
        payload = {
            "model":            self._ai_model,
            "messages":         [{"role": "system",
                                   "content": self._ai_system_prompt()}]
                                 + self._ai_history,
            "temperature":      0.8,
            "top_p":            1,
            "stream":           True,
            "reasoning_effort": "low",
        }
        headers = {
            "API-Subscription-Key": self._api_key.strip(),
            "Content-Type":         "application/json",
        }
        try:
            resp = _requests.post(SARVAM_URL, headers=headers,
                                  json=payload, stream=True, timeout=60)
            resp.raise_for_status()
        except Exception as e:
            self.after(0, self._ai_write, "err", f"⚠ API error: {e}\n")
            return

        self.after(0, self._ai_write, "label", "AI\n")
        full = []
        try:
            for raw in resp.iter_lines():
                if not raw:
                    continue
                line = raw.decode("utf-8") if isinstance(raw, bytes) else raw
                if not line.startswith("data: "):
                    continue
                data = line[6:]
                if data == "[DONE]":
                    break
                try:
                    token = json.loads(data)["choices"][0]["delta"].get("content", "")
                    if token:
                        full.append(token)
                        self.after(0, self._ai_token, token)
                except Exception:
                    continue
        except Exception as e:
            self.after(0, self._ai_write, "err", f"\n⚠ Stream error: {e}\n")

        reply = "".join(full)
        self._ai_history.append({"role": "assistant", "content": reply})

        cmds = re.findall(r'\[CMD:([^\]]+)\]', reply)
        if cmds:
            def _exec():
                for c in cmds:
                    c = c.strip()
                    self._ai_write("cmd", f"  ⚡ {c}\n")
                    self._shell_write(f"[{ts()}]  🤖 AI → {c}\n")
                    self._send(c)
            self.after(0, _exec)

        self.after(0, self._ai_write, "bot", "\n")

    def _ai_token(self, token: str):
        self._ai_chat.config(state="normal")
        self._ai_chat.insert("end", token, "bot")
        self._ai_chat.see("end")
        self._ai_chat.config(state="disabled")

    def _ai_write(self, tag: str, text: str):
        self._ai_chat.config(state="normal")
        self._ai_chat.insert("end", text, tag)
        self._ai_chat.insert("end", "\n")
        self._ai_chat.see("end")
        self._ai_chat.config(state="disabled")

    def _ai_clear(self):
        self._ai_chat.config(state="normal")
        self._ai_chat.delete("1.0", "end")
        self._ai_chat.config(state="disabled")

    def _ai_new(self):
        self._ai_history.clear()
        self._ai_clear()
        self._ai_write("sys", "New session started.\n")

    # ════════════════════════════════════════════════════════
    #  LOG
    # ════════════════════════════════════════════════════════
    def _log(self, msg: str):
        line = f"[{ts()}]  {msg}\n"
        self._conn_log.config(state="normal")
        self._conn_log.insert("end", line)
        n = int(self._conn_log.index("end-1c").split(".")[0])
        if n > 500:
            self._conn_log.delete("1.0", f"{n - 500}.0")
        self._conn_log.see("end")
        self._conn_log.config(state="disabled")

    @staticmethod
    def _clear_text(w):
        w.config(state="normal")
        w.delete("1.0", "end")
        w.config(state="disabled")

    # ════════════════════════════════════════════════════════
    #  HELPERS
    # ════════════════════════════════════════════════════════
    def _set_cmd_state(self, enabled: bool):
        for b in self._cmd_btns:
            b.configure_state(enabled)
        self._btn_setmin.configure_state(enabled)
        self._btn_setseis.configure_state(enabled)
        st = "normal" if enabled else "disabled"
        self._ent_min.config(state=st)
        self._ent_seis.config(state=st)

    def _save_ai(self):
        self._api_key  = self._apikey_var.get()
        self._ai_model = self._model_var.get().strip() or SARVAM_MODEL
        self._save_config()
        self._log("AI settings saved.")

    # ════════════════════════════════════════════════════════
    #  THEME
    # ════════════════════════════════════════════════════════
    def _apply_theme(self, name: str):
        if name not in THEMES:
            return
        self._theme_name = name
        C.update(THEMES[name])
        _apply_ttk(self)
        self._recolor(self)
        self._graph.restyle()
        self._save_config()

    _BG_KEYS = ["bg", "surface", "panel", "panel2", "logbg", "aibg",
                "banner", "graphbg", "entry", "btn"]
    _FG_KEYS = ["text", "textdim", "textsub", "accent", "green", "red",
                "yellow", "logfg", "blue", "orange", "white"]

    def _recolor(self, widget):
        wt = widget.winfo_class()
        try:
            if wt in ("Frame", "Tk", "Toplevel"):
                widget.configure(bg=self._map("bg", str(widget.cget("bg"))))
            elif wt == "Label":
                widget.configure(
                    bg=self._map("bg", str(widget.cget("bg"))),
                    fg=self._map("fg", str(widget.cget("fg"))))
            elif wt == "Button":
                widget.configure(
                    bg=self._map("bg", str(widget.cget("bg"))),
                    fg=C["text"],
                    activebackground=C["btnhov"],
                    activeforeground=C["text"],
                    disabledforeground=C["textdim"])
            elif wt == "Entry":
                widget.configure(
                    bg=C["entry"], fg=C["text"],
                    insertbackground=C["text"],
                    disabledbackground=C["panel"],
                    disabledforeground=C["textdim"])
            elif wt == "Text":
                widget.configure(
                    bg=self._map("bg", str(widget.cget("bg"))),
                    selectbackground=C["blue"])
            elif wt == "Canvas":
                widget.configure(
                    bg=self._map("bg", str(widget.cget("bg"))),
                    highlightbackground=C["border"])
            elif wt in ("Radiobutton", "Checkbutton"):
                widget.configure(
                    bg=self._map("bg", str(widget.cget("bg"))),
                    fg=C["text"], selectcolor=C["panel2"],
                    activebackground=self._map("bg", str(widget.cget("bg"))),
                    activeforeground=C["accent"])
        except Exception:
            pass
        for ch in widget.winfo_children():
            self._recolor(ch)

    def _map(self, kind: str, cur: str) -> str:
        keys = self._BG_KEYS if kind == "bg" else self._FG_KEYS
        best_k, best_d = keys[0], 999999
        for t in THEMES.values():
            for k in keys:
                try:
                    c1 = tuple(int(cur.lstrip("#")[i:i+2], 16) for i in (0, 2, 4))
                    c2 = tuple(int(t[k].lstrip("#")[i:i+2], 16) for i in (0, 2, 4))
                    d  = sum(abs(a - b) for a, b in zip(c1, c2))
                    if d < best_d:
                        best_d = d
                        best_k = k
                except Exception:
                    pass
        return C.get(best_k, C[keys[0]])

    # ════════════════════════════════════════════════════════
    #  CONFIG
    # ════════════════════════════════════════════════════════
    def _load_config(self):
        if CONFIG_FILE.exists():
            try:
                cfg = json.loads(CONFIG_FILE.read_text())
                self._alarm_dist = cfg.get("alarm_dist", 100.0)
                self._alarm_seis = cfg.get("alarm_seis", 50.0)
                self._api_key    = cfg.get("api_key",    SARVAM_KEY)
                self._ai_model   = cfg.get("ai_model",   SARVAM_MODEL)
                self._theme_name = cfg.get("theme",      "dark")
                C.update(THEMES.get(self._theme_name, THEMES["dark"]))
            except Exception:
                pass

    def _save_config(self):
        cfg = {
            "alarm_dist": self._alarm_dist,
            "alarm_seis": self._alarm_seis,
            "api_key":    self._api_key,
            "ai_model":   self._ai_model,
            "theme":      self._theme_name,
        }
        try:
            CONFIG_FILE.write_text(json.dumps(cfg, indent=2))
        except Exception:
            pass

    def _on_close(self):
        self._alarm.stop()
        self._disconnect()
        self._logger.close()
        self._save_config()
        self.destroy()


# ════════════════════════════════════════════════════════════
#  ENTRY POINT
# ════════════════════════════════════════════════════════════
if __name__ == "__main__":
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    App().mainloop()
