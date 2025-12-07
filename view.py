import tkinter as tk
from tkinter import ttk
from functools import partial
from time import time
import json


class MinesweeperView(tk.Tk):
    """Главный класс View, отвечает за поведение главного окна, также через него
    создаются все элементы интерфейса"""

    def __init__(self, controller):
        super().__init__()
        self.withdraw()
        self.controller = controller
        self.modal = None
        self.title("Minesweeper")

        self.style = UIStyles(self)
        self.top_panel = TopPanel(self, self.controller)
        self.game_field = GameField(self, self.controller)
        self.bottom_panel = BottomPanel(self, self.controller)

        self.top_panel.make_top_panel()
        self.game_field.make_all_buttons()
        self.update_window_size()
        self.bottom_panel.timer.update_timer()
        self.deiconify()

    def update_window_size(self) -> None:
        """Обновляет размер главного окна при старте или при растягивании"""
        self.update_idletasks()
        min_w = self.winfo_reqwidth()
        min_h = self.winfo_reqheight()
        scr_w = self.winfo_screenwidth()
        scr_h = self.winfo_screenheight()
        self.geometry(f"{min_w}x{min_h}+{(scr_w - min_w) // 2}+{(scr_h - min_h) // 2}")

    def show_table_with_score(self, records: json, user: [str, None]) -> [json, None]:
        """Вызывает модальное окно с таблицей со счетом.
        Ждет от функции ниже ответ и возвращает его, либо json с новым временем либо None"""
        scoreboard = ViewScoreboard(self, records, user)
        self.bind("<Configure>", scoreboard.on_main_window_move)
        return scoreboard.make_scoreboard()

    def modal_instance(self):
        """Общие параметры для модальных окон"""
        self.modal = Modal(self)
        self.bind("<Configure>", self.modal.on_main_window_move)
        return self.modal

    def new_game_notify(self):
        """Вызывает модальное окно с запросом нужно ли начинать новую игру"""
        return self.modal_instance().new_game_modal()

    def win_notify(self):
        """Вызывает модальное окно уведомлением о победе"""
        return self.modal_instance().notification("You have won.")

    def lose_notify(self):
        """Вызывает модальное окно уведомлением о поражении"""
        return self.modal_instance().notification("You have lost.")

    def paused_notify(self):
        """Вызывает модальное окно паузы, блокирует интерфейс"""
        return self.modal_instance().paused_modal()


class Modal(tk.Toplevel):
    """Класс с модальными окнами и уведомлениями"""

    def __init__(self, master, *args):
        super().__init__(master, *args)
        self.transient(master)
        self.resizable(False, False)
        self.title = ""
        self.configure(bg="#272727")
        self.response = None

    def on_main_window_move(self, event):
        """Обработчик события перемещения основного окна"""
        for win in self.master.winfo_children():
            if isinstance(win, tk.Toplevel):
                self.update_popup_size()

    def update_popup_size(self):
        """Устанавливает координаты всплывающего окна"""
        main_x = self.master.winfo_rootx() + self.master.winfo_width() // 2
        main_y = self.master.winfo_rooty() + self.master.winfo_height() // 2
        popup_x = main_x - self.winfo_reqwidth() // 2
        popup_y = main_y - self.winfo_reqheight() // 2
        self.geometry("+{}+{}".format(popup_x, popup_y))

    def block_main_window(self) -> None:
        """Блокирует основное окно"""
        self.wait_visibility()
        self.update_popup_size()
        self.grab_set()

    def modal_handler(self, event: str):
        """Закрывает диалоговое окно"""
        self.response = True if event == "YES" else False
        self.destroy()

    def new_game_modal(self):
        """Спрашивает нужно ли начинать новую игру, если игра уже идет"""

        ttk.Label(self, text="Start a new game?", style="White.TLabel").pack(padx=10, pady=10)
        container = ttk.Frame(self, style="Header.TFrame")
        container.pack(padx=10)
        self.make_modal_btn(container, "YES", "Dark2.TButton", self.modal_handler)
        self.make_modal_btn(container, "NO", "Dark2.TButton", self.modal_handler)
        self.block_main_window()
        self.wait_window()
        return self.response

    def paused_modal(self):
        """Уведомляет о выигрыше или выигрыше"""
        label = ttk.Label(self, text="Paused", style="White.TLabel", anchor="center", justify="center", width=25)
        label.pack(expand=True, fill="both", pady=10)
        container = ttk.Frame(self, style="Header.TFrame")
        container.pack(padx=10, pady=5)
        self.make_modal_btn(container, "Cancel", "Dark2.TButton", self.modal_handler)
        self.block_main_window()
        self.wait_window()

    def notification(self, _text: str):
        """Уведомляет о выигрыше или выигрыше"""
        label = ttk.Label(self, text=_text, style="White.TLabel", anchor="center", justify="center", width=25)
        label.pack(expand=True, fill="both", pady=35)
        self.after(1500, self.destroy)
        self.wait_visibility()
        self.update_popup_size()

    @staticmethod
    def make_modal_btn(master, text_btn: str, style_btn: str, handler):
        """Кнопка для диалогового окна"""
        btn = ttk.Button(master, text=text_btn, style=style_btn, takefocus=False,
                         command=partial(handler, text_btn))
        btn.pack(padx=2, pady=10, side=tk.LEFT)
        return btn


