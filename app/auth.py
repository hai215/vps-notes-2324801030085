import re
import secrets
from functools import wraps

import psycopg
from flask import Blueprint, flash, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from .db import get_db

bp = Blueprint("auth", __name__, url_prefix="/auth")
USERNAME_RE = re.compile(r"^[a-z0-9_.-]{3,50}$")


@bp.before_app_request
def load_logged_in_user():
    user_id = session.get("user_id")
    g.user = None
    if user_id is not None:
        g.user = get_db().execute(
            "SELECT id, username FROM users WHERE id = %s", (user_id,)
        ).fetchone()
        if g.user is None:
            session.clear()


def login_required(view):
    @wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            flash("Vui lòng đăng nhập để tiếp tục.", "info")
            return redirect(url_for("auth.login"))
        return view(**kwargs)

    return wrapped_view


@bp.route("/register", methods=("GET", "POST"))
def register():
    if g.user is not None:
        return redirect(url_for("notes.index"))

    if request.method == "POST":

        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "")
        password_confirm = request.form.get("password_confirm", "")
        error = None

        if not USERNAME_RE.fullmatch(username):
            error = "Tên đăng nhập dài 3-50 ký tự, chỉ gồm a-z, số, dấu chấm, gạch ngang hoặc gạch dưới."
        elif len(password) < 8:
            error = "Mật khẩu phải có ít nhất 8 ký tự."
        elif password != password_confirm:
            error = "Hai lần nhập mật khẩu không khớp."

        if error is None:
            try:
                connection = get_db()
                connection.execute(
                    "INSERT INTO users (username, password_hash) VALUES (%s, %s)",
                    (username, generate_password_hash(password)),
                )
                connection.commit()
            except psycopg.errors.UniqueViolation:
                get_db().rollback()
                error = "Tên đăng nhập đã tồn tại."

        if error is None:
            flash("Đăng ký thành công. Hãy đăng nhập.", "success")
            return redirect(url_for("auth.login"))
        flash(error, "error")

    return render_template("auth/register.html", title="Đăng ký")


@bp.route("/login", methods=("GET", "POST"))
def login():
    if g.user is not None:
        return redirect(url_for("notes.index"))

    if request.method == "POST":

        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "")
        user = get_db().execute(
            "SELECT id, username, password_hash FROM users WHERE username = %s",
            (username,),
        ).fetchone()

        if user is None or not check_password_hash(user["password_hash"], password):
            flash("Tên đăng nhập hoặc mật khẩu không đúng.", "error")
        else:
            session.clear()
            session["user_id"] = user["id"]
            session["csrf_token"] = secrets.token_urlsafe(32)
            return redirect(url_for("notes.index"))

    return render_template("auth/login.html", title="Đăng nhập")


@bp.post("/logout")
def logout():
    session.clear()
    flash("Bạn đã đăng xuất.", "success")
    return redirect(url_for("auth.login"))
