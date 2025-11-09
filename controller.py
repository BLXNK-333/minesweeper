from model import MinesweeperModel
from view import MinesweeperView


class MinesweeperController:
    def __init__(self):
        self.model = MinesweeperModel(self)
        self.view = MinesweeperView(self)
        self.view.protocol("WM_DELETE_WINDOW", self.program_close_handler)

    def program_close_handler(self):
        """
        Обработчик закрытия программы
        """
        self.view.withdraw()
        self.model.save_settings()
        self.view.destroy()

    def new_game_handler(self, event):
        """
        Обработчик кнопки New Game. Начинает новую игру
        """
        if self.view.modal:
            self.view.modal.destroy()
        self.model.game_over = False
        self.model.block_game_field = False
        self.model.reload_board()
        self.view.game_field.update_buttons()
        self.view.bottom_panel.timer.clear_timer()
        self.view.bottom_panel.bomb_counter.clear_bomb_counter()
        self.view.update_idletasks()

    def pause_game_handler(self, event):
        """
        Обработчик кнопки Pause. Останавливает или возобновляет игру
        """
        if self.model.get_game_status():
            if self.view.bottom_panel.timer.running:
                self.view.bottom_panel.timer.stop_timer()
                self.view.paused_notify()
                self.view.bottom_panel.timer.start_timer()
            self.view.bottom_panel.timer.update_timer()

    def score_game_handler(self):
        """
        Обработчик кнопки "Score". Вызывает таблицу со счетом по запросу игрока
        """
        self.view.show_table_with_score(self.model.scoreboard.records, None)

    def program_call_scoreboard_handler(self, time: str):
        """
        Вызов от контроллера происходит в том случае, если игрок победил
        и его время подходит для таблицы рекордов

        :param time: Время игрока, для вставки в таблицу
        """
        new_records = self.model.scoreboard.get_modify_table_records(time)
        response = self.view.show_table_with_score(new_records, "root")
        if response:
            self.model.scoreboard.update_table_records(response)

    def change_difficulty_handler(self, event):
        """
        Обработчик событий с combobox на top panel, устанавливает выбранный уровень сложности
        """
        self.view.top_panel.difficulty_box.selection_clear()

        if self.model.get_game_status() and not self.view.new_game_notify():
            return
        self.view.withdraw()
        current_difficulty = self.view.top_panel.difficulty_box.get()
        self.model.set_difficulty(current_difficulty)
        self.new_game_handler(event)
        self.view.update_window_size()
        self.view.deiconify()

    def left_click_handler(self, button):
        """
        Обработка левого клика по игровому полю
        """

        # Начало игры. Если игра закончилась или установлена метка, то return иначе старт новой игры
        if self.model.block_game_field or button["text"] and button.is_bomb:
            return
        self.is_first_click_on_the_board(button)

        # Обработка клика
        bombs_set = set()
        if button["text"]:
            bombs_set |= self.clicked_on_the_number(button)
        else:
            bombs_set |= self.clicked_on_an_empty_cell(button)

        # Проверка на поражение или победу
        if len(bombs_set) == 1 and self.model.check_lose(bombs_set):
            self.is_lose(button)
        elif self.model.check_win():
            self.is_win()
        else:
            self.view.game_field.uncover_the_clearing(bombs_set)

    def right_click_handler(self, button):
        """
        Обработка правого клика по игровому полю
        """
        if self.model.get_game_status() and not button.is_open:
            button.mark_the_bomb()
            self.model.set_mark_bomb(button.bomb_mark, button.coord_x, button.coord_y)
            self.view.bottom_panel.bomb_counter.update_bomb_counter(button["text"])

    def clicked_on_an_empty_cell(self, button) -> set:
        """
        Переход, если игрок кликнул по закрытой ячейке
        """
        return self.model.bfs(button.coord_x, button.coord_y)

    def clicked_on_the_number(self, button) -> set:
        """
        Переход, если игрок кликнул по цифре
        """
        x, y = button.coord_x, button.coord_y
        bombs_set = self.view.game_field.get_coordinates_marked_bombs_nearby(x, y)
        response = self.model.compare_marked_bombs_with_real_ones(bombs_set, x, y)
        if response is True:
            return self.model.bfs(x, y, bombs_set)
        if response == 'lose':
            self.is_lose(button)
        return set()
            
    def is_first_click_on_the_board(self, button):
        """
        Проверка перед новой игрой, если идет уже идет, то возвращает None
        """
        if not self.model.get_game_status():
            self.model.game_over = False
            if self.model.swap_if_bomb(button.coord_x, button.coord_y):
                self.view.game_field.update_buttons()
            self.view.bottom_panel.timer.start_timer()

    def is_win(self):
        """
        Скрипт победы
        """
        self.set_general_game_ending_options()
        self.view.game_field.uncover_all_buttons()
        time = self.view.bottom_panel.timer.get_strip_time()
        if self.model.scoreboard.check_time(time):
            self.program_call_scoreboard_handler(time)
        else:
            self.view.win_notify()

    def is_lose(self, button):
        """
        Скрипт поражения
        """
        self.set_general_game_ending_options()
        self.view.game_field.uncover_all_mines(self.model.mines_cells)
        self.view.game_field.highlight_explosion(button)
        self.view.lose_notify()

    def set_general_game_ending_options(self):
        """
        Применяет общие параметры при победе или поражении
        """
        self.model.game_over = True
        self.model.block_game_field = True
        self.view.bottom_panel.timer.stop_timer()

    def get_current_difficulty(self) -> str:
        """
        Запрашивает у model текущий уровень сложности
        """
        return self.model.difficulty

    def get_field_size(self):
        """
        Запрашивает у model размер игрового поля
        """
        return self.model.rows, self.model.cols

    def get_bombs_amount(self):
        """
        Запрашивает количество бомб для установленной доски
        """
        return self.model.num_mines

    def get_cell_value(self, i: int, j: int) -> int:
        """
        Запрашивает у model значение ячейки
        """
        return self.model.board[i][j]

    def run(self):
        self.view.mainloop()