class ViewScoreboard(Modal):
    """Этот класс представляет таблицу рекордов в виде интерфейса, который работает с JSON-файлом
    в качестве базы данных для хранения рекордов игроков. При внесении изменений,
    таких как установка нового рекорда, класс обновляет соответствующие данные в JSON-файле и возвращает его.
    Если изменений не было, возвращается None."""

    def __init__(self, master, records: json, user: [str, None]) -> None:
        """
        :param master: Родительский виджет
        :param records: Таблица рекордов
        :param user: Указывает, от кого приходит вызов ("root" или None)
        """
        super().__init__(master)
        self.user = user
        self.records = records
        self.tables = {}
        self.bottom_containers = {}
        self.current_page = records["CurrentDifficulty"]
        self.user_input = tk.StringVar(value=self.records["LastPlayer"])
        self.entry = None
        self.entry_difficulty_page = None
        self.keys = ["Easy", "Medium", "Hard"]
        self.labels = {k: {1: [], 2: []} for k in self.keys}

    def make_scoreboard(self):
        """Функция для создания модального окна с таблицей рекордов"""
        inner = tk.Frame(self, padx=10, pady=10, bg="#272727")
        inner.pack(side="top", fill="y")
        frame_menu_btn = tk.Frame(inner, bg="#383838")
        frame_menu_btn.pack(side="left", fill="y")
        for key in self.keys:
            self.tables[key] = {"button": self.make_menu_button(frame_menu_btn, key),
                                "table": self.make_table(inner, key)}
        self.menu_btn_handler(self.tables[self.current_page]["button"], self.current_page)
        self.make_trash_button()
        self.make_bottom_containers()
        self.behavior_of_the_bottom_buttons()
        self.block_main_window()
        self.wait_window()
        return self.response  # <<<---- Возврат здесь

    def make_trash_button(self):
        """Создает кнопку корзины"""
        trash_container = ttk.Frame(self, style="Header.TFrame")
        trash_container.pack(side="left", padx=(7, 0), pady=(8, 5), fill="y")
        ttk.Button(trash_container, text="🗑", width=2, style="Trash.TButton", takefocus=False,
                   command=self.trash_handler).pack()

    def trash_handler(self):
        """Описывает поведение кнопки корзины"""
        self.records[self.current_page] = [["-", "-"] for _ in range(10)]
        for col in (1, 2):
            for label in self.labels[self.current_page][col]:
                label["text"] = "-"
        if self.entry and (self.current_page == self.entry_difficulty_page):
            self.switch_bottom_container("two", "one")
            self.entry.destroy()
        self.response = self.records

    def behavior_of_the_bottom_buttons(self):
        """Описывает поведение нижних кнопок"""
        if self.user:
            self.make_entry_field()
            self.switch_bottom_container("one", "two")
        else:
            self.switch_bottom_container("two", "one")

    def switch_bottom_container(self, hide_key, show_key):
        """Переключает нижние контейнеры"""
        self.bottom_containers[hide_key].pack_forget()
        self.bottom_containers[show_key].pack(expand=True)

    def make_bottom_containers(self):
        """Создает контейнеры с кнопками, в нижнем блоке"""
        frame = ttk.Frame(self, style="Header.TFrame")
        frame.pack(fill=tk.X, padx=(0, 10), expand=True)
        container1 = ttk.Frame(frame, style="Header.TFrame")
        self.make_modal_btn(container1, "Close", "Dark2.TButton", self.control_btn_handler)
        container2 = ttk.Frame(frame, style="Header.TFrame")
        self.make_modal_btn(container2, "Forget", "Dark2.TButton", self.control_btn_handler)
        self.make_modal_btn(container2, "Save", "Dark2.TButton", self.control_btn_handler)
        self.bottom_containers = {
            "one": container1, "two": container2
        }

    def make_entry_field(self):
        """Создает поле для ввода имени игрока"""
        entry = ttk.Entry(self.tables[self.records["CurrentDifficulty"]]["table"],
                          style="Input.TEntry", width=9, textvariable=self.user_input)
        entry.grid(row=self.records["Index"] + 1, column=1, sticky="we")
        entry.select_range(0, tk.END)
        entry.icursor(tk.END)
        entry.focus_set()
        strip = entry.register(lambda text: len(text) <= 10)
        entry.config(validate="key", validatecommand=(strip, "%P"))
        self.entry = entry
        self.entry_difficulty_page = self.current_page

    def make_menu_button(self, master, btn_text: str):
        """Создает "анимированные" кнопки меню"""
        font = ('Helvetica', 12)
        btn = tk.Canvas(master)
        btn.btn_text = btn_text
        btn.config(width=font[1] * 2, height=font[1] * 6, bg="#272727", highlightthickness=0)
        btn.create_text(font[1], font[1] * 3.5, text=btn_text, font=font, anchor="center", angle=90, fill="white")
        btn.bind("<Button-1>", partial(self.menu_btn_handler, key=btn_text))
        btn.bind("<Enter>", partial(self.on_hover, color="#5b5b5b"))
        btn.bind("<Leave>", partial(self.on_hover, color="#272727"))
        btn.pack(side="top", fill="both", expand=True)
        return btn

    def make_table(self, master, key: str):
        """Создает контейнер с таблицей рекордов"""
        frame = tk.Frame(master, bg="#383838", padx=10, pady=5)
        headers = ["Rank", "Name", "Time"]

        for i, header in enumerate(headers):
            label = ttk.Label(frame, text=header, style="TableHeader.TLabel")
            label.grid(row=0, column=i, padx=5, pady=5)

        for i in range(1, 11):
            label = ttk.Label(frame, text=f"#{i}", style="TableRow.TLabel")
            label.grid(row=i, column=0, padx=5, pady=1, sticky="w")

        for row_index, row_data in enumerate(self.records[key], start=1):
            for col_index, cell_data in enumerate(row_data, start=1):
                label = ttk.Label(frame, text=cell_data, style="TableRow.TLabel")
                # Здесь добавляем ссылку на метку в хэш таблицу
                self.labels[key][col_index].append(label)
                if col_index == 1:
                    label.configure(width=10)
                if col_index == 2:
                    label.configure(width=5)
                label.grid(row=row_index, column=col_index, padx=5, pady=1, sticky="w")
        return frame

    def control_btn_handler(self, event):
        """Обработчик кнопок для взаимодействия с игроком"""
        if event == "Save":
            inp_name = self.user_input.get().strip(" ")
            if len(inp_name):
                idx = self.records["Index"]
                cur_page = self.current_page

                self.records["LastPlayer"] = inp_name
                self.records[cur_page][idx][0] = inp_name
                self.response = self.records

                label = self.labels[cur_page][1][idx]
                label.configure(text=inp_name)
                self.entry.destroy()
                self.switch_bottom_container("two", "one")
        else:
            self.destroy()

    def menu_btn_handler(self, event, key):
        """Обработчик для кнопок меню"""
        self.tables[self.current_page]["button"].config(bg="#272727")
        self.tables[self.current_page]["table"].pack_forget()
        self.current_page = key
        self.tables[self.current_page]["button"].config(bg="#383838")
        self.tables[key]["table"].pack(side="left", fill="both", expand=True)

    def on_hover(self, event, color):
        """Подсветка кнопки меню при наведении"""
        if event.widget.btn_text != self.current_page:
            event.widget.configure(bg=color)


