from random import sample, randint
import json
from Crypto.Cipher import AES
from copy import deepcopy
import os.path


class MinesweeperModel:
    def __init__(self, controller):
        """
        Инициализирует экземпляр MinesweeperModel.

        :param controller: Контроллер игры.
        """
        self.controller = controller
        self.encryptor = DataEncryptor(b'7yqZ7Fq^#3Cr3%nY')  # Длина должна быть 16 символов
        self.scoreboard = ModelScoreboard(self.encryptor.load_records())
        self.difficulty = self.scoreboard.get_last_difficulty()
        # self.scoreboard.set_default()

        self.mapp = {'Easy': (9, 9, 10), 'Medium': (16, 16, 40), 'Hard': (16, 30, 99)}
        self.neighbors = ((-1, -1), (-1, 0), (-1, 1), (0, 1), (1, 1), (1, 0), (1, -1), (0, -1))

        self.mines_cells = set()
        self.uncover_cells = set()
        self.marked_cells = set()
        self.game_over = True
        self.block_game_field = False

        self.rows, self.cols, self.num_mines = self.mapp[self.difficulty]
        self.board = self.make_board()
        self.number_of_cells_needed_to_win = self.get_number_of_cells_needed_to_win()

    def reload_board(self) -> None:
        """
        Генерирует новую доску и обнуляет параметры
        """
        self.uncover_cells = set()
        self.mines_cells = set()
        self.marked_cells = set()
        self.game_over = True
        self.number_of_cells_needed_to_win = self.get_number_of_cells_needed_to_win()
        self.board = self.make_board()

    def check_win(self) -> bool:
        """
        Проверка условия победы. True или False
        """
        return self.number_of_cells_needed_to_win == len(self.uncover_cells)

    def check_lose(self, coord_set: set) -> bool:
        """
        Проверка условия поражения, принимает координаты кликнутой ячейки в виде {(x, y)}
        Возвращает True, если по переданным координатам находится бомба, иначе False
        """
        x, y = next(iter(coord_set))
        return (x + 1, y + 1) in self.mines_cells

    def set_difficulty(self, difficulty: str) -> None:
        """
        Установка сложности игры. (Easy, Medium, Hard)
        """
        self.difficulty = difficulty
        self.scoreboard.records["CurrentDifficulty"] = difficulty
        self.rows, self.cols, self.num_mines = self.mapp[self.difficulty]

    def set_mark_bomb(self, status: bool, x: int, y: int) -> None:
        """
        Добавляет или удаляет координаты (x, y) в set с метками бомб игрока,
        при обходе в ширину эти координаты игнорируются.
        Status сигнализирует какое действие необходимо выполнить.
        """
        if status:
            self.marked_cells.add((x, y))
        else:
            self.marked_cells.remove((x, y))

    def get_number_of_cells_needed_to_win(self) -> int:
        """
        Возвращает количество ячеек которые нужно открыть для победы
        """
        return self.rows * self.cols - self.num_mines

    def get_game_status(self) -> bool:
        """
        Возвращает статус игры True если игра идет, и False если игра не началась или завершена
        """
        return bool(self.uncover_cells) and not self.game_over

    def make_board(self) -> list:
        """
        Генерирует игровую доску с границами из нулей по краям
        """
        board = [[0] * (self.cols + 2) for _ in range(self.rows + 2)]
        self.mines_cells = set(sample([(i, j) for i in range(1, self.rows + 1)
                                       for j in range(1, self.cols + 1)], self.num_mines))

        for i, j in self.mines_cells:
            board[i][j] = 9
        for i in range(1, self.rows + 1):
            for j in range(1, self.cols + 1):
                if board[i][j] > 8:
                    for di, dj in self.neighbors:
                        board[i + di][j + dj] += 1
        return board

    def swap_if_bomb(self, x: int, y: int) -> bool:
        """
        Генерирует координаты новой бомбы, если при первом клике по игровому полю находится мина.
        Обновляет соседей в матрице вокруг новой и старой бомбы и самих себя.
        Возвращает True если подмена была и False если нет.

        :param x: Координата x начальной ячейки.
        :param y: Координата y начальной ячейки.
        """

        if (x, y) not in self.mines_cells:
            return False
        dx, dy = x, y
        while (dx, dy) in self.mines_cells:
            dx = randint(1, self.rows)
            dy = randint(1, self.cols)
        self.mines_cells.remove((x, y))
        self.mines_cells.add((dx, dy))
        self.board[x][y] = 0
        self.board[dx][dy] = 9
        for i, j in self.neighbors:
            ni, nj = x + i, y + j
            if self.board[ni][nj] < 9:
                self.board[ni][nj] -= 1
            else:
                self.board[x][y] += 1
        for i, j in self.neighbors:
            ni, nj = dx + i, dy + j
            self.board[ni][nj] += 1
        return True

    def bfs(self, x: int, y: int, marked_bombs_nearby: set = None) -> set:
        """
        Обходит таблицу и возвращает множество ячеек, которые можно открыть после клика.

        :param x: Координата x начальной ячейки.
        :param y: Координата y начальной ячейки.
        :param marked_bombs_nearby: Соседи ячейки board[x][y], которые помечены как бомбы.
        """

        hashset = set()
        queue = set()
        queue.add((x, y))
        self_visited = False

        while queue:
            dx, dy = next(iter(queue))
            queue.remove((dx, dy))

            # Сюда заходим если игрок кликнул, по уже открытой цифре и пришел не пустой set marked_bombs_nearby
            if marked_bombs_nearby and not self_visited and (dx, dy) == (x, y):
                self_visited = True

                for di, dj in self.neighbors:
                    i, j = dx + di, dy + dj
                    if self.is_valid_cell(i, j):
                        if (i, j) not in marked_bombs_nearby:
                            queue.add((i, j))

            # Добавляем текущую ячейку в множество открываемых ячеек
            hashset.add((dx - 1, dy - 1))

            # Добавляем текущую ячейку в множество уже открытых ячеек
            self.uncover_cells.add((dx, dy))

            # Если текущая ячейка не пуста, пропускаем ее и переходим к следующей
            if self.board[dx][dy]:
                continue

            for di, dj in self.neighbors:
                i, j = dx + di, dy + dj
                if self.is_valid_cell(i, j):
                    queue.add((i, j))

        return hashset

    def is_valid_cell(self, i: int, j: int) -> bool:
        """Проверка для BFS"""
        return ((0 < i <= self.rows and 0 < j <= self.cols)
                and (i, j) not in self.uncover_cells and (i, j) not in self.marked_cells)

    def compare_marked_bombs_with_real_ones(self, bombs_set: set, x: int, y: int) -> any:
        """
        Сравнивает координаты помеченных бомб с реальными,
        возвращает true, если координаты помеченных, ячеек совпадают с реальными;
        возвращает false, если помеченных бомб меньше или больше, чем реальных;
        возвращает lose, если их количество совпадает, а координаты нет
        """
        truly = 0
        counter = 0
        for di, dj in self.neighbors:
            i, j = x + di, y + dj
            if self.board[i][j] > 8:
                counter += 1
                if (i, j) in bombs_set:
                    truly += 1
        if counter != len(bombs_set):
            return False
        if truly == counter:
            return True
        return 'lose'

    def save_settings(self) -> None:
        """
        Скрипт для сохранения таблицы рекордов с настройками в один файл
        """
        self.scoreboard.records["LastDifficulty"] = self.difficulty
        self.scoreboard.records["CurrentDifficulty"] = self.difficulty
        self.encryptor.save_records(self.scoreboard.records)


