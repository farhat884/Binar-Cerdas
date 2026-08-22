"""
SEMUA route di file ini khusus
untuk role siswa.
"""

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
)

from auth.decorators import student_required

from models.user_model import (
    get_user_by_id
)

from models.program_model import (
    get_all_schedules
)

from models.registration_model import (
    buat_pendaftaran,
    get_pendaftaran_by_user,
    HARGA_PER_PAKET,
    PERTEMUAN_PER_PAKET,
    MAKS_PAKET_SEKALIGUS,
)

from utils.helpers import (
    format_rupiah
)


student_bp = Blueprint(
    "student",
    __name__
)


@student_bp.route("/dashboard")
@student_required
def dashboard():

    user = get_user_by_id(
        session["user_id"]
    )

    riwayat = (
        get_pendaftaran_by_user(
            session["user_id"]
        )[:5]
    )

    return render_template(
        "student/dashboard.html",
        user=user,
        riwayat=riwayat,
    )


@student_bp.route("/jadwal")
@student_required
def jadwal():

    user = get_user_by_id(
        session["user_id"]
    )

    semua_jadwal = (
        get_all_schedules()
    )

    return render_template(
        "student/jadwal.html",
        user=user,
        jadwal=semua_jadwal,
    )


@student_bp.route(
    "/daftar-les",
    methods=["GET", "POST"]
)
@student_required
def daftar_les():

    user = get_user_by_id(
        session["user_id"]
    )

    if request.method == "POST":

        try:
            jumlah_paket = int(
                request.form.get(
                    "jumlah_paket",
                    1
                )
            )

        except (
            ValueError,
            TypeError
        ):
            jumlah_paket = 1

        jumlah_paket = max(
            1,
            min(
                jumlah_paket,
                MAKS_PAKET_SEKALIGUS
            )
        )

        metode_pembayaran = (
            request.form.get(
                "metode_pembayaran",
                ""
            ).strip()
        )

        nama_pengirim = (
            request.form.get(
                "nama_pengirim",
                ""
            ).strip()
        )

        tanggal_transfer = (
            request.form.get(
                "tanggal_transfer",
                ""
            ).strip()
        )

        referensi_transfer = (
            request.form.get(
                "referensi_transfer",
                ""
            ).strip()
        )

        if not metode_pembayaran:

            flash(
                "Silakan pilih metode pembayaran.",
                "danger"
            )

            return redirect(
                url_for(
                    "student.daftar_les"
                )
            )

        if not nama_pengirim:

            flash(
                "Nama pengirim wajib diisi.",
                "danger"
            )

            return redirect(
                url_for(
                    "student.daftar_les"
                )
            )

        if not tanggal_transfer:

            flash(
                "Tanggal transfer wajib diisi.",
                "danger"
            )

            return redirect(
                url_for(
                    "student.daftar_les"
                )
            )

        if not referensi_transfer:

            flash(
                "Nomor referensi transfer wajib diisi.",
                "danger"
            )

            return redirect(
                url_for(
                    "student.daftar_les"
                )
            )

        buat_pendaftaran(
            user_id=user["id"],
            user_name=user["name"],

            jumlah_paket=jumlah_paket,

            metode_pembayaran=(
                metode_pembayaran
            ),

            nama_pengirim=(
                nama_pengirim
            ),

            tanggal_transfer=(
                tanggal_transfer
            ),

            referensi_transfer=(
                referensi_transfer
            ),
        )

        flash(
            "Pembelian paket berhasil dikirim! "
            "Menunggu persetujuan admin.",
            "success"
        )

        return redirect(
            url_for(
                "student.riwayat"
            )
        )

    return render_template(
        "student/daftar_les.html",

        user=user,

        harga_per_paket=(
            HARGA_PER_PAKET
        ),

        pertemuan_per_paket=(
            PERTEMUAN_PER_PAKET
        ),

        maks_paket=(
            MAKS_PAKET_SEKALIGUS
        ),
    )


@student_bp.route("/riwayat")
@student_required
def riwayat():

    user = get_user_by_id(
        session["user_id"]
    )

    daftar = (
        get_pendaftaran_by_user(
            user["id"]
        )
    )

    return render_template(
        "student/riwayat.html",

        user=user,

        riwayat=daftar,

        format_rupiah=format_rupiah,
    )