class TopPanel(ttk.Frame):
    """Создание верхней панели, кнопок и combobox"""

    def __init__(self, master, controller):
        super().__init__(master, style="Header.TFrame")
        self.pack(side=tk.TOP, fill=tk.X)
        self.controller = controller
        self.difficulty_box = None
        self.difficulty = ["Easy", "Medium", "Hard"]

    def make_top_panel(self):
        self.make_top_buttons()
        self.make_combobox()

    def make_top_buttons(self):
        """Создает кнопки в левом углу панели"""
        left_block = ttk.Frame(self, style="Header.TFrame")
        left_block.pack(side=tk.LEFT, fill=tk.X)
        self.make_header_button(left_block, "New game", (1, 1), self.controller.new_game_handler)
        self.make_header_button(left_block, "Pause", (1, 2), self.controller.pause_game_handler)
        ttk.Button(left_block, text="📌", width=2, style="Dark.TButton", takefocus=False,
                   command=self.controller.score_game_handler).grid(row=1, column=3)

    def make_combobox(self):
        """Создает combobox в правом углу панели"""
        right_block = ttk.Frame(self, style="Header.TFrame")
        right_block.pack(side=tk.RIGHT, fill=tk.X)
        self.difficulty_box = ttk.Combobox(right_block, values=self.difficulty, width=7, state="readonly",
                                           style="Dark.TCombobox")
        self.difficulty_box.grid(row=1, column=2, padx=5)
        self.difficulty_box.bind("<<ComboboxSelected>>", self.controller.change_difficulty_handler)
        current_difficulty = self.controller.get_current_difficulty()
        self.difficulty_box.current(self.difficulty.index(current_difficulty))

    @staticmethod
    def make_header_button(master, button_text: str, position: tuple, handler) -> ttk.Button:
        """Создает стилизованную кнопку для Header"""
        x, y = position
        button = ttk.Button(master, text=button_text, style="Dark.TButton", takefocus=False,
                            command=partial(handler, button_text))
        button.grid(row=x, column=y, padx=2, pady=2, sticky="nsew")
        return button


