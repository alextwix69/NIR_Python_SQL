"""Учебная программа для работы с базой итогов промежуточной аттестации."""

from __future__ import annotations

import csv
import sqlite3
from datetime import date
from pathlib import Path


DB_PATH = Path(__file__).with_name("nir_stage3.sqlite")
TABLE = "attestation"
FIELDS = (
    "code",
    "discipline",
    "semester",
    "attestation_type",
    "attestation_date",
    "teacher",
    "teacher_position",
    "grade",
    "updated_at",
)
NUMERIC_FIELDS = {"semester", "grade"}
DATE_FIELDS = {"attestation_date", "updated_at"}
HEADERS = {
    "code": "Код дисциплины",
    "discipline": "Название дисциплины",
    "semester": "Семестр",
    "attestation_type": "Тип аттестации",
    "attestation_date": "Дата аттестации",
    "teacher": "ФИО преподавателя",
    "teacher_position": "Должность преподавателя",
    "grade": "Оценка",
    "updated_at": "Дата обновления",
}


def connect() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH)
    con.execute(
        """CREATE TABLE IF NOT EXISTS attestation (
            code TEXT NOT NULL,
            discipline TEXT NOT NULL,
            semester INTEGER NOT NULL,
            attestation_type TEXT NOT NULL,
            attestation_date TEXT NOT NULL,
            teacher TEXT NOT NULL,
            teacher_position TEXT NOT NULL,
            grade INTEGER NOT NULL,
            updated_at TEXT NOT NULL
        )"""
    )
    return con


def format_table(rows: list[tuple], fields: tuple[str, ...] = FIELDS) -> str:
    labels = [HEADERS[field] for field in fields]
    values = [["" if value is None else str(value) for value in row] for row in rows]
    widths = [max(len(labels[i]), *(len(row[i]) for row in values)) for i in range(len(fields))]
    line = "+" + "+".join("-" * (width + 2) for width in widths) + "+"
    out = [line, "| " + " | ".join(labels[i].ljust(widths[i]) for i in range(len(fields))) + " |", line]
    out.extend("| " + " | ".join(row[i].ljust(widths[i]) for i in range(len(fields))) + " |" for row in values)
    out.append(line)
    return "\n".join(out)


def show_rows(rows: list[tuple]) -> None:
    print(format_table(rows) if rows else "Записей нет.")


def read_value(field: str, prompt: str, allow_empty: bool = False):
    while True:
        value = input(prompt).strip()
        if value or allow_empty:
            break
        print("Поле не должно быть пустым.")
    if field in NUMERIC_FIELDS:
        try:
            return int(value) if value else None
        except ValueError:
            print("Введите целое число.")
            return read_value(field, prompt, allow_empty)
    if field in DATE_FIELDS and value:
        try:
            return date.fromisoformat(value).isoformat()
        except ValueError:
            print("Введите дату в формате ГГГГ-ММ-ДД.")
            return read_value(field, prompt, allow_empty)
    return value or None


def select_field(prompt: str, allowed: tuple[str, ...] = FIELDS) -> str:
    print("Доступные поля:")
    for index, field in enumerate(allowed, 1):
        print(f"{index}. {HEADERS[field]} ({field})")
    while True:
        value = input(prompt).strip()
        if value.isdigit() and 1 <= int(value) <= len(allowed):
            return allowed[int(value) - 1]
        if value in allowed:
            return value
        print("Выберите номер из списка или введите имя поля.")


def predicate_for(field: str) -> tuple[str, object] | None:
    operators = ("=", "!=", ">=", "<=", ">", "<", "contains")
    print("Условие: поле, оператор (=, !=, >, >=, <, <=, contains) и значение.")
    operator = input("Оператор: ").strip().lower()
    if operator not in operators:
        print("Неизвестный оператор.")
        return None
    value = read_value(field, "Значение условия: ", allow_empty=True)
    if operator == "contains":
        return f"{field} LIKE ?", f"%{value or ''}%"
    return f"{field} {operator} ?", value


def save_to_text(rows: list[tuple]) -> None:
    name = input("Имя текстового файла (например, result.txt): ").strip()
    if not name:
        print("Имя файла не задано.")
        return
    path = Path(name)
    if not path.is_absolute():
        path = Path(__file__).with_name(path.name)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, delimiter="\t")
        writer.writerow([HEADERS[field] for field in FIELDS])
        writer.writerows(rows)
    print(f"Сохранено строк: {len(rows)}. Файл: {path}")


def add_row(con: sqlite3.Connection) -> None:
    values = []
    for field in FIELDS[:-1]:
        values.append(read_value(field, f"{HEADERS[field]}: "))
    values.append(date.today().isoformat())
    try:
        con.execute(
            "INSERT INTO attestation (" + ", ".join(FIELDS) + ") VALUES (" + ", ".join("?" for _ in FIELDS) + ")",
            values,
        )
        con.commit()
        print("Запись добавлена.")
    except sqlite3.IntegrityError as exc:
        print(f"Не удалось добавить запись: {exc}")


def filter_and_change(con: sqlite3.Connection) -> None:
    field = select_field("Поле для условия: ")
    predicate = predicate_for(field)
    if predicate is None:
        return
    where, value = predicate
    rows = con.execute(f"SELECT {', '.join(FIELDS)} FROM attestation WHERE {where}", (value,)).fetchall()
    print(f"Найдено строк: {len(rows)}")
    show_rows(rows)
    if not rows:
        return
    print("1. Удалить найденные строки\n2. Заменить значение выбранного поля\n0. Назад")
    action = input("Операция: ").strip()
    if action == "1":
        con.execute(f"DELETE FROM attestation WHERE {where}", (value,))
        con.commit()
        print(f"Удалено строк: {con.execute('SELECT changes()').fetchone()[0]}")
    elif action == "2":
        target = select_field("Поле для замены: ")
        replacement = read_value(target, f"Новое значение для поля «{HEADERS[target]}»: ", allow_empty=True)
        if target == "updated_at":
            con.execute(f"UPDATE attestation SET {target} = ? WHERE {where}", (replacement, value))
        else:
            con.execute(
                f"UPDATE attestation SET {target} = ?, updated_at = ? WHERE {where}",
                (replacement, date.today().isoformat(), value),
            )
        changed = con.execute("SELECT changes()").fetchone()[0]
        con.commit()
        print(f"Обновлено строк: {changed}")
    elif action != "0":
        print("Неизвестная операция.")


def main() -> None:
    con = connect()
    try:
        fields = con.execute(f"PRAGMA table_info({TABLE})").fetchall()
        print("База данных:", DB_PATH)
        print("Поля таблицы:", ", ".join(row[1] for row in fields))
        while True:
            print(
                "\nМеню:\n"
                "1. Показать содержимое таблицы\n"
                "2. Сохранить содержимое в текстовый файл\n"
                "3. Отобрать строки и удалить или изменить их\n"
                "4. Добавить строку\n"
                "0. Завершить работу"
            )
            choice = input("Выберите пункт: ").strip()
            if choice == "1":
                show_rows(con.execute(f"SELECT {', '.join(FIELDS)} FROM attestation").fetchall())
            elif choice == "2":
                save_to_text(con.execute(f"SELECT {', '.join(FIELDS)} FROM attestation").fetchall())
            elif choice == "3":
                filter_and_change(con)
            elif choice == "4":
                add_row(con)
            elif choice == "0":
                break
            else:
                print("Выберите пункт 0–4.")
    finally:
        con.close()


if __name__ == "__main__":
    main()