class DataEncryptor:
    """
    Класс для шифрования и дешифрования данных.
    """

    def __init__(self, key: bytes, block_size: int = 16) -> None:
        """
        Инициализация класса Cipher.

        :param key: Ключ для шифрования.
        :param block_size: Размер блока шифрования (по умолчанию 16).
        :return: None
        """
        self.KEY: bytes = key
        self.BLOCK_SIZE: int = block_size
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.path = os.path.join(current_dir, "records")

    def __pad(self, s: str) -> str:
        """
        Дополняет строку до кратности размеру блока.

        :param s: Строка для дополнения.
        :return: Дополненная строка.
        """
        return s + (self.BLOCK_SIZE - len(s) % self.BLOCK_SIZE) * chr(self.BLOCK_SIZE - len(s) % self.BLOCK_SIZE)

    def __unpad(self, s: str) -> str:
        """
        Удаляет дополнение из строки.

        :param s: Строка для удаления дополнения.
        :return: Строка без дополнения.
        """
        return s[:-ord(s[len(s) - 1:])]

    def __encrypt(self, message: str) -> bytes:
        """
        Шифрует сообщение, если сообщение повреждено игнорирует.

        :param message: Сообщение для шифрования.
        :return: Зашифрованное сообщение.
        """
        try:
            cipher = AES.new(self.KEY, AES.MODE_ECB)
            return cipher.encrypt(self.__pad(message).encode())
        except ValueError:
            pass

    def __decrypt(self, ciphertext: bytes) -> str:
        """
        Дешифрует сообщение, если сообщение повреждено игнорирует.

        :param ciphertext: Зашифрованное сообщение.
        :return: Дешифрованное сообщение.
        """
        try:
            cipher = AES.new(self.KEY, AES.MODE_ECB)
            decrypted_str: str = cipher.decrypt(ciphertext).decode()
            return self.__unpad(decrypted_str)
        except ValueError:
            pass

    def load_records(self) -> json:
        """
        Загружает настройки для игры из файла в контейнер json, если ловит ошибку, возвращает None.
        """
        try:
            with open(self.path, "rb") as file:
                encrypted_data = file.read()
                decrypted_data = self.__decrypt(encrypted_data)
                return json.loads(decrypted_data)
        except (FileNotFoundError, TypeError, json.JSONDecodeError):
            return None

    def save_records(self, jsn: json) -> None:
        """
        Сохраняет рекорды в файл.
        """
        encrypted_data = self.__encrypt(json.dumps(jsn))
        with open(self.path, "wb") as file:
            file.write(encrypted_data)


