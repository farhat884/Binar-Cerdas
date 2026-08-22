"""
Binar Cerdas - Aplikasi Bimbingan Belajar
==========================================
Entry point aplikasi Flask. File ini HANYA berisi setup app & pendaftaran
blueprint. Semua logika per-role dipisah:

  - routes/auth_routes.py     -> login, register, logout (semua orang)
  - routes/student_routes.py  -> khusus role "siswa"   (lihat jadwal, daftar
                                  les/beli paket, lihat sisa pertemuan)
  - routes/admin_routes.py    -> khusus role "admin"   (approve pendaftaran,
                                  kelola siswa, kurangi sisa pertemuan)

Pemisahan role dilakukan lewat decorator di auth/decorators.py
(@login_required, @admin_required, @student_required) yang mengecek
session['role'].
"""
import os
from flask import Flask, render_template
from dotenv import load_dotenv

load_dotenv()

from routes.auth_routes import auth_bp
from routes.admin_routes import admin_bp
from routes.student_routes import student_bp


def create_app():
    app = Flask(__name__, static_folder='static', static_url_path='/static')
    app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-ganti-ini")
    app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5MB, untuk upload bukti bayar

    # Setiap blueprint = satu "wilayah" role. Prefix URL juga sudah
    # mencerminkan role supaya jelas dari alamatnya siapa yang mengakses.
    app.register_blueprint(auth_bp)                              # /login /register /logout
    app.register_blueprint(admin_bp, url_prefix="/admin")        # /admin/...
    app.register_blueprint(student_bp, url_prefix="/siswa")      # /siswa/...

    @app.route("/")
    def index():
        """Landing page publik: info promosi Binar Cerdas + jadwal umum."""
        from models.program_model import get_all_schedules, DEFAULT_SCHEDULES
        try:
            jadwal = get_all_schedules() or DEFAULT_SCHEDULES
        except Exception:
            # Firebase belum dikonfigurasi saat pertama kali dijalankan -> tetap tampilkan landing page
            jadwal = DEFAULT_SCHEDULES

        kontak = [
            {"nama": "Ka Farhat", "nomor_tampil": "0895-3461-61387", "wa": "https://wa.me/62895346161387"},
            {"nama": "Ka Caca", "nomor_tampil": "0812-1212-0218", "wa": "https://wa.me/6281212120218"},
        ]
        return render_template("index.html", jadwal=jadwal, kontak=kontak)

    @app.errorhandler(404)
    def not_found(e):
        return render_template("404.html"), 404

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True, port=int(os.environ.get("PORT", 5000)))
