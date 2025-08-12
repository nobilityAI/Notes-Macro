import threading
import time
import platform
import pyautogui
import tkinter as tk
import subprocess
from tkinter import ttk
from tkinter import messagebox
import pyperclip
import csv
import os

# Optional global hotkey support
try:
    from pynput import keyboard
    PYNPUT_AVAILABLE = True
except Exception:
    PYNPUT_AVAILABLE = False

# Modifier (sanity print)
ctrl = 'command' if platform.system() == 'Darwin' else 'ctrl'
print('Using modifier:', ctrl)


class Macro:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Macro Controller")

        # --- state ---
        self.targets = ["first_note", "return_notes", "bottom_notes", "text_edit"]
        self.csv_file = "positions.csv"
        self.capture_armed = False
        self.selected_target = None

        # live cursor vars
        self.cursor_x_var = tk.StringVar(value="0")
        self.cursor_y_var = tk.StringVar(value="0")

        # per-row UI vars
        self.status_vars = {name: tk.StringVar(value="✖") for name in self.targets}  # ✖ or ✔
        self.coord_vars  = {name: tk.StringVar(value="(None, None)") for name in self.targets}

        # runtime / macro state
        self.stopMacro = False
        self.newNote = True
        self.before = None
        self.macro_thread = None
        self.macro_running = False
        self.esc_listener = None
        self.firstNote = ()
        self.returnNote = ()
        self.bottomNote = ()
        self.textEdit = ()
        # ensure the CSV exists with defaults
        self._ensure_csv_defaults()

        # BUILD UI FIRST (creates label widgets)
        self._build_ui()

        # NOW load values and color labels safely
        self._load_into_vars()

        # bindings + polling (window-focused)
        self.root.bind("<Return>", self._on_return_key)
        self.root.bind("<Escape>", self._on_escape_stop)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._poll_cursor()

        # Optional: initialize some coordinates (from CSV, with fallbacks)
        self.pts = self._load_points_dict()

        # Start global ESC listener if available
        if PYNPUT_AVAILABLE:
            self._start_global_esc()
            self.status_line.set("Idle — Click green circle or Start to run. Press Esc to stop (global).")
        else:
            self.status_line.set("Idle — Click green circle or Start to run. Press Esc to stop (window only).")

    # ---------- UI ----------
    def _build_ui(self):
        pad = {"padx": 10, "pady": 6}
        live_frame = ttk.LabelFrame(self.root, text="Live Cursor")
        live_frame.grid(row=0, column=0, sticky="nsew", **pad)

        ttk.Label(live_frame, text="X:").grid(row=0, column=0, sticky="e")
        ttk.Label(live_frame, textvariable=self.cursor_x_var, width=5, anchor="e").grid(row=0, column=1, sticky="w")
        ttk.Label(live_frame, text="Y:").grid(row=0, column=2, sticky="e")
        ttk.Label(live_frame, textvariable=self.cursor_y_var, width=5, anchor="w").grid(row=0, column=3, sticky="w")

        # Start controls row: green circle + Start button + Esc hint
        controls_row = 1
        self.start_circle = tk.Canvas(live_frame, width=16, height=16, highlightthickness=0)
        self.start_circle.create_oval(2, 2, 14, 14, fill="#22c55e", outline="")
        self.start_circle.grid(row=controls_row, column=0, sticky="w", pady=(4, 0))
        self.start_circle.bind("<Button-1>", lambda e: self._start_macro_thread())

        self.start_btn = ttk.Button(live_frame, text="Start Macro", command=self._start_macro_thread)
        self.start_btn.grid(row=controls_row, column=1, columnspan=2, sticky="ew", pady=(4, 0))

        self.esc_hint = ttk.Label(live_frame, text="Press Esc to STOP")
        self.esc_hint.grid(row=controls_row, column=3, sticky="e", pady=(4, 0))

        ttk.Separator(self.root, orient="horizontal").grid(row=1, column=0, sticky="ew", padx=10, pady=4)

        table = ttk.Frame(self.root)
        table.grid(row=2, column=0, sticky="nsew", **pad)

        # header
        ttk.Label(table, text="Status").grid(row=0, column=0, sticky="w")
        ttk.Label(table, text="Name").grid(row=0, column=1, sticky="w")
        ttk.Label(table, text="Coordinates").grid(row=0, column=2, sticky="w")
        ttk.Label(table, text="Action").grid(row=0, column=3, sticky="w")

        # keep references to the colored labels
        self.status_labels = {}

        # rows
        for r, name in enumerate(self.targets, start=1):
            # status label: use tk.Label for color control
            status_lbl = tk.Label(
                table,
                textvariable=self.status_vars[name],
                width=2,
                fg="red" if self.status_vars[name].get() == "✖" else "green",
                font=("Arial", 12, "bold")
            )
            status_lbl.grid(row=r, column=0, sticky="w")
            self.status_labels[name] = status_lbl  # store widget

            ttk.Label(table, text=name).grid(row=r, column=1, sticky="w")
            ttk.Label(table, textvariable=self.coord_vars[name], width=18).grid(row=r, column=2, sticky="w")
            ttk.Button(table, text="Select", command=lambda n=name: self._select_target(n)).grid(row=r, column=3, sticky="ew")

        # status line
        self.status_line = tk.StringVar(value="Idle — Click green circle or Start to run. Press Esc to stop.")
        ttk.Label(self.root, textvariable=self.status_line).grid(row=3, column=0, sticky="w", padx=10, pady=4)

        self.root.columnconfigure(0, weight=1)

    # ---------- CSV helpers ----------
    def _ensure_csv_defaults(self):
        if os.path.exists(self.csv_file):
            return
        rows = [
            ("first_note", None, None),
            ("return_notes", None, None),
            ("bottom_notes", None, None),
            ("text_edit", None, None),
        ]
        with open(self.csv_file, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["name", "x", "y"])
            w.writerows(rows)

    def _load_points_dict(self):
        pts = {}
        with open(self.csv_file, "r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                # keep as int if possible, else None
                x = None if row["x"] in ("", "None", None) else int(row["x"])
                y = None if row["y"] in ("", "None", None) else int(row["y"])
                pts[row["name"]] = (x, y)
        return pts

    def _save_point(self, name, x, y):
        pts = self._load_points_dict()
        pts[name] = (x, y)
        with open(self.csv_file, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["name", "x", "y"])
            # keep fixed order
            for k in self.targets:
                vx, vy = pts.get(k, (None, None))
                w.writerow([k, vx, vy])

    def _load_into_vars(self):
        pts = self._load_points_dict()
        for name in self.targets:
            x, y = pts.get(name, (None, None))
            if x is None or y is None:
                self.status_vars[name].set("✖")
                self.coord_vars[name].set("(None, None)")
                if name in self.status_labels:
                    self.status_labels[name].config(fg="red")
            else:
                self.status_vars[name].set("✔")
                self.coord_vars[name].set(f"({x}, {y})")
                if name in self.status_labels:
                    self.status_labels[name].config(fg="green")

    # ---------- Cursor polling ----------
    def _poll_cursor(self):
        try:
            x, y = pyautogui.position()
            self.cursor_x_var.set(f"{x:4d}")
            self.cursor_y_var.set(f"{y:4d}")
        except Exception as e:
            self.status_line.set(f"Cursor read failed: {e}")
        self.root.after(50, self._poll_cursor)

    # ---------- Selection + save ----------
    def _select_target(self, name):
        self.selected_target = name
        self.capture_armed = True
        self.status_line.set(f"Selected '{name}'. Move the cursor, then press Enter to save.")

    def _on_return_key(self, event=None):
        if not self.capture_armed or self.selected_target is None:
            return
        # parse live cursor
        try:
            x = int(self.cursor_x_var.get().strip())
            y = int(self.cursor_y_var.get().strip())
        except ValueError:
            self.status_line.set("Invalid cursor values.")
            return

        self._save_point(self.selected_target, x, y)
        self.coord_vars[self.selected_target].set(f"({x}, {y})")
        self.status_vars[self.selected_target].set("✔")
        if self.selected_target in self.status_labels:
            self.status_labels[self.selected_target].config(fg="green")
        self.status_line.set(f"Saved {self.selected_target} = ({x},{y})")
        self.capture_armed = False
        self.selected_target = None

    # ---------- Start/Stop controls ----------
    def _start_macro_thread(self):
        if (self._macro_warmup()):
            if self.macro_running:
                return
            self.stopMacro = False
            self.newNote = True
            self.macro_running = True
            try:
                self.start_btn.config(state="disabled")
            except Exception:
                pass
            self.status_line.set("Macro running… Press Esc to stop.")
            self.macro_thread = threading.Thread(target=self._run_macro_safe, daemon=True)
            self.macro_thread.start()

    def _macro_warmup(self):
        self.pts = self._load_points_dict()
        missing = [name for name, coords in self.pts.items() if None in coords]
        if missing:
            self.status_line.set("Missing: " + ", ".join(missing))
            return False
        else:
            self.firstNote = self.pts["first_note"]
            self.returnNote = self.pts["return_notes"]
            self.bottomNote = self.pts["bottom_notes"]
            self.textEdit = self.pts["text_edit"]
            return True
    def _run_macro_safe(self):
        try:
            self._begin_macro_()
        finally:
            def on_done():
                self.macro_running = False
                try:
                    self.start_btn.config(state="normal")
                except Exception:
                    pass
                if self.stopMacro:
                    self.status_line.set("Macro stopped.")
                else:
                    self.status_line.set("Macro finished.")
            self.root.after(0, on_done)

    def _on_escape_stop(self, event=None):
        self._stop_macro_()
        self.status_line.set("Stop requested (Esc).")

    # ---------- Global ESC (pynput) ----------
    def _start_global_esc(self):
        if not PYNPUT_AVAILABLE:
            return
        # Listener runs in background; calls back into Tk safely via .after
        def on_press(key):
            try:
                if key == keyboard.Key.esc:
                    self.root.after(0, self._on_escape_stop)
            except Exception:
                pass
        self.esc_listener = keyboard.Listener(on_press=on_press)
        self.esc_listener.daemon = True
        self.esc_listener.start()

    # ---------- Macro helpers (AppleScript-based combos) ----------
    def mac_cmd(self, char: str):
        # send Command+<char> via System Events (bypasses PyAutoGUI timing/modifier issues)
        subprocess.run(["osascript", "-e",
                        f'tell application "System Events" to keystroke "{char}" using {{command down}}'])

    def mac_menu(self, app_name: str, menu: str, item: str):
        # invoke exact menu item instead of keystroke
        script = f'''
        tell application "{app_name}" to activate
        tell application "System Events"
            click menu item "{item}" of menu "{menu}" of menu bar 1 of process "{app_name}"
        end tell'''
        subprocess.run(["osascript", "-e", script])

    # ---------- Macro ----------
    def _begin_macro_(self):
        start = True
        while self.newNote:
            if self.stopMacro:
                print("Stopping Macro")
                break

            if start:
                pyautogui.click(self.firstNote)
                start = False
            else:
                pyautogui.doubleClick(self.returnNote)  # focus the note list
                time.sleep(0.05)
                pyautogui.press('down')
                time.sleep(0.05)

            pyautogui.click(self.bottomNote)  # Click on Note Data
            time.sleep(0.05)

            self.before = pyperclip.paste()
            time.sleep(0.05)

            self.mac_cmd('a'); time.sleep(0.05)  # Select All
            self.mac_cmd('c'); time.sleep(0.05)  # Copy

            if not start:
                if not self.newNoteCheck():
                    break

            #Change how it outputs to document
            pyautogui.click(self.textEdit)
            pyautogui.write('"""')
            pyautogui.press('enter')
            self.mac_cmd('v')  # Paste
            pyautogui.press('enter')
            pyautogui.write('"""')
            pyautogui.press('enter')


    # ---------- Macro util ----------
    def newNoteCheck(self):
        self.after = pyperclip.paste()
        return self.before != self.after

    def _stop_macro_(self):
        self.stopMacro = True

    def _on_close(self):
        # stop global listener if running
        try:
            if self.esc_listener is not None:
                self.esc_listener.stop()
        except Exception:
            pass
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    try:
        style = ttk.Style()
        if "vista" in style.theme_names():
            style.theme_use("vista")
    except Exception:
        pass
    app = Macro(root)
    root.mainloop()