class BottomPanel(ttk.Frame):
    """Создание нижней панели с таймером и информацией о минах"""

    def __init__(self, master, controller):
        super().__init__(master, style="Header.TFrame")
        self.controller = controller
        self.pack(fill=tk.X)

        self.inner_frame = ttk.Frame(self, style="Header.TFrame")
        self.inner_frame.pack()
        self.timer = Timer(self.inner_frame)
        self.timer.pack(side=tk.LEFT, padx=5)
        self.bomb_counter = BombsCounter(self.inner_frame, controller)
        self.bomb_counter.pack(side=tk.LEFT, padx=5)


class BombsCounter(ttk.Frame):
    """Создает счетчик бомб в контейнере"""

    def __init__(self, master, controller):
        super().__init__(master, style="Header.TFrame")

        self.controller = controller
        self.counter = 0
        self.total_bombs = self.controller.get_bombs_amount()
        self.screen_counter = tk.StringVar()

        label = ttk.Label(self, textvariable=self.screen_counter, style="White.TLabel")
        label.pack()
        self.clear_bomb_counter()

    def update_bomb_counter(self, value: str):
        self.counter += 1 if value else -1
        self.screen_counter.set(f"Mines: {self.counter}/{self.total_bombs}")

    def clear_bomb_counter(self):
        self.counter = 0
        self.total_bombs = self.controller.get_bombs_amount()
        self.screen_counter.set(f"Mines: 0/{self.total_bombs}")


