from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for

from .auth import login_required
from .db import get_db

bp = Blueprint("notes", __name__)


def note_from_current_user(note_id):
    note = get_db().execute(
        """
        SELECT id, title, content, created_at, updated_at
        FROM notes
        WHERE id = %s AND user_id = %s
        """,
        (note_id, g.user["id"]),
    ).fetchone()
    if note is None:
        abort(404)
    return note


def validate_note_form():
    title = request.form.get("title", "").strip()
    content = request.form.get("content", "").strip()
    if not title:
        return None, None, "Tiêu đề không được để trống."
    if len(title) > 200:
        return None, None, "Tiêu đề tối đa 200 ký tự."
    if len(content) > 20000:
        return None, None, "Nội dung tối đa 20.000 ký tự."
    return title, content, None


@bp.get("/")
@login_required
def index():
    notes = get_db().execute(
        """
        SELECT id, title, content, created_at, updated_at
        FROM notes
        WHERE user_id = %s
        ORDER BY updated_at DESC, id DESC
        """,
        (g.user["id"],),
    ).fetchall()
    return render_template("notes/list.html", title="Ghi chú của tôi", notes=notes)


@bp.route("/notes/new", methods=("GET", "POST"))
@login_required
def create():
    if request.method == "POST":
        title, content, error = validate_note_form()
        if error:
            flash(error, "error")
        else:
            connection = get_db()
            connection.execute(
                "INSERT INTO notes (user_id, title, content) VALUES (%s, %s, %s)",
                (g.user["id"], title, content),
            )
            connection.commit()
            flash("Đã thêm ghi chú.", "success")
            return redirect(url_for("notes.index"))
    return render_template("notes/form.html", title="Ghi chú mới", note=None)


@bp.get("/notes/<int:note_id>")
@login_required
def detail(note_id):
    note = note_from_current_user(note_id)
    return render_template("notes/detail.html", title=note["title"], note=note)


@bp.route("/notes/<int:note_id>/edit", methods=("GET", "POST"))
@login_required
def edit(note_id):
    note = note_from_current_user(note_id)
    if request.method == "POST":
        title, content, error = validate_note_form()
        if error:
            flash(error, "error")
        else:
            connection = get_db()
            connection.execute(
                """
                UPDATE notes
                SET title = %s, content = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s AND user_id = %s
                """,
                (title, content, note_id, g.user["id"]),
            )
            connection.commit()
            flash("Đã cập nhật ghi chú.", "success")
            return redirect(url_for("notes.detail", note_id=note_id))
    return render_template("notes/form.html", title="Sửa ghi chú", note=note)


@bp.post("/notes/<int:note_id>/delete")
@login_required
def delete(note_id):
    note_from_current_user(note_id)
    connection = get_db()
    connection.execute(
        "DELETE FROM notes WHERE id = %s AND user_id = %s",
        (note_id, g.user["id"]),
    )
    connection.commit()
    flash("Đã xóa ghi chú.", "success")
    return redirect(url_for("notes.index"))
