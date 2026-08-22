from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from models.user_model import create_user, get_user_by_email, verify_password

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    """Pendaftaran akun BARU selalu jadi role 'siswa'. Akun admin tidak
    bisa dibuat lewat form publik ini (lihat README bagian 'Membuat admin')."""
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        phone = request.form.get("phone", "").strip()
        jenjang = request.form.get("jenjang")
        kelas = request.form.get("kelas")

        if not all([name, email, password, phone, jenjang, kelas]):
            flash("Semua kolom wajib diisi.", "danger")
            return render_template("register.html")

        user, error = create_user(
            name=name, email=email, password=password, phone=phone,
            role="siswa", jenjang=jenjang, kelas=kelas,
        )
        if error:
            flash(error, "danger")
            return render_template("register.html")

        flash("Akun berhasil dibuat! Silakan login.", "success")
        return redirect(url_for("auth.login"))

    return render_template("register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        user = get_user_by_email(email)
        if not user or not verify_password(user, password):
            flash("Email atau kata sandi salah.", "danger")
            return render_template("login.html")

        # Ini titik kunci pemisahan role: role disimpan di session,
        # lalu decorator admin_required / student_required membacanya.
        session["user_id"] = user["id"]
        session["name"] = user["name"]
        session["role"] = user["role"]

        if user["role"] == "admin":
            return redirect(url_for("admin.dashboard"))
        return redirect(url_for("student.dashboard"))

    return render_template("login.html")


@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("Berhasil logout.", "success")
    return redirect(url_for("index"))
