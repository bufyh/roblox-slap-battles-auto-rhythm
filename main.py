import os
import sys
import time
import threading
import ctypes
import winsound
import numpy as np
import cv2
import mss
import customtkinter as ctk
import pydirectinput
import keyboard
import pyautogui

pydirectinput.PAUSE = 0
pydirectinput.FAILSAFE = False

try:
    ctypes.windll.user32.SetProcessDpiAwarenessContext(-4)
    myappid = 'rhythm.client.stealth.1'
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
except:
    pass


def get_path(filename):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, filename)
    return os.path.join(os.path.abspath("."), filename)


ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")


class status_overlay(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.geometry("8x8+20+20")
        self.configure(fg_color="#ffffff")
        self.withdraw()


class rhythmclient(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("rhythm")
        self.geometry("260x580")
        self.resizable(False, False)
        self.configure(fg_color="#000000")

        try:
            self.iconbitmap(get_path("rhythmicon.ico"))
        except:
            pass

        self.running = False
        self.scan_thread = None
        self.is_selecting = False

        self.overlay = status_overlay(self)
        self.target_pos = (972, 856)

        self.colors = {
            "purple": (187, 70, 255),
            "yellow": (255, 192, 67),
            "white": (255, 255, 255)
        }
        self.active_bounds = []

        self.scan_size = 8
        self.delay = 0.0
        self.cooldown = 0.15
        self.action = "m1"

        self.fnt = ("helvetica", 11)
        self.fnt_sm = ("helvetica", 10)

        self.build_ui()
        self.apply_config()

    def build_ui(self):
        ctk.CTkLabel(self, text="rhythm", font=("helvetica", 14), text_color="#555555").pack(pady=(20, 15))

        f_opts = {"fg_color": "#020202", "corner_radius": 0}
        e_opts = {"fg_color": "#0a0a0a", "border_width": 0, "text_color": "#888888", "height": 22, "font": self.fnt}

        p_frame = ctk.CTkFrame(self, **f_opts)
        p_frame.pack(pady=4, padx=15, fill="x")

        ctk.CTkLabel(p_frame, text="x", font=self.fnt_sm, text_color="#333333").grid(row=0, column=0, padx=(12, 4),
                                                                                     pady=8)
        self.entry_x = ctk.CTkEntry(p_frame, width=40, justify="center", **e_opts)
        self.entry_x.insert(0, str(self.target_pos[0]))
        self.entry_x.grid(row=0, column=1, padx=0, pady=8)

        ctk.CTkLabel(p_frame, text="y", font=self.fnt_sm, text_color="#333333").grid(row=0, column=2, padx=(10, 4),
                                                                                     pady=8)
        self.entry_y = ctk.CTkEntry(p_frame, width=40, justify="center", **e_opts)
        self.entry_y.insert(0, str(self.target_pos[1]))
        self.entry_y.grid(row=0, column=3, padx=0, pady=8)

        self.btn_select = ctk.CTkButton(p_frame, text="pick", font=self.fnt_sm, fg_color="#0a0a0a",
                                        hover_color="#141414",
                                        text_color="#555555", width=42, height=22, corner_radius=0,
                                        command=self.start_manual_selection)
        self.btn_select.grid(row=0, column=4, padx=(8, 0), pady=8)

        c_frame = ctk.CTkFrame(self, **f_opts)
        c_frame.pack(pady=4, padx=15, fill="x")

        chk_opts = {"checkbox_width": 14, "checkbox_height": 14, "border_width": 1, "font": self.fnt_sm,
                    "text_color": "#555555"}

        self.chk_purple = ctk.CTkCheckBox(c_frame, text="purple", fg_color="#bb46ff", hover_color="#9a30d6",
                                          border_color="#1a1a1a", **chk_opts)
        self.chk_purple.pack(pady=(12, 4), padx=20, anchor="w")
        self.chk_purple.select()

        self.chk_yellow = ctk.CTkCheckBox(c_frame, text="yellow", fg_color="#ffc043", hover_color="#d69d2c",
                                          border_color="#1a1a1a", **chk_opts)
        self.chk_yellow.pack(pady=4, padx=20, anchor="w")
        self.chk_yellow.select()

        self.chk_white = ctk.CTkCheckBox(c_frame, text="white", fg_color="#ffffff", hover_color="#cccccc",
                                         border_color="#1a1a1a", **chk_opts)
        self.chk_white.pack(pady=(4, 12), padx=20, anchor="w")
        self.chk_white.select()

        s_frame = ctk.CTkFrame(self, **f_opts)
        s_frame.pack(pady=4, padx=15, fill="x")

        self.entry_delay = self.add_setting(s_frame, "delay", "0", e_opts)
        self.entry_cooldown = self.add_setting(s_frame, "cooldown", "0.15", e_opts)
        self.entry_bind = self.add_setting(s_frame, "action", "m1", e_opts)
        self.entry_toggle = self.add_setting(s_frame, "toggle key", "f2", e_opts)
        self.entry_hide = self.add_setting(s_frame, "hide key", "f3", e_opts)

        ctk.CTkButton(self, text="apply", font=self.fnt, fg_color="#0a0a0a", hover_color="#111111",
                      text_color="#444444", height=28, corner_radius=0, command=self.apply_config).pack(pady=(12, 5),
                                                                                                        padx=15,
                                                                                                        fill="x")

        self.lbl_status = ctk.CTkLabel(self, text="idle", text_color="#222222", font=self.fnt_sm)
        self.lbl_status.pack(pady=2)

    def add_setting(self, parent, label, default, e_opts):
        r = ctk.CTkFrame(parent, fg_color="transparent")
        r.pack(fill="x", padx=15, pady=3)
        ctk.CTkLabel(r, text=label, font=self.fnt_sm, text_color="#444444").pack(side="left")
        e = ctk.CTkEntry(r, width=45, justify="center", **e_opts)
        e.insert(0, default)
        e.pack(side="right")
        return e

    def apply_config(self):
        keyboard.unhook_all()

        self.toggle_key = self.entry_toggle.get().lower().strip() or "f2"
        self.hide_key = self.entry_hide.get().lower().strip() or "f3"

        keyboard.add_hotkey(self.toggle_key, self.switch_state)
        keyboard.add_hotkey(self.hide_key, self.toggle_window)

        try:
            self.delay = float(self.entry_delay.get())
            self.cooldown = float(self.entry_cooldown.get())
            self.target_pos = (int(self.entry_x.get()), int(self.entry_y.get()))
        except:
            pass

        self.action = self.entry_bind.get().lower().strip()
        self.compile_colors()

        self.lbl_status.configure(text="applied", text_color="#555555")
        self.after(800, lambda: self.lbl_status.configure(text="active" if self.running else "idle",
                                                          text_color="#777777" if self.running else "#222222"))

    def compile_colors(self):
        self.active_bounds = []
        tol = int(255 * 0.08)

        active = []
        if self.chk_purple.get(): active.append(self.colors["purple"])
        if self.chk_yellow.get(): active.append(self.colors["yellow"])
        if self.chk_white.get(): active.append(self.colors["white"])

        for c in active:
            bgr = np.array([c[2], c[1], c[0]], dtype=np.int16)
            lower = np.clip(bgr - tol, 0, 255).astype(np.uint8)
            upper = np.clip(bgr + tol, 0, 255).astype(np.uint8)
            self.active_bounds.append((lower, upper))

    def toggle_window(self):
        if self.winfo_viewable():
            self.withdraw()
            threading.Thread(target=winsound.Beep, args=(400, 80), daemon=True).start()
        else:
            self.deiconify()
            self.lift()
            self.focus_force()
            threading.Thread(target=winsound.Beep, args=(600, 80), daemon=True).start()

    def start_manual_selection(self):
        if self.is_selecting:
            return
        self.is_selecting = True

        was_visible = self.winfo_viewable()
        if was_visible:
            self.withdraw()

        self.lbl_status.configure(text="click anywhere...", text_color="#777777")
        threading.Thread(target=winsound.Beep, args=(650, 60), daemon=True).start()

        def monitor_click():
            import ctypes
            while self.is_selecting:
                if ctypes.windll.user32.GetAsyncKeyState(0x01) & 0x8000:
                    while ctypes.windll.user32.GetAsyncKeyState(0x01) & 0x8000:
                        time.sleep(0.01)

                    x, y = pyautogui.position()
                    self.after(0, lambda: self.finish_selection(x, y, was_visible))
                    break
                time.sleep(0.01)

        threading.Thread(target=monitor_click, daemon=True).start()

    def finish_selection(self, x, y, was_visible):
        self.is_selecting = False
        self.entry_x.delete(0, 'end')
        self.entry_x.insert(0, str(x))
        self.entry_y.delete(0, 'end')
        self.entry_y.insert(0, str(y))
        self.target_pos = (x, y)

        if was_visible:
            self.deiconify()
            self.lift()
            self.focus_force()

        threading.Thread(target=winsound.Beep, args=(880, 80), daemon=True).start()
        self.lbl_status.configure(text="idle", text_color="#222222")

    def switch_state(self):
        if self.running:
            self.running = False
            self.overlay.withdraw()
            self.lbl_status.configure(text="idle", text_color="#222222")
            threading.Thread(target=winsound.Beep, args=(500, 100), daemon=True).start()
        else:
            if self.scan_thread and self.scan_thread.is_alive(): return
            self.running = True
            self.overlay.deiconify()
            self.lbl_status.configure(text="active", text_color="#777777")
            threading.Thread(target=winsound.Beep, args=(900, 100), daemon=True).start()
            self.scan_thread = threading.Thread(target=self.scan_loop, daemon=True)
            self.scan_thread.start()

    def do_action(self):
        if self.action in ['m1', 'left', 'lmb']:
            pydirectinput.click()
        elif self.action in ['m2', 'right', 'rmb']:
            pydirectinput.click(button='right')
        elif self.action in ['m3', 'middle', 'mmb']:
            pydirectinput.click(button='middle')
        else:
            pydirectinput.press(self.action)

    def scan_loop(self):
        x, y = self.target_pos
        offset = self.scan_size // 2
        area = {"top": y - offset, "left": x - offset, "width": self.scan_size, "height": self.scan_size}

        with mss.MSS() as sct:
            while self.running:
                if not self.active_bounds:
                    time.sleep(0.05)
                    continue

                try:
                    img = np.array(sct.grab(area))[:, :, :3]
                    found = False

                    for lower, upper in self.active_bounds:
                        if np.any(cv2.inRange(img, lower, upper)):
                            found = True
                            break

                    if found:
                        if self.delay > 0: time.sleep(self.delay)
                        self.do_action()
                        time.sleep(self.cooldown)
                    else:
                        time.sleep(0.001)
                except:
                    time.sleep(0.001)


if __name__ == "__main__":
    rhythmclient().mainloop()