class Timer(ttk.Frame):
    """Создает таймер в контейнере"""

    def __init__(self, master):
        super().__init__(master, style="Header.TFrame")

        self.running = False
        self.start_time = None
        self.pause_time = None
        self.screen_time = tk.StringVar()

        label = ttk.Label(self, textvariable=self.screen_time, style="White.TLabel")
        label.pack()
        self.clear_timer()

    def update_timer(self) -> None:
        """Функция счетчика, обновляет значение в подключенной переменной StringVar"""
        if self.running:
            elapsed_time = int(time() - self.start_time)
            minutes, seconds = divmod(elapsed_time, 60)
            self.screen_time.set(f"Time: {minutes:02}:{seconds:02}")
            self.after(1000, self.update_timer)

    def start_timer(self):
        """Запускает таймер"""
        if not self.running:
            self.running = True
            if self.start_time is None:
                self.start_time = time()
            else:
                self.start_time += time() - self.pause_time
            self.update_timer()

    def stop_timer(self):
        """Останавливает таймер"""
        if self.running:
            self.running = False
            self.pause_time = time()

    def clear_timer(self):
        """Устанавливает таймер на 0"""
        self.screen_time.set("Time: 00:00")
        self.running = False
        self.start_time = None

    def get_strip_time(self):
        """Возвращает обрезанное время"""
        return self.screen_time.get()[-5:]


class GameField(ttk.Frame):
    """Создание игрового поля и его кнопок"""

    def __init__(self, master, controller):
        super().__init__(master)
        self.master = master
        self.controller = controller
        self.buttons = []
        self.buttons_container = self.make_container_for_buttons()
        self.max_n, self.max_m = 16, 30
        self.n, self.m = None, None
        self.neighbors = ((-1, -1), (-1, 0), (-1, 1), (0, 1), (1, 1), (1, 0), (1, -1), (0, -1))

    def make_container_for_buttons(self) -> ttk.Frame:
        """Создает контейнер для игрового поля"""
        main = ttk.Frame(self.master, padding="10 10 10 20", style="Field.TFrame")
        main.pack(fill=tk.BOTH, expand=True)
        inner = ttk.Frame(main, style="FieldInner.TFrame", padding="2")
        inner.pack(expand=True)
        return inner

    def make_all_buttons(self):
        """Создает кнопки для игрового поля"""
        for i in range(1, self.max_n + 1):
            row = []
            for j in range(1, self.max_m + 1):
                btn = GameFieldButton(self.buttons_container, i, j)
                btn.bind("<Button-1>", lambda event, button=btn: self.controller.left_click_handler(button))
                btn.bind("<Button-3>", lambda event, button=btn: self.controller.right_click_handler(button))
                btn.unbind("<Double-Button-1>")
                btn.unbind("<Double-Button-3>")
                row.append(btn)
            self.buttons.append(row)
        self.update_buttons()

    def update_buttons(self):
        """Включает или выключает кнопки в зависимости от уровня сложности"""
        self.n, self.m = self.controller.get_field_size()
        for i in range(self.max_n):
            for j in range(self.max_m):
                if i < self.n and j < self.m:
                    btn = self.buttons[i][j]
                    self.update_btn_value(btn)
                    btn.grid(row=i, column=j)
                else:
                    self.buttons[i][j].grid_forget()

    def update_btn_value(self, button) -> None:
        """Отправляет запрос в контроллер, для получения значения в ячейке"""
        button.reload_button(self.controller.get_cell_value(button.coord_x, button.coord_y))

    def uncover_the_clearing(self, coord: set) -> None:
        """Принимает координаты и открывает просеку по ним"""
        for i, j in coord:
            btn = self.buttons[i][j]
            btn.uncover_button()

    def uncover_all_buttons(self) -> None:
        """Открывает все ячейки при победе"""
        [self.buttons[i][j].uncover_button() for i in range(self.n) for j in range(self.m)]

    def uncover_all_mines(self, hashset: set) -> None:
        """Открывает все ячейки с минами при поражении, остальные блокирует"""
        for i in range(self.n):
            for j in range(self.m):
                btn = self.buttons[i][j]
                if (btn.coord_x, btn.coord_y) in hashset:
                    btn.uncover_bomb()
                elif btn.bomb_mark:
                    btn.wrong_label()
                elif not btn.is_open:
                    btn.disable_button()

    def highlight_explosion(self, button):
        """Подсвечивает ячейки на которых подорвался игрок"""
        if button.is_bomb:
            return button.bomb_exploded()
        x, y = button.coord_x - 1, button.coord_y - 1
        for di, dj in self.neighbors:
            i, j = x + di, y + dj
            if 0 <= i < self.n and 0 <= j < self.m:
                btn = self.buttons[i][j]
                if btn.is_bomb and not btn.bomb_mark:
                    btn.bomb_exploded()

    def get_coordinates_marked_bombs_nearby(self, x: int, y: int) -> set:
        """Проверяет соседние ячейки на метку, возвращает set с координатами
        помеченных игроком ячеек. x, y координаты самой себя"""
        bombs_set = set()
        x -= 1
        y -= 1
        for di, dj in self.neighbors:
            i, j = x + di, y + dj
            if 0 <= i < self.n and 0 <= j < self.m and self.buttons[i][j].bomb_mark:
                bombs_set.add((self.buttons[i][j].coord_x, self.buttons[i][j].coord_y))
        return bombs_set