class ModelScoreboard:
    """
    Этот класс представляет таблицу рекордов в модели игры.
    Он передает данные в виде JSON и принимает JSON с изменениями.
    """

    def __init__(self, scoreboard: dict) -> None:
        """
        Инициализирует таблицу рекордов.

        :param scoreboard: Словарь существующей таблицы рекордов или None.
        """
        self.records = scoreboard or self.set_default()

    def get_last_difficulty(self) -> str:
        """
        Возвращает последний использованный уровень сложности
        или устанавливает его в "Medium", если нет данных.
        """
        try:
            return self.records["LastDifficulty"]
        except (KeyError, TypeError):
            self.set_default()
            return "Medium"

    def get_table_records(self) -> json:
        """
        Возвращает таблицу рекордов в формате JSON.
        """
        return self.records

    def get_modify_table_records(self, time: str) -> json:
        """
        Возвращает модифицированную таблицу рекордов (измененный JSON).

        :param time: Время для проверки.
        :return: Возвращает модифицированную таблицу рекордов в формате JSON.
        """
        modify_records = self.records.copy()  # Поверхностная копия
        new_array, new_index = self.append_record(time)
        modify_records[self.records["CurrentDifficulty"]] = new_array
        modify_records["Index"] = new_index
        return modify_records

    def update_table_records(self, records: json) -> None:
        """
        Обновляет таблицу рекордов.

        :param records: JSON с обновленными данными.
        """
        if records:
            self.records = records

    def check_time(self, time: str) -> bool:
        """
        Проверяет переданное время. Возвращает True, если лучше предыдущих, иначе False.

        :param time: Время для проверки.
        :return: True, если переданное время лучше предыдущих, иначе False.
        """
        difficulty = self.records["CurrentDifficulty"]
        if self.records[difficulty][9][1] == "-":
            return True
        return time < self.records[difficulty][9][1]

    def append_record(self, time: str) -> tuple[list, int]:
        """
        Эта функция создает новый список рекордов для текущего уровня сложности игры,
        в который вставляется новая запись о времени игрока. Затем она возвращает этот новый список и индекс,
        на котором была выполнена вставка новой записи.

        :param time: Время игрока.
        :return: Кортеж
        """
        array = deepcopy(self.records[self.records["CurrentDifficulty"]])
        i = 0
        for i in range(len(array)):
            if array[i][1] == "-" or time < array[i][1]:
                array.insert(i, [self.records["LastPlayer"], time])
                break
        array.pop()
        return array, i

    def set_default(self):
        """
        Устанавливает параметры по умолчанию для таблицы рекордов.
        """
        default = {
            # имя последнего игрока, для подстановки в поле ввода.
            "LastPlayer": "BLXNK",
            # установленный уровень сложности перед закрытием игры.
            "LastDifficulty": "Medium",
            # текущий уровень сложности.
            "CurrentDifficulty": "Medium",
            # индекс по которому были внесены изменения.
            "Index": 0
        }
        for level in ["Easy", "Medium", "Hard"]:
            default[level] = [["-", "-"] for _ in range(10)]
        self.records = default
