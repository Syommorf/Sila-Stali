import os
import sys
import threading
import time
import webbrowser
from datetime import date, datetime, timedelta
import tkinter as tk
from tkinter import ttk, messagebox

import api as api_mod
import auth_store

BASE_DIR = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))

def _img(name):
    return os.path.join(BASE_DIR, name)

# Версия приложения (совпадает с актуальным релизом)
VERSION = "1.2.24"

# ---- Material colors (as in Android app) ----
BG = "#F5F5F5"
CARD = "#FFFFFF"
BORDER = "#E0E0E0"
PRIMARY = "#2E7D32"
PRIMARY_DARK = "#1B5E20"
ACCENT = "#1565C0"
SECONDARY_DARK = "#0D47A1"
PURPLE = "#6A1B9A"
PURPLE_MID = "#7E57C2"
PURPLE_LIGHT = "#AB47BC"
ORANGE = "#E65100"
DARK_GRAY = "#37474F"
GRAY_BTN = "#455A64"
METAL = "#C9D3DE"
RED = "#C62828"
GOOD_BG = "#E8F5E9"        # светлый зелёный фон для «готово»
WORK_BG = "#FFF9C4"        # светлый жёлтый фон для «взял в работу»
INACTIVE_BG = "#ECEFF1"    # серый фон для деталей, не на вашем этапе
INACTIVE_FG = "#9E9E9E"    # серый текст для неактивных деталей
TEXT = "#333333"
TEXT_SEC = "#666666"
TEXT_HINT = "#999999"
TEXT_WEAK = "#888888"

FONT = "Segoe UI"

ROLE_NAMES = {
    "admin": "Администратор",
    "manager": "Начальник",
    "apprentice": "Ученик гибщика",
    "bender": "Гибщик",
    "senior_bender": "Старший гибщик",
    "laser_cutter": "Лазерщик",
    "fitter": "Слесарь",
    "welder": "Сварщик",
    "storekeeper": "Кладовщик",
}

BLOCK_LASER = "laser"
BLOCK_BENDER = "bender"
BLOCK_FITTER = "fitter"
BLOCK_WELDER = "welder"
BLOCK_STOREKEEPER = "storekeeper"
BLOCK_CHIEF = "chief"
BLOCK_KEYS = [BLOCK_LASER, BLOCK_BENDER, BLOCK_FITTER, BLOCK_WELDER, BLOCK_STOREKEEPER]
CHIEF_BLOCK_KEYS = BLOCK_KEYS + [BLOCK_CHIEF]
BLOCK_NAMES = {
    BLOCK_LASER: "Лазер",
    BLOCK_BENDER: "Гибка",
    BLOCK_FITTER: "Мех. обработка",
    BLOCK_WELDER: "Сварка",
    BLOCK_STOREKEEPER: "Склад",
    BLOCK_CHIEF: "Руководство",
}

ROLES_BY_BLOCK = {
    BLOCK_BENDER: [("apprentice", "Ученик гибщика"), ("bender", "Гибщик"), ("senior_bender", "Старший гибщик")],
    BLOCK_LASER: [("laser_cutter", "Лазерщик")],
    BLOCK_FITTER: [("fitter", "Слесарь")],
    BLOCK_WELDER: [("welder", "Сварщик")],
    BLOCK_STOREKEEPER: [("storekeeper", "Кладовщик")],
    BLOCK_CHIEF: [("manager", "Начальник")],
}


def roles_for_block(block):
    return ROLES_BY_BLOCK.get(block, ROLES_BY_BLOCK[BLOCK_BENDER])


WORKER_ROLE_KEYS = {r for blk in BLOCK_KEYS for r, _ in ROLES_BY_BLOCK[blk]}


def role_name(role):
    return ROLE_NAMES.get(role or "", role or "")


def block_name(b):
    return BLOCK_NAMES.get(b, "Без блока")


# ---- Стадии маршрутов (как в Android-приложении) ----
PROD_STAGE_ORDER = [BLOCK_LASER, BLOCK_BENDER, BLOCK_FITTER, BLOCK_WELDER]

STAGE_NAMES = {
    BLOCK_LASER: "Лазер",
    BLOCK_BENDER: "Гибка",
    BLOCK_FITTER: "Мех. обработка",
    BLOCK_WELDER: "Сварка",
    BLOCK_STOREKEEPER: "Склад",
}

WORKER_BLOCK = {
    "laser_cutter": BLOCK_LASER,
    "apprentice": BLOCK_BENDER,
    "bender": BLOCK_BENDER,
    "senior_bender": BLOCK_BENDER,
    "fitter": BLOCK_FITTER,
    "welder": BLOCK_WELDER,
    "storekeeper": BLOCK_STOREKEEPER,
}


def stage_name(s):
    return STAGE_NAMES.get(s or "", s or "")


def order_stages_line(stages):
    """Строка прогресса по стадиям: «Лазер 3/10 · Гибка 0/10»."""
    stages = stages or {}
    parts = []
    for s in PROD_STAGE_ORDER:
        st = stages.get(s)
        if st and st.get("total"):
            parts.append(f"{stage_name(s)} {st.get('done', 0)}/{st['total']}")
    return " · ".join(parts)


def item_stages_line(item):
    return order_stages_line(item.get("stages"))


def _btn(parent, text, color, command, height=46, fs=14, outlined=False, bold=True):
    bg = CARD if outlined else color
    fg = color if outlined else "#FFFFFF"
    b = tk.Button(
        parent, text=text, bg=bg, fg=fg, activebackground=bg, activeforeground=fg,
        relief="flat", bd=0, font=(FONT, fs, "bold" if bold else "normal"),
        cursor="hand2", command=command, pady=8,
        highlightthickness=1 if outlined else 0,
        highlightbackground=color, highlightcolor=color,
    )
    return b


def _small_btn(parent, text, color, command, fs=12):
    return _btn(parent, text, color, command, height=30, fs=fs, outlined=True)

def _darken(color, pct=0.08):
    try:
        r = int(color[1:3], 16)
        g = int(color[3:5], 16)
        b = int(color[5:7], 16)
        return "#{:02x}{:02x}{:02x}".format(
            int(r * (1 - pct)), int(g * (1 - pct)), int(b * (1 - pct)))
    except Exception:
        return color


def _entry(parent, border_color=PRIMARY, width=28, fs=13):
    e = tk.Entry(
        parent, bg=CARD, fg=TEXT, relief="flat", width=width, font=(FONT, fs),
        highlightthickness=1, highlightbackground=border_color,
        highlightcolor=border_color, insertbackground=TEXT,
    )
    return e


class FieldDialog(tk.Toplevel):
    def __init__(self, parent, title, fields):
        super().__init__(parent)
        self.title(title)
        self.resizable(False, False)
        self.transient(parent)
        self.configure(bg=BG)
        self.grab_set()
        self.result = None
        self.entries = []

        body = tk.Frame(self, bg=BG, padx=18, pady=16)
        body.pack(fill="both", expand=True)
        tk.Label(body, text=title, bg=BG, fg=PRIMARY_DARK,
                 font=(FONT, 14, "bold")).pack(anchor="w", pady=(0, 12))

        for label, value, is_password in fields:
            tk.Label(body, text=label, bg=BG, fg=TEXT,
                     font=(FONT, 11)).pack(anchor="w", pady=(6, 2))
            ent = _entry(body, border_color=PRIMARY, fs=13)
            ent.insert(0, value or "")
            if is_password:
                ent.config(show="*")
            ent.pack(fill="x")
            self.entries.append(ent)

        btns = tk.Frame(body, bg=BG)
        btns.pack(fill="x", pady=(16, 0))
        _btn(btns, "Отмена", DARK_GRAY, self.destroy, height=38, fs=12,
             outlined=True).pack(side="right", padx=4, ipadx=8)
        _btn(btns, "Сохранить", PRIMARY, self._ok, height=38, fs=12).pack(
            side="right", padx=4, ipadx=8)
        self.bind("<Return>", lambda e: self._ok())

    def _ok(self):
        self.result = [e.get() for e in self.entries]
        self.destroy()


