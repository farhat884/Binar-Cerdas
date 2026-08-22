"""
Decorator untuk membedakan akses ADMIN vs SISWA.

Dipakai di routes/admin_routes.py dan routes/student_routes.py.
Role disimpan di session['role'] saat login (lihat routes/auth_routes.py).
"""
from functools import wraps
from flask import session, redirect, url_for, flash, request


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Silakan login terlebih dahulu.", "warning")
            return redirect(url_for("auth.login", next=request.path))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    """Hanya role == 'admin' yang boleh lewat. Selain itu ditolak."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Silakan login terlebih dahulu.", "warning")
            return redirect(url_for("auth.login", next=request.path))
        if session.get("role") != "admin":
            flash("Halaman ini khusus admin.", "danger")
            return redirect(url_for("student.dashboard"))
        return f(*args, **kwargs)
    return decorated


def student_required(f):
    """Hanya role == 'siswa' yang boleh lewat. Admin tidak dialihkan ke sini,
    supaya admin tidak bisa 'menyamar' melihat halaman siswa lewat sesi admin."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Silakan login terlebih dahulu.", "warning")
            return redirect(url_for("auth.login", next=request.path))
        if session.get("role") != "siswa":
            flash("Halaman ini khusus siswa.", "danger")
            return redirect(url_for("admin.dashboard"))
        return f(*args, **kwargs)
    return decorated
