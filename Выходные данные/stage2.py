"""Учебное приложение для этапа 2: работа с базой студентов и сессий."""

from __future__ import annotations

import sqlite3
from pathlib import Path


DB_PATH = Path(__file__).with_name("bd1.sqlite")


def connect() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH)
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript(
        """CREATE TABLE IF NOT EXISTS stud (
               id TEXT PRIMARY KEY,
               fio TEXT NOT NULL,
               email TEXT NOT NULL
           );
           CREATE TABLE IF NOT EXISTS sessija (
               id TEXT NOT NULL REFERENCES stud(id),
               Disz TEXT NOT NULL,
               Ozenka INTEGER NOT NULL,
               Prepod TEXT NOT NULL,
               Dat TEXT NOT NULL
           );"""
    )
    return con


def show_table(con: sqlite3.Connection, table: str) -> None:
    rows = con.execute(f'SELECT * FROM "{table}"').fetchall()
    print(f"{table}: {len(rows)} записей")
    for row in rows:
        print(row)


def show_schema(con: sqlite3.Connection) -> None:
    tables = con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()
    print("Таблицы:", [row[0] for row in tables])
    for (name,) in tables:
        print(f"Поля {name}:")
        for field in con.execute(f'PRAGMA table_info("{name}")'):
            print(f"  {field[1]}: {field[2] or 'без типа'}; ключ={bool(field[5])}")


def add_student(con: sqlite3.Connection) -> None:
    values = (
        input("Номер студенческого билета: ").strip(),
        input("ФИО студента: ").strip(),
        input("E-mail студента: ").strip(),
    )
    con.execute("INSERT INTO stud (id, fio, email) VALUES (?, ?, ?)", values)
    con.commit()
    print("Запись добавлена.")


def read_session() -> tuple[str, str, int, str, str]:
    return (
        input("Номер студенческого билета: ").strip(),
        input("Название дисциплины: ").strip(),
        int(input("Оценка: ").strip()),
        input("ФИО преподавателя: ").strip(),
        input("Дата сдачи (ГГГГ-ММ-ДД): ").strip(),
    )


def add_session(con: sqlite3.Connection) -> None:
    con.execute("INSERT INTO sessija (id, Disz, Ozenka, Prepod, Dat) VALUES (?, ?, ?, ?, ?)", read_session())
    con.commit()
    print("Запись добавлена.")


def add_sessions_bulk(con: sqlite3.Connection) -> None:
    count = int(input("Количество записей: ").strip())
    rows = [read_session() for _ in range(count)]
    con.executemany("INSERT INTO sessija (id, Disz, Ozenka, Prepod, Dat) VALUES (?, ?, ?, ?, ?)", rows)
    con.commit()
    print(f"Добавлено записей: {len(rows)}")


def main() -> None:
    with connect() as con:
        print("База данных:", DB_PATH)
        show_schema(con)
        while True:
            print("\n1. Показать stud\n2. Показать sessija\n3. Список таблиц и полей")
            print("4. Добавить студента\n5. Добавить результат сессии\n6. Добавить результаты списком\n0. Завершить")
            choice = input("Выберите пункт: ").strip()
            if choice == "1":
                show_table(con, "stud")
            elif choice == "2":
                show_table(con, "sessija")
            elif choice == "3":
                show_schema(con)
            elif choice == "4":
                add_student(con)
            elif choice == "5":
                add_session(con)
            elif choice == "6":
                add_sessions_bulk(con)
            elif choice == "0":
                break
            else:
                print("Выберите пункт 0–6.")


if __name__ == "__main__":
    main()
