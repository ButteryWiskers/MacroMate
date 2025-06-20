import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
from PIL import ImageGrab, Image, ImageTk
import pyautogui
import cv2
import numpy as np
import time
import json
import threading
import os
import random
import keyboard
import serial
import serial.tools.list_ports
from tkinter import ttk
import math
import pyautogui
import random
import time
import zipfile
import tempfile
import shutil


def find_image_on_screen(template_path, similarity=80.0):
    screen = pyautogui.screenshot()
    screen_np = np.array(screen)
    screen_gray = cv2.cvtColor(screen_np, cv2.COLOR_BGR2GRAY)
    template = cv2.imread(template_path, 0)
    if template is None:
        print(f"Error: Could not load template image at {template_path}")
        return None
    result = cv2.matchTemplate(screen_gray, template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(result)
    if max_val >= similarity / 100.0:
        return (max_loc[0] + template.shape[1] // 2, max_loc[1] + template.shape[0] // 2)
    return None

def find_any_image_on_screen(paths, similarity=80.0):
    """Return location of the first matching image from the list."""
    for p in paths:
        loc = find_image_on_screen(p, similarity)
        if loc is not None:
            return loc
    return None



def human_move_mouse(to_x, to_y, duration=0.5, steps=18, wiggle_px=8):
    """
    Moves mouse to (to_x, to_y) in a wiggly, human-like way.
    """
    from_x, from_y = pyautogui.position()
    path = []
    for i in range(steps):
        frac = i / float(steps-1)
        x = from_x + (to_x - from_x) * frac
        y = from_y + (to_y - from_y) * frac
        decay = math.sin(math.pi * frac)
        wiggle_x = random.uniform(-wiggle_px, wiggle_px) * decay
        wiggle_y = random.uniform(-wiggle_px, wiggle_px) * decay
        path.append((x + wiggle_x, y + wiggle_y))
    t_per_step = duration / (steps-1)
    for (x, y) in path:
        pyautogui.moveTo(int(x), int(y), duration=0)
        time.sleep(t_per_step)


# --- SNIPPING TOOL ---
class SnippingTool(tk.Toplevel):
    def __init__(self, master=None):
        super().__init__(master)
        self.withdraw()
        self.master = master
        self.overrideredirect(True)
        self.screen_width = self.winfo_screenwidth()
        self.screen_height = self.winfo_screenheight()
        self.geometry(f"{self.screen_width}x{self.screen_height}+0+0")
        self.attributes('-alpha', 0.3)
        self.canvas = tk.Canvas(self, cursor="cross", bg="grey")
        self.canvas.pack(fill=tk.BOTH, expand=tk.YES)
        self.start_x = self.start_y = self.end_x = self.end_y = 0
        self.rect = None
        self.snip_path = None
        self.bind("<Escape>", lambda e: self.destroy())
        self.canvas.bind("<ButtonPress-1>", self.on_button_press)
        self.canvas.bind("<B1-Motion>", self.on_mouse_move)
        self.canvas.bind("<ButtonRelease-1>", self.on_button_release)
        self.update()
        self.deiconify()
        self._clipboard_actions = []
        self._undo_stack = []
        self._redo_stack = []

    def on_button_press(self, event):
        self.start_x = self.canvas.canvasx(event.x)
        self.start_y = self.canvas.canvasy(event.y)
        if self.rect:
            self.canvas.delete(self.rect)
        self.rect = self.canvas.create_rectangle(self.start_x, self.start_y, self.start_x, self.start_y, outline='red', width=2)
    def on_mouse_move(self, event):
        cur_x, cur_y = (self.canvas.canvasx(event.x), self.canvas.canvasy(event.y))
        self.canvas.coords(self.rect, self.start_x, self.start_y, cur_x, cur_y)
    def on_button_release(self, event):
        self.end_x = self.canvas.canvasx(event.x)
        self.end_y = self.canvas.canvasy(event.y)
        self.grab_snip()
        self.destroy()
    def grab_snip(self):
        x1 = int(min(self.start_x, self.end_x))
        y1 = int(min(self.start_y, self.end_y))
        x2 = int(max(self.start_x, self.end_x))
        y2 = int(max(self.start_y, self.end_y))
        self.coords = (x1, y1, x2, y2)
        self.withdraw()
        time.sleep(0.2)
        img = ImageGrab.grab(bbox=(x1, y1, x2, y2))
        snip_dir = os.path.join(os.path.expanduser("~"), "Pictures", "MacroSnips")
        os.makedirs(snip_dir, exist_ok=True)
        ts = int(time.time())
        snip_path = os.path.join(snip_dir, f"snip_{ts}.png")
        img.save(snip_path)
        self.snip_path = snip_path
def get_snip_from_screen():
    root = tk.Tk()
    root.withdraw()
    snipper = SnippingTool(root)
    root.wait_window(snipper)
    root.destroy()
    return snipper.snip_path

def get_dynamic_snips_from_screen(count=5, duration=2.0):
    root = tk.Tk()
    root.withdraw()
    snipper = SnippingTool(root)
    root.wait_window(snipper)
    coords = getattr(snipper, "coords", None)
    first_path = snipper.snip_path
    root.destroy()
    if not coords or not first_path:
        return []
    x1, y1, x2, y2 = coords
    snip_dir = os.path.join(os.path.expanduser("~"), "Pictures", "MacroSnips")
    os.makedirs(snip_dir, exist_ok=True)
    paths = [first_path]
    interval = duration / max(count - 1, 1)
    ts = int(time.time())
    for i in range(1, count):
        time.sleep(interval)
        img = ImageGrab.grab(bbox=(x1, y1, x2, y2))
        path = os.path.join(snip_dir, f"snip_{ts}_{i}.png")
        img.save(path)
        paths.append(path)
    return paths


def ask_dynamic_snip_dialog(default_count=5, default_duration=2.0):
    """Ask the user how many images and over what duration to capture."""
    dlg = tk.Toplevel()
    dlg.title("Dynamic Snip")
    dlg.grab_set()
    dlg.resizable(False, False)

    count_var = tk.IntVar(value=default_count)
    duration_var = tk.DoubleVar(value=default_duration)
    result = {}

    tk.Label(dlg, text="Images:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
    tk.Entry(dlg, textvariable=count_var, width=6).grid(row=0, column=1, padx=5, pady=5)
    tk.Label(dlg, text="Duration (s):").grid(row=1, column=0, padx=5, pady=5, sticky="e")
    tk.Entry(dlg, textvariable=duration_var, width=6).grid(row=1, column=1, padx=5, pady=5)

    def do_snip():
        result["count"] = max(1, int(count_var.get()))
        result["duration"] = max(0.1, float(duration_var.get()))
        dlg.destroy()

    def cancel():
        dlg.destroy()

    tk.Button(dlg, text="Snip", command=do_snip).grid(row=2, column=0, padx=5, pady=8)
    tk.Button(dlg, text="Cancel", command=cancel).grid(row=2, column=1, padx=5, pady=8)

    dlg.wait_window()
    return result if result else None

def ask_delay_dialog(default_min=1000, default_between=False, default_max=2000, default_wiggle=False):
    dlg = tk.Toplevel()
    dlg.title("Delay")
    dlg.grab_set()
    dlg.resizable(False, False)

    min_var = tk.IntVar(value=default_min)
    between_var = tk.BooleanVar(value=default_between)
    max_var = tk.IntVar(value=default_max)
    wiggle_var = tk.BooleanVar(value=default_wiggle)

    result = {}

    def on_between_toggle():
        entry_max.config(state="normal" if between_var.get() else "disabled")

    def ok():
        result["min"] = min_var.get()
        result["between"] = between_var.get()
        if between_var.get():
            result["max"] = max_var.get()
        # Store wiggle mouse action as a 'during_action'
        if wiggle_var.get():
            result["during_action"] = {
                "action": "WIGGLE_MOUSE",
                "params": {"range": 8}  # Change the range as desired, or make it a dialog input
            }
        dlg.destroy()

    def cancel():
        dlg.destroy()

    tk.Label(dlg, text="Delay (ms):").grid(row=0, column=0, padx=5, pady=5)
    entry_min = tk.Entry(dlg, textvariable=min_var, width=8)
    entry_min.grid(row=0, column=1, padx=2, pady=5)

    tk.Checkbutton(dlg, text="Between", variable=between_var, command=on_between_toggle).grid(row=0, column=2, padx=2, pady=5)
    tk.Label(dlg, text="and (ms):").grid(row=0, column=3, padx=2, pady=5)
    entry_max = tk.Entry(dlg, textvariable=max_var, width=8)
    entry_max.grid(row=0, column=4, padx=2, pady=5)
    if not between_var.get():
        entry_max.config(state="disabled")

    # NEW: Wiggle mouse during delay
    tk.Checkbutton(
        dlg,
        text="Wiggle mouse during delay",
        variable=wiggle_var
    ).grid(row=1, column=0, columnspan=5, padx=5, pady=8, sticky="w")

    tk.Button(dlg, text="OK", command=ok).grid(row=2, column=2, pady=10)
    tk.Button(dlg, text="Cancel", command=cancel).grid(row=2, column=3, pady=10)

    dlg.wait_window()
    return result if "min" in result else None



# ---------- Combined Mouse Action Dialog ---------- #
def ask_mouse_action_dialog(
    default_action_type="click",
    **kwargs
):
    import tkinter as tk
    from tkinter import ttk
    import keyboard
    import pyautogui

    click_defaults = dict(
        default_action="left_click",
        default_delay=0,
        default_between=False,
        default_delay_max=0,
        default_randomize=False,
        default_rand_px_x=3,
        default_rand_px_y=3,
    )
    move_defaults = dict(
        default_x=0,
        default_y=0,
        default_mode="abs",
        default_ignore=False,
        default_randomize=False,
        default_rand_px=0,
        default_delay=0.15,
        default_between=False,
        default_delay_max=0.35,
    )
    click_defaults.update(kwargs)
    move_defaults.update(kwargs)

    dlg = tk.Toplevel()
    dlg.title("Mouse Action")
    dlg.grab_set()
    dlg.resizable(False, False)

    action_type_var = tk.StringVar(value=default_action_type)
    rb_click = tk.Radiobutton(dlg, text="Click", variable=action_type_var, value="click")
    rb_move = tk.Radiobutton(dlg, text="Move", variable=action_type_var, value="move")
    rb_click.grid(row=0, column=0, padx=5, pady=5, sticky="w")
    rb_move.grid(row=0, column=1, padx=5, pady=5, sticky="w")

    click_tab = tk.Frame(dlg)
    move_tab = tk.Frame(dlg)
    click_tab.grid(row=1, column=0, columnspan=5, padx=5, pady=5)
    move_tab.grid(row=1, column=0, columnspan=5, padx=5, pady=5)

    def update_view(*args):
        if action_type_var.get() == "click":
            move_tab.grid_remove()
            click_tab.grid()
        else:
            click_tab.grid_remove()
            move_tab.grid()

    action_type_var.trace_add("write", update_view)

    # --- Click tab ---
    actions = [
        ("Left Click", "left_click"),
        ("Right Click", "right_click"),
        ("Left Button Down", "left_down"),
        ("Right Button Down", "right_down"),
        ("Left Button Up", "left_up"),
        ("Right Button Up", "right_up"),
        ("Scroll Wheel Up", "scroll_up"),
        ("Scroll Wheel Down", "scroll_down"),
        ("Scroll Wheel Click", "middle_click"),
    ]
    action_var = tk.StringVar(value=click_defaults["default_action"])
    c_delay_var = tk.IntVar(value=click_defaults["default_delay"])
    c_between_var = tk.BooleanVar(value=click_defaults["default_between"])
    c_delay_max_var = tk.IntVar(value=click_defaults["default_delay_max"])
    c_random_var = tk.BooleanVar(value=click_defaults["default_randomize"])
    c_rand_x_var = tk.IntVar(value=click_defaults["default_rand_px_x"])
    c_rand_y_var = tk.IntVar(value=click_defaults["default_rand_px_y"])
    rotations_var = tk.DoubleVar(value=1.0)

    def on_c_between():
        c_delay_max_entry.config(state="normal" if c_between_var.get() else "disabled")

    def on_c_random():
        state = "normal" if c_random_var.get() else "disabled"
        c_rand_x_entry.config(state=state)
        c_rand_y_entry.config(state=state)

    ttk.Label(click_tab, text="Action:").grid(row=0, column=0, padx=5, pady=5)
    c_action_menu = ttk.Combobox(click_tab, textvariable=action_var, values=[a[0] for a in actions], state="readonly", width=20)
    c_action_menu.grid(row=0, column=1, padx=5, pady=5)
    label_to_val = {a[0]: a[1] for a in actions}
    def on_action_select(event=None):
        v = c_action_menu.get()
        if v in label_to_val:
            val = label_to_val[v]
            action_var.set(val)
            if val in ["scroll_up", "scroll_down"]:
                rotations_entry.config(state="normal")
            else:
                rotations_entry.config(state="disabled")

    c_action_menu.bind("<<ComboboxSelected>>", on_action_select)
    ttk.Label(click_tab, text="Delay (ms):").grid(row=1, column=0, padx=5, pady=5)
    tk.Entry(click_tab, textvariable=c_delay_var, width=8).grid(row=1, column=1, padx=5, pady=5)
    tk.Checkbutton(click_tab, text="Between", variable=c_between_var, command=on_c_between).grid(row=1, column=2, padx=2, pady=5)
    ttk.Label(click_tab, text="and (ms):").grid(row=1, column=3, padx=2, pady=5)
    c_delay_max_entry = tk.Entry(click_tab, textvariable=c_delay_max_var, width=8)
    c_delay_max_entry.grid(row=1, column=4, padx=2, pady=5)
    if not c_between_var.get():
        c_delay_max_entry.config(state="disabled")

    tk.Checkbutton(click_tab, text="Randomize click coords", variable=c_random_var, command=on_c_random).grid(row=2, column=0, padx=5, pady=5, sticky="w")
    ttk.Label(click_tab, text="±X:").grid(row=2, column=1, padx=0, pady=5, sticky="e")
    c_rand_x_entry = tk.Entry(click_tab, textvariable=c_rand_x_var, width=5)
    c_rand_x_entry.grid(row=2, column=2, padx=0, pady=5)
    ttk.Label(click_tab, text="±Y:").grid(row=2, column=3, padx=0, pady=5, sticky="e")
    c_rand_y_entry = tk.Entry(click_tab, textvariable=c_rand_y_var, width=5)
    c_rand_y_entry.grid(row=2, column=4, padx=0, pady=5)
    ttk.Label(click_tab, text="Rotations:").grid(row=3, column=0, padx=5, pady=5, sticky="e")
    rotations_entry = tk.Entry(click_tab, textvariable=rotations_var, width=6)
    rotations_entry.grid(row=3, column=1, padx=5, pady=5, sticky="w")
    if not c_random_var.get():
        c_rand_x_entry.config(state="disabled")
        c_rand_y_entry.config(state="disabled")

    # --- Move tab ---
    x_var = tk.IntVar(value=move_defaults["default_x"])
    y_var = tk.IntVar(value=move_defaults["default_y"])
    mode_var = tk.StringVar(value=move_defaults["default_mode"])
    ignore_var = tk.BooleanVar(value=move_defaults["default_ignore"])
    m_random_var = tk.BooleanVar(value=move_defaults["default_randomize"])
    rand_px_var = tk.IntVar(value=move_defaults["default_rand_px"])
    m_delay_var = tk.DoubleVar(value=move_defaults["default_delay"])
    m_between_var = tk.BooleanVar(value=move_defaults["default_between"])
    m_delay_max_var = tk.DoubleVar(value=move_defaults["default_delay_max"])
    live_x = tk.StringVar(value="0")
    live_y = tk.StringVar(value="0")

    def update_live_coords():
        pos = pyautogui.position()
        live_x.set(str(pos.x))
        live_y.set(str(pos.y))
        dlg.after(50, update_live_coords)

    def on_f2(event=None):
        pos = pyautogui.position()
        x_var.set(pos.x)
        y_var.set(pos.y)

    def on_m_random():
        rand_px_entry.config(state="normal" if m_random_var.get() and not ignore_var.get() else "disabled")

    def on_m_between():
        if m_between_var.get() and not ignore_var.get():
            m_delay_max_entry.config(state="normal")
        else:
            m_delay_max_entry.config(state="disabled")

    def on_ignore_toggle():
        state = "disabled" if ignore_var.get() else "normal"
        for w in (x_entry, y_entry, abs_btn, rel_btn, offset_btn, randomize_chk, rand_px_entry, delay_entry, between_chk, m_delay_max_entry):
            try:
                w.config(state=state)
            except Exception:
                pass
        if not m_random_var.get() or ignore_var.get():
            rand_px_entry.config(state="disabled")
        if not m_between_var.get() or ignore_var.get():
            m_delay_max_entry.config(state="disabled")
        f2_lbl.config(state="disabled" if ignore_var.get() else "normal")

    tk.Label(move_tab, text="Coordinates:").grid(row=0, column=0, sticky="e", padx=5)
    x_entry = tk.Entry(move_tab, textvariable=x_var, width=6)
    x_entry.grid(row=0, column=1)
    tk.Label(move_tab, text=",").grid(row=0, column=2)
    y_entry = tk.Entry(move_tab, textvariable=y_var, width=6)
    y_entry.grid(row=0, column=3)
    f2_lbl = tk.Label(move_tab, text="Press F2 to capture current position")
    f2_lbl.grid(row=0, column=4, sticky="w")

    tk.Label(move_tab, textvariable=live_x).grid(row=1, column=1)
    tk.Label(move_tab, textvariable=live_y).grid(row=1, column=3)

    abs_btn = tk.Radiobutton(move_tab, text="Absolute", variable=mode_var, value="abs")
    abs_btn.grid(row=2, column=0, columnspan=5, sticky="w", padx=20)
    rel_btn = tk.Radiobutton(move_tab, text="Relative to window", variable=mode_var, value="rel")
    rel_btn.grid(row=3, column=0, columnspan=5, sticky="w", padx=20)
    offset_btn = tk.Radiobutton(move_tab, text="Offset", variable=mode_var, value="offset")
    offset_btn.grid(row=4, column=0, columnspan=5, sticky="w", padx=20)

    ignore_chk = tk.Checkbutton(move_tab, text="Ignore coordinates", variable=ignore_var, command=on_ignore_toggle)
    ignore_chk.grid(row=5, column=0, columnspan=5, sticky="w", padx=20)

    tk.Label(move_tab, text="Move duration (sec):").grid(row=6, column=0, sticky="e", padx=5)
    delay_entry = tk.Entry(move_tab, textvariable=m_delay_var, width=6)
    delay_entry.grid(row=6, column=1)
    between_chk = tk.Checkbutton(move_tab, text="Between", variable=m_between_var, command=on_m_between)
    between_chk.grid(row=6, column=2, sticky="w")
    tk.Label(move_tab, text="and").grid(row=6, column=3)
    m_delay_max_entry = tk.Entry(move_tab, textvariable=m_delay_max_var, width=6)
    m_delay_max_entry.grid(row=6, column=4)

    randomize_chk = tk.Checkbutton(move_tab, text="Randomize by", variable=m_random_var, command=on_m_random)
    randomize_chk.grid(row=7, column=0, sticky="w", padx=20)
    rand_px_entry = tk.Entry(move_tab, textvariable=rand_px_var, width=5)
    rand_px_entry.grid(row=7, column=1)
    tk.Label(move_tab, text="pixels").grid(row=7, column=2, sticky="w")

    if not m_random_var.get() or ignore_var.get():
        rand_px_entry.config(state="disabled")
    if not m_between_var.get() or ignore_var.get():
        m_delay_max_entry.config(state="disabled")
    dlg.after(100, on_ignore_toggle)
    update_live_coords()
    f2_id = keyboard.add_hotkey('f2', on_f2)

    result = {}

    def ok():
        if action_type_var.get() == "click":
            result.update({
                "mouse_action": action_var.get(),
                "delay": c_delay_var.get(),
                "between": c_between_var.get(),
                "randomize": c_random_var.get(),
            })
            if c_between_var.get():
                result["delay_max"] = c_delay_max_var.get()
            if c_random_var.get():
                result["rand_px_x"] = c_rand_x_var.get()
                result["rand_px_y"] = c_rand_y_var.get()
            if action_var.get() in ["scroll_up", "scroll_down"]:
                result["rotations"] = rotations_var.get()
            result["action_type"] = "click"
        else:
            if ignore_var.get():
                result["ignore"] = True
            else:
                result.update({
                    "x": x_var.get(),
                    "y": y_var.get(),
                    "mode": mode_var.get(),
                })
            result["delay"] = m_delay_var.get()
            result["between"] = m_between_var.get()
            if m_between_var.get():
                result["delay_max"] = m_delay_max_var.get()
            result["randomize"] = m_random_var.get()
            if m_random_var.get():
                result["rand_px"] = rand_px_var.get()
            result["action_type"] = "move"
        dlg.destroy()

    def cancel():
        keyboard.remove_hotkey(f2_id)
        dlg.destroy()

    button_frame = tk.Frame(dlg)
    button_frame.grid(row=2, column=0, columnspan=5, pady=5, sticky="e")
    tk.Button(button_frame, text="Cancel", width=8, command=cancel).pack(side="right", padx=5)
    tk.Button(button_frame, text="OK", width=8, command=ok).pack(side="right")

    update_view()

    dlg.wait_window()
    keyboard.remove_hotkey(f2_id)
    return result if result else None



def ask_if_image_dialog(
    default_not_found=False,
    existing_image=None,
    existing_images=None,
    default_move_mouse=False,
    default_move_duration_min=0.6,
    default_move_between=False,
    default_move_duration_max=1.2,
    default_similarity=80,
    default_wait_mode="off"
):
    import tkinter as tk
    from tkinter import messagebox
    from PIL import Image, ImageTk
    import os
    import pyautogui
    import cv2
    import numpy as np

    dlg = tk.Toplevel()
    dlg.title("Add IF IMAGE")
    dlg.grab_set()
    dlg.resizable(False, False)
    dlg.protocol("WM_DELETE_WINDOW", lambda: cancel())
    thumb_size = (80, 80)
    blank = Image.new("RGBA", thumb_size, (220,220,220,255))
    preview_img_obj = ImageTk.PhotoImage(blank)
    img_path_var = tk.StringVar(value=existing_image)
    image_paths = list(existing_images) if existing_images else ([] if not existing_image else [existing_image])
    not_found_var = tk.BooleanVar(value=default_not_found)
    move_mouse_var = tk.BooleanVar(value=default_move_mouse)
    move_between_var = tk.BooleanVar(value=default_move_between)
    move_duration_min_var = tk.DoubleVar(value=default_move_duration_min)
    move_duration_max_var = tk.DoubleVar(value=default_move_duration_max)
    similarity_var = tk.DoubleVar(value=default_similarity)
    wait_mode_var = tk.StringVar(value=default_wait_mode)
    result = {}

    slideshow_job = None
    slideshow_index = 0

    def _show_image(path):
        nonlocal preview_img_obj
        if path and os.path.isfile(path):
            try:
                img = Image.open(path)
                img.thumbnail(thumb_size)
                preview_img_obj = ImageTk.PhotoImage(img)
                preview_img_label.config(image=preview_img_obj, text="")
            except Exception:
                preview_img_label.config(image=preview_img_obj, text="(Invalid Image)")
        else:
            preview_img_label.config(image=preview_img_obj, text="")

    def update_image_preview(path):
        nonlocal slideshow_job, slideshow_index
        if slideshow_job:
            preview_img_label.after_cancel(slideshow_job)
            slideshow_job = None
        if len(image_paths) > 1:
            slideshow_index = 0

            def cycle():
                nonlocal slideshow_index, slideshow_job
                if not image_paths:
                    return
                _show_image(image_paths[slideshow_index % len(image_paths)])
                slideshow_index += 1
                slideshow_job = preview_img_label.after(500, cycle)

            cycle()
        else:
            _show_image(path)

    def snip():
        dlg.withdraw()
        if dlg.master:
            dlg.master.withdraw()
        dlg.update_idletasks()
        path = get_snip_from_screen()
        if dlg.master:
            dlg.master.deiconify()
        dlg.deiconify()
        if path:
            image_paths.clear()
            image_paths.append(path)
            img_path_var.set(path)
            update_image_preview(path)

    def snip_dynamic():
        params = ask_dynamic_snip_dialog()
        if not params:
            return
        dlg.withdraw()
        if dlg.master:
            dlg.master.withdraw()
        dlg.update_idletasks()
        paths = get_dynamic_snips_from_screen(params.get("count", 5), params.get("duration", 2.0))
        if dlg.master:
            dlg.master.deiconify()
        dlg.deiconify()
        if paths:
            image_paths.clear()
            image_paths.extend(paths)
            img_path_var.set(paths[0])
            update_image_preview(paths[0])

    def on_move_mouse_toggle():
        state = "normal" if move_mouse_var.get() else "disabled"
        check_between.config(state=state)
        entry_move_duration_min.config(state=state)
        if move_between_var.get() and move_mouse_var.get():
            entry_move_duration_max.config(state="normal")
        else:
            entry_move_duration_max.config(state="disabled")

    def on_between_toggle():
        if move_between_var.get() and move_mouse_var.get():
            entry_move_duration_max.config(state="normal")
        else:
            entry_move_duration_max.config(state="disabled")

    def ok():
        if not img_path_var.get():
            messagebox.showerror("Missing Image", "You must snip or select an image.")
            return
        result["image_path"] = img_path_var.get()
        if image_paths:
            result["image_paths"] = list(image_paths)
        result["not_found"] = not_found_var.get()
        result["move_mouse"] = move_mouse_var.get()
        result["move_between"] = move_between_var.get()
        result["similarity"] = float(similarity_var.get())
        result["wait_mode"] = wait_mode_var.get()
        if move_mouse_var.get():
            result["move_duration_min"] = float(move_duration_min_var.get())
            if move_between_var.get():
                result["move_duration_max"] = float(move_duration_max_var.get())
            else:
                result["move_duration_max"] = float(move_duration_min_var.get())
        if slideshow_job:
            preview_img_label.after_cancel(slideshow_job)
        dlg.destroy()

    def cancel():
        if slideshow_job:
            preview_img_label.after_cancel(slideshow_job)
        dlg.destroy()

    def test_image():
        path = img_path_var.get()
        similarity = similarity_var.get()
        invert = not_found_var.get()
        if not path or not os.path.isfile(path):
            messagebox.showerror("Test Failed", "Image path not set or file not found.")
            return
        try:
            screen = pyautogui.screenshot()
            screen_np = np.array(screen)
            screen_gray = cv2.cvtColor(screen_np, cv2.COLOR_BGR2GRAY)
            template = cv2.imread(path, 0)
            if template is None:
                messagebox.showerror("Test Failed", f"Could not read image file:\n{path}")
                return
            res = cv2.matchTemplate(screen_gray, template, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(res)
            found = (max_val >= float(similarity)/100.0)
            condition_result = (not found if invert else found)
            if found:
                h, w = template.shape
                cx, cy = max_loc[0] + w // 2, max_loc[1] + h // 2
                pyautogui.moveTo(cx, cy)
            if condition_result:
                messagebox.showinfo("Test Result", f"**TRUE**\nCondition PASSED\nHighest similarity: {max_val*100:.1f}%")
            else:
                messagebox.showinfo("Test Result", f"**FALSE**\nCondition FAILED\nHighest similarity: {max_val*100:.1f}%")
        except Exception as e:
            messagebox.showerror("Test Failed", f"Error during image test:\n{e}")

    # --- Layout ---
    preview_img_label = tk.Label(dlg, image=preview_img_obj, width=thumb_size[0], height=thumb_size[1], bg="#ddd")
    preview_img_label.grid(row=0, column=0, rowspan=8, padx=8, pady=8, sticky="n")
    tk.Label(dlg, text="Image Path:").grid(row=0, column=1, sticky="w", padx=5, pady=5)
    tk.Entry(dlg, textvariable=img_path_var, width=38, state="readonly").grid(row=0, column=2, padx=5)
    tk.Button(dlg, text="Snip Image", command=snip).grid(row=0, column=3, padx=5)
    tk.Button(dlg, text="Snip Dynamic Image", command=snip_dynamic).grid(row=0, column=4, padx=5)
    tk.Label(dlg, text="Condition:").grid(row=1, column=1, padx=5, sticky="e")
    wait_options = ["off", "wait for image", "wait until not found"]
    wait_menu = ttk.Combobox(dlg, textvariable=wait_mode_var, values=wait_options, width=20, state="readonly")
    wait_menu.grid(row=1, column=2, padx=5, pady=5, sticky="w")
    tk.Checkbutton(dlg, text="If NOT found", variable=not_found_var).grid(row=2, column=1, columnspan=3, sticky="w", padx=5)
    tk.Label(dlg, text="Similarity (%):").grid(row=3, column=1, sticky="e", padx=5)
    sim_slider = tk.Scale(dlg, variable=similarity_var, from_=1, to=100, orient="horizontal", length=160)
    sim_slider.grid(row=3, column=2, columnspan=2, sticky="w", padx=5)
    tk.Checkbutton(dlg, text="Move mouse to image", variable=move_mouse_var, command=on_move_mouse_toggle).grid(row=4, column=1, sticky="w", padx=5)
    tk.Label(dlg, text="Duration (s):").grid(row=4, column=2, sticky="e", padx=5)
    check_between = tk.Checkbutton(dlg, text="Between", variable=move_between_var, command=on_between_toggle)
    check_between.grid(row=5, column=1, sticky="w", padx=5)
    entry_move_duration_min = tk.Entry(dlg, textvariable=move_duration_min_var, width=6)
    entry_move_duration_min.grid(row=5, column=2, sticky="w")
    tk.Label(dlg, text="and").grid(row=5, column=3, sticky="e")
    entry_move_duration_max = tk.Entry(dlg, textvariable=move_duration_max_var, width=6)
    entry_move_duration_max.grid(row=5, column=4, sticky="w")

    tk.Button(dlg, text="OK", command=ok).grid(row=6, column=2, pady=10)
    tk.Button(dlg, text="Cancel", command=cancel).grid(row=6, column=3, pady=10)
    tk.Button(dlg, text="Test", command=test_image).grid(row=6, column=4, pady=10)  # <-- The new test button

    if not move_mouse_var.get():
        check_between.config(state="disabled")
        entry_move_duration_min.config(state="disabled")
        entry_move_duration_max.config(state="disabled")
    else:
        check_between.config(state="normal")
        entry_move_duration_min.config(state="normal")
        entry_move_duration_max.config(state="normal" if move_between_var.get() else "disabled")
    update_image_preview(img_path_var.get())
    dlg.update_idletasks()
    dlg.geometry("")
    dlg.wait_window()
    return result if "image_path" in result else None


def ask_find_image_dialog(
    existing_image=None,
    existing_images=None,
    default_move_mouse=True,
    default_move_duration_min=0.6,
    default_move_between=False,
    default_move_duration_max=1.2,
    default_similarity=80,
):
    """Dialog to configure a Find Image action."""
    import tkinter as tk
    from tkinter import messagebox
    from PIL import Image, ImageTk
    import os
    import pyautogui
    import cv2
    import numpy as np

    dlg = tk.Toplevel()
    dlg.title("Find Image")
    dlg.grab_set()
    dlg.resizable(False, False)
    dlg.protocol("WM_DELETE_WINDOW", lambda: cancel())

    thumb_size = (80, 80)
    blank = Image.new("RGBA", thumb_size, (220, 220, 220, 255))
    preview_img_obj = ImageTk.PhotoImage(blank)

    img_path_var = tk.StringVar(value=existing_image)
    image_paths = list(existing_images) if existing_images else ([] if not existing_image else [existing_image])
    move_mouse_var = tk.BooleanVar(value=default_move_mouse)
    move_between_var = tk.BooleanVar(value=default_move_between)
    move_duration_min_var = tk.DoubleVar(value=default_move_duration_min)
    move_duration_max_var = tk.DoubleVar(value=default_move_duration_max)
    similarity_var = tk.DoubleVar(value=default_similarity)
    result = {}

    slideshow_job = None
    slideshow_index = 0

    def _show_image(path):
        nonlocal preview_img_obj
        if path and os.path.isfile(path):
            try:
                img = Image.open(path)
                img.thumbnail(thumb_size)
                preview_img_obj = ImageTk.PhotoImage(img)
                preview_img_label.config(image=preview_img_obj, text="")
            except Exception:
                preview_img_label.config(image=preview_img_obj, text="(Invalid Image)")
        else:
            preview_img_label.config(image=preview_img_obj, text="")

    def update_image_preview(path):
        nonlocal slideshow_job, slideshow_index
        if slideshow_job:
            preview_img_label.after_cancel(slideshow_job)
            slideshow_job = None
        if len(image_paths) > 1:
            slideshow_index = 0

            def cycle():
                nonlocal slideshow_index, slideshow_job
                if not image_paths:
                    return
                _show_image(image_paths[slideshow_index % len(image_paths)])
                slideshow_index += 1
                slideshow_job = preview_img_label.after(500, cycle)

            cycle()
        else:
            _show_image(path)

    def snip():
        dlg.withdraw()
        if dlg.master:
            dlg.master.withdraw()
        dlg.update_idletasks()
        path = get_snip_from_screen()
        if dlg.master:
            dlg.master.deiconify()
        dlg.deiconify()
        if path:
            image_paths.clear()
            image_paths.append(path)
            img_path_var.set(path)
            update_image_preview(path)

    def snip_dynamic():
        params = ask_dynamic_snip_dialog()
        if not params:
            return
        dlg.withdraw()
        if dlg.master:
            dlg.master.withdraw()
        dlg.update_idletasks()
        paths = get_dynamic_snips_from_screen(params.get("count", 5), params.get("duration", 2.0))
        if dlg.master:
            dlg.master.deiconify()
        dlg.deiconify()
        if paths:
            image_paths.clear()
            image_paths.extend(paths)
            img_path_var.set(paths[0])
            update_image_preview(paths[0])

    def on_move_mouse_toggle():
        state = "normal" if move_mouse_var.get() else "disabled"
        check_between.config(state=state)
        entry_move_duration_min.config(state=state)
        if move_between_var.get() and move_mouse_var.get():
            entry_move_duration_max.config(state="normal")
        else:
            entry_move_duration_max.config(state="disabled")

    def on_between_toggle():
        if move_between_var.get() and move_mouse_var.get():
            entry_move_duration_max.config(state="normal")
        else:
            entry_move_duration_max.config(state="disabled")

    def ok():
        if not img_path_var.get():
            messagebox.showerror("Missing Image", "You must snip or select an image.")
            return
        result["image_path"] = img_path_var.get()
        if image_paths:
            result["image_paths"] = list(image_paths)
        result["move_mouse"] = move_mouse_var.get()
        result["move_between"] = move_between_var.get()
        result["similarity"] = float(similarity_var.get())
        if move_mouse_var.get():
            result["move_duration_min"] = float(move_duration_min_var.get())
            if move_between_var.get():
                result["move_duration_max"] = float(move_duration_max_var.get())
            else:
                result["move_duration_max"] = float(move_duration_min_var.get())
        if slideshow_job:
            preview_img_label.after_cancel(slideshow_job)
        dlg.destroy()

    def cancel():
        if slideshow_job:
            preview_img_label.after_cancel(slideshow_job)
        dlg.destroy()

    def test_image():
        path = img_path_var.get()
        similarity = similarity_var.get()
        if not path or not os.path.isfile(path):
            messagebox.showerror("Test Failed", "Image path not set or file not found.")
            return
        try:
            screen = pyautogui.screenshot()
            screen_np = np.array(screen)
            screen_gray = cv2.cvtColor(screen_np, cv2.COLOR_BGR2GRAY)
            template = cv2.imread(path, 0)
            if template is None:
                messagebox.showerror("Test Failed", f"Could not read image file:\n{path}")
                return
            res = cv2.matchTemplate(screen_gray, template, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(res)
            found = (max_val >= float(similarity)/100.0)
            if found:
                h, w = template.shape
                cx, cy = max_loc[0] + w // 2, max_loc[1] + h // 2
                pyautogui.moveTo(cx, cy)
                messagebox.showinfo("Test Result", f"Found image at similarity {max_val*100:.1f}%")
            else:
                messagebox.showinfo("Test Result", f"Image NOT found\nHighest similarity: {max_val*100:.1f}%")
        except Exception as e:
            messagebox.showerror("Test Failed", f"Error during image test:\n{e}")

    # --- Layout ---
    preview_img_label = tk.Label(dlg, image=preview_img_obj, width=thumb_size[0], height=thumb_size[1], bg="#ddd")
    preview_img_label.grid(row=0, column=0, rowspan=6, padx=8, pady=8, sticky="n")
    tk.Label(dlg, text="Image Path:").grid(row=0, column=1, sticky="w", padx=5, pady=5)
    tk.Entry(dlg, textvariable=img_path_var, width=38, state="readonly").grid(row=0, column=2, padx=5)
    tk.Button(dlg, text="Snip Image", command=snip).grid(row=0, column=3, padx=5)
    tk.Button(dlg, text="Snip Dynamic Image", command=snip_dynamic).grid(row=0, column=4, padx=5)
    tk.Label(dlg, text="Similarity (%):").grid(row=1, column=1, sticky="e", padx=5)
    sim_slider = tk.Scale(dlg, variable=similarity_var, from_=1, to=100, orient="horizontal", length=160)
    sim_slider.grid(row=1, column=2, columnspan=2, sticky="w", padx=5)
    tk.Checkbutton(dlg, text="Move mouse to image", variable=move_mouse_var, command=on_move_mouse_toggle).grid(row=2, column=1, sticky="w", padx=5)
    tk.Label(dlg, text="Duration (s):").grid(row=2, column=2, sticky="e", padx=5)
    check_between = tk.Checkbutton(dlg, text="Between", variable=move_between_var, command=on_between_toggle)
    check_between.grid(row=3, column=1, sticky="w", padx=5)
    entry_move_duration_min = tk.Entry(dlg, textvariable=move_duration_min_var, width=6)
    entry_move_duration_min.grid(row=3, column=2, sticky="w")
    tk.Label(dlg, text="and").grid(row=3, column=3, sticky="e")
    entry_move_duration_max = tk.Entry(dlg, textvariable=move_duration_max_var, width=6)
    entry_move_duration_max.grid(row=3, column=4, sticky="w")

    tk.Button(dlg, text="OK", command=ok).grid(row=4, column=2, pady=10)
    tk.Button(dlg, text="Cancel", command=cancel).grid(row=4, column=3, pady=10)
    tk.Button(dlg, text="Test", command=test_image).grid(row=4, column=4, pady=10)

    if not move_mouse_var.get():
        check_between.config(state="disabled")
        entry_move_duration_min.config(state="disabled")
        entry_move_duration_max.config(state="disabled")
    else:
        check_between.config(state="normal")
        entry_move_duration_min.config(state="normal")
        entry_move_duration_max.config(state="normal" if move_between_var.get() else "disabled")

    update_image_preview(img_path_var.get())
    dlg.update_idletasks()
    dlg.geometry("")
    dlg.wait_window()
    return result if "image_path" in result else None


def get_common_keys():
    return [
        'enter','esc','tab','backspace','delete','insert','space','shift','ctrl','ctrlleft','ctrlright','alt','altleft','altright','win','winleft','winright','apps',
        'up','down','left','right','home','end','pageup','pagedown',
        'f1','f2','f3','f4','f5','f6','f7','f8','f9','f10','f11','f12',
        'a','b','c','d','e','f','g','h','i','j','k','l','m','n','o','p','q','r','s','t','u','v','w','x','y','z',
        '0','1','2','3','4','5','6','7','8','9',
        'num0','num1','num2','num3','num4','num5','num6','num7','num8','num9',
        'multiply','add','separator','subtract','decimal','divide',
        'capslock','numlock','scrolllock','printscreen','pause'
    ]

def ask_keyaction_dialog(default_key='enter', default_action='press'):
    dlg = tk.Toplevel()
    dlg.title("Add Key Action")
    dlg.grab_set()
    dlg.resizable(False, False)

    key_var = tk.StringVar(value=default_key)
    action_var = tk.StringVar(value=default_action)
    result = {}

    tk.Label(dlg, text="Key:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
    key_lbl = tk.Label(dlg, textvariable=key_var, relief="sunken", width=12)
    key_lbl.grid(row=0, column=1, padx=5, pady=5)

    def select_key():
        messagebox.showinfo("Select Key", "Please press the key you'd like")
        key = keyboard.read_key()
        key_var.set(key)

    tk.Button(dlg, text="Select", command=select_key).grid(row=0, column=2, padx=5, pady=5)

    tk.Label(dlg, text="Action:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
    action_menu = ttk.Combobox(dlg, textvariable=action_var, values=['press','down','up'], width=10, state="readonly")
    action_menu.grid(row=1, column=1, padx=5, pady=5)

    def ok():
        result["key"] = key_var.get()
        result["action"] = action_var.get()
        dlg.destroy()

    def cancel():
        dlg.destroy()

    button_frame = tk.Frame(dlg)
    button_frame.grid(row=2, column=0, columnspan=3, pady=10, sticky="e")
    tk.Button(button_frame, text="Cancel", command=cancel, width=8).pack(side="right", padx=5)
    tk.Button(button_frame, text="OK", command=ok, width=8).pack(side="right")

    dlg.wait_window()
    return result if "key" in result else None

def ask_typetext_dialog(default_text='', default_delay=True, default_delay_ms=50):
    dlg = tk.Toplevel()
    dlg.title("Type Text")
    dlg.grab_set()
    dlg.resizable(False, False)
    text_var = tk.StringVar(value=default_text)
    delay_var = tk.BooleanVar(value=default_delay)
    delay_ms_var = tk.IntVar(value=default_delay_ms)
    result = {}
    def on_delay_toggle():
        entry_delay.config(state="normal" if delay_var.get() else "disabled")
    def ok():
        result["text"] = text_var.get()
        result["delay"] = delay_var.get()
        if delay_var.get():
            result["delay_ms"] = delay_ms_var.get()
        dlg.destroy()
    def cancel():
        dlg.destroy()
    tk.Label(dlg, text="Text:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
    tk.Entry(dlg, textvariable=text_var, width=25).grid(row=0, column=1, padx=5)
    tk.Checkbutton(dlg, text="Delay per key", variable=delay_var, command=on_delay_toggle).grid(row=1, column=0, sticky="w", padx=5)
    tk.Label(dlg, text="Delay (ms):").grid(row=1, column=1, sticky="e", padx=5)
    entry_delay = tk.Entry(dlg, textvariable=delay_ms_var, width=6)
    entry_delay.grid(row=1, column=2, padx=5)
    if not delay_var.get():
        entry_delay.config(state="disabled")
    tk.Button(dlg, text="OK", command=ok).grid(row=2, column=1, pady=10)
    tk.Button(dlg, text="Cancel", command=cancel).grid(row=2, column=2, pady=10)
    dlg.wait_window()
    return result if "text" in result else None

def ask_wait_for_input_dialog(default_key='x'):
    dlg = tk.Toplevel()
    dlg.title("Wait for Input")
    dlg.grab_set()
    dlg.resizable(False, False)
    key_var = tk.StringVar(value=default_key)
    result = {}
    tk.Label(dlg, text="Wait for key:").grid(row=0, column=0, padx=10, pady=10)
    key_choices = get_common_keys()
    key_menu = ttk.Combobox(dlg, textvariable=key_var, values=key_choices, width=20, state="readonly")
    key_menu.grid(row=0, column=1, padx=5, pady=10)
    def ok():
        result["key"] = key_var.get()
        dlg.destroy()
    def cancel():
        dlg.destroy()
    tk.Button(dlg, text="OK", command=ok).grid(row=1, column=0, pady=10)
    tk.Button(dlg, text="Cancel", command=cancel).grid(row=1, column=1, pady=10)
    dlg.wait_window()
    return result if "key" in result else None

def ask_goto_dialog(labels, default_label=None):
    dlg = tk.Toplevel()
    dlg.title("Goto")
    dlg.grab_set()
    dlg.resizable(False, False)

    label_var = tk.StringVar(value=default_label if default_label else (labels[0] if labels else ""))
    result = {}

    tk.Label(dlg, text="Goto label:").grid(row=0, column=0, padx=10, pady=10)
    label_menu = ttk.Combobox(dlg, textvariable=label_var, values=labels, width=20, state="readonly")
    label_menu.grid(row=0, column=1, padx=5, pady=10)

    def ok():
        if not label_var.get():
            messagebox.showerror("Invalid", "Please select a label")
            return
        result["label"] = label_var.get()
        dlg.destroy()

    def cancel():
        dlg.destroy()

    tk.Button(dlg, text="OK", command=ok).grid(row=1, column=0, pady=10)
    tk.Button(dlg, text="Cancel", command=cancel).grid(row=1, column=1, pady=10)
    dlg.wait_window()
    return result.get("label")

def ask_repeat_dialog(default_count=2, default_random=False, default_max=None):
    dlg = tk.Toplevel()
    dlg.title("Repeat Block")
    dlg.grab_set()
    dlg.resizable(False, False)

    if default_max is None:
        default_max = max(default_count, 5)

    count_var = tk.IntVar(value=default_count)
    max_var = tk.IntVar(value=default_max)
    use_random = tk.BooleanVar(value=default_random)
    result = {}

    tk.Label(dlg, text="Repeat X times:").grid(row=0, column=0, padx=10, pady=5, sticky="e")
    entry_x = tk.Entry(dlg, textvariable=count_var, width=5)
    entry_x.grid(row=0, column=1, padx=5, pady=5, sticky="w")

    def toggle_max():
        state = "normal" if use_random.get() else "disabled"
        entry_y.config(state=state)

    rand_chk = tk.Checkbutton(dlg, text="Random between X and Y", variable=use_random, command=toggle_max)
    rand_chk.grid(row=1, column=0, columnspan=2, sticky="w", padx=10)

    tk.Label(dlg, text="Y value:").grid(row=2, column=0, padx=10, pady=5, sticky="e")
    entry_y = tk.Entry(dlg, textvariable=max_var, width=5)
    entry_y.grid(row=2, column=1, padx=5, pady=5, sticky="w")

    toggle_max()

    def ok():
        x = count_var.get()
        y = max_var.get()
        if x < 1:
            messagebox.showerror("Invalid", "Repeat count must be at least 1")
            return
        if use_random.get():
            if y < x:
                messagebox.showerror("Invalid", "Y must be greater than or equal to X")
                return
            result.update({"random": True, "min": x, "max": y})
        else:
            result.update({"random": False, "count": x})
        dlg.destroy()

    def cancel():
        dlg.destroy()

    tk.Button(dlg, text="OK", command=ok).grid(row=3, column=0, pady=10)
    tk.Button(dlg, text="Cancel", command=cancel).grid(row=3, column=1, pady=10)
    dlg.wait_window()
    return result if result else None

# ----- CONTINUE FOR: MacroAction, OverlayControl, MacroRecorderApp, __main__ -----

class MacroAction:
    def __init__(self, action, params):
        self.action = action
        self.params = params
    def run_action_during_delay(self, duration_secs, during_action, check_interrupt=None):
        import time, random, pyautogui, math
        start = time.time()
        last_target = pyautogui.position()
        while time.time() - start < duration_secs:
            if check_interrupt:
                check_interrupt()
            next_wiggle = random.uniform(0.18, 0.4)
            px = during_action["params"].get("range", 8)
            target_x = last_target[0] + random.randint(-px, px)
            target_y = last_target[1] + random.randint(-px, px)
            pyautogui.moveTo(target_x, target_y, duration=next_wiggle, tween=pyautogui.easeInOutSine)
            last_target = (target_x, target_y)
            time.sleep(random.uniform(0.12, 0.25))

    

    def __str__(self):
        if self.action == "IF_IMAGE":
            nf = " (NOT found)" if self.params.get("not_found") else ""
            mm = ""
            sim = self.params.get("similarity", 80)
            cond = ""
            if self.params.get("wait_mode","off") == "wait for image":
                cond = " (Wait for image)"
            elif self.params.get("wait_mode","off") == "wait until not found":
                cond = " (Wait until not found)"
            if self.params.get("move_mouse"):
                mm = f" [Move mouse {self.params.get('move_duration', 0.6)}s]"
            paths = self.params.get("image_paths") or [self.params.get("image_path")]
            img_name = os.path.basename(paths[0]) if paths else ""
            if len(paths) > 1:
                img_name += f" (+{len(paths)-1})"
            return f"IF IMAGE: {img_name}{nf}{cond}{mm} [Sim {sim:.0f}%]"
        elif self.action == "FIND_IMAGE":
            sim = self.params.get("similarity", 80)
            mm = ""
            if self.params.get("move_mouse"):
                mm = f" [Move mouse {self.params.get('move_duration_min', 0.6)}s]"
            paths = self.params.get("image_paths") or [self.params.get("image_path")]
            img_name = os.path.basename(paths[0]) if paths else ""
            if len(paths) > 1:
                img_name += f" (+{len(paths)-1})"
            return f"Find Image: {img_name}{mm} [Sim {sim:.0f}%]"
        elif self.action == "MOUSE_CLICK":
            action = self.params.get("mouse_action", "left_click")
            delay_str = ""
            if self.params.get("between"):
                delay_str = f" ({self.params.get('delay', 0)}-{self.params.get('delay_max', 0)}ms)"
            elif self.params.get("delay", 0):
                delay_str = f" ({self.params.get('delay', 0)}ms)"
            rand_str = ""
            if self.params.get("randomize"):
                rand_str = f" [±{self.params.get('rand_px_x',3)}x{self.params.get('rand_px_y',3)} px]"
            return f"Mouse: {action.replace('_',' ').capitalize()}{delay_str}{rand_str}"
        # ------- NEW: Mouse Move String -------
        elif self.action == "MOUSE_MOVE":
            mode = self.params.get("mode", "abs")
            x = self.params.get("x", 0)
            y = self.params.get("y", 0)
            rand_str = ""
            if self.params.get("randomize", False):
                rand_str = f" [±{self.params.get('rand_px',0)} px]"
            mode_str = {
                "abs": "Absolute",
                "rel": "Relative",
                "offset": "Offset",
                "ignore": "Current Pos"
            }.get(mode, mode)
            return f"Mouse: Move {mode_str} to ({x}, {y}){rand_str}"
        # ------- END NEW -------
        elif self.action == "ELSE":
            return "ELSE"
        elif self.action == "END_IF":
            return "END IF"
        elif self.action == "DELAY":
            if self.params.get("between"):
                return f"Delay {self.params['min']} - {self.params['max']} ms"
            else:
                return f"Delay {self.params['min']} ms"
        elif self.action == "KEY_ACTION":
            return f"Key {self.params['action'].capitalize()} '{self.params['key']}'"
        elif self.action == "TYPE_TEXT":
            delay_part = ""
            if self.params.get("delay"):
                delay_part = f" [Delay {self.params.get('delay_ms', 50)}ms]"
            return f"Type Text '{self.params['text']}'{delay_part}"
        elif self.action == "LABEL":
            return f"LABEL: {self.params['label']}"
        elif self.action == "GOTO":
            return f"GOTO: {self.params['label']}"
        elif self.action == "RANDOM_START":
            return "--- RANDOM ---"
        elif self.action == "RANDOM_END":
            return "--- END RANDOM ---"
        elif self.action == "WAIT_FOR_INPUT":
            return f"Wait for key '{self.params.get('key', '')}'"
        elif self.action == "IF_KEY":
            return f"IF Key '{self.params.get('key', '')}' Pressed"
        elif self.action == "REPEAT":
            if self.params.get("random"):
                mn = self.params.get("min", 1)
                mx = self.params.get("max", mn)
                return f"Repeat random {mn}-{mx}x"
            else:
                return f"Repeat {self.params.get('count', 2)}x"
        elif self.action == "END_REPEAT":
            return f"End Repeat"
        else:
            return f"{self.action}: {self.params}"

class OverlayControl(tk.Toplevel):
    def __init__(self, parent, on_stop, on_pause_toggle, debug=False):
        super().__init__(parent)
        self.on_stop = on_stop
        self.on_pause_toggle = on_pause_toggle
        self.paused = False
        self.debug = debug

        screen_width = self.winfo_screenwidth()
        self.geometry(f"{screen_width}x100+0+0")
        self.attributes("-topmost", True)
        self.overrideredirect(True)
        self.configure(bg="black")

        self.step_lbl = tk.Label(
            self,
            text="",
            bg="black",
            fg="yellow",
            font=("Segoe UI", 14, "bold"),
            anchor="e"
        )
        self.step_lbl.place(x=screen_width-10, y=5, anchor="ne")
        if not self.debug:
            self.step_lbl.place_forget()

        tk.Button(self, text="⏸ Pause", width=9, bg="#DDD", fg="#000",
                  command=self.pause_or_resume).place(x=10, y=5)
        tk.Button(self, text="⏹ Stop", width=9, bg="#F44", fg="#000",
                  command=self.on_stop).place(x=10, y=50)

        self.lbl = tk.Label(self, text="", bg="black", fg="#FFF")
        self.lbl.place(x=120, y=18)

        self.bind("<Escape>", lambda e: self.on_stop())
        self.focus_force()
        self.after(100, self.bring_to_top)

    def bring_to_top(self):
        # Defensive: skip if window is already destroyed
        if not self.winfo_exists():
            return
        self.lift()
        self.after(100, self.bring_to_top)

    def pause_or_resume(self):
        self.paused = not self.paused
        self.on_pause_toggle(self.paused)
        if self.lbl.winfo_exists():
            self.lbl.config(text="Paused" if self.paused else "")

    def set_step_text(self, txt):
        # Defensive: skip if label/window is destroyed
        try:
            if self.debug:
                if self.step_lbl.winfo_exists():
                    self.step_lbl.place(x=self.winfo_screenwidth()-10, y=5, anchor="ne")
                    self.step_lbl.config(text=txt)
            else:
                if self.step_lbl.winfo_exists():
                    self.step_lbl.place_forget()
        except tk.TclError:
            pass

    def set_debug(self, debug):
        self.debug = debug
        try:
            if self.debug:
                if self.step_lbl.winfo_exists():
                    self.step_lbl.place(x=self.winfo_screenwidth()-10, y=5, anchor="ne")
            else:
                if self.step_lbl.winfo_exists():
                    self.step_lbl.place_forget()
        except tk.TclError:
            pass



class StepOverlay(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        screen_width = self.winfo_screenwidth()
        self.geometry(f"{screen_width}x40+0+0")
        self.configure(bg="black")
        self.step_lbl = tk.Label(self, text="", bg="black", fg="yellow",
                                 font=("Segoe UI", 14, "bold"), anchor="e")
        self.step_lbl.place(x=screen_width-10, y=5, anchor="ne")
        self.after(100, self.bring_to_top)

    def bring_to_top(self):
        self.lift()
        self.after(100, self.bring_to_top)

    def set_step_text(self, txt):
        try:
            if self.step_lbl.winfo_exists():
                self.step_lbl.config(text=txt)
        except tk.TclError:
            pass


class MacroRecorderApp:
    def __init__(self, master):
        self.master = master
        self._undo_stack = []
        self._redo_stack = []
        self._clipboard_actions = []
        self.master.title("Python Macro Creator")
        self.macro = []
        self._dragging = False
        self._drag_start_index = None
        self.running_macro = False
        self.should_stop = False
        self.should_pause = False
        self.overlay = None
        self.debug_var = tk.BooleanVar(value=False)
        self.current_step_var = tk.StringVar(value="")

        # SERIAL: serial_conn and new UI
        self.serial_conn = None

        # ------ ADD THESE ------
        self.pi_ip_var = tk.StringVar(value="192.168.0.103")
        self.wifi_mode_var = tk.BooleanVar(value=False)
        self.humanize_var = tk.BooleanVar(value=False)
        self.take_breaks_var = tk.BooleanVar(value=False)
        self._next_break_time = None
        # -----------------------

        self.create_widgets()
        # Allow the grid columns to expand when the window is resized
        for col in range(8):
            self.master.grid_columnconfigure(col, weight=1)
        self.master.grid_rowconfigure(0, weight=1)
        for row in range(1, 6):
            self.master.grid_rowconfigure(row, weight=0)
        self.master.protocol("WM_DELETE_WINDOW", self.on_close)

    def send_wiggle_to_pi(self, duration, pi_server_url, px=8, steps=20):
        import requests, time, random, math
        print(f"WIGGLE TO PI: duration={duration}, px={px}, steps={steps}")
        start = time.time()
        for i in range(steps):
            frac = i / float(steps - 1)
            decay = math.sin(math.pi * frac)
            dx = int(random.uniform(-px, px) * decay)
            dy = int(random.uniform(-px, px) * decay)
            payload = {
                "type": "mouse_move",
                "x": dx,
                "y": dy,
                "wheel": 0,
                "buttons": 0
            }
            print(f"WIGGLE PAYLOAD: {payload}")
            try:
                requests.post(f"{pi_server_url}/action", json=payload, timeout=2)
            except Exception as e:
                print("Wiggle step failed:", e)
            time.sleep(duration / steps)

    def safe_overlay_text(self, text):
        if self.overlay and self.overlay.winfo_exists():
            try:
                self.overlay.after(0, lambda t=text: self.overlay.set_step_text(t))
            except tk.TclError:
                pass



    def create_widgets(self):
        self.step_label = tk.Label(
            self.master,
            textvariable=self.current_step_var,
            fg="white",
            bg="black",
            font=("Segoe UI", 12),
            anchor="e"
        )
        self.step_label.place(relx=1.0, x=-10, y=2, anchor="ne")  # TOP RIGHT

        self.action_listbox = tk.Listbox(self.master, width=60, selectmode=tk.EXTENDED)
        self.action_listbox.grid(row=0, column=0, columnspan=8, sticky="nsew", pady=5)
        self.action_listbox.bind("<Button-3>", self.on_right_click)
        self.action_listbox.bind("<Double-1>", self.on_double_click)
        self.action_listbox.bind('<ButtonPress-1>', self.on_drag_start)
        self.action_listbox.bind('<B1-Motion>', self.on_drag_motion)
        self.action_listbox.bind('<ButtonRelease-1>', self.on_drag_drop)
        self.action_listbox.bind("<Delete>", lambda e: self.remove_step())
        self.action_listbox.bind("<Control-c>", lambda e: self.copy_steps())
        self.action_listbox.bind("<Control-v>", lambda e: self.paste_steps())
        self.master.bind_all("<Control-z>", lambda e: self.undo())
        self.master.bind_all("<Control-y>", lambda e: self.redo())


        btns = [
            ("IF IMAGE", self.add_if_image),
            ("Find Image", self.add_find_image),
            ("IF KEY", self.add_if_key),
            ("ELSE", self.add_else),
            ("END IF", self.add_end_if),
            ("Random", self.add_random_start),
            ("End Random", self.add_random_end),
            ("Wait for Input", self.add_wait_for_input),
            ("Repeat", self.add_repeat),
            ("End Repeat", self.add_end_repeat),
            ("Mouse", self.add_mouse_command),
            ("Delay", self.add_delay),
            ("Key Action", self.add_keyaction),
            ("Type Text", self.add_typetext),
            ("LABEL", self.add_label),
            ("GOTO", self.add_goto),
            # Don't put Export Arduino here (not a macro step)
        ]
        for i, (txt, cmd) in enumerate(btns):
            tk.Button(self.master, text=txt, command=lambda c=cmd: self.add_action_btn(c), width=12)\
                .grid(row=1 + i // 8, column=i % 8, padx=2, pady=2, sticky="nsew")

        tk.Button(self.master, text="▶ Play", font=("Segoe UI Symbol", 16), command=self.run_macro_thread, borderwidth=0, highlightthickness=0, cursor="hand2", width=8, height=1)\
            .grid(row=4, column=0, pady=10, sticky="nsew")
        tk.Button(self.master, text="New", command=self.new_macro, width=12)\
            .grid(row=3, column=0, pady=2, sticky="nsew")
        tk.Button(self.master, text="Save Macro", command=self.save_macro, width=12)\
            .grid(row=3, column=1, pady=10, sticky="nsew")
        tk.Button(self.master, text="Load Macro", command=self.load_macro, width=12)\
            .grid(row=3, column=2, pady=10, sticky="nsew")
        tk.Button(self.master, text="Remove Step", command=self.remove_step, width=12)\
            .grid(row=3, column=3, pady=10, sticky="nsew")
        tk.Button(self.master, text="Export Arduino", command=self.export_arduino, width=12)\
            .grid(row=4, column=1, pady=10, sticky="nsew")

        debug_chk = tk.Checkbutton(self.master, text="Debug", variable=self.debug_var, command=self.on_debug_toggle)
        debug_chk.grid(row=3, column=7, padx=2, pady=10, sticky="e")

        humanize_chk = tk.Checkbutton(self.master, text="Humanize", variable=self.humanize_var, command=self.on_humanize_toggle)
        humanize_chk.grid(row=4, column=2, sticky="w", padx=2)
        self.take_breaks_chk = tk.Checkbutton(self.master, text="Take breaks", variable=self.take_breaks_var)
        self.take_breaks_chk.grid(row=4, column=3, sticky="w", padx=2)
        self.take_breaks_chk.config(state="disabled")
        self.on_humanize_toggle()

        # -- SERIAL CONNECTION UI SECTION --
        self.serial_frame = tk.Frame(self.master)
        # Allow the serial connection controls to stretch with the window
        self.serial_frame.grid(row=5, column=0, columnspan=8, sticky="ew", pady=4)
        tk.Label(self.serial_frame, text="Serial port:").pack(side="left")
        self.serial_port_var = tk.StringVar()
        self.serial_ports_combo = ttk.Combobox(self.serial_frame, textvariable=self.serial_port_var, width=25, state="readonly")
        self.serial_ports_combo.pack(side="left")
        self.refresh_serial_ports()
        tk.Button(self.serial_frame, text="Refresh", command=self.refresh_serial_ports).pack(side="left", padx=3)
        self.connect_btn = tk.Button(self.serial_frame, text="Connect", command=self.connect_serial)
        self.connect_btn.pack(side="left", padx=3)
        self.serial_status_lbl = tk.Label(self.serial_frame, text="Not connected", fg="red")
        self.serial_status_lbl.pack(side="left", padx=5)

        # ----------- PI IP AND WIFI CHECKBOX ----------- #
        tk.Label(self.master, text="Pi IP:").grid(row=3, column=5, sticky="e", padx=2)
        tk.Entry(self.master, textvariable=self.pi_ip_var, width=15).grid(row=3, column=6, sticky="w", padx=2)
        tk.Checkbutton(
            self.master,
            text="Send clicks/keys to Pi over WiFi",
            variable=self.wifi_mode_var
        ).grid(row=3, column=7, sticky="w", padx=2)

    # --- Serial helpers ---
    def refresh_serial_ports(self):
        ports = [port.device for port in serial.tools.list_ports.comports()]
        self.serial_ports_combo['values'] = ports
        if ports:
            self.serial_ports_combo.current(0)
        else:
            self.serial_port_var.set("")

    def connect_serial(self):
        port = self.serial_port_var.get()
        try:
            self.serial_conn = serial.Serial(port, baudrate=115200, timeout=1)
            self.serial_status_lbl.config(text=f"Connected: {port}", fg="green")
        except Exception as e:
            self.serial_status_lbl.config(text=f"Error: {e}", fg="red")
            self.serial_conn = None

    # --- All your other logic (unchanged!) below here ---

    def undo(self):
        if not self._undo_stack:
            messagebox.showinfo("Undo", "Nothing to undo.")
            return

        # Restore previous macro state
        self._redo_stack.append([{"action": a.action, "params": dict(a.params)} for a in self.macro])
        previous = self._undo_stack.pop()
        self.macro = [MacroAction(a['action'], dict(a['params'])) for a in previous]
        self.refresh_listbox()

    def redo(self):
        if not self._redo_stack:
            messagebox.showinfo("Redo", "Nothing to redo.")
            return

        self._undo_stack.append([{"action": a.action, "params": dict(a.params)} for a in self.macro])
        next_state = self._redo_stack.pop()
        self.macro = [MacroAction(a['action'], dict(a['params'])) for a in next_state]
        self.refresh_listbox()

    def push_undo_snapshot(self):
        self._undo_stack.append([{"action": a.action, "params": dict(a.params)} for a in self.macro])
        if len(self._undo_stack) > 50:  # optional stack limit
            self._undo_stack.pop(0)
        self._redo_stack.clear()
    

    def on_debug_toggle(self):
        if self.overlay:
            self.overlay.set_debug(self.debug_var.get())

    def on_humanize_toggle(self):
        if self.humanize_var.get():
            self.take_breaks_chk.config(state="normal")
            if self.take_breaks_var.get():
                self._next_break_time = time.time() + random.uniform(3600, 9000)
        else:
            self.take_breaks_chk.config(state="disabled")
            self.take_breaks_var.set(False)
            self._next_break_time = None

    def maybe_take_break(self, check_interrupt):
        if not (self.humanize_var.get() and self.take_breaks_var.get()):
            return
        if self._next_break_time is None:
            self._next_break_time = time.time() + random.uniform(3600, 9000)
            return
        if time.time() >= self._next_break_time:
            break_dur = random.uniform(60, 420)
            if self.overlay:
                self.safe_overlay_text("Taking break...")
            end = time.time() + break_dur
            while time.time() < end:
                check_interrupt()
                time.sleep(1)
            self._next_break_time = time.time() + random.uniform(3600, 9000)
            if self.overlay:
                self.safe_overlay_text("")

    def add_action_btn(self, add_func):
        idx = self.action_listbox.curselection()
        insert_idx = idx[0]+1 if idx else len(self.macro)
        result = add_func(insert_idx=insert_idx)
        if result:
            self.refresh_listbox()

    def add_action(self, action, params, insert_idx=None):
        self.push_undo_snapshot()
        if insert_idx is None:
            self.macro.append(MacroAction(action, params))
            self.action_listbox.insert(tk.END, str(self.macro[-1]))
        else:
            self.macro.insert(insert_idx, MacroAction(action, params))
            self.refresh_listbox()

    def add_if_image(self, insert_idx=None):
        res = ask_if_image_dialog()
        if res:
            self.add_action("IF_IMAGE", res, insert_idx=insert_idx)
            return True

    def add_find_image(self, insert_idx=None):
        res = ask_find_image_dialog()
        if res:
            self.add_action("FIND_IMAGE", res, insert_idx=insert_idx)
            return True

    def add_else(self, insert_idx=None):
        self.add_action("ELSE", {}, insert_idx=insert_idx)
        return True

    def add_end_if(self, insert_idx=None):
        self.add_action("END_IF", {}, insert_idx=insert_idx)
        return True

    def add_random_start(self, insert_idx=None):
        self.add_action("RANDOM_START", {}, insert_idx=insert_idx)
        return True

    def add_random_end(self, insert_idx=None):
        self.add_action("RANDOM_END", {}, insert_idx=insert_idx)
        return True

    def add_mouse_click(self, insert_idx=None):
        res = ask_mouse_action_dialog(default_action_type="click")
        if res:
            atype = res.pop("action_type")
            if atype == "move":
                self.add_action("MOUSE_MOVE", res, insert_idx=insert_idx)
            else:
                self.add_action("MOUSE_CLICK", res, insert_idx=insert_idx)
            return True

    def add_mouse_command(self, insert_idx=None):
        res = ask_mouse_action_dialog(default_action_type="move")
        if res:
            atype = res.pop("action_type")
            if atype == "click":
                self.add_action("MOUSE_CLICK", res, insert_idx=insert_idx)
            else:
                self.add_action("MOUSE_MOVE", res, insert_idx=insert_idx)
            return True

    def add_delay(self, insert_idx=None):
        res = ask_delay_dialog()
        if res:
            self.add_action("DELAY", res, insert_idx=insert_idx)
            return True

    def add_keyaction(self, insert_idx=None):
        res = ask_keyaction_dialog()
        if res:
            self.add_action("KEY_ACTION", res, insert_idx=insert_idx)
            return True

    def add_typetext(self, insert_idx=None):
        res = ask_typetext_dialog()
        if res:
            self.add_action("TYPE_TEXT", res, insert_idx=insert_idx)
            return True

    def add_label(self, insert_idx=None):
        label = simpledialog.askstring("Label", "Enter label name:")
        if label:
            self.add_action("LABEL", {"label": label}, insert_idx=insert_idx)
            return True

    def add_goto(self, insert_idx=None):
        labels = [a.params['label'] for a in self.macro if a.action == 'LABEL']
        label = ask_goto_dialog(labels)
        if label:
            self.add_action("GOTO", {"label": label}, insert_idx=insert_idx)
            return True

    def add_wait_for_input(self, insert_idx=None):
        res = ask_wait_for_input_dialog()
        if res:
            self.add_action("WAIT_FOR_INPUT", res, insert_idx=insert_idx)
            return True

    def add_if_key(self, insert_idx=None):
        res = ask_wait_for_input_dialog()
        if res:
            self.add_action("IF_KEY", res, insert_idx=insert_idx)
            return True

    def add_repeat(self, insert_idx=None):
        res = ask_repeat_dialog()
        if res:
            self.add_action("REPEAT", res, insert_idx=insert_idx)
            return True

    def add_end_repeat(self, insert_idx=None):
        self.add_action("END_REPEAT", {}, insert_idx=insert_idx)
        return True

    def on_drag_start(self, event):
        idx = self.action_listbox.nearest(event.y)
        if 0 <= idx < len(self.macro):
            self._dragging = True
            self._drag_start_index = idx

    def on_drag_motion(self, event):
        pass

    def on_drag_drop(self, event):
        if not self._dragging:
            return
        self.push_undo_snapshot()
        target_idx = self.action_listbox.nearest(event.y)
        selected = list(self.action_listbox.curselection())
        if not selected:
            return

        # Remove and store selected steps
        selected_actions = [self.macro[i] for i in selected]
        for i in reversed(selected):
            del self.macro[i]

        # Adjust insert index
        if target_idx > selected[-1]:
            target_idx -= len(selected)

        for i, act in enumerate(selected_actions):
            self.macro.insert(target_idx + i, act)

        self.refresh_listbox()
        for i in range(len(selected_actions)):
            self.action_listbox.selection_set(target_idx + i)

        self._dragging = False
        self._drag_start_index = None


    def remove_step(self):
        selected = self.action_listbox.curselection()
        if selected:
            self.push_undo_snapshot()
            idx = selected[0]
            self.action_listbox.delete(idx)
            del self.macro[idx]

    def copy_steps(self):
        selected = self.action_listbox.curselection()
        if not selected:
            return
        self._clipboard_actions = [self.macro[i] for i in selected]

    def paste_steps(self):
        if not self._clipboard_actions:
            return
        # ✅ Save before modifying
        self.push_undo_snapshot()

        idx = self.action_listbox.curselection()
        insert_idx = idx[-1] + 1 if idx else len(self.macro)
        for action in self._clipboard_actions:
            copy = MacroAction(action.action, dict(action.params))
            self.macro.insert(insert_idx, copy)
            insert_idx += 1
        self.refresh_listbox()



    def on_right_click(self, event):
        self.edit_selected_step(event)

    def on_double_click(self, event):
        self.edit_selected_step(event)

    def edit_selected_step(self, event):
        try:
            idx = self.action_listbox.nearest(event.y)
            action = self.macro[idx]
            changed = False
            self.push_undo_snapshot()
            if action.action == "DELAY":
                res = ask_delay_dialog(
                    default_min=action.params.get("min", 1000),
                    default_between=action.params.get("between", False),
                    default_max=action.params.get("max", 2000),
                    # Add the following line:
                    default_wiggle=bool(action.params.get("during_action", {}).get("action") == "WIGGLE_MOUSE")
                )
                if res:
                    # Remove old 'during_action' if not set in new params:
                    if "during_action" in action.params:
                        action.params.pop("during_action")
                    action.params.update(res)
                    changed = True

            elif action.action == "LABEL":
                label = simpledialog.askstring("Edit Label", "Label name:", initialvalue=action.params.get("label", ""))
                if label:
                    action.params["label"] = label
                    changed = True
            elif action.action == "GOTO":
                labels = [a.params['label'] for a in self.macro if a.action == 'LABEL']
                label = ask_goto_dialog(labels, default_label=action.params.get("label", ""))
                if label:
                    action.params["label"] = label
                    changed = True
            elif action.action == "KEY_ACTION":
                res = ask_keyaction_dialog(
                    default_key=action.params.get("key", "enter"),
                    default_action=action.params.get("action", "press")
                )
                if res:
                    action.params.update(res)
                    changed = True
            elif action.action == "TYPE_TEXT":
                res = ask_typetext_dialog(
                    default_text=action.params.get("text", ""),
                    default_delay=action.params.get("delay", True),
                    default_delay_ms=action.params.get("delay_ms", 50)
                )
                if res:
                    action.params.update(res)
                    changed = True
            elif action.action in ("MOUSE_CLICK", "MOUSE_MOVE"):
                res = ask_mouse_action_dialog(
                    default_action_type="click" if action.action == "MOUSE_CLICK" else "move",
                    default_action=action.params.get("mouse_action", "left_click"),
                    default_delay=action.params.get("delay", 0),
                    default_between=action.params.get("between", False),
                    default_delay_max=action.params.get("delay_max", 0 if action.action=="MOUSE_CLICK" else 0.35),
                    default_randomize=action.params.get("randomize", False),
                    default_rand_px_x=action.params.get("rand_px_x", 3),
                    default_rand_px_y=action.params.get("rand_px_y", 3),
                    default_x=action.params.get("x", 0),
                    default_y=action.params.get("y", 0),
                    default_mode=action.params.get("mode", "abs"),
                    default_ignore=action.params.get("ignore", False),
                    default_rand_px=action.params.get("rand_px", 0),
                )
                if res:
                    atype = res.pop("action_type")
                    if atype == "move":
                        action.action = "MOUSE_MOVE"
                    else:
                        action.action = "MOUSE_CLICK"
                    action.params.update(res)
                    changed = True
            elif action.action == "IF_IMAGE":
                res = ask_if_image_dialog(
                    default_not_found=action.params.get("not_found", False),
                    existing_image=action.params.get("image_path"),
                    existing_images=action.params.get("image_paths"),
                    default_move_mouse=action.params.get("move_mouse", False),
                    default_move_duration_min=action.params.get("move_duration_min", 0.6),
                    default_move_between=action.params.get("move_between", False),
                    default_move_duration_max=action.params.get("move_duration_max", 1.2),
                    default_similarity=action.params.get("similarity", 80),
                    default_wait_mode=action.params.get("wait_mode", "off")
                )
                if res:
                    action.params.update(res)
                    changed = True
            elif action.action == "FIND_IMAGE":
                res = ask_find_image_dialog(
                    existing_image=action.params.get("image_path"),
                    existing_images=action.params.get("image_paths"),
                    default_move_mouse=action.params.get("move_mouse", True),
                    default_move_duration_min=action.params.get("move_duration_min", 0.6),
                    default_move_between=action.params.get("move_between", False),
                    default_move_duration_max=action.params.get("move_duration_max", 1.2),
                    default_similarity=action.params.get("similarity", 80),
                )
                if res:
                    action.params.update(res)
                    changed = True
            elif action.action == "WAIT_FOR_INPUT":
                res = ask_wait_for_input_dialog(default_key=action.params.get("key", "x"))
                if res:
                    action.params.update(res)
                    changed = True
            elif action.action == "IF_KEY":
                res = ask_wait_for_input_dialog(default_key=action.params.get("key", "x"))
                if res:
                    action.params.update(res)
                    changed = True
            elif action.action == "REPEAT":
                res = ask_repeat_dialog(
                    default_count=action.params.get("count", action.params.get("min", 2)),
                    default_random=action.params.get("random", False),
                    default_max=action.params.get("max", action.params.get("count", 2))
                )
                if res:
                    action.params.update(res)
                    changed = True
            if changed:
                self.refresh_listbox()
        except Exception as e:
            print(f"Edit error: {e}")

    def refresh_listbox(self):
        self.action_listbox.delete(0, tk.END)
        indent = 0
        for a in self.macro:
            if a.action in ("END_IF", "ELSE", "END_REPEAT", "RANDOM_END"):
                indent = max(0, indent - 1)
            label = "    " * indent + str(a)
            self.action_listbox.insert(tk.END, label)
            if a.action in ("IF_IMAGE", "IF_KEY", "ELSE", "RANDOM_START", "REPEAT"):
                indent += 1

    def run_macro_thread(self):
        if self.running_macro:
            return
        self.running_macro = True
        self.should_stop = False
        self.should_pause = False
        self.master.withdraw()
        self.overlay = OverlayControl(self.master, self.stop_macro, self.toggle_pause, debug=self.debug_var.get())
        threading.Thread(target=self.run_macro).start()


    def stop_macro(self):
        self.should_stop = True

        def _cleanup():
            if self.overlay:
                try:
                    self.overlay.destroy()
                except tk.TclError:
                    pass
                self.overlay = None
            try:
                self.master.deiconify()
            except tk.TclError:
                pass

        try:
            self.master.after(0, _cleanup)
        except tk.TclError:
            _cleanup()

    def toggle_pause(self, pause_state):
        self.should_pause = pause_state

    def run_single_action(self, action, check_interrupt=None):
        import pyautogui
        import random
        import time
        import requests

        print("RUNNING SINGLE ACTION:", action.action, action.params)
        wifi_mode = self.wifi_mode_var.get()
        pi_server_url = f"http://{self.pi_ip_var.get()}:8080"
        print("wifi_mode is:", wifi_mode)
        if wifi_mode:
            print("Would send to Pi:", action.action, action.params)

        # --- SERIAL MODE ---
        if getattr(self, "serial_conn", None) and self.serial_conn.is_open:
            if action.action == "KEY_ACTION":
                key = action.params['key']
                act = action.params.get("action", "press")
                cmd = f"KEY {act.upper()} {key}\n"
                self.serial_conn.write(cmd.encode())
            elif action.action == "TYPE_TEXT":
                text = action.params['text']
                delay = action.params.get("delay", True)
                delay_ms = action.params.get("delay_ms", 50)
                if delay:
                    for char in text:
                        cmd = f"KEY PRESS {char}\n"
                        self.serial_conn.write(cmd.encode())
                        time.sleep(delay_ms / 1000)
                else:
                    cmd = f"TYPE {text}\n"
                    self.serial_conn.write(cmd.encode())
            elif action.action == "MOUSE_MOVE":
                x = action.params['x']
                y = action.params['y']
                cmd = f"MOUSE_MOVE {x} {y}\n"
                self.serial_conn.write(cmd.encode())
            elif action.action == "MOUSE_CLICK":
                btn = action.params.get('mouse_action', 'left_click')
                rotations = action.params.get("rotations", 1.0)
                if btn in ("scroll_up", "scroll_down"):
                    wheel = int(rotations * 120)
                    wheel *= 1 if btn == "scroll_up" else -1
                    cmd = f"MOUSE_WHEEL {wheel}\n"
                else:
                    cmd = f"MOUSE_CLICK {btn}\n"
                self.serial_conn.write(cmd.encode())
            if action.action == "DELAY":
                if action.params.get("between"):
                    duration = random.randint(action.params["min"], action.params["max"])
                else:
                    duration = action.params["min"]
                duration_secs = duration / 1000

                during_action = action.params.get("during_action")
                if during_action:
                    print("DEBUG: DURING_ACTION FOUND", during_action)
                    print("DEBUG: wifi_mode", wifi_mode)
                    if wifi_mode and during_action.get("action") == "WIGGLE_MOUSE":
                        px = during_action.get("params", {}).get("range", 8)
                        print(f"DEBUG: Sending wiggle to Pi, duration={duration_secs}, px={px}")
                        self.send_wiggle_to_pi(duration_secs, pi_server_url, px=px)
                    else:
                        print("DEBUG: Running local wiggle (or other action)")
                        action.run_action_during_delay(duration_secs, during_action, check_interrupt)
                else:
                    print("DEBUG: No during_action; sleeping", duration_secs)
                    time.sleep(duration_secs)
            return

        # --- WIFI MODE (PI) ---
        if wifi_mode:
            if action.action == "MOUSE_MOVE":
                params = action.params
                if params.get("ignore", False):
                    return
                mode = params.get("mode", "abs")
                x = params.get("x", 0)
                y = params.get("y", 0)
                rand_px = params.get("rand_px", 0) if params.get("randomize", False) else 0
                move_duration = params.get("delay", 0.15)
                steps = 18

                if rand_px:
                    x += random.randint(-rand_px, rand_px)
                    y += random.randint(-rand_px, rand_px)

                if mode == "offset":
                    payload = {
                        "type": "smooth_move_offset",
                        "dx": x,
                        "dy": y,
                        "duration": move_duration,
                        "steps": steps
                    }
                else:
                    payload = {
                        "type": "smooth_move",
                        "to_x": x,
                        "to_y": y,
                        "duration": move_duration,
                        "steps": steps
                    }
                try:
                    requests.post(f"{pi_server_url}/action", json=payload, timeout=2)
                except Exception as e:
                    print("Failed to send smooth mouse move to Pi:", e)
                return

            elif action.action == "MOUSE_CLICK":
                btn = action.params.get('mouse_action', 'left_click')
                rotations = action.params.get("rotations", 1.0)
                if btn in ("scroll_up", "scroll_down"):
                    wheel = int(rotations * 120)
                    wheel *= 1 if btn == "scroll_up" else -1
                    payload = {"type": "mouse_move", "x": 0, "y": 0, "wheel": wheel, "buttons": 0}
                else:
                    payload = {"type": "click", "button": btn}
                try:
                    requests.post(f"{pi_server_url}/action", json=payload, timeout=2)
                except Exception as e:
                    print("Failed to send click/scroll to Pi:", e)
                delay = action.params.get("delay", 0)
                delay_max = action.params.get("delay_max", delay)
                if action.params.get("between", False):
                    delay = random.randint(delay, delay_max)
                time.sleep(delay / 1000)
                return

            elif action.action == "KEY_ACTION":
                key = action.params['key']
                act = action.params.get("action", "press")
                payload = {
                    "type": "key",
                    "action": act,
                    "key": key
                }
                try:
                    requests.post(f"{pi_server_url}/action", json=payload, timeout=2)
                except Exception as e:
                    print("Failed to send key to Pi:", e)
                return

            elif action.action == "TYPE_TEXT":
                text = action.params['text']
                delay = action.params.get("delay", True)
                delay_ms = action.params.get("delay_ms", 50)
                payload = {
                    "type": "type",
                    "text": text,
                    "delay": delay,
                    "delay_ms": delay_ms
                }
                try:
                    requests.post(f"{pi_server_url}/action", json=payload, timeout=4)
                except Exception as e:
                    print("Failed to send type to Pi:", e)
                return
            elif action.action == "FIND_IMAGE":
                similarity = action.params.get("similarity", 80.0)
                paths = action.params.get("image_paths") or [action.params.get("image_path")]
                loc = find_any_image_on_screen(paths, similarity)
                if loc and action.params.get("move_mouse"):
                    if action.params.get("move_between", False):
                        duration = random.uniform(
                            action.params.get("move_duration_min", 0.6),
                            action.params.get("move_duration_max", 1.2),
                        )
                    else:
                        duration = action.params.get("move_duration_min", 0.6)
                    payload = {
                        "type": "smooth_move",
                        "to_x": loc[0],
                        "to_y": loc[1],
                        "duration": duration,
                        "steps": 18,
                    }
                    try:
                        requests.post(f"{pi_server_url}/action", json=payload, timeout=2)
                    except Exception as e:
                        print("Failed to send smooth move to Pi:", e)
                return

            elif action.action == "DELAY":
                if action.params.get("between"):
                    duration = random.randint(action.params["min"], action.params["max"])
                else:
                    duration = action.params["min"]
                duration_secs = duration / 1000

                during_action = action.params.get("during_action")
                if during_action:
                    if wifi_mode and during_action.get("action") == "WIGGLE_MOUSE":
                        px = during_action.get("params", {}).get("range", 8)
                        self.send_wiggle_to_pi(duration_secs, pi_server_url, px=px)
                    else:
                        action.run_action_during_delay(duration_secs, during_action, check_interrupt)
                else:
                    time.sleep(duration_secs)
                return

        # --- LOCAL MODE (DEFAULT) ---
        if action.action == "MOUSE_CLICK":
            mouse_action = action.params.get("mouse_action", "left_click")
            delay = action.params.get("delay", 0)
            delay_max = action.params.get("delay_max", delay)
            if action.params.get("between", False):
                delay = random.randint(delay, delay_max)
            if action.params.get("randomize"):
                rand_x = action.params.get("rand_px_x", 3)
                rand_y = action.params.get("rand_px_y", 3)
                cur_x, cur_y = pyautogui.position()
                target_x = cur_x + random.randint(-rand_x, rand_x)
                target_y = cur_y + random.randint(-rand_y, rand_y)
                move_time = random.uniform(0.08, 0.25)
                if self.humanize_var.get():
                    human_move_mouse(target_x, target_y, duration=move_time)
                else:
                    pyautogui.moveTo(target_x, target_y, duration=move_time, tween=pyautogui.easeInOutQuad)

            rotations = action.params.get("rotations", 1.0)
            if mouse_action == "left_click":
                pyautogui.click(button="left")
            elif mouse_action == "right_click":
                pyautogui.click(button="right")
            elif mouse_action == "left_down":
                pyautogui.mouseDown(button="left")
            elif mouse_action == "right_down":
                pyautogui.mouseDown(button="right")
            elif mouse_action == "left_up":
                pyautogui.mouseUp(button="left")
            elif mouse_action == "right_up":
                pyautogui.mouseUp(button="right")
            elif mouse_action == "scroll_up":
                pyautogui.scroll(int(120 * rotations))
            elif mouse_action == "scroll_down":
                pyautogui.scroll(int(-120 * rotations))
            elif mouse_action == "middle_click":
                pyautogui.click(button="middle")
            time.sleep(delay / 1000)

        elif action.action == "MOUSE_MOVE":
            params = action.params
            if params.get("ignore", False):
                return
            mode = params.get("mode", "abs")
            x = params.get("x", 0)
            y = params.get("y", 0)
            rand_px = params.get("rand_px", 0) if params.get("randomize", False) else 0
            move_duration = params.get("delay", 0.15)
            if params.get("between", False):
                d_min = params.get("delay", 0.15)
                d_max = params.get("delay_max", 0.35)
                move_duration = random.uniform(d_min, d_max)

            if mode == "abs":
                target_x, target_y = x, y
            elif mode == "rel":
                try:
                    import pygetwindow
                    win = pygetwindow.getActiveWindow()
                    if win is not None:
                        target_x, target_y = win.left + x, win.top + y
                    else:
                        target_x, target_y = x, y
                except Exception:
                    target_x, target_y = x, y
            elif mode == "offset":
                cur = pyautogui.position()
                target_x, target_y = cur.x + x, cur.y + y
            else:
                cur = pyautogui.position()
                target_x, target_y = cur.x, cur.y

            if rand_px > 0:
                target_x += random.randint(-rand_px, rand_px)
                target_y += random.randint(-rand_px, rand_px)

            if self.humanize_var.get():
                human_move_mouse(target_x, target_y, duration=move_duration, steps=18, wiggle_px=8)
            else:
                pyautogui.moveTo(target_x, target_y, duration=move_duration, tween=pyautogui.easeInOutQuad)

        elif action.action == "KEY_ACTION":
            key = action.params['key']
            act = action.params.get("action", "press")
            if act == "press":
                pyautogui.press(key)
            elif act == "down":
                pyautogui.keyDown(key)
            elif act == "up":
                pyautogui.keyUp(key)

        elif action.action == "DELAY":
            if action.params.get("between"):
                duration = random.randint(action.params["min"], action.params["max"])
            else:
                duration = action.params["min"]
            duration_secs = duration / 1000
            during_action = action.params.get("during_action")
            if during_action:
                action.run_action_during_delay(duration_secs, during_action, check_interrupt)
            else:
                time.sleep(duration_secs)

        elif action.action == "TYPE_TEXT":
            text = action.params['text']
            delay = action.params.get("delay", True)
            delay_ms = action.params.get("delay_ms", 50)
            if delay:
                for char in text:
                    pyautogui.typewrite(char)
                    time.sleep(delay_ms / 1000)
            else:
                pyautogui.typewrite(text)
        elif action.action == "FIND_IMAGE":
            similarity = action.params.get("similarity", 80.0)
            paths = action.params.get("image_paths") or [action.params.get("image_path")]
            loc = find_any_image_on_screen(paths, similarity)
            if loc and action.params.get("move_mouse"):
                if action.params.get("move_between", False):
                    duration = random.uniform(
                        action.params.get("move_duration_min", 0.6),
                        action.params.get("move_duration_max", 1.2),
                    )
                else:
                    duration = action.params.get("move_duration_min", 0.6)
                if self.humanize_var.get():
                    human_move_mouse(loc[0], loc[1], duration=duration)
                else:
                    pyautogui.moveTo(loc[0], loc[1], duration=duration, tween=pyautogui.easeInOutQuad)

    def execute_action_sequence(self, actions, check_interrupt):
        import pyautogui, random, keyboard
        i = 0
        stack = []
        while i < len(actions):
            a = actions[i]
            if a.action == "IF_IMAGE" or a.action == "IF_KEY":
                # Simplified IF handling used for RANDOM blocks
                cond_met = False
                if a.action == "IF_KEY":
                    key_to_check = a.params['key']
                    cond_met = keyboard.is_pressed(key_to_check)
                else:
                    similarity = a.params.get("similarity", 80.0)
                    loc = find_image_on_screen(a.params['image_path'], similarity)
                    cond_met = loc is not None
                    if a.params.get("not_found", False):
                        cond_met = not cond_met
                    if cond_met and a.params.get("move_mouse") and loc:
                        dur = a.params.get("move_duration_min", 0.6)
                        if a.params.get("move_between", False):
                            dur = random.uniform(
                                a.params.get("move_duration_min", 0.6),
                                a.params.get("move_duration_max", 1.2),
                            )
                        pyautogui.moveTo(loc[0], loc[1], duration=dur, tween=pyautogui.easeInOutQuad)
                if cond_met:
                    stack.append(True)
                else:
                    depth = 1
                    j = i + 1
                    found = False
                    while j < len(actions):
                        if actions[j].action in ("IF_IMAGE", "IF_KEY"):
                            depth += 1
                        elif actions[j].action == "END_IF":
                            depth -= 1
                            if depth == 0:
                                i = j
                                found = True
                                break
                        elif actions[j].action == "ELSE" and depth == 1:
                            i = j
                            found = True
                            break
                        j += 1
                    if not found:
                        break
            elif a.action == "ELSE":
                depth = 1
                j = i + 1
                while j < len(actions):
                    if actions[j].action in ("IF_IMAGE", "IF_KEY"):
                        depth += 1
                    elif actions[j].action == "END_IF":
                        depth -= 1
                        if depth == 0:
                            i = j
                            break
                    j += 1
            elif a.action == "END_IF":
                pass
            else:
                self.run_single_action(a, check_interrupt=check_interrupt)
            i += 1



    def run_macro(self):
        import pyautogui
        import random
        import numpy as np
        import cv2
        try:
            def check_interrupt():
                if self.should_stop:
                    raise Exception("Macro Stopped")
                while self.should_pause:
                    time.sleep(0.1)
                    if self.should_stop:
                        raise Exception("Macro Stopped")
            keyboard.on_press_key("esc", lambda e: self.stop_macro(), suppress=False)
            label_map = {}
            for idx, action in enumerate(self.macro):
                if action.action == "LABEL":
                    label_map[action.params['label']] = idx
            i = 0
            stack = []
            repeat_stack = []
            while i < len(self.macro):
                if self.overlay is not None:
                    if self.debug_var.get():
                        step_text = str(self.macro[i])
                        self.safe_overlay_text(step_text)
                    else:
                        self.safe_overlay_text("")
                check_interrupt()
                self.maybe_take_break(check_interrupt)
                action = self.macro[i]
                if action.action == "REPEAT":
                    if action.params.get("random"):
                        mn = action.params.get("min", 1)
                        mx = action.params.get("max", mn)
                        times = random.randint(mn, mx)
                    else:
                        times = action.params.get("count", 1)
                    repeat_stack.append({"start_idx": i+1, "end_idx": None, "count": times, "iter": 0})
                    i += 1
                    continue
                elif action.action == "END_REPEAT":
                    if repeat_stack:
                        top = repeat_stack[-1]
                        if top["end_idx"] is None:
                            top["end_idx"] = i
                        top["iter"] += 1
                        if top["iter"] < top["count"]:
                            i = top["start_idx"]
                            continue
                        else:
                            repeat_stack.pop()
                    i += 1
                    continue
                if action.action == "RANDOM_START":
                    block = []
                    idx2 = i + 1
                    depth = 0
                    while idx2 < len(self.macro):
                        if self.macro[idx2].action == "RANDOM_END" and depth == 0:
                            break
                        block.append(self.macro[idx2])
                        if self.macro[idx2].action == "RANDOM_START":
                            depth += 1
                        elif self.macro[idx2].action == "RANDOM_END":
                            depth -= 1
                        idx2 += 1
                    groups = []
                    j = 0
                    while j < len(block):
                        a = block[j]
                        if a.action in ("IF_IMAGE", "IF_KEY"):
                            group = [a]
                            d = 1
                            j += 1
                            while j < len(block) and d > 0:
                                group.append(block[j])
                                if block[j].action in ("IF_IMAGE", "IF_KEY"):
                                    d += 1
                                elif block[j].action == "END_IF":
                                    d -= 1
                                j += 1
                            groups.append(group)
                        else:
                            groups.append([a])
                            j += 1
                    if groups:
                        chosen = random.choice(groups)
                        self.execute_action_sequence(chosen, check_interrupt)
                    i = idx2 + 1
                    continue
                
                
                
                elif action.action == "RANDOM_END":
                    pass
                elif action.action == "IF_IMAGE":
                    similarity = action.params.get("similarity", 80.0)
                    wait_mode = action.params.get("wait_mode", "off")
                    invert = action.params.get("not_found", False)
                    loc = None
                    paths = action.params.get("image_paths") or [action.params.get("image_path")]
                    if wait_mode == "wait for image":
                        while True:
                            check_interrupt()
                            loc = find_any_image_on_screen(paths, similarity)
                            found = (loc is not None)
                            if found != invert:
                                break
                            time.sleep(0.25)
                        match = True
                    elif wait_mode == "wait until not found":
                        while True:
                            check_interrupt()
                            loc = find_any_image_on_screen(paths, similarity)
                            found = (loc is not None)
                            if found == invert:
                                break
                            time.sleep(0.25)
                        match = True
                    else:
                        loc = find_any_image_on_screen(paths, similarity)
                        match = (loc is not None)
                        if invert:
                            match = not match
                    if match:
                        if action.params.get("move_mouse") and loc:
                            if action.params.get("move_between", False):
                                duration = random.uniform(
                                    action.params.get("move_duration_min", 0.6),
                                    action.params.get("move_duration_max", 1.2)
                                )
                            else:
                                duration = action.params.get("move_duration_min", 0.6)
                            if self.humanize_var.get():
                                human_move_mouse(loc[0], loc[1], duration=duration)
                            else:
                                pyautogui.moveTo(loc[0], loc[1], duration=duration, tween=pyautogui.easeInOutQuad)
                        stack.append(("IF", True))
                    else:
                        found_else, idx2 = False, i+1
                        depth = 1
                        while idx2 < len(self.macro):
                            if self.macro[idx2].action in ["IF_IMAGE", "IF_KEY"]:
                                depth += 1
                            elif self.macro[idx2].action == "END_IF":
                                depth -= 1
                                if depth == 0:
                                    i = idx2
                                    found_else = True
                                    break
                            elif self.macro[idx2].action == "ELSE" and depth == 1:
                                i = idx2
                                found_else = True
                                break
                            idx2 += 1
                        if not found_else:
                            break
                elif action.action == "IF_KEY":
                    key_to_check = action.params['key']
                    if keyboard.is_pressed(key_to_check):
                        stack.append(("IF", True))
                    else:
                        found_else, idx2 = False, i+1
                        depth = 1
                        while idx2 < len(self.macro):
                            if self.macro[idx2].action in ["IF_IMAGE", "IF_KEY"]:
                                depth += 1
                            elif self.macro[idx2].action == "END_IF":
                                depth -= 1
                                if depth == 0:
                                    i = idx2
                                    found_else = True
                                    break
                            elif self.macro[idx2].action == "ELSE" and depth == 1:
                                i = idx2
                                found_else = True
                                break
                            idx2 += 1
                        if not found_else:
                            break
                elif action.action == "ELSE":
                    idx2 = i+1
                    depth = 1
                    while idx2 < len(self.macro):
                        if self.macro[idx2].action in ["IF_IMAGE", "IF_KEY"]:
                            depth += 1
                        elif self.macro[idx2].action == "END_IF":
                            depth -= 1
                            if depth == 0:
                                i = idx2
                                break
                        idx2 += 1
                elif action.action == "END_IF":
                    pass
                elif action.action == "WAIT_FOR_INPUT":
                    wait_key = action.params['key']
                    print(f"Waiting for key '{wait_key}'...")
                    while True:
                        check_interrupt()
                        if keyboard.is_pressed(wait_key):
                            break
                        time.sleep(0.05)
                elif action.action == "MOUSE_CLICK":
                    self.run_single_action(action, check_interrupt=check_interrupt)
                elif action.action == "MOUSE_MOVE":
                    self.run_single_action(action, check_interrupt=check_interrupt)
                elif action.action == "DELAY":
                    self.run_single_action(action, check_interrupt=check_interrupt)

                elif action.action == "KEY_ACTION":
                    key = action.params['key']
                    act = action.params.get("action", "press")
                    if act == "press":
                        pyautogui.press(key)
                    elif act == "down":
                        pyautogui.keyDown(key)
                    elif act == "up":
                        pyautogui.keyUp(key)
                elif action.action == "TYPE_TEXT":
                    text = action.params['text']
                    delay = action.params.get("delay", True)
                    delay_ms = action.params.get("delay_ms", 50)
                    if delay:
                        for char in text:
                            check_interrupt()
                            pyautogui.typewrite(char)
                            time.sleep(delay_ms/1000)
                    else:
                        pyautogui.typewrite(text)
                elif action.action == "LABEL":
                    pass
                elif action.action == "GOTO":
                    label = action.params['label']
                    if label not in label_map:
                        self.master.after(0, lambda l=label: messagebox.showerror("Macro Error", f"GOTO label '{l}' not found."))
                        break
                    i = label_map[label]
                    continue
                i += 1
        except Exception as e:
            print(f"Macro stopped or interrupted: {e}")
        finally:
            self.running_macro = False
            def _cleanup():
                if self.overlay:
                    try:
                        self.overlay.set_step_text("")
                        self.overlay.destroy()
                    except tk.TclError:
                        pass
                    self.overlay = None
                self.master.deiconify()
            self.master.after(0, _cleanup)

    def export_arduino(self):
        from tkinter import filedialog, messagebox
        if not self.macro:
            messagebox.showerror("Export", "No macro steps to export!")
            return
        lines = [
            "// Generated by Python Macro Creator",
            "#include <Keyboard.h>",
            "void setup() {",
            "  delay(2500); // Wait for OS to recognize device",
            "  Keyboard.begin();"
        ]
        # Mapping for supported keys in Keyboard.h
        keymap = {
            "enter": "KEY_RETURN",
            "esc": "KEY_ESC",
            "tab": "KEY_TAB",
            "space": "' '",
            "backspace": "KEY_BACKSPACE",
            "delete": "KEY_DELETE",
            "insert": "KEY_INSERT",
            "up": "KEY_UP_ARROW",
            "down": "KEY_DOWN_ARROW",
            "left": "KEY_LEFT_ARROW",
            "right": "KEY_RIGHT_ARROW",
            "home": "KEY_HOME",
            "end": "KEY_END",
            "pageup": "KEY_PAGE_UP",
            "pagedown": "KEY_PAGE_DOWN",
            "f1": "KEY_F1",
            "f2": "KEY_F2",
            "f3": "KEY_F3",
            "f4": "KEY_F4",
            "f5": "KEY_F5",
            "f6": "KEY_F6",
            "f7": "KEY_F7",
            "f8": "KEY_F8",
            "f9": "KEY_F9",
            "f10": "KEY_F10",
            "f11": "KEY_F11",
            "f12": "KEY_F12"
        }
        # Add single-character keys ('a'...'z', '0'...'9')
        for ch in "abcdefghijklmnopqrstuvwxyz0123456789":
            keymap[ch] = f"'{ch}'"
    
        for action in self.macro:
            if action.action == "KEY_ACTION":
                key = action.params['key'].lower()
                act = action.params.get("action", "press")
                # Use mapped key, else default to printable char
                k = keymap.get(key, f"'{key}'" if len(key) == 1 else f"// Unknown key: {key}")
    
                if "Unknown key" in k:
                    lines.append(k + " // <-- Manual edit may be needed")
                    continue
                
                if act == "press":
                    lines.append(f"  Keyboard.press({k}); delay(30); Keyboard.release({k});")
                elif act == "down":
                    lines.append(f"  Keyboard.press({k});")
                elif act == "up":
                    lines.append(f"  Keyboard.release({k});")
            elif action.action == "DELAY":
                if action.params.get("between"):
                    mn = action.params.get("min", 100)
                    mx = action.params.get("max", 1000)
                    lines.append(f"  delay({mn} + random({mx}-{mn}));")
                else:
                    lines.append(f"  delay({action.params.get('min', 500)});")
            elif action.action == "TYPE_TEXT":
                t = action.params.get("text", "")
                # Escape double quotes for C strings
                t = t.replace('"', r'\"')
                lines.append(f'  Keyboard.print("{t}");')
        lines.append("  Keyboard.end();")
        lines.append("}")
        lines.append("void loop() {}")
        file = filedialog.asksaveasfilename(defaultextension=".ino", filetypes=[("Arduino Sketch","*.ino")])
        if file:
            with open(file, "w") as f:
                f.write("\n".join(lines))
            messagebox.showinfo("Export", "Arduino code exported!")
    
    def on_close(self):
        if self.running_macro:
            if not messagebox.askokcancel("Quit", "A macro is running. Do you really want to quit?"):
                return
        self.master.destroy()

    def new_macro(self):
        if self.running_macro:
            messagebox.showwarning("Cannot Clear", "Stop the running macro before creating a new one.")
            return

        if self.macro:
            confirm = messagebox.askyesno("New Macro", "Are you sure you want to clear the current macro?")
            if not confirm:
                return
            self.push_undo_snapshot()

        self.macro = []
        self.refresh_listbox()


    def load_macro(self):
        from tkinter import filedialog, messagebox
    
        file_path = filedialog.askopenfilename(filetypes=[("Macro files", "*.zip;*.json")])
        if not file_path:
            return
    
        try:
            macro_list = []
    
            if file_path.lower().endswith(".zip"):
                with tempfile.TemporaryDirectory() as temp_dir:
                    with zipfile.ZipFile(file_path, 'r') as zf:
                        zf.extractall(temp_dir)
    
                    json_path = os.path.join(temp_dir, "macro.json")
                    if not os.path.exists(json_path):
                        raise Exception("Missing macro.json in zip file")
    
                    with open(json_path, "r") as f:
                        macro_list = json.load(f)
    
                    # Copy image files from temp to Pictures\MacroSnips
                    snip_dir = os.path.join(os.path.expanduser("~"), "Pictures", "MacroSnips")
                    os.makedirs(snip_dir, exist_ok=True)
    
                    for step in macro_list:
                        if step["action"] in ("IF_IMAGE", "FIND_IMAGE"):
                            img_rel_path = step["params"].get("image_path")
                            if img_rel_path:
                                temp_img_path = os.path.join(temp_dir, img_rel_path)
                                if os.path.exists(temp_img_path):
                                    img_name = os.path.basename(temp_img_path)
                                    final_img_path = os.path.join(snip_dir, img_name)
                                    if os.path.abspath(temp_img_path) != os.path.abspath(final_img_path):
                                        shutil.copy(temp_img_path, final_img_path)
                                    step["params"]["image_path"] = final_img_path
                            img_rel_list = step["params"].get("image_paths")
                            if img_rel_list:
                                new_list = []
                                for rel in img_rel_list:
                                    temp_img_path = os.path.join(temp_dir, rel)
                                    if os.path.exists(temp_img_path):
                                        img_name = os.path.basename(temp_img_path)
                                        final_img_path = os.path.join(snip_dir, img_name)
                                        if os.path.abspath(temp_img_path) != os.path.abspath(final_img_path):
                                            shutil.copy(temp_img_path, final_img_path)
                                        new_list.append(final_img_path)
                                if new_list:
                                    step["params"]["image_paths"] = new_list
                                    step["params"]["image_path"] = new_list[0]
    
            elif file_path.lower().endswith(".json"):
                with open(file_path, "r") as f:
                    macro_list = json.load(f)
    
                # Try resolving image paths to existing files (assumed local)
                for step in macro_list:
                    if step["action"] in ("IF_IMAGE", "FIND_IMAGE"):
                        old_path = step["params"].get("image_path")
                        if old_path and os.path.exists(old_path):
                            # Copy image to MacroSnips
                            snip_dir = os.path.join(os.path.expanduser("~"), "Pictures", "MacroSnips")
                            os.makedirs(snip_dir, exist_ok=True)
                            img_name = os.path.basename(old_path)
                            new_path = os.path.join(snip_dir, img_name)
                            if os.path.exists(old_path):
                                if os.path.abspath(old_path) != os.path.abspath(new_path):
                                    shutil.copy(old_path, new_path)
                                    step["params"]["image_path"] = new_path
                                else:
                                    # File is already in the correct location — no need to copy or update path
                                    step["params"]["image_path"] = old_path
                            else:
                                print(f"[WARNING] Image not found: {old_path}")

                            step["params"]["image_path"] = new_path
                        old_list = step["params"].get("image_paths")
                        if old_list:
                            new_list = []
                            for p in old_list:
                                if os.path.exists(p):
                                    snip_dir = os.path.join(os.path.expanduser("~"), "Pictures", "MacroSnips")
                                    os.makedirs(snip_dir, exist_ok=True)
                                    img_name = os.path.basename(p)
                                    new_p = os.path.join(snip_dir, img_name)
                                    if os.path.abspath(p) != os.path.abspath(new_p):
                                        shutil.copy(p, new_p)
                                    new_list.append(new_p)
                            if new_list:
                                step["params"]["image_paths"] = new_list
                                step["params"]["image_path"] = new_list[0]
    
            else:
                raise Exception("Unsupported file format.")
    
            self.macro = [MacroAction(a['action'], a['params']) for a in macro_list]
            self.refresh_listbox()
    
        except Exception as e:
            messagebox.showerror("Load Error", f"Error loading macro:\n{e}")
    


    def save_macro(self):
        from tkinter import filedialog, messagebox
    
        if not self.macro:
            messagebox.showerror("Save", "No macro steps to save!")
            return
    
        # Ask for .zip file
        zip_path = filedialog.asksaveasfilename(defaultextension=".zip", filetypes=[("Macro Package", "*.zip")])
        if not zip_path:
            return
    
        try:
            # Create temp directory to stage files
            with tempfile.TemporaryDirectory() as temp_dir:
                images_dir = os.path.join(temp_dir, "images")
                os.makedirs(images_dir, exist_ok=True)
    
                macro_list = []
                for action in self.macro:
                    new_params = dict(action.params)  # copy

                    if action.action in ("IF_IMAGE", "FIND_IMAGE"):
                        img_path = new_params.get("image_path")
                        if img_path and os.path.isfile(img_path):
                            img_name = os.path.basename(img_path)
                            dest_path = os.path.join(images_dir, img_name)
                            shutil.copy(img_path, dest_path)
                            new_params["image_path"] = os.path.join("images", img_name)
                        img_list = new_params.get("image_paths")
                        if img_list:
                            new_list = []
                            for p in img_list:
                                if p and os.path.isfile(p):
                                    img_name = os.path.basename(p)
                                    dest_path = os.path.join(images_dir, img_name)
                                    shutil.copy(p, dest_path)
                                    new_list.append(os.path.join("images", img_name))
                            if new_list:
                                new_params["image_paths"] = new_list
                                new_params["image_path"] = new_list[0]
    
                    macro_list.append({"action": action.action, "params": new_params})
    
                # Save JSON
                json_path = os.path.join(temp_dir, "macro.json")
                with open(json_path, "w") as f:
                    json.dump(macro_list, f, indent=2)
    
                # Zip it
                with zipfile.ZipFile(zip_path, 'w') as zf:
                    zf.write(json_path, arcname="macro.json")
                    for root, dirs, files in os.walk(images_dir):
                        for file in files:
                            full_path = os.path.join(root, file)
                            arcname = os.path.relpath(full_path, temp_dir)
                            zf.write(full_path, arcname=arcname)
    
                messagebox.showinfo("Save Macro", "Macro saved as .zip successfully!")
        except Exception as e:
            messagebox.showerror("Save Error", f"Error saving macro:\n{e}")
    

if __name__ == "__main__":
    root = tk.Tk()
    app = MacroRecorderApp(root)
    root.mainloop()