class App:
    def __init__(self, root):
        self.root = root
        self.root.configure(bg=BG)
        self.api = api_mod.Api()
        self._busy = False
        self._stack = []
        self._logo_img = None
        self._handled_invites = set()
        self._invite_deferred = {}
        self._invite_dialog = None
        self._invite_current_id = None
        try:
            self._logo_img = tk.PhotoImage(file=_img("logo.png"))
        except Exception:
            pass
        try:
            win_icon = tk.PhotoImage(file=_img("window_icon.png"))
            root.iconphoto(True, win_icon)
        except Exception:
            pass
        self._module_imgs = {}
        self._module_hub_imgs = {}
        self._module_square_imgs = {}
        self._module_grid_imgs = {}
        for m in ("laser", "bender", "mech", "weld", "store", "chief"):
            try:
                self._module_imgs[m] = tk.PhotoImage(file=_img(f"module_{m}.png"))
            except Exception:
                pass
            try:
                self._module_hub_imgs[m] = tk.PhotoImage(file=_img(f"module_{m}_hub.png"))
            except Exception:
                pass
            try:
                self._module_square_imgs[m] = tk.PhotoImage(file=_img(f"module_{m}_square.png"))
            except Exception:
                pass
            try:
                self._module_grid_imgs[m] = tk.PhotoImage(file=_img(f"module_{m}_grid.png"))
            except Exception:
                pass

    def _logo(self, parent, size=None):
        if self._logo_img is None:
            tk.Label(parent, text="\U0001F3ED", bg=BG, font=(FONT, 56)).pack()
            return
        tk.Label(parent, image=self._logo_img, bg=BG).pack()

    # ------------------ helpers ------------------
    def _exec(self, fn, ok=None, timeout=25, on_timeout=None):
        if self._busy:
            return
        self._busy = True
        self.root.config(cursor="watch")
        result_box = []
        err_box = []
        done = threading.Event()

        def worker():
            try:
                result_box.append(fn())
            except Exception as e:
                err_box.append(e)
            finally:
                done.set()

        t = threading.Thread(target=worker, daemon=True)
        t.start()
        deadline = time.monotonic() + timeout
        self._poll_exec(done, result_box, err_box, ok, deadline, on_timeout)

    def _poll_exec(self, done, result_box, err_box, ok, deadline, on_timeout):
        if done.is_set():
            self._busy = False
            self.root.config(cursor="")
            if err_box:
                self._show_api_error(err_box[0])
            elif ok:
                ok(result_box[0])
            return
        if time.monotonic() >= deadline:
            self._busy = False
            self.root.config(cursor="")
            if on_timeout:
                on_timeout()
            else:
                messagebox.showerror(
                    "Ошибка",
                    "Сервер не отвечает (превышено время ожидания).\n"
                    "Проверьте доступ к сети и к сайту https://silastali.su",
                    parent=self.root)
            return
        self._after_exec = self.root.after(200, self._poll_exec,
                                           done, result_box, err_box, ok, deadline, on_timeout)

    def _show_api_error(self, e):
        messagebox.showerror("Ошибка", str(e), parent=self.root)

    def _clear(self):
        if getattr(self, "_poll_after", None):
            try:
                self.root.after_cancel(self._poll_after)
            except Exception:
                pass
            self._poll_after = None
        for w in self.root.winfo_children():
            w.destroy()

    def _schedule_poll(self, cb, ms):
        self._poll_after = self.root.after(ms, cb)

    def _switch(self, builder, *args):
        self._stack.append((builder, args))
        self._clear()
        builder(*args)

    def _back(self):
        if len(self._stack) > 1:
            self._stack.pop()
        builder, args = self._stack[-1]
        self._clear()
        builder(*args)

    def _pick_from_list(self, title, items, initial_idx=0):
        idx = initial_idx if 0 <= initial_idx < len(items) else 0
        dlg = tk.Toplevel(self.root)
        dlg.title(title)
        dlg.geometry("340x160")
        dlg.configure(bg=BG)
        dlg.transient(self.root)
        dlg.grab_set()
        result = [None]
        tk.Label(dlg, text=title, bg=BG, fg=TEXT, font=(FONT, 12)).pack(pady=(16, 8))
        var = tk.StringVar(value=items[idx])
        combo = ttk.Combobox(dlg, textvariable=var, values=items, state="readonly",
                             font=(FONT, 12))
        combo.pack(pady=4, padx=16)
        tk.Frame(dlg, bg=BG).pack(pady=4)
        btns = tk.Frame(dlg, bg=BG)
        btns.pack()
        _btn(btns, "Отмена", DARK_GRAY, dlg.destroy, height=36, fs=12, outlined=True).pack(side="right", padx=4, ipadx=8)
        def ok():
            result[0] = items.index(var.get()) if var.get() in items else None
            dlg.destroy()
        _btn(btns, "OK", PRIMARY, ok, height=36, fs=12).pack(side="right", padx=4, ipadx=8)
        self.root.wait_window(dlg)
        return result[0]

    def _go_role(self):
        s = auth_store.get_session()
        role = s.get("role", "bender")
        builders = {
            "admin": self.show_admin,
            "manager": self.show_manager_home,
        }
        builder = builders.get(role)
        if builder is None:
            block = s.get("block")
            if block in (BLOCK_LASER, BLOCK_FITTER, BLOCK_WELDER, BLOCK_STOREKEEPER):
                builder = lambda: self.show_block_orders(block)
            else:
                builder = self.show_bender_home
        self._stack = [(builder, ())]
        self._clear()
        builder()

    def _logout(self):
        auth_store.clear()
        self._stack = []
        self.show_login()

    def _scrollable(self, parent):
        canvas = tk.Canvas(parent, bg=BG, highlightthickness=0)
        sb = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        inner = tk.Frame(canvas, bg=BG)
        inner_id = canvas.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>",
                   lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>",
                    lambda e: canvas.itemconfigure(inner_id, width=e.width))
        canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        def _wheel(event):
            canvas.yview_scroll(int(-event.delta / 120), "units")
        canvas.bind_all("<MouseWheel>", _wheel)
        inner._canvas = canvas
        return inner

    def _toolbar(self, title, color, back=None):
        bar = tk.Frame(self.root, bg=color, height=52)
        bar.pack(fill="x")
        bar.pack_propagate(False)
        if back:
            tk.Button(bar, text="\u2190", bg=color, fg="#FFFFFF",
                      activebackground=color, activeforeground="#FFFFFF",
                      relief="flat", bd=0, font=(FONT, 16), cursor="hand2",
                      command=self._back).pack(side="left", padx=(8, 4), pady=6)
        tk.Label(bar, text=title, bg=color, fg="#FFFFFF",
                 font=(FONT, 17, "bold")).pack(side="left", padx=8, pady=6)
        s = auth_store.get_session()
        if s.get("full_name"):
            tk.Label(bar, text=s["full_name"], bg=color, fg="#FFFFFF",
                     font=(FONT, 12)).pack(side="right", padx=14, pady=6)
        return bar

    def _name_line(self, text, color):
        tk.Label(self.root, text=text, bg=BG, fg=color,
                 font=(FONT, 20, "bold")).pack(anchor="w", padx=20, pady=(14, 4))

    def _card(self, parent):
        c = tk.Frame(parent, bg=CARD, highlightbackground=BORDER,
                     highlightthickness=1, bd=0)
        return c

    def _change_credentials(self):
        parent = self.root
        dlg = FieldDialog(parent, "Сменить логин и пароль", [
            ("Текущий пароль", "", True),
            ("Новый логин", auth_store.get_session().get("username", ""), False),
            ("Новый пароль", "", True),
            ("Повторите пароль", "", True),
        ])
        parent.wait_window(dlg)
        vals = dlg.result
        if not vals:
            return
        cur, new_user, new_pass, confirm = vals
        if not cur.strip():
            messagebox.showwarning("Внимание", "Введите текущий пароль", parent=parent)
            return
        if not new_user.strip():
            messagebox.showwarning("Внимание", "Логин не может быть пустым", parent=parent)
            return
        if new_pass and new_pass != confirm:
            messagebox.showwarning("Внимание", "Пароли не совпадают", parent=parent)
            return
        self._exec(
            lambda: self.api.update_me(cur.strip(), new_user.strip(), new_pass or None),
            ok=lambda _: (auth_store.set_username(new_user.strip()),
                          messagebox.showinfo("Готово", "Логин и пароль обновлены", parent=parent)),
        )

    @staticmethod
    def _today_range():
        d = date.today()
        return d.isoformat(), d.isoformat()

    @staticmethod
    def _week_range():
        today = date.today()
        return (today - timedelta(days=6)).isoformat(), today.isoformat()

    @staticmethod
    def _month_range():
        d = date.today()
        first = d.replace(day=1)
        last = d.replace(day=28) + timedelta(days=4)
        last = last.replace(day=1) - timedelta(days=1)
        return first.isoformat(), last.isoformat()

    @staticmethod
    def _year_range():
        y = date.today().year
        return f"{y}-01-01", f"{y}-12-31"

    @staticmethod
    def _fmt_dt(value):
        try:
            return value[:16].replace("T", " ")
        except Exception:
            return value or ""

    # ------------------ crew invites ------------------
    def _start_invite_poll(self):
        self.root.after(10000, self._invite_tick)

    def _invite_tick(self):
        try:
            self._poll_invites()
        except Exception:
            pass
        self._start_invite_poll()

    def _poll_invites(self):
        if self._invite_dialog is not None:
            return
        s = auth_store.get_session()
        if not s.get("token"):
            return
        if s.get("role") not in ("apprentice", "bender", "senior_bender"):
            return
        if self._busy:
            return
        invites = []
        try:
            invites = self.api.get_crew_invites()
        except Exception:
            return
        now = time.time()
        for inv in invites or []:
            iid = inv.get("id")
            if iid in self._handled_invites:
                continue
            if now < self._invite_deferred.get(iid, 0):
                continue
            self._show_invite(inv)
            return

    def _show_invite(self, inv):
        self._invite_current_id = inv.get("id")
        dlg = tk.Toplevel(self.root)
        self._invite_dialog = dlg
        dlg.title("Приглашение в бригаду")
        dlg.configure(bg=BG)
        dlg.resizable(False, False)
        dlg.transient(self.root)
        dlg.grab_set()
        body = tk.Frame(dlg, bg=BG, padx=20, pady=16)
        body.pack(fill="both", expand=True)
        tk.Label(body, text="Приглашение в бригаду", bg=BG, fg=PRIMARY_DARK,
                 font=(FONT, 15, "bold")).pack(anchor="w", pady=(0, 8))
        tk.Label(body,
                 text=(f"{inv.get('inviter_name') or 'Начальник'} приглашает вас в бригаду\n"
                       f"Заказ {inv.get('order_number') or inv.get('order_id')} · "
                       f"Деталь {inv.get('part_number')} · {inv.get('quantity')} шт"),
                 bg=BG, fg=TEXT, font=(FONT, 12), justify="left").pack(anchor="w")
        btns = tk.Frame(body, bg=BG)
        btns.pack(fill="x", pady=(18, 0))

        def respond(accept):
            iid = inv.get("id")
            self._handled_invites.add(iid)
            self._close_invite()
            self._exec(lambda: self.api.respond_invite(iid, accept),
                       ok=lambda _: self._refresh_after_invite())

        _btn(btns, "Принять", PRIMARY, lambda: respond(True), height=40, fs=13).pack(
            side="right", padx=(6, 0))
        _btn(btns, "Отклонить", RED, lambda: respond(False), height=40, fs=13,
             outlined=True).pack(side="right", padx=(6, 0))
        _btn(btns, "Позже", DARK_GRAY, self._defer_invite, height=40, fs=13,
             outlined=True).pack(side="right", padx=(0, 6))
        dlg.protocol("WM_DELETE_WINDOW", self._defer_invite)

    def _close_invite(self):
        if self._invite_dialog is not None:
            try:
                self._invite_dialog.destroy()
            except Exception:
                pass
        self._invite_dialog = None

    def _defer_invite(self):
        if self._invite_current_id is not None:
            self._invite_deferred[self._invite_current_id] = time.time() + 60
        self._close_invite()

    def _refresh_after_invite(self):
        try:
            if not self._stack:
                return
            builder, args = self._stack[-1]
            if builder in (self.show_order_detail, self.show_orders,
                           self.show_bender_home, self.show_manager_home):
                self._clear()
                builder(*args)
        except Exception:
            pass

    # ------------------ login ------------------
    def show_login(self):
        self._clear()
        self.root.geometry("540x620")
        self.root.title(f"Сила стали — главный вход · v{VERSION}")
        frame = tk.Frame(self.root, bg=BG)
        frame.place(relx=0.5, rely=0.5, anchor="center", relwidth=1.0)

        self._logo(frame)
        tk.Label(frame, text="Сила стали", bg=BG, fg=PRIMARY_DARK,
                 font=(FONT, 24, "bold")).pack(pady=(0, 4))
        tk.Label(frame, text="Металлообрабатывающее производство", bg=BG, fg=TEXT_SEC,
                 font=(FONT, 12)).pack(pady=(0, 6))
        tk.Label(frame, text=f"Версия {VERSION}", bg=BG, fg=TEXT_SEC,
                 font=(FONT, 10)).pack(pady=(0, 18))

        def image_card(parent, text, img, cmd):
            if img is None:
                return _btn(parent, text, GRAY_BTN, cmd, height=64, fs=13)
            b = tk.Button(parent, text=text, image=img, compound="center", bg=BG,
                          fg=METAL, font=(FONT, 12, "bold"), relief="flat", bd=0,
                          cursor="hand2", activebackground=BG, activeforeground="#FFFFFF",
                          highlightthickness=1, highlightbackground="#B0BEC5",
                          highlightcolor="#B0BEC5", command=cmd)
            b.image = img
            return b

        def module_trio(items):
            row = tk.Frame(frame, bg=BG)
            row.pack(fill="x", padx=44, pady=(0, 10))
            for i, (text, img, cmd) in enumerate(items):
                b = image_card(row, text, img, cmd)
                b.pack(side="left", fill="x", expand=True, ipady=6,
                       padx=(0 if i == 0 else 6, 0 if i == len(items) - 1 else 6))

        tk.Label(frame, text="УЧАСТКИ", bg=BG, fg=TEXT_SEC,
                 font=(FONT, 12, "bold")).pack(anchor="w", padx=54, pady=(0, 8))

        module_trio([
            ("Руководство", self._module_grid_imgs.get("chief"), self.show_login_chief),
            ("Лазер", self._module_grid_imgs.get("laser"),
             lambda: self.show_login_block(BLOCK_LASER)),
            ("Гибка", self._module_grid_imgs.get("bender"),
             lambda: self.show_login_block(BLOCK_BENDER)),
        ])
        module_trio([
            ("Мех. обработка", self._module_grid_imgs.get("mech"),
             lambda: self.show_login_block(BLOCK_FITTER)),
            ("Сварка", self._module_grid_imgs.get("weld"),
             lambda: self.show_login_block(BLOCK_WELDER)),
            ("Склад", self._module_grid_imgs.get("store"),
             lambda: self.show_login_block(BLOCK_STOREKEEPER)),
        ])

        tk.Frame(frame, height=12, bg=BG).pack()
        _btn(frame, "✕ Закрыть", DARK_GRAY, self.root.destroy, height=40,
             fs=12, outlined=True).pack(fill="x", padx=50)

    def show_module_todo(self, name, img_key):
        self._clear()
        self.root.geometry("660x780")
        self.root.title("Сила стали — в разработке")
        frame = tk.Frame(self.root, bg=BG)
        frame.place(relx=0.5, rely=0.5, anchor="center", relwidth=1.0)

        self._logo(frame)
        tk.Label(frame, text="Участок", bg=BG, fg=TEXT_SEC,
                 font=(FONT, 12, "bold")).pack(pady=(8, 0))
        tk.Label(frame, text=name, bg=BG, fg=PRIMARY_DARK,
                 font=(FONT, 22, "bold")).pack(pady=(2, 8))
        img = self._module_square_imgs.get(img_key)
        if img is not None:
            box = tk.Frame(frame, bg=DARK_GRAY, padx=6, pady=6)
            box.pack(pady=(4, 10))
            tk.Label(box, image=img, bg=DARK_GRAY, bd=0).pack()
        tk.Label(frame, text="Будет работать позже", bg=BG, fg=TEXT,
                 font=(FONT, 16, "bold")).pack(pady=(6, 2))
        tk.Label(frame, text="Модуль появится в следующих версиях приложения", bg=BG,
                 fg=TEXT_SEC, font=(FONT, 12)).pack()
        _btn(frame, "← На главный экран", DARK_GRAY, self.show_login, height=44,
             fs=13, outlined=True).pack(fill="x", padx=70, pady=(26, 8))

    def show_block_orders(self, block):
        self._clear()
        self.root.geometry("880x680")
        name = block_name(block)
        self.root.title(f"Заказы — {name}")
        self._toolbar(f"Заказы: {name}", PRIMARY_DARK, back=True)

        frame = tk.Frame(self.root, bg=BG)
        frame.pack(fill="both", expand=True)
        container = tk.Frame(frame, bg=BG)
        container.pack(fill="both", expand=True)

        hint = tk.Label(container, text="", bg=BG, fg=TEXT,
                        font=(FONT, 12), justify="left", wraplength=760)
        hint.pack(fill="x", padx=24, pady=12)

        if not auth_store.get_session().get("token"):
            hint.configure(
                text="Чтобы видеть заказы блоков, сначала войдите как «Руководство» "
                     "или сотрудник с доступом к участку.")
            _btn(container, "Вход руководителя", PRIMARY,
                 self.show_login_chief, height=44, fs=13,
                 bold=True).pack(pady=(4, 0))
            _btn(container, "← К выбору участка", DARK_GRAY,
                 self.show_login, height=40, fs=12,
                 outlined=True).pack(pady=(10, 0))
            return

        band = tk.Frame(container, bg=BG)
        band.pack(fill="x", padx=24, pady=(0, 6))
        _btn(band, "🔄 Обновить", PRIMARY, None, height=38, fs=12,
             bold=True).pack(side="left")
        tk.Label(band, text=("Заказы в работе · " + name), bg=BG, fg=TEXT_SEC,
                 font=(FONT, 13)).pack(side="left", padx=(18, 0))

        inner = self._scrollable(container)

        def load():
            if getattr(self, "_block_loading", False):
                return
            self._block_loading = True
            try:
                rows = self.api.get_orders("open", block=block)
            except api_mod.ApiError as e:
                text = str(e)
                if "401" in text or "авториз" in text.lower():
                    hint.configure(text="Сессия истекла — войдите заново как «Руководство».")
                else:
                    hint.configure(text=f"Ошибка загрузки: {text}")
                return
            finally:
                self._block_loading = False
            for w in inner.winfo_children():
                w.destroy()

            if not rows:
                tk.Label(inner, text="…нет открытых заказов по участку…", bg=BG,
                         fg=TEXT_SEC, font=(FONT, 12)).pack(pady=40)
                return

            for o in rows:
                card = self._card(inner, PRIMARY_DARK)
                order_percent = self._percent_for_order(o)
                line_top = f"Заказ №{o.get('number') or o.get('id')} · {o.get('name') or ''}".strip()
                if o.get("unit"):
                    line_top += f" · {o['unit']}"
                tk.Label(card, text=line_top, bg=BG, fg=TEXT,
                         font=(FONT, 13, "bold")).pack(anchor="w", pady=(2, 0))
                line_ph = o.get("phase") or ""
                if line_ph:
                    tk.Label(card, text=line_ph, bg=BG, fg=TEXT_SEC,
                             font=(FONT, 11)).pack(anchor="w")
                stages_line = order_stages_line(o.get("stages"))
                if stages_line:
                    tk.Label(card, text=stages_line, bg=BG, fg=TEXT_SEC,
                             font=(FONT, 11)).pack(anchor="w")
                tk.Label(card, text=f"Выполнено: {order_percent}%",
                         bg=BG, fg=PRIMARY_DARK,
                         font=(FONT, 12, "bold")).pack(anchor="w", pady=(2, 4))
                _btn(card, "Открыть заказ", ACCENT,
                     lambda oid=o["id"]: self.show_order_detail(oid),
                     height=36, fs=12, bold=True).pack(fill="x")

        for w in band.winfo_children():
            if isinstance(w, tk.Button):
                w.configure(command=load)
        load()

    def _percent_for_order(self, order):
        """Процент выполнения заказа по стадиям (как в Android)."""
        o_stages = order.get("stages") or {}
        st_total = sum(int(s.get("total", 0) or 0) for s in o_stages.values())
        st_done = sum(int(s.get("done", 0) or 0) for s in o_stages.values())
        if st_total > 0:
            return min(100, int(round(st_done * 100.0 / st_total)))
        items = order.get("items") or []
        total = 0
        done = 0
        for it in items:
            for s in (it.get("stages") or {}).values():
                total += int(s.get("total", 0) or 0)
                done += int(s.get("done", 0) or 0)
        if total > 0:
            return min(100, int(round(done * 100.0 / total)))
        b_total = int(order.get("total_bend_quantity") or sum(int(it.get("quantity") or 0) for it in items))
        b_done = int(order.get("done_bend_quantity") or 0)
        if b_done <= 0 and items:
            for it in items:
                for c in it.get("completions") or []:
                    if (c.get("stage") or "bender") == "bender":
                        b_done += int(c.get("quantity") or 0)
        if b_total > 0:
            return min(100, int(round(b_done * 100.0 / b_total)))
        return 0

    def _order_stages_agg(self, items):
        agg = {}
        for it in items:
            for k, s in (it.get("stages") or {}).items():
                if k not in agg:
                    agg[k] = {"total": 0, "done": 0, "full": True}
                agg[k]["total"] += int(s.get("total", 0) or 0)
                agg[k]["done"] += int(s.get("done", 0) or 0)
            for k in agg:
                agg[k]["full"] = agg[k]["done"] >= agg[k]["total"]
        return agg

    def _stages_line_from_items(self, items):
        return order_stages_line(self._order_stages_agg(items))

    def _pending_stages(self, item):
        out = []
        for k, s in (item.get("stages") or {}).items():
            if (s.get("done", 0) or 0) < (s.get("total", 0) or 0):
                out.append(k)
        return out

    def show_login_chief(self):
        self._clear()
        self.root.geometry("440x560")
        self.root.title("Сила стали — вход руководителя")
        frame = tk.Frame(self.root, bg=BG)
        frame.place(relx=0.5, rely=0.5, anchor="center", relwidth=1.0)

        self._logo(frame)
        tk.Label(frame, text="Руководство", bg=BG, fg=PRIMARY_DARK,
                 font=(FONT, 22, "bold")).pack(pady=(0, 24))
        tk.Label(frame, text="Пароль", bg=BG, fg=TEXT, font=(FONT, 11)).pack(anchor="w", padx=60)
        e_pass = _entry(frame, PRIMARY, 30)
        e_pass.config(show="*")
        e_pass.pack(fill="x", padx=60, pady=(2, 6))
        tk.Label(frame, text="Логин вводить не нужно", bg=BG, fg=TEXT_SEC,
                 font=(FONT, 10)).pack(anchor="w", padx=60, pady=(0, 20))

        def do_login():
            p = e_pass.get()
            if not p:
                messagebox.showwarning("Внимание", "Введите пароль", parent=self.root)
                return
            self._exec(lambda: self.api.login_chief(p), ok=self._on_login_ok)

        _btn(frame, "Войти", PRIMARY, do_login, height=52, fs=16,
             bold=True).pack(fill="x", padx=60, ipady=4)
        tk.Frame(frame, height=12, bg=BG).pack()
        _btn(frame, "← Назад", DARK_GRAY, self.show_login, height=40,
             fs=12, outlined=True).pack(fill="x", padx=60)
        self.root.bind("<Return>", lambda e: do_login())
        e_pass.focus_set()

    def show_login_block(self, block):
        self._clear()
        self.root.geometry("460x640")
        self.root.title("Сила стали — вход")
        frame = tk.Frame(self.root, bg=BG)
        frame.place(relx=0.5, rely=0.5, anchor="center", relwidth=1.0)

        self._logo(frame)
        tk.Label(frame, text=block_name(block), bg=BG, fg=ACCENT,
                 font=(FONT, 22, "bold")).pack(pady=(0, 24))

        tk.Label(frame, text="Выберите себя из списка", bg=BG, fg=TEXT,
                 font=(FONT, 11)).pack(anchor="w", padx=50)
        var = tk.StringVar()
        combo = ttk.Combobox(frame, textvariable=var, state="readonly",
                             font=(FONT, 13))
        combo.pack(fill="x", padx=50, pady=(2, 4))
        _btn(frame, "🔄 Обновить список", DARK_GRAY, lambda: reload_emps(),
             height=30, fs=11, outlined=True).pack(fill="x", padx=50, ipady=2)
        emps = []

        def reload_emps():
            nonlocal emps
            try:
                data = self.api.get_employees(block=block)
            except Exception:
                data = []
            emps = data or []
            labels = [f"{e.get('full_name')} — {role_name(e.get('role'))}" for e in emps]
            combo.configure(values=labels)
            if labels:
                var.set(labels[0])
            else:
                var.set("")

        tk.Label(frame, text="Пароль", bg=BG, fg=TEXT,
                 font=(FONT, 11)).pack(anchor="w", padx=50, pady=(10, 2))
        e_pass = _entry(frame, ACCENT, 30)
        e_pass.config(show="*")
        e_pass.pack(fill="x", padx=50, pady=(2, 24))

        def do_login():
            sel = var.get()
            if not sel:
                messagebox.showwarning("Внимание", "Выберите сотрудника", parent=self.root)
                return
            emp = next((e for e in emps
                        if f"{e.get('full_name')} — {role_name(e.get('role'))}" == sel), None)
            if emp is None:
                messagebox.showwarning("Внимание", "Сотрудник не найден", parent=self.root)
                return
            p = e_pass.get()
            if not p:
                messagebox.showwarning("Внимание", "Введите пароль", parent=self.root)
                return
            self._exec(lambda: self.api.login(emp["username"], p), ok=self._on_login_ok)

        _btn(frame, "Войти", ACCENT, do_login, height=52, fs=16).pack(fill="x", padx=50, ipady=4)
        tk.Frame(frame, height=12, bg=BG).pack()
        _btn(frame, "← Назад", DARK_GRAY, self.show_login, height=40,
             fs=12, outlined=True).pack(fill="x", padx=50)
        self.root.bind("<Return>", lambda e: do_login())
        reload_emps()

    def _on_login_ok(self, r):
        self.api.token = r["access_token"]
        me = self.api.me()
        auth_store.save_login(r["access_token"], r["user_id"], me["username"],
                              r["full_name"], r["role"], block=me.get("block"))
        self._go_role()

    def show_start(self):
        self.show_login()

    # ------------------ ADMIN ------------------
    def show_admin(self):
        self._clear()
        self.root.geometry("980x640")
        self.root.title("Администратор")
        self._toolbar("Администратор", DARK_GRAY)
        self._name_line("Администратор", DARK_GRAY)
        _btn(self.root, "📦 Заказы", "#00695C",
             lambda: self._switch(self.show_orders), height=40, fs=13).pack(
            fill="x", padx=16, pady=(0, 4))
        _btn(self.root, "💬 Чат", DARK_GRAY,
             lambda: self._switch(self.show_chat_list), height=40, fs=13).pack(
            fill="x", padx=16, pady=(0, 4))

        container = tk.Frame(self.root, bg=BG)
        container.pack(fill="both", expand=True, padx=16, pady=(4, 8))
        inner = self._scrollable(container)

        users = []

        def render(ok_data=None):
            nonlocal users
            users = ok_data or []
            for w in inner.winfo_children():
                w.destroy()
            if not users:
                tk.Label(inner, text="Начальников пока нет", bg=BG, fg=TEXT_HINT,
                         font=(FONT, 13)).pack(pady=24)
            else:
                grouped = {}
                for u in users:
                    b = u.get("block") or None
                    grouped.setdefault(b, []).append(u)
                for blk in CHIEF_BLOCK_KEYS + ([None] if None in grouped else []):
                    members = grouped.get(blk) or []
                    if not members:
                        continue
                    tk.Label(inner, text=block_name(blk), bg=BG, fg=ORANGE,
                             font=(FONT, 12, "bold")).pack(anchor="w", padx=2, pady=(10, 2))
                    for u in members:
                        card = self._card(inner)
                        card.pack(fill="x", pady=5, padx=2)
                        head = tk.Frame(card, bg=CARD)
                        head.pack(fill="x", padx=14, pady=(10, 2))
                        tk.Label(head, text=u["full_name"], bg=CARD, fg=TEXT,
                                 font=(FONT, 15, "bold")).pack(side="left")
                        is_manager = u["role"] == "manager"
                        tk.Label(head, text=role_name(u["role"]), bg=CARD, fg=ORANGE,
                                 font=(FONT, 12, "bold")).pack(side="right")
                        body = tk.Frame(card, bg=CARD)
                        body.pack(fill="x", padx=14)
                        tk.Label(body, text="@" + u["username"], bg=CARD, fg=TEXT_SEC,
                                 font=(FONT, 12)).pack(side="left")
                        pw = u.get("password_plain") or "—"
                        tk.Label(body, text="Пароль: " + pw, bg=CARD, fg=PRIMARY,
                                 font=(FONT, 12)).pack(side="right")
                        acts = tk.Frame(card, bg=CARD)
                        acts.pack(fill="x", padx=14, pady=(6, 10))
                        if is_manager:
                            _small_btn(acts, "🗑 Удалить", RED,
                                       lambda u=u: self._admin_delete(u, render)
                                       ).pack(side="right", padx=(6, 0))
                        _small_btn(acts, "✏️ Изменить", DARK_GRAY,
                                   lambda u=u: self._admin_edit(u, render)).pack(side="right")

        def refresh():
            self._exec(lambda: self.api.get_users(), ok=render)

        foot = tk.Frame(self.root, bg=BG)
        foot.pack(fill="x", padx=16, pady=(0, 12))
        row = tk.Frame(foot, bg=BG)
        row.pack(fill="x", pady=6)
        _btn(row, "🔄 Обновить", DARK_GRAY, refresh, height=40, fs=12,
             outlined=True).pack(side="left", expand=True, fill="x", padx=(0, 6))
        _btn(row, "➕ Добавить сотрудника", PRIMARY,
             lambda: self._admin_add(render), height=40, fs=13).pack(
            side="left", expand=True, fill="x", padx=(6, 0))
        _btn(foot, "Выйти", RED, self._logout, height=40, fs=13,
             outlined=True).pack(fill="x", pady=(8, 0))

        refresh()

    def _admin_add(self, render):
        dlg = FieldDialog(self.root, "Новый сотрудник", [
            ("Логин", "", False), ("Пароль", "", True), ("ФИО", "", False)])
        self.root.wait_window(dlg)
        v = dlg.result
        if not v:
            return
        u, p, name = v
        if not u.strip() or not p.strip() or not name.strip():
            messagebox.showwarning("Внимание", "Заполните все поля", parent=self.root)
            return
        block, role = self._pick_block_role(u.get("block"), None)
        if block is None and role is None:
            return
        self._exec(lambda: self.api.create_user(u.strip(), p.strip(), name.strip(), role, block=block),
                   ok=lambda _: (render(),
                                 messagebox.showinfo("Готово", "Сотрудник создан", parent=self.root)))

    def _admin_edit(self, u, render):
        dlg = FieldDialog(self.root, "Логин и пароль: " + u["full_name"], [
            ("Логин", u["username"], False),
            ("Пароль", u.get("password_plain") or "", False),
            ("ФИО", u["full_name"], False),
        ])
        self.root.wait_window(dlg)
        v = dlg.result
        if not v:
            return
        username, password, name = v
        if not username.strip() or not name.strip():
            messagebox.showwarning("Внимание", "Логин и ФИО не могут быть пустыми", parent=self.root)
            return
        block, role = self._pick_block_role(u.get("block"), u.get("role"))
        if block is None and role is None:
            return
        self._exec(
            lambda: self.api.update_user(u["id"], username=username.strip(),
                                         password=password or None, full_name=name.strip(),
                                         role=role, block=block),
            ok=lambda _: (render(), messagebox.showinfo("Готово", "Сохранено", parent=self.root)))

    def _pick_block_role(self, current_block, current_role, keys=None):
        if keys is None:
            keys = CHIEF_BLOCK_KEYS
        block_labels = [block_name(k) for k in keys]
        bi = self._pick_from_list("Блок", block_labels,
                                  keys.index(current_block) if current_block in keys else 0)
        if bi is None:
            return None, None
        block = keys[bi]
        roles = roles_for_block(block)
        ri = self._pick_from_list("Должность", [r[1] for r in roles],
                                  next((i for i, r in enumerate(roles) if r[0] == current_role), 0))
        if ri is None:
            return None, None
        return block, roles[ri][0]

    def _pick_role(self, block, current_role=None):
        roles = roles_for_block(block)
        names = [r[1] for r in roles]
        cur = current_role
        if cur is None or cur not in [r[0] for r in roles]:
            cur = roles[0][0]
        ri = self._pick_from_list(
            "Должность", names,
            next((i for i, r in enumerate(roles) if r[0] == cur), 0))
        if ri is None:
            return None
        return roles[ri][0]

    def _admin_delete(self, u, render):
        if messagebox.askyesno("Удалить", f"Удалить сотрудника {u['full_name']}?",
                               parent=self.root):
            self._exec(lambda: self.api.delete_user(u["id"]), ok=lambda _: render())

    # ------------------ MANAGER ------------------
    def show_manager_home(self):
        self._clear()
        self.root.geometry("560x680")
        self.root.title("Панель руководителя")
        self._toolbar("Панель руководителя", PRIMARY_DARK)
        s = auth_store.get_session()
        self._name_line(s.get("full_name", ""), PRIMARY_DARK)

        body = tk.Frame(self.root, bg=BG)
        body.pack(fill="both", expand=True, padx=24, pady=(12, 8))
        _btn(body, "🛠 Управление работой", "#00695C",
             lambda: self._switch(self.show_work_menu),
             height=58, fs=16, bold=True).pack(fill="x", pady=8, ipady=4)
        _btn(body, "👥 Управление персоналом", ORANGE,
             lambda: self._switch(self.show_staff_menu),
             height=58, fs=16, bold=True).pack(fill="x", pady=8, ipady=4)
        _btn(body, "💬 Чат", DARK_GRAY,
             lambda: self._switch(self.show_chat_list),
             height=48, fs=14).pack(fill="x", pady=8)
        foot = tk.Frame(self.root, bg=BG)
        foot.pack(fill="x", padx=24, pady=(4, 16))
        _btn(foot, "🔑 Сменить логин и пароль", GRAY_BTN,
             self._change_credentials, height=40, fs=12).pack(fill="x")
        _btn(foot, "Выйти", RED, self._logout, height=42, fs=13,
             outlined=True).pack(fill="x", pady=(8, 0))

    def show_work_menu(self):
        self._clear()
        self.root.geometry("560x560")
        self.root.title("Управление работой")
        self._toolbar("Управление работой", "#00695C", back=True)
        body = tk.Frame(self.root, bg=BG)
        body.pack(fill="both", expand=True, padx=24, pady=(18, 8))
        items = [
            ("📥 Загрузить заказ", PRIMARY, lambda: self._load_spec()),
            ("📋 Просмотр заказа", "#00695C",
             lambda: self._switch(self.show_orders)),
            ("📊 Статистика работ", PURPLE,
             lambda: self._switch(self.show_stats)),
            ("📥 Экспорт в Excel", ACCENT,
             lambda: self._switch(self.show_export)),
        ]
        for text, color, cmd in items:
            _btn(body, text, color, cmd, height=52, fs=15).pack(fill="x", pady=8)

    def show_staff_menu(self):
        self._clear()
        self.root.geometry("560x600")
        self.root.title("Управление персоналом")
        self._toolbar("Управление персоналом", ORANGE, back=True)
        body = tk.Frame(self.root, bg=BG)
        body.pack(fill="both", expand=True, padx=24, pady=(18, 8))
        pairs = [
            ("🔬 Лазерщики", BLOCK_LASER, "#1565C0"),
            ("🔧 Гибщики", BLOCK_BENDER, "#00695C"),
            ("🛠️ Слесаря", BLOCK_FITTER, PRIMARY),
            ("🔥 Сварщики", BLOCK_WELDER, "#E65100"),
            ("📦 Кладовщики", BLOCK_STOREKEEPER, PURPLE),
        ]
        for text, block, color in pairs:
            _btn(body, text, color,
                 lambda b=block: self._switch(self.show_employees, b),
                 height=50, fs=15).pack(fill="x", pady=6)

    def show_works(self):
        self._clear()
        self.root.geometry("980x640")
        self.root.title("Все работы")
        self._toolbar("Все работы", ACCENT, back=True)

        filter_bar = tk.Frame(self.root, bg=BG)
        filter_bar.pack(fill="x", padx=16, pady=(10, 4))
        tk.Label(filter_bar, text="От:", bg=BG, fg=TEXT_SEC,
                 font=(FONT, 12)).pack(side="left")
        e_from = _entry(filter_bar, ACCENT, 11)
        e_from.pack(side="left", padx=(4, 12))
        tk.Label(filter_bar, text="До:", bg=BG, fg=TEXT_SEC,
                 font=(FONT, 12)).pack(side="left")
        e_to = _entry(filter_bar, ACCENT, 11)
        e_to.pack(side="left", padx=(4, 12))
        tk.Label(filter_bar, text="Деталь:", bg=BG, fg=TEXT_SEC,
                 font=(FONT, 12)).pack(side="left")
        e_part = _entry(filter_bar, ACCENT, 12)
        e_part.pack(side="left", padx=(4, 12))
        _btn(filter_bar, "Применить", ACCENT, lambda: refresh(), height=32,
             fs=12, outlined=True).pack(side="left", ipadx=8)
        tk.Frame(filter_bar, width=6, bg=BG).pack(side="left")
        _btn(filter_bar, "Сброс", RED, lambda: clear_filters(), height=32,
             fs=12, outlined=True).pack(side="left", ipadx=8)
        tk.Frame(filter_bar, width=6, bg=BG).pack(side="left")
        _btn(filter_bar, "🔄 Обновить", DARK_GRAY, lambda: refresh(), height=32,
             fs=12, outlined=True).pack(side="left", ipadx=8)

        container = tk.Frame(self.root, bg=BG)
        container.pack(fill="both", expand=True, padx=16, pady=(4, 8))
        inner = self._scrollable(container)
        works = []

        def render(ok_data=None):
            nonlocal works
            works = ok_data or []
            for w in inner.winfo_children():
                w.destroy()
            if not works:
                tk.Label(inner, text="Работ пока нет", bg=BG, fg=TEXT_HINT,
                         font=(FONT, 13)).pack(pady=24)
            for w in works:
                card = self._card(inner)
                card.pack(fill="x", pady=5, padx=2)
                head = tk.Frame(card, bg=CARD)
                head.pack(fill="x", padx=14, pady=(10, 0))
                tk.Label(head, text=w["part_number"], bg=CARD, fg=TEXT,
                         font=(FONT, 15, "bold")).pack(side="left")
                tk.Label(head, text=str(w["quantity"]) + " шт", bg=CARD,
                         fg=ACCENT, font=(FONT, 15, "bold")).pack(side="right")
                mid = tk.Frame(card, bg=CARD)
                mid.pack(fill="x", padx=14)
                tk.Label(mid, text=self._fmt_dt(w["start_time"]), bg=CARD,
                         fg=TEXT_SEC, font=(FONT, 12)).pack(side="left")
                dur = w.get("duration_minutes")
                tk.Label(mid, text=f"{dur} мин" if dur else "—",
                         bg=CARD, fg=TEXT_HINT, font=(FONT, 11)).pack(side="right")
                if w.get("note"):
                    tk.Label(card, text=w["note"], bg=CARD, fg=TEXT_WEAK,
                             font=(FONT, 12, "italic")).pack(anchor="w", padx=14)
                tk.Label(card, text="Рабочий: " + w["worker_name"], bg=CARD,
                         fg=TEXT_SEC, font=(FONT, 12)).pack(anchor="w", padx=14)
                acts = tk.Frame(card, bg=CARD)
                acts.pack(fill="x", padx=14, pady=(6, 10))
                _small_btn(acts, "Удалить", RED,
                           lambda w=w: self._delete_work(w, render)).pack(side="right")

        def clear_filters():
            e_from.delete(0, "end")
            e_to.delete(0, "end")
            e_part.delete(0, "end")
            refresh()

        def refresh():
            df = e_from.get().strip() or None
            dt = e_to.get().strip() or None
            pn = e_part.get().strip() or None
            self._exec(lambda: self.api.get_works(df, dt, part_number=pn), ok=render)

        render([])
        refresh()

    def _delete_work(self, w, render):
        if messagebox.askyesno("Удалить работу",
                               "Вы точно хотите удалить работу гибщика?",
                               parent=self.root):
            self._exec(lambda: self.api.delete_work(w["id"]), ok=lambda _: render())

    def show_stats(self):
        self._clear()
        self.root.geometry("720x640")
        self.root.title("Статистика")
        self._toolbar("Статистика", PURPLE, back=True)

        top = tk.Frame(self.root, bg=BG)
        top.pack(fill="x", padx=16, pady=(12, 0))
        specs = [("День", PURPLE, self._today_range, "day", "По рабочим:"),
                 ("Месяц", PURPLE_MID, self._month_range, "day", "Итоги по дням:"),
                 ("Год", PURPLE_LIGHT, self._year_range, "month", "Итоги по месяцам:")]
        for text, color, rng, gb, header in specs:
            _btn(top, text, color, lambda r=rng, g=gb, h=header: render(r, g, h),
                 height=36, fs=12).pack(side="left", expand=True, fill="x",
                                        padx=3, ipady=3)

        summ = self._card(tk.Frame(self.root, bg=BG))
        summ.pack(fill="x", padx=16, pady=(14, 6))
        self._sum_body = {}
        for row, key, fs, col, bold in (
                (0, "total", 18, PRIMARY_DARK, True),
                (1, "works", 16, TEXT, False),
                (2, "extra", 16, TEXT, False)):
            lab = tk.Label(summ, bg=CARD, fg=col, font=(FONT, fs, "bold" if bold else "normal"))
            lab.grid(row=row, column=0, sticky="w", padx=16, pady=2)
            self._sum_body[key] = lab
        tk.Label(summ, text="", bg=CARD, fg=TEXT_SEC,
                 font=(FONT, 12)).grid(row=3, column=0, sticky="w", padx=16, pady=(0, 10))
        self._sum_body["period"] = summ.grid_slaves(row=3, column=0)[0]

        container = tk.Frame(self.root, bg=BG)
        container.pack(fill="both", expand=True, padx=16, pady=(4, 12))
        self._stats_header = tk.Label(container, text="", bg=BG, fg=TEXT,
                                      font=(FONT, 15, "bold"))
        self._stats_header.pack(anchor="w", pady=(4, 2))
        self._stats_inner = self._scrollable(container)

        def render(rng, gb, header):
            df, dt = rng()
            def data():
                ov = self.api.stats_overview(df, dt)
                if gb == "day":
                    rows = self.api.stats_by_worker(df, dt)
                else:
                    rows = self.api.stats_timeline(gb, df, dt)
                order_rows = self.api.order_stats(df, dt)
                return ov, rows, order_rows
            def show(res):
                ov, rows, order_rows = res
                self._sum_body["total"].config(
                    text=f"Всего деталей: {ov['total_quantity']}")
                self._sum_body["works"].config(
                    text=f"Всего работ: {ov['total_works']}    Рабочих: {ov['total_workers']}")
                self._sum_body["extra"].config(
                    text=f"Среднее время: {ov['avg_duration_minutes'] or '—'} мин")
                self._sum_body["period"].config(text=f"Период: {df} — {dt}")
                for w in self._stats_inner.winfo_children():
                    w.destroy()

                self._stats_header.config(text="Гибка по заказам:")
                if not order_rows:
                    tk.Label(self._stats_inner, text="Отметок по заказам в периоде нет",
                             bg=BG, fg=TEXT_HINT, font=(FONT, 13)).pack(pady=(0, 8))
                for r in order_rows:
                    card = self._card(self._stats_inner)
                    card.pack(fill="x", pady=3, padx=2)
                    tk.Label(card, text=r.get("worker_name") or f"Р Р°Р±РѕС‡РёР№ #{r.get('worker_id')}",
                             bg=CARD, fg=PURPLE, font=(FONT, 14, "bold")).pack(anchor="w", padx=14, pady=(8, 0))
                    line = tk.Frame(card, bg=CARD)
                    line.pack(fill="x", padx=14, pady=(2, 8))
                    tk.Label(line, text=f"Согнуто деталей: {r.get('total_bent_quantity', 0)}",
                             bg=CARD, fg=PRIMARY, font=(FONT, 13, "bold")).pack(side="left", padx=(0, 16))
                    tk.Label(line,
                             text=f"Отметок: {r.get('marks', 0)} · Деталей: {r.get('distinct_parts', 0)}",
                             bg=CARD, fg=TEXT, font=(FONT, 13)).pack(side="left")

                tk.Label(self._stats_inner, text=header,
                         bg=BG, fg=TEXT, font=(FONT, 15, "bold")).pack(anchor="w", pady=(8, 2))
                if not rows:
                    tk.Label(self._stats_inner, text="Нет данных", bg=BG,
                             fg=TEXT_HINT, font=(FONT, 13)).pack(pady=16)
                for r in rows:
                    card = self._card(self._stats_inner)
                    card.pack(fill="x", pady=4, padx=2)
                    tk.Frame(card, bg=CARD).pack(fill="x", pady=6)
                    name = r.get("worker_name") or r.get("period")
                    tk.Label(card, text=name, bg=CARD, fg=PURPLE,
                             font=(FONT, 14, "bold")).pack(anchor="w", padx=14)
                    line = tk.Frame(card, bg=CARD)
                    line.pack(fill="x", padx=14, pady=(2, 8))
                    tk.Label(line, text=f"Деталей: {r['total_quantity']}", bg=CARD,
                             fg=PRIMARY, font=(FONT, 13, "bold")).pack(side="left", padx=(0, 16))
                    tk.Label(line, text=f"Работ: {r['total_works']}", bg=CARD,
                             fg=TEXT, font=(FONT, 13)).pack(side="left")
                    if r.get("avg_duration_minutes"):
                        tk.Label(card, text=f"Среднее: {r['avg_duration_minutes']} мин",
                                 bg=CARD, fg=TEXT_SEC, font=(FONT, 12)).pack(anchor="w", padx=14)
                    breaks = r.get("parts_breakdown")
                    if breaks:
                        tk.Label(card, text=" · ".join(f"{k}: {v}" for k, v in breaks.items()),
                                 bg=CARD, fg=TEXT_WEAK, font=("Consolas", 11)).pack(anchor="w", padx=14, pady=(0, 8))

            self._exec(data, ok=show)

        render(self._today_range, "day", "По рабочим:")

    def show_employees(self, block=None):
        self._clear()
        self.root.geometry("760x640")
        title = ("Сотрудники — " + block_name(block)) if block else "Сотрудники"
        self.root.title(title)
        self._toolbar(title, ORANGE, back=True)

        container = tk.Frame(self.root, bg=BG)
        container.pack(fill="both", expand=True, padx=16, pady=(10, 8))
        inner = self._scrollable(container)
        users = []

        def render(ok_data=None):
            nonlocal users
            users = [u for u in (ok_data or [])
                     if block is None or u.get("block") == block]
            for w in inner.winfo_children():
                w.destroy()
            if not users:
                tk.Label(inner, text="Сотрудников пока нет", bg=BG, fg=TEXT_HINT,
                         font=(FONT, 13)).pack(pady=24)
            else:
                grouped = {}
                for u in users:
                    b = u.get("block") or None
                    grouped.setdefault(b, []).append(u)
                blk_list = (BLOCK_KEYS if block is None else [block])
                if None in grouped:
                    blk_list = list(blk_list) + [None]
                for blk in blk_list:
                    members = grouped.get(blk) or []
                    if not members:
                        continue
                    tk.Label(inner, text=block_name(blk), bg=BG, fg=ORANGE,
                             font=(FONT, 12, "bold")).pack(anchor="w", padx=2, pady=(10, 2))
                    for u in members:
                        card = self._card(inner)
                        card.pack(fill="x", pady=5, padx=2)
                        head = tk.Frame(card, bg=CARD)
                        head.pack(fill="x", padx=14, pady=(10, 0))
                        tk.Label(head, text=u["full_name"], bg=CARD, fg=TEXT,
                                 font=(FONT, 15, "bold")).pack(side="left")
                        tk.Label(head, text=role_name(u["role"]), bg=CARD, fg=ORANGE,
                                 font=(FONT, 12, "bold")).pack(side="right")
                        tk.Label(card, text="@" + u["username"], bg=CARD, fg=TEXT_SEC,
                                 font=(FONT, 12)).pack(anchor="w", padx=14)
                        pw = u.get("password_plain")
                        if pw:
                            tk.Label(card, text="Пароль: " + pw, bg=CARD, fg=TEXT_SEC,
                                     font=(FONT, 12)).pack(anchor="w", padx=14)
                        tk.Label(card, text="Блок: " + block_name(u.get("block")), bg=CARD, fg=PRIMARY,
                                 font=(FONT, 12)).pack(anchor="w", padx=14)
                        acts = tk.Frame(card, bg=CARD)
                        acts.pack(fill="x", padx=14, pady=(6, 10))
                        _small_btn(acts, "✕ Удалить", RED,
                                   lambda u=u: self._emp_delete(u, render)).pack(side="right", padx=(6, 0))
                        if pw:
                            _small_btn(acts, "🔑 Пароль", PRIMARY,
                                       lambda u=u: self._emp_password(u, render)).pack(side="right", padx=(6, 0))
                        _small_btn(acts, "✏️ Роль", ORANGE,
                                   lambda u=u: self._emp_role(u, render, locked=block)).pack(side="right")

        def refresh():
            self._exec(lambda: self.api.get_users(), ok=render)

        def add_user():
            dlg = FieldDialog(self.root, "Новый сотрудник", [
                ("Логин", "", False), ("Пароль", "", True), ("ФИО", "", False)])
            self.root.wait_window(dlg)
            v = dlg.result
            if not v:
                return
            u, p, name = v
            if not u.strip() or not p.strip() or not name.strip():
                messagebox.showwarning("Внимание", "Заполните все поля", parent=self.root)
                return
            if block:
                role = self._pick_role(block)
                if role is None:
                    return
                create_block = block
            else:
                create_block, role = self._pick_block_role(None, None, keys=BLOCK_KEYS)
                if create_block is None and role is None:
                    return
            self._exec(lambda: self.api.create_user(
                u.strip(), p.strip(), name.strip(), role, block=create_block),
                ok=lambda _: (refresh(),
                              messagebox.showinfo("Готово", "Сотрудник создан", parent=self.root)))

        foot = tk.Frame(self.root, bg=BG)
        foot.pack(fill="x", padx=16, pady=(0, 12))
        row = tk.Frame(foot, bg=BG)
        row.pack(fill="x", pady=6)
        _btn(row, "🔄 Обновить", DARK_GRAY, refresh, height=40, fs=12,
             outlined=True).pack(side="left", expand=True, fill="x", padx=(0, 6))
        _btn(row, "➕ Добавить", PRIMARY, add_user, height=40, fs=13).pack(
            side="left", expand=True, fill="x", padx=(6, 0))
        refresh()

    def _emp_password(self, u, render):
        cur = u.get("password_plain") or ""
        dlg = FieldDialog(self.root, "Новый пароль", [
            (u["full_name"] + " — новый пароль", cur, True)])
        self.root.wait_window(dlg)
        v = dlg.result
        if not v:
            return
        np = v[0]
        if not np.strip():
            messagebox.showwarning("Внимание", "Пароль не может быть пустым", parent=self.root)
            return
        self._exec(lambda: self.api.update_user(u["id"], password=np.strip()),
                   ok=lambda _: (render(),
                                 messagebox.showinfo("Готово", "Пароль изменён", parent=self.root)))

    def _emp_role(self, u, render, locked=None):
        if locked is not None:
            block = locked
            roles = roles_for_block(block)
            names = [r[1] for r in roles]
            cur = next((r[1] for r in roles if r[0] == u.get("role")), names[0])
            ri = self._pick_from_list("Должность", names, names.index(cur) if cur in names else 0)
            if ri is None:
                return
            new_role = roles[ri][0]
            self._exec(lambda: self.api.update_user(u["id"], role=new_role, block=block),
                       ok=lambda _: render())
            return
        block_labels = [block_name(k) for k in BLOCK_KEYS]
        block_idx = BLOCK_KEYS.index(u.get("block")) if u.get("block") in BLOCK_KEYS else (
            BLOCK_KEYS.index(BLOCK_BENDER) if BLOCK_BENDER in BLOCK_KEYS else 0)
        dlg = tk.Toplevel(self.root)
        dlg.title("Должность и блок")
        dlg.geometry("380x200")
        dlg.configure(bg=BG)
        tk.Label(dlg, text="Сотрудник: " + u["full_name"], bg=BG, fg=TEXT,
                 font=(FONT, 12)).pack(pady=(16, 8))
        tk.Label(dlg, text="Блок", bg=BG, fg=TEXT, font=(FONT, 11)).pack(anchor="w", padx=16)
        var_block = tk.StringVar(value=block_labels[block_idx])
        combo_block = ttk.Combobox(dlg, textvariable=var_block, values=block_labels, state="readonly",
                                   font=(FONT, 12))
        combo_block.pack(pady=4, padx=16, fill="x")
        tk.Label(dlg, text="Должность", bg=BG, fg=TEXT, font=(FONT, 11)).pack(anchor="w", padx=16, pady=(8, 0))
        var_role = tk.StringVar()
        combo_role = ttk.Combobox(dlg, textvariable=var_role, state="readonly", font=(FONT, 12))
        combo_role.pack(pady=4, padx=16, fill="x")

        def reload_roles(*_):
            block = BLOCK_KEYS[block_labels.index(var_block.get())]
            names = [r[1] for r in roles_for_block(block)]
            combo_role.config(values=names)
            if var_role.get() not in names:
                var_role.set(names[0])

        var_block.trace_add("write", reload_roles)
        reload_roles()
        cur_names = [r[1] for r in roles_for_block(BLOCK_KEYS[block_idx])]
        var_role.set(cur_names[0] if u.get("role") not in [r[0] for r in roles_for_block(BLOCK_KEYS[block_idx])]
                     else next(r[1] for r in roles_for_block(BLOCK_KEYS[block_idx]) if r[0] == u.get("role")))

        btns = tk.Frame(dlg, bg=BG)
        btns.pack(pady=(12, 0))
        _btn(btns, "Отмена", DARK_GRAY, dlg.destroy, height=36, fs=12,
             outlined=True).pack(side="right", padx=4, ipadx=8)

        def save():
            new_block = BLOCK_KEYS[block_labels.index(var_block.get())]
            roles = roles_for_block(new_block)
            new_role = roles[[r[1] for r in roles].index(var_role.get())][0]
            self._exec(lambda: self.api.update_user(u["id"], role=new_role, block=new_block),
                       ok=lambda _: render())
            dlg.destroy()

        _btn(btns, "Сохранить", PRIMARY, save, height=36, fs=12).pack(side="right", padx=4, ipadx=8)

    def _emp_delete(self, u, render):
        if messagebox.askyesno("Удалить", f"Удалить {u['full_name']}?", parent=self.root):
            self._exec(lambda: self.api.delete_user(u["id"]), ok=lambda _: render())

    def show_export(self):
        self._clear()
        self.root.geometry("560x420")
        self.root.title("Экспорт в Excel")
        self._toolbar("Экспорт в Excel", PRIMARY, back=True)

        body = tk.Frame(self.root, bg=BG)
        body.place(relx=0.5, rely=0.45, anchor="center", relwidth=0.8)
        df, dt = self._month_range()
        tk.Label(body, text="Экспорт за период", bg=BG, fg=PRIMARY_DARK,
                 font=(FONT, 16, "bold")).pack(anchor="w", pady=(0, 16))
        row = tk.Frame(body, bg=BG)
        row.pack(fill="x", pady=6)
        tk.Label(row, text="От:", bg=BG, fg=TEXT, font=(FONT, 12)).pack(side="left")
        e_from = _entry(row, PRIMARY, 12)
        e_from.insert(0, df)
        e_from.pack(side="left", padx=8, fill="x", expand=True)
        row = tk.Frame(body, bg=BG)
        row.pack(fill="x", pady=6)
        tk.Label(row, text="До:", bg=BG, fg=TEXT, font=(FONT, 12)).pack(side="left")
        e_to = _entry(row, PRIMARY, 12)
        e_to.insert(0, dt)
        e_to.pack(side="left", padx=8, fill="x", expand=True)
        tk.Label(body, text="Файл Excel откроется в браузере", bg=BG, fg=TEXT_SEC,
                 font=(FONT, 11)).pack(anchor="w", pady=(8, 0))

        def download():
            a = e_from.get().strip()
            b = e_to.get().strip()
            webbrowser.open(self.api.export_url(a or None, b or None))

        tk.Frame(body, bg=BG).pack(pady=8)
        _btn(body, "📥 Скачать Excel", PRIMARY, download, height=52, fs=16).pack(fill="x", ipady=4)

    # ------------------ BENDER ------------------
    def show_bender_home(self):
        self._clear()
        self.root.geometry("520x720")
        self.root.title("Моя работа")
        self._toolbar("Моя работа", PRIMARY_DARK)
        s = auth_store.get_session()
        self._name_line(s.get("full_name", ""), PRIMARY_DARK)

        body = tk.Frame(self.root, bg=BG)
        body.pack(fill="both", expand=True, padx=24, pady=(12, 8))
        _btn(body, "➕ Добавить деталь", ACCENT, lambda: self._switch(self.show_add_detail),
             height=62, fs=18).pack(fill="x", pady=8, ipady=6)
        _btn(body, "📦 Заказы на гибку", "#00695C", lambda: self._switch(self.show_orders),
             height=50, fs=15, outlined=True).pack(fill="x", pady=8, ipady=3)
        _btn(body, "📊 Моя статистика", PURPLE, lambda: self._switch(self.show_my_stats),
             height=50, fs=15, outlined=True).pack(fill="x", pady=8, ipady=3)
        _btn(body, "💬 Чат", DARK_GRAY, lambda: self._switch(self.show_chat_list),
             height=50, fs=15, outlined=True).pack(fill="x", pady=8, ipady=3)
        _btn(body, "🔑 Сменить логин и пароль", GRAY_BTN, self._change_credentials,
             height=50, fs=15, outlined=True).pack(fill="x", pady=8, ipady=3)
        foot = tk.Frame(self.root, bg=BG)
        foot.pack(fill="x", padx=24, pady=(4, 16))
        _btn(foot, "Выйти", RED, self._logout, height=42, fs=13,
             outlined=True).pack(fill="x")

    def show_add_detail(self):
        self._clear()
        self.root.geometry("620x580")
        self.root.title("Ввод детали")
        self._toolbar("Ввод детали", ACCENT, back=True)

        body = tk.Frame(self.root, bg=BG)
        body.pack(fill="both", expand=True, padx=40, pady=16)
        now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S").replace("T", " ")

        fields = []

        def add_field(label):
            tk.Label(body, text=label, bg=BG, fg=TEXT,
                     font=(FONT, 11)).pack(anchor="w", pady=(8, 2))
            e = _entry(body, ACCENT, 32, fs=14)
            e.pack(fill="x")
            fields.append(e)
            return e

        e_part = add_field("Номер детали")
        e_qty = add_field("Количество")
        e_note = add_field("Примечание")
        e_start = add_field("Начало (ГГГГ-ММ-ДД ЧЧ:ММ)")
        e_start.insert(0, now)
        e_end = add_field("Окончание (ГГГГ-ММ-ДД ЧЧ:ММ)")
        e_end.insert(0, now)

        def save():
            part = e_part.get().strip()
            qty_s = e_qty.get().strip()
            if not part or not qty_s:
                messagebox.showwarning("Внимание", "Укажите номер детали и количество", parent=self.root)
                return
            try:
                qty = int(qty_s)
            except ValueError:
                messagebox.showwarning("Внимание", "Количество должно быть числом", parent=self.root)
                return
            try:
                start = e_start.get().strip().replace(" ", "T")
                end = e_end.get().strip().replace(" ", "T") or None
            except Exception:
                start = end = now.replace(" ", "T")
            self._exec(
                lambda: self.api.create_work(part, qty, e_note.get().strip(), start, end),
                ok=lambda _: (messagebox.showinfo("Готово", "Работа добавлена", parent=self.root),
                              e_part.delete(0, "end"), e_qty.delete(0, "end"),
                              e_note.delete(0, "end")))

        tk.Frame(body, bg=BG).pack(pady=10)
        _btn(body, "💾 Сохранить", PRIMARY, save, height=52, fs=16).pack(fill="x", ipady=4)

    def _work_card(self, parent, w):
        card = self._card(parent)
        card.pack(fill="x", pady=5, padx=2)
        head = tk.Frame(card, bg=CARD)
        head.pack(fill="x", padx=14, pady=(10, 0))
        tk.Label(head, text=w.get("part_number") or "", bg=CARD, fg=TEXT,
                 font=(FONT, 15, "bold")).pack(side="left")
        tk.Label(head, text=f"{w.get('quantity') or 0} шт", bg=CARD, fg=ACCENT,
                 font=(FONT, 15, "bold")).pack(side="right")
        mid = tk.Frame(card, bg=CARD)
        mid.pack(fill="x", padx=14)
        tk.Label(mid, text=self._fmt_dt(w.get("start_time") or ""), bg=CARD,
                 fg=TEXT_SEC, font=(FONT, 12)).pack(side="left")
        dur = w.get("duration_minutes")
        tk.Label(mid, text=f"{dur} мин" if dur else "—", bg=CARD, fg=TEXT_HINT,
                 font=(FONT, 11)).pack(side="right")
        if w.get("note"):
            tk.Label(card, text=w["note"], bg=CARD, fg=TEXT_WEAK,
                     font=(FONT, 12, "italic")).pack(anchor="w", padx=14, pady=(2, 0))
        tk.Frame(card, bg=CARD).pack(pady=(0, 10))

    def show_my_works(self):
        self._clear()
        self.root.geometry("820x640")
        self.root.title("Мои работы")
        self._toolbar("Мои работы", PRIMARY_DARK, back=True)

        container = tk.Frame(self.root, bg=BG)
        container.pack(fill="both", expand=True, padx=16, pady=(10, 8))
        inner = self._scrollable(container)

        def refresh():
            self._exec(lambda: self.api.get_my_works(),
                       ok=lambda rows: self._render_my_works(inner, rows))

        band = tk.Frame(self.root, bg=BG)
        band.pack(fill="x", padx=16, pady=(0, 12))
        _btn(band, "🔄 Обновить", PRIMARY, refresh, height=40, fs=13,
             outlined=True).pack(fill="x")
        refresh()

    def _render_my_works(self, inner, rows):
        for w in inner.winfo_children():
            w.destroy()
        if not rows:
            tk.Label(inner, text="Работ пока нет", bg=BG, fg=TEXT_HINT,
                     font=(FONT, 13)).pack(pady=24)
        for w in rows:
            self._work_card(inner, w)

    def show_my_stats(self):
        self._clear()
        self.root.geometry("720x620")
        self.root.title("Моя статистика")
        self._toolbar("Моя статистика", PRIMARY_DARK, back=True)

        top = tk.Frame(self.root, bg=BG)
        top.pack(fill="x", padx=16, pady=(12, 0))
        specs = [("Сегодня", self._today_range, "day"),
                 ("Неделя", self._week_range, "day"),
                 ("Месяц", self._month_range, "day"),
                 ("Год", self._year_range, "month")]
        for text, rng, gb in specs:
            _btn(top, text, PRIMARY, lambda r=rng, g=gb: render(r, g),
                 height=36, fs=12).pack(side="left", expand=True, fill="x", padx=3, ipady=3)

        summ = tk.Frame(self.root, bg=BG)
        summ.pack(fill="x", padx=16, pady=(14, 2))
        l_total = tk.Label(summ, text="", bg=BG, fg=PRIMARY_DARK,
                           font=(FONT, 18, "bold"))
        l_total.pack(anchor="w")
        l_period = tk.Label(summ, text="", bg=BG, fg=TEXT_SEC, font=(FONT, 12))
        l_period.pack(anchor="w")
        lab_extra = tk.Label(summ, text="", bg=BG, fg=TEXT, font=(FONT, 16))
        lab_extra.pack(anchor="w")
        lab_orders = tk.Label(summ, text="", bg=BG, fg=PURPLE, font=(FONT, 16, "bold"))
        lab_orders.pack(anchor="w")

        header = tk.Label(self.root, text="Итоги по дням:", bg=BG, fg=ORANGE,
                          font=(FONT, 14, "bold"))
        header.pack(anchor="w", padx=16, pady=(6, 2))

        container = tk.Frame(self.root, bg=BG)
        container.pack(fill="both", expand=True, padx=16, pady=(0, 12))
        inner = self._scrollable(container)

        def render(rng, gb):
            df, dt = rng()
            self._exec(
                lambda: (self.api.stats_my(df, dt, gb), self.api.order_stats_my(df, dt)),
                ok=lambda res: self._render_my_stats(inner, res[0], res[1], df, dt,
                                                     l_total, l_period, lab_extra, lab_orders),
            )

        render(self._today_range, "day")

    def _render_my_stats(self, inner, st, order, df, dt, l_total, l_period, lab_extra, lab_orders):
        l_total.config(text=f"Всего деталей: {st['total_quantity']}")
        l_period.config(text=f"Период: {df} — {dt}")
        lab_extra.config(text=f"Всего работ: {st['total_works']}    "
                              f"Среднее время: {st['avg_duration_minutes'] or '—'} мин")
        lab_orders.config(text=f"Гибка по заказам: {order.get('total_bent_quantity', 0)} РґРµС‚. В· "
                               f"{order.get('marks', 0)} отм. · {order.get('distinct_parts', 0)} поз.")
        for w in inner.winfo_children():
            w.destroy()
        if not st.get("periods"):
            tk.Label(inner, text="Нет данных", bg=BG, fg=TEXT_HINT,
                     font=(FONT, 13)).pack(pady=16)
        for p in st.get("periods", []):
            card = self._card(inner)
            card.pack(fill="x", pady=4, padx=2)
            tk.Frame(card, bg=CARD).pack(fill="x", pady=6)
            tk.Label(card, text=p["period"], bg=CARD, fg=PRIMARY_DARK,
                     font=(FONT, 14, "bold")).pack(anchor="w", padx=14)
            line = tk.Frame(card, bg=CARD)
            line.pack(fill="x", padx=14, pady=(2, 8))
            tk.Label(line, text=f"Деталей: {p['total_quantity']}", bg=CARD, fg=PRIMARY,
                     font=(FONT, 13, "bold")).pack(side="left", padx=(0, 16))
            tk.Label(line, text=f"Работ: {p['total_works']}", bg=CARD, fg=TEXT,
                     font=(FONT, 13)).pack(side="left")


    def show_orders(self):
        self._clear()
        self.root.geometry("900x680")
        session = auth_store.get_session()
        is_manager = session.get("role") in ("manager", "admin")
        self.root.title("Заказы")
        self._toolbar("Заказы" if is_manager else "Заказы на гибку", "#00695C", back=True)

        view = {"arch": False}

        top = tk.Frame(self.root, bg=BG)
        top.pack(fill="x", padx=16, pady=(10, 4))
        if is_manager:
            _btn(top, "📥 Загрузить спецификацию (Excel)", PRIMARY,
                 lambda: self._load_spec(), height=42, fs=13).pack(
                side="left", expand=True, fill="x", padx=(0, 6))
            _btn(top, "📊 Статистика гибки", PURPLE,
                 lambda: self._switch(self.show_order_stats), height=42, fs=13).pack(
                side="left", expand=True, fill="x", padx=(6, 0))
        else:
            _btn(top, "🔄 Обновить", "#00695C", lambda: refresh(), height=40,
                 fs=13, outlined=True).pack(side="left")

        if is_manager:
            arch = tk.Frame(self.root, bg=BG)
            arch.pack(fill="x", padx=16, pady=(2, 0))
            b_cur = _btn(arch, "Текущие", PRIMARY,
                         lambda: set_arch(False), height=34, fs=12)
            b_cur.pack(side="left", expand=True, fill="x", padx=(0, 3))
            b_arch = _btn(arch, "Архив (готовые)", DARK_GRAY,
                          lambda: set_arch(True), height=34, fs=12)
            b_arch.pack(side="left", expand=True, fill="x", padx=(3, 0))

            def set_arch(val):
                view["arch"] = val
                b_cur.configure(bg=PRIMARY if not val else DARK_GRAY)
                b_arch.configure(bg=PURPLE if val else DARK_GRAY)
                refresh()

        container = tk.Frame(self.root, bg=BG)
        container.pack(fill="both", expand=True, padx=16, pady=(6, 8))
        inner = self._scrollable(container)

        def refresh():
            self._exec(lambda: self.api.get_orders("ready" if view["arch"] else None),
                       ok=lambda rows: self._render_orders(inner, rows,
                                                           is_manager, refresh))

        band = tk.Frame(self.root, bg=BG)
        band.pack(fill="x", padx=16, pady=(0, 12))
        _btn(band, "🔄 Обновить", "#00695C", refresh, height=40, fs=13,
             outlined=True).pack(fill="x", pady=(6, 0) if is_manager else 0)

        refresh()

    def _render_orders(self, inner, orders, is_manager=False, refresh=None):
        for w in inner.winfo_children():
            w.destroy()
        if not orders:
            tk.Label(inner, text="Заказов пока нет", bg=BG, fg=TEXT_HINT,
                     font=(FONT, 13)).pack(pady=24)
        for o in orders:
            card = self._card(inner)
            card.pack(fill="x", pady=5, padx=2)
            head = tk.Frame(card, bg=CARD)
            head.pack(fill="x", padx=14, pady=(10, 0))
            tk.Label(head, text=o.get("name") or f"Заказ {o.get('order_number')}",
                     bg=CARD, fg=PRIMARY_DARK, font=(FONT, 15, "bold")).pack(side="left")
            is_ready = o.get("status") == "ready"
            is_finished = is_ready or (
                o.get("total_bend_quantity", 0) > 0 and o.get("remaining_bend_quantity", 0) <= 0
            )
            card.configure(bg=GOOD_BG if is_finished else CARD)
            bgrow = GOOD_BG if is_finished else CARD
            head = tk.Frame(card, bg=bgrow)
            head.pack(fill="x", padx=14, pady=(10, 0))
            tk.Label(head, text=o.get("name") or f"Заказ {o.get('order_number')}",
                     bg=bgrow, fg=PRIMARY_DARK, font=(FONT, 15, "bold")).pack(side="left")
            tk.Label(head, text="ГОТОВ" if is_finished else "ОТКРЫТ",
                     bg=bgrow, fg=PRIMARY_DARK if is_finished else PRIMARY,
                     font=(FONT, 12, "bold")).pack(side="right")
            mid = tk.Frame(card, bg=bgrow)
            mid.pack(fill="x", padx=14)
            tk.Label(mid,
                     text=f"Согнуто: {o.get('done_bend_quantity', 0)} из {o.get('total_bend_quantity', 0)}",
                     bg=bgrow, fg=ACCENT, font=(FONT, 13, "bold")).pack(side="left")
            st_line = order_stages_line(o.get("stages"))
            if st_line:
                tk.Label(mid, text=st_line, bg=bgrow, fg=TEXT_SEC,
                         font=(FONT, 11)).pack(side="left", padx=(14, 0))
            tk.Label(mid,
                     text=f"Осталось: {o.get('remaining_bend_quantity', 0)}",
                     bg=bgrow, fg=TEXT, font=(FONT, 13)).pack(side="right")
            tk.Label(mid,
                     text=f"Выполнено: {self._percent_for_order(o)}%",
                     bg=bgrow, fg=PRIMARY, font=(FONT, 13, "bold")).pack(side="right", padx=(10, 0))
            sub = tk.Frame(card, bg=bgrow)
            sub.pack(fill="x", padx=14)
            tk.Label(sub,
                     text=f"Позиций: {o.get('total_items', 0)} · с гибкой: {o.get('bending_items', 0)}",
                     bg=bgrow, fg=TEXT_HINT, font=(FONT, 12)).pack(side="left")
            tk.Label(sub, text=self._fmt_dt(o.get("created_at") or ""),
                     bg=bgrow, fg=TEXT_HINT, font=(FONT, 12)).pack(side="right")
            acts = tk.Frame(card, bg=bgrow)
            acts.pack(fill="x", padx=14, pady=(6, 10))
            if is_manager and not is_finished:
                _small_btn(acts, "✅ В архив", PRIMARY,
                           lambda oo=o: self._mark_ready_order(oo, refresh)).pack(side="left", padx=(0, 4))
            if is_manager:
                _small_btn(acts, "🗑 Удалить", RED,
                           lambda oo=o: self._delete_order(oo, refresh)).pack(side="left", padx=(0, 4))
            _small_btn(acts, "Открыть", "#00695C",
                       lambda oo=o: self._switch(self.show_order_detail, oo["order_id"])
                       ).pack(side="right")

    def _mark_ready_order(self, o, refresh):
        if not messagebox.askyesno(
                "В архив", f"Отметить заказ «{o.get('name') or o.get('order_number')}» готовым?\n"
                           "Он перейдёт в Архив (хранится год).", parent=self.root):
            return
        self._exec(lambda: self.api.mark_order_ready(o["order_id"]),
                   ok=lambda _: (messagebox.showinfo(
                       "Готово", "Заказ отмечен готовым и ушёл в архив.", parent=self.root),
                       refresh()))

    def _delete_order(self, o, refresh):
        if not messagebox.askyesno(
                "Удалить заказ", f"Удалить заказ «{o.get('name') or o.get('order_number')}»?\n"
                                "Позиции и все отметки о гибке будут удалены. Действие необратимо.",
                parent=self.root):
            return
        self._exec(lambda: self.api.delete_order(o["order_id"]),
                   ok=lambda _: (messagebox.showinfo(
                       "Готово", "Заказ удалён.", parent=self.root), refresh()))

    def _load_spec(self):
        from tkinter import filedialog
        path = filedialog.askopenfilename(
            parent=self.root, title="Файл спецификации",
            filetypes=[("Excel", "*.xlsx *.xlsm"), ("Все файлы", "*.*")])
        if not path:
            return
        self._exec(
            lambda: self.api.upload_order(path),
            ok=lambda r: (messagebox.showinfo(
                "Готово",
                "\n".join(f"{x.get('name')}: создан ({x.get('items')} поз., "
                          f"{x.get('bending_items')} с гибкой)" for x in r.get("orders", []))
                or "Загрузка завершена", parent=self.root),
                self.show_orders()))

    def show_order_detail(self, order_id):
        self._clear()
        self.root.geometry("940x700")
        self.root.title("Заказ")
        self._toolbar("Заказ", "#00695C", back=True)
        session = auth_store.get_session()
        is_manager = session.get("role") in ("manager", "admin")

        summ = tk.Frame(self.root, bg=BG)
        summ.pack(fill="x", padx=16, pady=(12, 2))
        l_title = tk.Label(summ, text="", bg=BG, fg=PRIMARY_DARK, font=(FONT, 18, "bold"))
        l_title.pack(anchor="w")
        l_progress = tk.Label(summ, text="", bg=BG, fg=ACCENT, font=(FONT, 14, "bold"))
        l_progress.pack(anchor="w")

        container = tk.Frame(self.root, bg=BG)
        container.pack(fill="both", expand=True, padx=16, pady=(6, 8))
        inner = self._scrollable(container)

        band = tk.Frame(self.root, bg=BG)
        band.pack(fill="x", padx=16, pady=(0, 12))
        if is_manager:
            _btn(band, "🔒 Закрыть заказ", ORANGE, lambda: self._close_order(order_id),
                 height=42, fs=13).pack(fill="x")
        _btn(band, "🔄 Обновить", DARK_GRAY, lambda: refresh(), height=38, fs=12,
             outlined=True).pack(fill="x", pady=(6, 0))

        def refresh():
            self._exec(
                lambda: (self.api.get_order(order_id),
                         (self.api.get_users() if is_manager else [])),
                ok=lambda pair: self._render_order_detail(
                    inner, pair[0], pair[1], l_title, l_progress, is_manager, refresh))

        refresh()

    def _render_order_detail(self, inner, order, users, l_title, l_progress,
                             is_manager, refresh):
        for w in inner.winfo_children():
            w.destroy()
        session = auth_store.get_session()
        benders = [u for u in users if u.get("role") in WORKER_ROLE_KEYS]
        role = session.get("role")
        my_block = WORKER_BLOCK.get(role)
        l_title.config(text=order.get("name") or f"Заказ {order.get('order_number')}")
        items_all = order.get("items", [])
        bend_items = [i for i in items_all if i.get("needs_bending")]
        done = sum(i.get("done_quantity", 0) for i in bend_items)
        total = sum(i.get("quantity", 0) for i in bend_items)
        percent = self._percent_for_order({"items": items_all})
        prog = f"Согнуто: {done} из {total} · Осталось: {max(0, total - done)}"
        st_line = self._stages_line_from_items(items_all)
        if st_line:
            prog += f" · {st_line}"
        if percent:
            prog += f" · Выполнено: {percent}%"
        l_progress.config(
            text=prog,
            fg=ACCENT)

        closed = order.get("status") == "closed"
        if not order.get("items"):
            tk.Label(inner, text="Позиций нет", bg=BG, fg=TEXT_HINT,
                     font=(FONT, 13)).pack(pady=24)

        for item in order.get("items", []):
            done = item.get("quantity", 0) > 0 and item.get("remaining", 0) <= 0
            claim = item.get("claim")
            in_work = not done and claim and claim.get("completed_at") is None
            item_active = item.get("active", True)
            can_act = is_manager or item_active
            if is_manager:
                bgrow = GOOD_BG if done else (WORK_BG if in_work else CARD)
            else:
                bgrow = GOOD_BG if done else (INACTIVE_BG if not item_active else (WORK_BG if in_work else CARD))
            card = self._card(inner)
            card.configure(bg=bgrow)
            card.pack(fill="x", pady=5, padx=2)

            claim = item.get("claim")
            worker_id = session.get("user_id")
            my_open = claim and claim.get("completed_at") is None and claim.get("worker_id") == worker_id

            # Строчка «исполнить заказ» — на первом месте в карточке
            if item.get("needs_bending") and not closed and not done and can_act:
                acts_top = tk.Frame(card, bg=bgrow)
                acts_top.pack(fill="x", padx=14, pady=(10, 0))
                if is_manager:
                    _btn(acts_top, "📝 Исполнить заказ", ACCENT,
                         lambda it=item: self._mark_dialog(
                             order["order_id"], it, benders, refresh),
                         height=36, fs=12).pack(fill="x")
                    if claim and claim.get("completed_at") is None:
                        _btn(acts_top, "👥 Состав бригады", DARK_GRAY,
                             lambda it=item: self._crew_action(
                                 order["order_id"], it, refresh),
                             height=30, fs=11, outlined=True, bold=False).pack(
                            fill="x", pady=(4, 0))
                elif my_open:
                    _btn(acts_top, "✅ Выполнено", PRIMARY,
                         lambda it=item: self._mark_dialog(
                             order["order_id"], it, benders, refresh),
                         height=36, fs=12).pack(fill="x")
                    sub = tk.Frame(acts_top, bg=bgrow)
                    sub.pack(fill="x", pady=(4, 0))
                    _btn(sub, "👥 Состав бригады", DARK_GRAY,
                         lambda it=item: self._crew_action(
                             order["order_id"], it, refresh),
                         height=30, fs=11, outlined=True, bold=False).pack(
                        side="left", expand=True, fill="x", padx=(0, 3))
                    _btn(sub, "Отказаться", "#C62828",
                         lambda it=item: self._release_action(
                             order["order_id"], it, refresh),
                         height=30, fs=11, outlined=True, bold=False).pack(
                        side="left", expand=True, fill="x", padx=(3, 0))
                elif claim and claim.get("completed_at") is None:
                    tk.Label(acts_top, text=f"🚫 Деталь взял(а): {claim.get('worker_name', '')}",
                             bg=bgrow, fg=TEXT_HINT, font=(FONT, 12, "bold")).pack(fill="x")
                else:
                    _btn(acts_top, "🚀 Взять в работу", ORANGE,
                         lambda it=item: self._claim_action(
                             order["order_id"], it, refresh),
                         height=36, fs=12).pack(fill="x")

            head = tk.Frame(card, bg=bgrow)
            head.pack(fill="x", padx=14, pady=(8, 0))
            tk.Label(head, text=item.get("part_number") or "—", bg=bgrow, fg=TEXT,
                     font=(FONT, 15, "bold")).pack(side="left")
            tk.Label(head,
                     text=("✅ ГОТОВО" if done else f"{item.get('quantity', 0)} шт"),
                     bg=bgrow, fg=PRIMARY_DARK if done else ACCENT,
                     font=(FONT, 15, "bold")).pack(side="right")
            spec_parts = []
            if item.get("thickness") is not None:
                th = item["thickness"]
                spec_parts.append(f"Толщина: {int(th) if th == int(th) else th}")
            spec_parts.append(f"Марка: {item.get('steel_grade') or '—'}")
            spec_parts.append(f"Маршрут: {item.get('route') or '—'}")
            mid = tk.Frame(card, bg=bgrow)
            mid.pack(fill="x", padx=14)
            tk.Label(mid, text=" · ".join(spec_parts), bg=bgrow, fg=TEXT_SEC,
                 font=(FONT, 12)).pack(side="left")
            tk.Label(mid, text=f"Выполнено: {item.get('done_quantity', 0)}",
                     bg=bgrow, fg=PRIMARY, font=(FONT, 12, "bold")).pack(side="right")
            st_line = item_stages_line(item)
            if st_line:
                strow = tk.Frame(card, bg=bgrow)
                strow.pack(fill="x", padx=14, pady=(4, 0))
                tk.Label(strow, text=st_line, bg=bgrow, fg=TEXT_SEC,
                         font=(FONT, 11)).pack(side="left")
            if not is_manager and not item_active:
                hintrow = tk.Frame(card, bg=bgrow)
                hintrow.pack(fill="x", padx=14, pady=(4, 0))
                tk.Label(hintrow, text="⏳ Деталь ещё не на вашем этапе", bg=bgrow,
                         fg=INACTIVE_FG, font=(FONT, 11, "bold")).pack(anchor="w")

            if claim:
                claim_row = tk.Frame(card, bg=bgrow)
                claim_row.pack(fill="x", padx=14, pady=(6, 0))
                workers = claim.get("workers") or []
                if len(workers) > 1:
                    crew_text = " · ".join(w.get("name") or "?" for w in workers)
                else:
                    crew_text = claim.get("worker_name") or "?"
                claim_text = "Взяли: " + crew_text
                claim_text += " " + self._fmt_dt(claim.get("claimed_at") or "")
                if claim.get("completed_at"):
                    claim_text += " · Завершил(а): " + self._fmt_dt(claim.get("completed_at") or "")
                else:
                    claim_text += " (в работе)"
                tk.Label(claim_row, text=claim_text, bg=bgrow,
                         fg=PRIMARY_DARK if claim.get("completed_at") else "#9A7D00",
                         font=(FONT, 11)).pack(anchor="w")

            pending = self._pending_stages(item)
            if not closed and not done and pending and (is_manager or (item_active and my_block)):
                acts = tk.Frame(card, bg=bgrow)
                acts.pack(fill="x", padx=14, pady=(6, 10))
                if is_manager:
                    _small_btn(acts, "📌 Отметить стадию", "#00695C",
                               lambda it=item: self._stage_dialog(
                                   order["order_id"], it, refresh)
                               ).pack(side="right", padx=(0, 6))
                elif my_block == BLOCK_BENDER:
                    if BLOCK_BENDER in pending:
                        _small_btn(acts,
                                   f"📌 Отметить (осталось {item.get('remaining', 0)})",
                                   "#00695C",
                                   lambda it=item: self._mark_dialog(
                                       order["order_id"], it, benders, refresh)
                                   ).pack(side="right", padx=(0, 6))
                elif my_block in pending:
                    blk = stage_name(my_block)
                    _small_btn(acts, f"📌 Отметить: {blk}", "#00695C",
                               lambda it=item: self._stage_dialog(
                                   order["order_id"], it, refresh, only=(my_block,))
                               ).pack(side="right", padx=(0, 6))
                if item.get("completions"):
                    _small_btn(acts, "📜 История", PURPLE,
                               lambda it=item: self._history_dialog(
                                   order["order_id"], it, is_manager, refresh)
                               ).pack(side="right")
            elif item.get("completions"):
                acts = tk.Frame(card, bg=bgrow)
                acts.pack(fill="x", padx=14, pady=(6, 10))
                _small_btn(acts, "📜 История", PURPLE,
                           lambda it=item: self._history_dialog(
                               order["order_id"], it, is_manager, refresh)
                           ).pack(side="right")
            else:
                tk.Frame(card, bg=bgrow).pack(pady=6)
        tk.Frame(inner, bg=BG).pack(pady=4)

    def _claim_action(self, order_id, item, refresh):
        session = auth_store.get_session()
        is_manager = session.get("role") in ("manager", "admin")
        if is_manager:
            users = []
            try:
                users = self.api.get_users()
            except Exception:
                pass
            benders = [u for u in users if u.get("role") in WORKER_ROLE_KEYS]
            names = [f"{b.get('full_name')} ({b.get('username')})" for b in benders]
            if not names:
                messagebox.showwarning("Внимание", "Нет гибщиков", parent=self.root)
                return
            dlg = tk.Toplevel(self.root)
            dlg.title("Выдать деталь")
            dlg.configure(bg=BG)
            dlg.resizable(False, False)
            dlg.transient(self.root)
            dlg.grab_set()
            body = tk.Frame(dlg, bg=BG, padx=20, pady=16)
            body.pack(fill="both", expand=True)
            tk.Label(body, text=f"Выдать «{item.get('part_number')}» гибщику:",
                     bg=BG, fg=PRIMARY_DARK, font=(FONT, 13, "bold")).pack(anchor="w", pady=(0, 8))
            var = tk.StringVar(value=names[0])
            combo = ttk.Combobox(body, textvariable=var, values=names, state="readonly",
                                 font=(FONT, 12))
            combo.pack(fill="x")
            btns = tk.Frame(body, bg=BG)
            btns.pack(fill="x", pady=(16, 0))
            def give():
                idx = names.index(var.get())
                self._exec(lambda: self.api.claim_item(order_id, item["id"], benders[idx]["id"]),
                           ok=lambda _: (dlg.destroy(), refresh()))
            _btn(btns, "Выдать", PRIMARY, give, height=40, fs=13).pack(
                side="right", padx=(6, 0))
            _btn(btns, "Отмена", DARK_GRAY, dlg.destroy, height=40, fs=13,
                 outlined=True).pack(side="right", padx=(0, 6))
            return
        self._exec(lambda: self.api.claim_item(order_id, item["id"]),
                   ok=lambda _: (messagebox.showinfo(
                       "Готово", "Деталь взята в работу. По завершении нажмите «Выполнено».",
                       parent=self.root), refresh()))

    def _release_action(self, order_id, item, refresh):
        if messagebox.askyesno(
                "Отказ от гибки",
                f"{item.get('part_number')} — деталь снова станет доступной другим. Отказаться?",
                parent=self.root):
            self._exec(lambda: self.api.release_item(order_id, item["id"]),
                       ok=lambda _: (messagebox.showinfo(
                           "Готово", "Деталь возвращена, можно взять снова.",
                           parent=self.root), refresh()))

    def _crew_action(self, order_id, item, refresh):
        users = []
        try:
            users = self.api.get_users()
        except Exception:
            pass
        claim = item.get("claim") or {}
        main_id = claim.get("worker_id")
        others = [u for u in users if u.get("id") != main_id]
        if not others:
            messagebox.showwarning("Внимание", "Нет других сотрудников", parent=self.root)
            return
        current = {p.get("id") for p in (claim.get("workers") or []) if p.get("id") != main_id}
        pending = {p.get("id") for p in (claim.get("pending") or [])}

        dlg = tk.Toplevel(self.root)
        dlg.title("Состав бригады")
        dlg.configure(bg=BG)
        dlg.transient(self.root)
        dlg.grab_set()
        body = tk.Frame(dlg, bg=BG, padx=20, pady=16)
        body.pack(fill="both", expand=True)
        tk.Label(body, text=f"Отметьте соисполнителей по «{item.get('part_number')}»:",
                 bg=BG, fg=PRIMARY_DARK, font=(FONT, 13, "bold")).pack(anchor="w", pady=(0, 8))

        checkvars = {}
        for b in others:
            label = f"{b.get('full_name')} ({b.get('username')}) — {role_name(b.get('role'))}"
            if b["id"] in pending:
                label += " — ожидает ответа"
            checkvars[b["id"]] = tk.BooleanVar(value=(b["id"] in current))
            tk.Checkbutton(body, text=label, variable=checkvars[b["id"]],
                           bg=BG, fg=TEXT, activebackground=BG,
                           font=(FONT, 12)).pack(anchor="w", pady=2)

        btns = tk.Frame(body, bg=BG)
        btns.pack(fill="x", pady=(16, 0))

        def save():
            want = {i for i, v in checkvars.items() if v.get()}
            add = want - current
            remove = current - want
            def work():
                for wid in sorted(add):
                    self.api.add_claim_participant(order_id, item["id"], wid)
                for wid in sorted(remove):
                    self.api.remove_claim_participant(order_id, item["id"], wid)
            self._exec(work, ok=lambda _: (dlg.destroy(), refresh()))

        _btn(btns, "Сохранить", PRIMARY, save, height=40, fs=13).pack(
            side="right", padx=(6, 0))
        _btn(btns, "Отмена", DARK_GRAY, dlg.destroy, height=40, fs=13,
             outlined=True).pack(side="right", padx=(0, 6))

    def _history_dialog(self, order_id, item, is_manager, refresh):
        dlg = tk.Toplevel(self.root)
        dlg.title("История отметок")
        dlg.configure(bg=BG)
        dlg.transient(self.root)
        dlg.grab_set()
        body = tk.Frame(dlg, bg=BG, padx=20, pady=16)
        body.pack(fill="both", expand=True)
        tk.Label(body, text=f"{item.get('part_number')} · {item.get('quantity', 0)} шт",
                 bg=BG, fg=PRIMARY_DARK, font=(FONT, 14, "bold")).pack(anchor="w", pady=(0, 8))
        me = auth_store.get_session().get("user_id")
        completions = item.get("completions", []) or []
        if not completions:
            tk.Label(body, text="Отметок ещё нет", bg=BG, fg=TEXT_HINT,
                     font=(FONT, 12)).pack(anchor="w", pady=8)
        for c in completions:
            row = tk.Frame(body, bg=BG)
            row.pack(fill="x", pady=3)
            stage_c = c.get("stage") or "bender"
            text = (f"[{stage_name(stage_c)}] {c.get('executor_name') or '?'}: "
                    f"{c.get('quantity')} шт ({self._fmt_dt(c.get('completed_at') or '')})")
            if c.get("note"):
                text += " — " + c["note"]
            tk.Label(row, text=text, bg=BG, fg=TEXT_SEC,
                     font=(FONT, 11)).pack(side="left", anchor="w")
            can_del = (is_manager or c.get("marked_by") == me
                       or c.get("executor_id") == me)
            if can_del:
                _small_btn(row, "✕ Удалить", RED,
                           lambda cc=c: self._delete_completion(order_id, cc, dlg, refresh),
                           fs=10).pack(side="right", padx=(8, 0))
        btns = tk.Frame(body, bg=BG)
        btns.pack(fill="x", pady=(14, 0))
        _btn(btns, "Закрыть", DARK_GRAY, dlg.destroy, height=38, fs=12,
             outlined=True).pack(side="right")

    def _delete_completion(self, order_id, c, dlg, refresh):
        if messagebox.askyesno(
                "Удалить отметку",
                f"Удалить отметку {c.get('executor_name') or '?'}: {c.get('quantity')} шт?",
                parent=dlg):
            self._exec(lambda: self.api.delete_completion(c["id"]),
                       ok=lambda _: (dlg.destroy(), refresh()))

    def _mark_dialog(self, order_id, item, benders, refresh):
        dlg = tk.Toplevel(self.root)
        dlg.title("Отметить выполнение")
        dlg.configure(bg=BG)
        dlg.resizable(False, False)
        dlg.transient(self.root)
        dlg.grab_set()
        body = tk.Frame(dlg, bg=BG, padx=20, pady=16)
        body.pack(fill="both", expand=True)
        tk.Label(body, text=f"{item.get('part_number')} · осталось {item.get('remaining', 0)}",
                 bg=BG, fg=PRIMARY_DARK, font=(FONT, 14, "bold")).pack(anchor="w")

        for c in item.get("completions", []):
            hrow = tk.Frame(body, bg=BG)
            hrow.pack(fill="x", pady=2, anchor="w")
            stage_c = c.get("stage") or "bender"
            tk.Label(hrow,
                     text=f"[{stage_name(stage_c)}] {c.get('executor_name')}: {c.get('quantity')} шт "
                          f"({self._fmt_dt(c.get('completed_at') or '')})",
                     bg=BG, fg=TEXT_SEC, font=(FONT, 11)).pack(side="left")

        tk.Label(body, text=f"Сколько согнуто (осталось {item.get('remaining', 0)}):",
                 bg=BG, fg=TEXT, font=(FONT, 11)).pack(anchor="w", pady=(12, 2))
        e_qty = _entry(body, "#00695C", 12, fs=14)
        e_qty.pack(fill="x")

        executor_var = None
        if benders:
            tk.Label(body, text="Исполнитель (фактический гибщик):", bg=BG, fg=TEXT,
                     font=(FONT, 11)).pack(anchor="w", pady=(10, 2))
            names = [f"{b.get('full_name')} ({b.get('username')})" for b in benders]
            claim_wid = item.get("claim", {}).get("worker_id")
            default_name = names[0]
            if claim_wid is not None:
                for b in benders:
                    if b.get("id") == claim_wid:
                        default_name = f"{b.get('full_name')} ({b.get('username')})"
                        break
            executor_var = tk.StringVar(value=default_name)
            combo = ttk.Combobox(body, textvariable=executor_var, values=names,
                                 state="readonly", font=(FONT, 12))
            combo.pack(fill="x")

        btns = tk.Frame(body, bg=BG)
        btns.pack(fill="x", pady=(16, 0))

        def save():
            qty_s = e_qty.get().strip()
            try:
                qty = int(qty_s)
            except ValueError:
                messagebox.showwarning("Внимание", "Введите число", parent=dlg)
                return
            if qty <= 0:
                messagebox.showwarning("Внимание", "Количество больше нуля", parent=dlg)
                return
            executor_id = None
            if executor_var is not None:
                idx = names.index(executor_var.get())
                executor_id = benders[idx]["id"]
            self._exec(
                lambda: self.api.complete_item(order_id, item["id"], qty, executor_id),
                ok=lambda _: (dlg.destroy(), refresh()))

        _btn(btns, "Сохранить", PRIMARY, save, height=40, fs=13).pack(
            side="right", padx=(6, 0))
        _btn(btns, "Отмена", DARK_GRAY, dlg.destroy, height=40, fs=13,
             outlined=True).pack(side="right", padx=(0, 6))

    def _stage_dialog(self, order_id, item, refresh, only=None):
        stages = self._pending_stages(item)
        if only:
            stages = [s for s in stages if s in only]
        if not stages:
            messagebox.showinfo(
                "Внимание", "По этой позиции выполнение уже отмечено по всем стадиям.",
                parent=self.root)
            return
        dlg = tk.Toplevel(self.root)
        dlg.title("Отметить стадию")
        dlg.configure(bg=BG)
        dlg.resizable(False, False)
        dlg.transient(self.root)
        dlg.grab_set()
        body = tk.Frame(dlg, bg=BG, padx=20, pady=16)
        body.pack(fill="both", expand=True)
        tk.Label(body, text=f"{item.get('part_number')} · {item.get('quantity', 0)} шт",
                 bg=BG, fg=PRIMARY_DARK, font=(FONT, 14, "bold")).pack(anchor="w")

        names = [stage_name(s) for s in stages]
        stage_var = tk.StringVar(value=names[0])

        tk.Label(body, text="Стадия:", bg=BG, fg=TEXT,
                 font=(FONT, 11)).pack(anchor="w", pady=(12, 2))
        combo = ttk.Combobox(body, textvariable=stage_var, values=names,
                             state="readonly", font=(FONT, 12))
        combo.pack(fill="x")

        tk.Label(body, text=f"Сколько выполнено (осталось {item.get('remaining', 0)}):",
                 bg=BG, fg=TEXT, font=(FONT, 11)).pack(anchor="w", pady=(10, 2))
        e_qty = _entry(body, "#00695C", 12, fs=14)
        e_qty.pack(fill="x")

        btns = tk.Frame(body, bg=BG)
        btns.pack(fill="x", pady=(16, 0))

        def save():
            qty_s = e_qty.get().strip()
            try:
                qty = int(qty_s)
            except ValueError:
                messagebox.showwarning("Внимание", "Введите число", parent=dlg)
                return
            if qty <= 0:
                messagebox.showwarning("Внимание", "Количество больше нуля", parent=dlg)
                return
            code = stages[names.index(stage_var.get())]
            self._exec(
                lambda: self.api.complete_item(order_id, item["id"], qty, stage=code),
                ok=lambda _: (dlg.destroy(), refresh()))

        _btn(btns, "Сохранить", PRIMARY, save, height=40, fs=13).pack(
            side="right", padx=(6, 0))
        _btn(btns, "Отмена", DARK_GRAY, dlg.destroy, height=40, fs=13,
             outlined=True).pack(side="right", padx=(0, 6))

    def _close_order(self, order_id):
        if messagebox.askyesno("Закрыть заказ", "Закрыть заказ?", parent=self.root):
            self._exec(lambda: self.api.close_order(order_id),
                       ok=lambda _: self.show_order_detail(order_id))

    def show_order_stats(self):
        self._clear()
        self.root.geometry("720x620")
        self.root.title("Статистика гибки по заказам")
        self._toolbar("Статистика гибки по заказам", PURPLE, back=True)

        container = tk.Frame(self.root, bg=BG)
        container.pack(fill="both", expand=True, padx=16, pady=(12, 8))
        inner = self._scrollable(container)

        def render(rows):
            for w in inner.winfo_children():
                w.destroy()
            if not rows:
                tk.Label(inner, text="Отметок по заказам пока нет", bg=BG, fg=TEXT_HINT,
                         font=(FONT, 13)).pack(pady=24)
            for row in rows:
                card = self._card(inner)
                card.pack(fill="x", pady=5, padx=2)
                tk.Label(card, text=row.get("worker_name") or f"Рабочий #{row.get('worker_id')}",
                         bg=CARD, fg=PURPLE, font=(FONT, 15, "bold")).pack(
                    anchor="w", padx=14, pady=(10, 0))
                line = tk.Frame(card, bg=CARD)
                line.pack(fill="x", padx=14, pady=(2, 8))
                tk.Label(line, text=f"Согнуто деталей: {row.get('total_bent_quantity', 0)}",
                         bg=CARD, fg=PRIMARY, font=(FONT, 13, "bold")).pack(side="left", padx=(0, 16))
                tk.Label(line,
                         text=f"Отметок: {row.get('marks', 0)} · Деталей: {row.get('distinct_parts', 0)}",
                         bg=CARD, fg=TEXT, font=(FONT, 13)).pack(side="left")

        self._exec(lambda: self.api.order_stats(), ok=render)

    # ===================== Чат =====================

    @staticmethod
    def _chat_time(iso):
        if not iso:
            return ""
        try:
            dt = datetime.strptime(iso, "%Y-%m-%dT%H:%M:%S")
            if dt.date() == datetime.now().date():
                return dt.strftime("%H:%M")
            return dt.strftime("%d.%m %H:%M")
        except Exception:
            return iso or ""

    def _try_users(self):
        try:
            return self.api.get_users()
        except api_mod.ApiError as e:
            messagebox.showerror("Ошибка", str(e), parent=self.root)
            return None

    def _pick_users(self, title, users):
        win = tk.Toplevel(self.root)
        win.title(title)
        win.geometry("440x440")
        win.configure(bg=BG)
        win.transient(self.root)
        win.grab_set()
        result = [None]
        outer = tk.Frame(win, bg=BG)
        outer.pack(fill="both", expand=True, padx=12, pady=8)
        canvas = tk.Canvas(outer, bg=BG, highlightthickness=0)
        sb = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        inner = tk.Frame(canvas, bg=BG)
        inner_id = canvas.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(inner_id, width=e.width))
        canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        vars_ = {}
        for u in users:
            v = tk.BooleanVar(value=False)
            vars_[u["id"]] = v
            tk.Checkbutton(
                inner, text=u["full_name"] + " (" + role_name(u["role"]) + ")",
                variable=v, bg=BG, fg=TEXT, activebackground=BG, activeforeground=TEXT,
                font=(FONT, 12), anchor="w",
            ).pack(fill="x", anchor="w", pady=2)
        btns = tk.Frame(win, bg=BG)
        btns.pack(fill="x", padx=12, pady=8)
        _btn(btns, "Отмена", DARK_GRAY, win.destroy, height=38, fs=12,
             outlined=True).pack(side="right", padx=(6, 0))

        def ok():
            result[0] = [u for u in users if vars_.get(u["id"]) and vars_[u["id"]].get()]
            win.destroy()

        _btn(btns, "OK", PRIMARY, ok, height=38, fs=13).pack(side="right")
        self.root.wait_window(win)
        return result[0]

    def _chat_new(self):
        dlg = tk.Toplevel(self.root)
        dlg.title("Новый чат")
        dlg.geometry("360x170")
        dlg.configure(bg=BG)
        dlg.transient(self.root)
        dlg.grab_set()
        tk.Label(dlg, text="Что создаём?", bg=BG, fg=TEXT,
                 font=(FONT, 13)).pack(pady=(18, 10))
        btns = tk.Frame(dlg, bg=BG)
        btns.pack()
        _btn(btns, "Личный", ACCENT, lambda: (dlg.destroy(), self._chat_new_dm()),
             height=40, fs=13).pack(side="left", padx=6, ipadx=12)
        _btn(btns, "Группа", PRIMARY, lambda: (dlg.destroy(), self._chat_new_group()),
             height=40, fs=13).pack(side="left", padx=6, ipadx=12)

    def _chat_new_dm(self):
        users = self._try_users()
        if users is None:
            return
        if not users:
            messagebox.showinfo("Чат", "Некому писать — сотрудников нет", parent=self.root)
            return
        labels = [u["full_name"] + " — " + role_name(u["role"]) for u in users]
        idx = self._pick_from_list("Выберите сотрудника", labels, 0)
        if idx is None:
            return
        target = users[idx]

        def ok(ch):
            self._switch(self.show_chat_room, ch["id"],
                         ch.get("other_user_name") or "Чат", "dm")

        self._exec(lambda: self.api.create_dm(target["id"]), ok=ok)

    def _chat_new_group(self):
        users = self._try_users()
        if users is None:
            return
        dlg = FieldDialog(self.root, "Новая группа", [("Название", "", False)])
        self.root.wait_window(dlg)
        v = dlg.result
        if not v or not v[0].strip():
            return
        name = v[0].strip()
        picked = self._pick_users("Участники", users)
        if picked is None:
            return
        if not picked:
            messagebox.showwarning("Внимание", "Выберите хотя бы одного участника",
                                   parent=self.root)
            return

        def ok(ch):
            self._switch(self.show_chat_room, ch["id"], ch.get("name") or name, "group")

        self._exec(lambda: self.api.create_chat(name, [u["id"] for u in picked]), ok=ok)

    def show_chat_list(self):
        self._clear()
        self.root.geometry("760x660")
        self.root.title("Чат")
        self._toolbar("Чат", DARK_GRAY, back=True)

        container = tk.Frame(self.root, bg=BG)
        container.pack(fill="both", expand=True, padx=12, pady=(8, 4))
        inner = self._scrollable(container)

        def render(chats=None):
            chats = chats or []
            for w in inner.winfo_children():
                w.destroy()
            if not chats:
                tk.Label(inner, text="Чатов пока нет. Создайте новый или напишите сотруднику.",
                         bg=BG, fg=TEXT_HINT, font=(FONT, 13), wraplength=600,
                         justify="center").pack(pady=24)
            for ch in chats:
                card = self._card(inner)
                card.pack(fill="x", pady=4, padx=2)
                name = (ch.get("other_user_name") if ch["type"] == "dm"
                        else (ch.get("name") or "Чат"))
                head = tk.Frame(card, bg=CARD)
                head.pack(fill="x", padx=14, pady=(8, 0))
                tk.Label(head, text=name, bg=CARD, fg=TEXT,
                         font=(FONT, 14, "bold")).pack(side="left")
                unread = ch.get("unread_count") or 0
                if unread:
                    tk.Label(head, text=f" {unread} ", bg=ORANGE, fg="#FFFFFF",
                             font=(FONT, 11, "bold")).pack(side="right", padx=6, pady=2)
                last = ch.get("last_message")
                if last:
                    sender = "" if ch["type"] == "dm" else ((last.get("sender_name") or "?") + ": ")
                    tk.Label(card, text=sender + (last.get("text") or ""), bg=CARD,
                             fg=TEXT_SEC, font=(FONT, 12), wraplength=640,
                             justify="left").pack(anchor="w", padx=14, pady=(2, 0))
                    tk.Label(card, text=self._chat_time(last.get("created_at")),
                             bg=CARD, fg=TEXT_HINT, font=(FONT, 11)).pack(
                        anchor="e", padx=14, pady=(0, 8))
                else:
                    tk.Label(card, text="Сообщений нет", bg=CARD, fg=TEXT_HINT,
                             font=(FONT, 12)).pack(anchor="w", padx=14, pady=(0, 8))
                card.bind("<Button-1>", lambda e, c=ch: self._open_chat(c))

        def refresh():
            def ok(data):
                render(data)
                self._schedule_poll(refresh, 10000)

            self._exec(lambda: self.api.get_chats(), ok=ok)

        foot = tk.Frame(self.root, bg=BG)
        foot.pack(fill="x", padx=12, pady=(0, 10))
        row = tk.Frame(foot, bg=BG)
        row.pack(fill="x", pady=4)
        _btn(row, "🔄 Обновить", DARK_GRAY, refresh, height=38, fs=12,
             outlined=True).pack(side="left", expand=True, fill="x", padx=(0, 6))
        _btn(row, "➕ Новый чат", PRIMARY, self._chat_new, height=38, fs=13).pack(
            side="left", expand=True, fill="x", padx=(6, 0))

        render([])
        refresh()

    def _open_chat(self, ch):
        title = (ch.get("other_user_name") if ch["type"] == "dm"
                 else (ch.get("name") or "Чат"))
        self._switch(self.show_chat_room, ch["id"], title, ch["type"])

    def show_chat_room(self, chat_id, title, chat_type):
        self._clear()
        self.root.geometry("820x680")
        self.root.title(title)
        self._toolbar(title, DARK_GRAY, back=True)

        s = auth_store.get_session()
        my_id = s.get("user_id")
        state = {"last_id": 0, "msgs": []}

        container = tk.Frame(self.root, bg=BG)
        container.pack(fill="both", expand=True, padx=12, pady=(8, 4))
        inner = self._scrollable(container)

        input_frame = tk.Frame(self.root, bg=BG)
        input_frame.pack(fill="x", padx=12, pady=(0, 10))
        e_text = _entry(input_frame, DARK_GRAY, 60, fs=13)
        e_text.pack(side="left", fill="x", expand=True, padx=(0, 8))
        e_text.bind("<Return>", lambda ev: send())

        def add_members():
            users = self._try_users()
            if users is None:
                return
            picked = self._pick_users("Добавить участников", users)
            if picked is None or not picked:
                return

            def ok(_):
                messagebox.showinfo("Готово", "Участники добавлены", parent=self.root)

            self._exec(lambda: self.api.add_chat_members(chat_id, [u["id"] for u in picked]),
                       ok=ok)

        if chat_type == "group":
            _btn(input_frame, "➕ участника", DARK_GRAY, add_members, height=34, fs=12,
                 outlined=True).pack(side="right", padx=(0, 8))
        _btn(input_frame, "➤", PRIMARY, send, height=34, fs=14).pack(side="right")

        def render(msgs):
            state["msgs"] = msgs
            for w in inner.winfo_children():
                w.destroy()
            if not msgs:
                tk.Label(inner, text="Сообщений пока нет. Напишите первым!",
                         bg=BG, fg=TEXT_HINT, font=(FONT, 12)).pack(pady=24)
            for m in msgs:
                own = m.get("sender_id") == my_id
                bg_card = GOOD_BG if own else CARD
                card = tk.Frame(inner, bg=bg_card, highlightbackground=BORDER,
                                highlightthickness=1, bd=0)
                card.pack(fill="x", pady=3, padx=2, anchor="e" if own else "w")
                if chat_type != "dm" and not own:
                    tk.Label(card, text=m.get("sender_name") or "Удалён", bg=bg_card,
                             fg=ORANGE, font=(FONT, 11, "bold")).pack(
                        anchor="w", padx=12, pady=(6, 0))
                tk.Label(card, text=m.get("text", ""), bg=bg_card, fg=TEXT, justify="left",
                         wraplength=700, font=(FONT, 13)).pack(anchor="w", padx=12, pady=(4, 0))
                tk.Label(card, text=self._chat_time(m.get("created_at")), bg=bg_card,
                         fg=TEXT_HINT, font=(FONT, 10)).pack(anchor="e", padx=12, pady=(0, 4))
            inner.update_idletasks()
            try:
                inner._canvas.yview_moveto(1.0)
            except Exception:
                pass

        def mark_read():
            if state["last_id"]:
                self._exec(lambda: self.api.mark_chat_read(chat_id, state["last_id"]))

        def load_history():
            def ok(data):
                msgs = data.get("messages") or []
                state["last_id"] = msgs[-1]["id"] if msgs else 0
                render(msgs)
                mark_read()
                self._schedule_poll(poll_new, 5000)

            self._exec(lambda: self.api.get_chat_messages(chat_id, after_id=0, limit=200),
                       ok=ok)

        def poll_new():
            def ok(data):
                fresh = data.get("messages") or []
                if fresh:
                    state["last_id"] = fresh[-1]["id"]
                    render(state["msgs"] + fresh)
                    mark_read()
                self._schedule_poll(poll_new, 5000)

            self._exec(lambda: self.api.get_chat_messages(chat_id, after_id=state["last_id"]),
                       ok=ok)

        def send():
            text = e_text.get().strip()
            if not text:
                return
            e_text.delete(0, "end")

            def ok(msg):
                state["last_id"] = msg["id"]
                render(state["msgs"] + [msg])
                mark_read()

            self._exec(lambda: self.api.send_chat_message(chat_id, text), ok=ok)

        load_history()


def main():
    root = tk.Tk()
    app = App(root)
    app.api.token = auth_store.get_session().get("token")
    app._start_invite_poll()
    app.show_start()
    root.mainloop()


if __name__ == "__main__":
    main()