class GameFieldButton(ttk.Button):
    """Кнопки для игрового поля"""

    mark = "⚑"
    error = "❌"

    style_map = {
        "1": "One", "2": "Two", "3": "Three", "4": "Four", "5": "Five",
        "6": "Six", "7": "Seven", "8": "Eight", mark: "Bomb", "": "Empty"
    }

    def __init__(self, master, x, y):
        super().__init__(master, width=2, takefocus=False)
        self.coord_x = x
        self.coord_y = y
        self.value = None
        self.is_open = False
        self.is_bomb = None
        self.bomb_mark = False

    def reload_button(self, value: int):
        """Устанавливает дефолтные параметры для кнопки"""
        self.value = self.set_button_value(value)
        self.is_open = False
        self.is_bomb = True if self.value == GameFieldButton.mark else False
        self.bomb_mark = False
        self.configure(text="", state="normal", style="Default.TButton")

    def uncover_button(self):
        """Открывает значение value и блокирует кнопку"""
        self.configure(text=self.value, state="normal",
                       style=f"{GameFieldButton.style_map[self.value]}.TButton")
        if not self.value:
            self.configure(state="disabled")
        self.is_open = True

    def mark_the_bomb(self):
        """Ставит или снимает бомбу по правому клику"""
        self["text"] = "" if self["text"] else GameFieldButton.mark
        self.bomb_mark = not self.bomb_mark

    def uncover_bomb(self):
        """Открывает кнопку с бомбой"""
        if self.bomb_mark:
            self.configure(text=self.value, state="disabled", style="UncoverMarked.TButton")
        else:
            self.configure(text=self.value, state="disabled", style="UncoverClosed.TButton")

    def bomb_exploded(self):
        """Подсвечивает ячейку на которой подорвался игрок"""
        self.configure(text=self.value, state="disabled", style="Exploded.TButton")

    def disable_button(self):
        """Отключает кнопку"""
        self.configure(text="", state="disabled")

    def wrong_label(self):
        """Подсвечивает ошибку игрока"""
        self.configure(text=GameFieldButton.error, state="disabled", style="WrongLabel.TButton")

    @staticmethod
    def set_button_value(value: int) -> str:
        """Устанавливает значение в value"""
        if not value:
            return ""
        elif value > 8:
            return GameFieldButton.mark
        return str(value)


