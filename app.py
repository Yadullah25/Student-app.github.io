import html
import os
import re
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse
import database

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")

DEPARTMENTS = [
    "Management Information Systems",
    "Accounting",
    "Business Administration",
    "Computer Science",
    "Statistics",
]


def render(template_name, **values):
    path = os.path.join(TEMPLATE_DIR, template_name)
    with open(path, encoding="utf-8") as file:
        page = file.read()

    def replace(match):
        return str(values.get(match.group(1), ""))

    return re.sub(r"\{\{\s*(\w+)\s*\}\}", replace, page)


def esc(value):
    return html.escape("" if value is None else str(value))


def build_table_rows(students):
    rows = []
    for number, student in enumerate(students, start=1):
        rows.append(
            """
            <tr>
              <td>{number}</td>
              <td>{student_id}</td>
              <td>{full_name}</td>
              <td>{department}</td>
              <td>{created_at}</td>
              <td class="actions">
                <a href="/edit?id={row_id}">Edit</a>
                <form method="POST" action="/delete" class="inline"
                      onsubmit="return confirm('Delete this student?');">
                  <input type="hidden" name="id" value="{row_id}">
                  <button type="submit" class="danger">Delete</button>
                </form>
              </td>
            </tr>
            """.format(
                number=number,
                row_id=student["id"],
                student_id=esc(student["student_id"]),
                full_name=esc(student["full_name"]),
                department=esc(student["department"]),
                created_at=esc(student["created_at"]),
            )
        )
    return "".join(rows)


def build_department_options(selected):
    parts = []
    for name in DEPARTMENTS:
        chosen = " selected" if name == selected else ""
        parts.append('<option value="%s"%s>%s</option>' % (esc(name), chosen, esc(name)))
    return "\n".join(parts)


class StudentAppHandler(BaseHTTPRequestHandler):
    # ---------- GET ----------
    def do_GET(self):
        url = urlparse(self.path)

        if url.path == "/":
            query = urllib.parse.parse_qs(url.query)
            self.page_home(query.get("q", [""])[0])
        elif url.path == "/add":
            self.page_form()
        elif url.path == "/edit":
            query = urllib.parse.parse_qs(url.query)
            self.page_form(query.get("id", [""])[0])
        elif url.path.startswith("/static/"):
            self.send_static(url.path[len("/static/"):])
        else:
            self.send_response(404)
            self.end_headers()

    # ---------- POST ----------
    def do_POST(self):
        url = urlparse(self.path)

        if url.path == "/add":
            self.save_student()
        elif url.path == "/edit":
            self.save_student(is_edit=True)
        elif url.path == "/delete":
            form = self.read_form()
            database.delete_student(form.get("id"))
            self.redirect("/")
        else:
            self.send_response(404)
            self.end_headers()

    # ---------- Pages ----------
    def page_home(self, search=""):
        students = database.get_all_students(search)

        if students:
            table = render("list.html",
                           rows=build_table_rows(students),
                           total=len(students))
        elif search:
            table = "<p>No student matches &quot;" + esc(search) + "&quot;.</p>"
        else:
            table = "<p>No student is registered yet.</p>"

        body = render("home.html", table=table)
        page = render("layout.html", title="Students", content=body)
        self.send_html(page)

    def page_form(self, row_id="", errors="", values=None):
        student = database.get_student(row_id) if row_id else None

        if row_id and student is None:
            self.send_response(404)
            self.end_headers()
            return

        if values is None:
            values = dict(student) if student else {}

        is_edit = student is not None
        gender = values.get("gender", "")
        body = render(
            "form.html",
            heading="Edit student" if is_edit else "Register a new student",
            action="/edit" if is_edit else "/add",
            submit_label="Save changes" if is_edit else "Register student",
            row_id=esc(values.get("id", "")),
            errors=errors,
            student_id=esc(values.get("student_id", "")),
            full_name=esc(values.get("full_name", "")),
            email=esc(values.get("email", "")),
            phone=esc(values.get("phone", "")),
            departments=build_department_options(values.get("department", "")),
            male_checked=" checked" if gender == "Male" else "",
            female_checked=" checked" if gender == "Female" else "",
        )
        title = "Edit student" if is_edit else "New student"
        self.send_html(render("layout.html", title=title, content=body))

    # ---------- Saving ----------
    def save_student(self, is_edit=False):
        form = self.read_form()
        row_id = form.get("id", "") if is_edit else ""

        problems = []
        if not form.get("student_id"):
            problems.append("Student ID is required.")
        if not form.get("full_name"):
            problems.append("Full name is required.")
        if not form.get("department"):
            problems.append("Please choose a department.")
        if not form.get("gender"):
            problems.append("Please choose a gender.")
        if form.get("email") and "@" not in form["email"]:
            problems.append("The email address is not valid.")
        if form.get("student_id") and database.student_id_exists(
            form["student_id"], ignore_row_id=row_id if is_edit else None
        ):
            problems.append("This student ID is already registered.")

        if problems:
            items = "".join("<li>" + esc(p) + "</li>" for p in problems)
            errors = '<div class="alert"><ul>' + items + "</ul></div>"
            return self.page_form(row_id, errors, form)

        values = (
            form["student_id"], form["full_name"], form["department"],
            form["gender"], form.get("email", ""), form.get("phone", ""),
        )
        if is_edit:
            database.update_student(row_id, *values)
        else:
            database.add_student(*values)
        self.redirect("/")

    # ---------- Helpers ----------
    def send_html(self, content, status=200):
        body = content.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(body)

    def redirect(self, location):
        self.send_response(303)
        self.send_header("Location", location)
        self.end_headers()

    def read_form(self):
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length).decode("utf-8")
        data = urllib.parse.parse_qs(raw)
        return {key: value[0].strip() for key, value in data.items()}

    def send_static(self, filename):
        safe_name = os.path.basename(filename)
        path = os.path.join(STATIC_DIR, safe_name)

        if not os.path.isfile(path):
            self.send_response(404)
            self.end_headers()
            return

        with open(path, "rb") as file:
            body = file.read()

        self.send_response(200)
        self.send_header("Content-Type", "text/css; charset=utf-8")
        self.end_headers()
        self.wfile.write(body)


# ---------- Start the server (must stay at the very bottom) ----------
database.init_db()
from http.server import ThreadingHTTPServer
database.init_db()
port = int(os.environ.get("PORT", 8000))
server = ThreadingHTTPServer(("0.0.0.0", port), StudentAppHandler)
print("Server running on port", port)
server.serve_forever()
