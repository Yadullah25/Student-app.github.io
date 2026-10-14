import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "students.db")


def get_connection():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS students (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id  TEXT NOT NULL UNIQUE,
                full_name   TEXT NOT NULL,
                department  TEXT NOT NULL,
                gender      TEXT NOT NULL,
                email       TEXT,
                phone       TEXT,
                created_at  TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
            )
            """
        )


def add_student(student_id, full_name, department, gender, email, phone):
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO students (student_id, full_name, department, gender, email, phone)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (student_id, full_name, department, gender, email, phone),
        )
        return cursor.lastrowid


def get_all_students(search=""):
    with get_connection() as connection:
        if search:
            pattern = "%" + search + "%"
            return connection.execute(
                """
                SELECT * FROM students
                WHERE full_name  LIKE ?
                   OR student_id LIKE ?
                   OR department LIKE ?
                ORDER BY id DESC
                """,
                (pattern, pattern, pattern),
            ).fetchall()
        return connection.execute(
            "SELECT * FROM students ORDER BY id DESC"
        ).fetchall()


def student_id_exists(student_id, ignore_row_id=None):
    with get_connection() as connection:
        if ignore_row_id is None:
            row = connection.execute(
                "SELECT id FROM students WHERE student_id = ?", (student_id,)
            ).fetchone()
        else:
            row = connection.execute(
                "SELECT id FROM students WHERE student_id = ? AND id <> ?",
                (student_id, ignore_row_id),
            ).fetchone()
        return row is not None


def get_student(row_id):
    with get_connection() as connection:
        return connection.execute(
            "SELECT * FROM students WHERE id = ?", (row_id,)
        ).fetchone()


def update_student(row_id, student_id, full_name, department, gender, email, phone):
    with get_connection() as connection:
        connection.execute(
            """
            UPDATE students
               SET student_id = ?,
                   full_name  = ?,
                   department = ?,
                   gender     = ?,
                   email      = ?,
                   phone      = ?
             WHERE id = ?
            """,
            (student_id, full_name, department, gender, email, phone, row_id),
        )


def delete_student(row_id):
    with get_connection() as connection:
        connection.execute("DELETE FROM students WHERE id = ?", (row_id,))