class UIStyles(ttk.Style):
    """Стили для ViewUI"""

    # Определение базового стиля для кнопок игрового поля
    button_normal_kw = {
        "background": "#bbbbbb",
        "font": ("TkDefaultFont", 10, "bold"),
        "relief": "sunken"
    }

    button_disabled_kw = {
        "background": [("disabled", "#bbbbbb")],
        "font": [("disabled", ("TkDefaultFont", 10, "bold"))],
        "relief": [("disabled", "sunken")]
    }

    digit_color_map = {
        "One": "blue", "Two": "green", "Three": "red", "Four": "purple", "Five": "maroon",
        "Six": "#006e50", "Seven": "#1b1b1b", "Eight": "#464646", "Bomb": "#333333", "Empty": "black"
    }

    def __init__(self, master):
        super().__init__()
        self.make_frame_and_label_styles()
        self.make_buttons_styles()
        self.make_field_buttons_styles()
        self.make_combobox_style(master)
        self.make_scoreboard_table_styles()

    def make_frame_and_label_styles(self):
        """Создает стили для фреймов и меток в программе"""
        self.configure("Field.TFrame", background="#5b5b5b")
        self.configure("FieldInner.TFrame", background="grey")
        self.configure("Header.TFrame", background="#272727")

        self.configure("White.TLabel", background="#272727", foreground="white")
        self.configure("Popup.TLabel", background="#5b5b5b", foreground="white")

    def make_buttons_styles(self):
        """Создает стили для кнопок в программе"""
        self.configure("Dark.TButton", background="#272727", foreground="white", borderwidth=0)
        self.map("Dark.TButton", background=[("active", "#464646")])
        self.configure("Dark2.TButton", background="#464646", foreground="white", borderwidth=0)
        self.map("Dark2.TButton", background=[("active", "#5b5b5b")])
        self.configure("Trash.TButton", background="#272727", foreground="#c33200", borderwidth=0,
                       font=("Arial", 15))
        self.map("Trash.TButton", background=[("active", "#464646")])

        # Кнопки на игровом поле
        self.configure("Default.TButton", foreground="#222222", relief="raised")
        self.map("UncoverMarked.TButton", foreground=[("disabled", "#333333")])
        self.map("UncoverClosed.TButton", foreground=[("disabled", "#777777")])
        self.map("WrongLabel.TButton", foreground=[("disabled", "red")])
        self.map("Exploded.TButton", background=[("disabled", "#c5c477")],
                 foreground=[("disabled", "#222222")], relief=[("disabled", "sunken")])
        self.map("Default.TButton", relief=[("disabled", "raised")])

    def make_field_buttons_styles(self):
        """Создает стили для кнопок игрового поля в зависимости от значения"""
        for key, value in UIStyles.digit_color_map.items():
            self.configure(f"{key}.TButton", foreground=value, **UIStyles.button_normal_kw)
            self.map(f"{key}.TButton", foreground=[("disabled", value)], **UIStyles.button_disabled_kw)

    def make_combobox_style(self, master):
        """Создает тему для combobox"""

        # Настройка стилей для выпадающего списка Combobox
        master.option_add("*TCombobox*Listbox.background", "#272727")
        master.option_add("*TCombobox*Listbox.foreground", "#ffffff")
        master.option_add("*TCombobox*Listbox.selectBackground", "#464646")
        master.option_add("*TCombobox*Listbox.selectForeground", "#ffffff")

        self.configure("Dark.TCombobox", arrowcolor="#c8c8c8", background="#272727", foreground="#ffffff",
                       padding=(5, 0))
        self.map("Dark.TCombobox",
                 background=[("active", "#5b5b5b")],
                 fieldbackground=[("readonly", "#383838")])

    def make_scoreboard_table_styles(self):
        """Создает стили для таблицы со счетом"""
        self.configure("TableHeader.TLabel", background="#383838", foreground="white", font=("Arial", 11, "bold"))
        self.configure("TableRow.TLabel", background="#383838", foreground="white", font=("Arial", 11))
        self.configure("Input.TEntry", foreground="white", font=("Arial", 11),
                       fieldbackground="#272727", selectbackground="#4f6f80", insertcolor="white",
                       borderwidth=0)

