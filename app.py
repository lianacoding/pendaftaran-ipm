import os
import uuid
import pymysql

from pathlib import Path
from functools import wraps

from flask import (
    Flask, request, redirect, url_for,
    render_template_string, session,
    flash, send_from_directory, abort
)

from markupsafe import Markup
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge


# ==========================================
# 1. KONFIGURASI
# ==========================================

APP_TITLE = "Pendaftaran Kader IPM"
PERIODE = "Periode 2026/2027"

# Akun per role (ganti sesuai kebutuhan)
AKUN = {
    "admin": {"username": "admin", "password": "1234"},
    "user":  {"username": "user",  "password": "user123"},
}

DB_HOST = "localhost"
DB_USER = "root"
DB_PASSWORD = ""
DB_NAME = "pendaftaran"

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

app = Flask(__name__)

app.secret_key = os.environ.get(
    "IPM_SECRET_KEY",
    "ipm-lokal-ganti-kunci-rahasia"
)

app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024


# ==========================================
# 2. DATA BIDANG, KELAS, JURUSAN
# ==========================================

BIDANG = ["PIP", "Seni", "LPM", "KWU", "PKD", "KDI", "PPK"]

KELAS = {
    "10": [
        "AKL 1", "AKL 2", "AKL 3",
        "TKJ 1", "TKJ 2",
        "RPL 1", "RPL 2", "RPL 3",
        "TO 1", "TO 2", "TO 3", "TO 4",
        "TO 5", "TO 6", "TO 7", "TO 8",
        "ICP Bismen", "ICP IT",
        "PMS 1", "PMS 2"
    ],
    "11": [
        "ICP", "DT",
        "RPL 1", "RPL 2",
        "PMS 1",
        "TKJ 1",
        "TO 1", "TO 2", "TO 3",
        "TO 4", "TO 5", "TO 6"
    ]
}


# ==========================================
# 3. IKON SVG (gaya Lucide)
# ==========================================

_IKON = {
    "cap": '<path d="M21.42 10.922a1 1 0 0 0-.019-1.838L12.83 5.18a2 2 0 0 0-1.66 0L2.6 9.08a1 1 0 0 0 0 1.832l8.57 3.908a2 2 0 0 0 1.66 0z"/><path d="M22 10v6"/><path d="M6 12.5V16a6 3 0 0 0 12 0v-3.5"/>',
    "edit": '<path d="M12 20h9"/><path d="M16.376 3.622a1 1 0 0 1 3.002 3.002L7.368 18.635a2 2 0 0 1-.855.506l-2.872.838a.5.5 0 0 1-.62-.62l.838-2.872a2 2 0 0 1 .506-.854z"/>',
    "list": '<path d="M3 12h.01"/><path d="M3 18h.01"/><path d="M3 6h.01"/><path d="M8 12h13"/><path d="M8 18h13"/><path d="M8 6h13"/>',
    "upload": '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" x2="12" y1="3" y2="15"/>',
    "download": '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" x2="12" y1="15" y2="3"/>',
    "logout": '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" x2="9" y1="12" y2="12"/>',
    "login": '<path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"/><polyline points="10 17 15 12 10 7"/><line x1="15" x2="3" y1="12" y2="12"/>',
    "trash": '<path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/>',
    "save": '<path d="M15.2 3a2 2 0 0 1 1.4.6l3.8 3.8a2 2 0 0 1 .6 1.4V19a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2z"/><path d="M17 21v-7a1 1 0 0 0-1-1H8a1 1 0 0 0-1 1v7"/><path d="M7 3v4a1 1 0 0 0 1 1h7"/>',
    "search": '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>',
    "shield": '<path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/>',
    "userico": '<path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>',
    "folder": '<path d="M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z"/>',
}


def icon(nama, size=18):
    return Markup(
        f'<svg class="ico" width="{size}" height="{size}" '
        f'viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        f'stroke-width="2" stroke-linecap="round" '
        f'stroke-linejoin="round" aria-hidden="true">'
        f'{_IKON[nama]}</svg>'
    )


app.jinja_env.globals["icon"] = icon


# ==========================================
# 4. KONEKSI MYSQL  (struktur tidak diubah)
# ==========================================

def koneksi():
    return pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False
    )


def query(sql, params=None, one=False):
    db = koneksi()

    try:
        with db.cursor() as cursor:
            cursor.execute(sql, params or ())

            if sql.lstrip().upper().startswith("SELECT"):
                hasil = cursor.fetchone() if one else cursor.fetchall()
            else:
                hasil = cursor.rowcount

        db.commit()
        return hasil

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


def buat_database():
    db = koneksi()

    try:
        with db.cursor() as cursor:

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS anggota (
                    id_pendaftaran INT(10)
                        NOT NULL PRIMARY KEY,
                    nama VARCHAR(100) NOT NULL,
                    bidang VARCHAR(100) NOT NULL,
                    kelas VARCHAR(50) NOT NULL,
                    Jurusan VARCHAR(50) NOT NULL
                ) ENGINE=InnoDB
                DEFAULT CHARSET=utf8mb4
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS dokumen_anggota (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    anggota_id INT NOT NULL,
                    nama_asli VARCHAR(255) NOT NULL,
                    nama_file VARCHAR(255) NOT NULL,
                    ukuran BIGINT NOT NULL,
                    dibuat TIMESTAMP DEFAULT
                        CURRENT_TIMESTAMP
                ) ENGINE=InnoDB
                DEFAULT CHARSET=utf8mb4
            """)

        db.commit()

    finally:
        db.close()


# ==========================================
# 5. LOGIN & HAK AKSES
# ==========================================

def wajib_login(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not session.get("login"):
            return redirect(url_for("login"))
        return func(*args, **kwargs)

    return wrapper


def wajib_admin(func):
    """Hanya role admin yang boleh mengakses."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not session.get("login"):
            return redirect(url_for("login"))

        if session.get("role") != "admin":
            flash("Akses ditolak. Halaman ini khusus Admin.")
            return redirect(url_for("data"))

        return func(*args, **kwargs)

    return wrapper


# ==========================================
# 6. CSS TAMPILAN (Glassmorphism - Retro Magic)
# ==========================================

CSS = """
:root {
    --yellow: #FFF7AD;
    --peach:  #FFB3AE;
    --pink:   #FF49C1;
    --purple: #6A1452;
    --plum:   #44113E;
    --glass:  rgba(255, 255, 255, 0.38);
    --glass-strong: rgba(255, 255, 255, 0.55);
    --border: rgba(255, 255, 255, 0.65);
    --shadow: 0 8px 32px rgba(68, 17, 62, 0.18);
}

* { box-sizing: border-box; }

html, body { min-height: 100%; }

body {
    margin: 0;
    font-family: "Segoe UI", system-ui, -apple-system, Arial, sans-serif;
    color: var(--plum);
    background: linear-gradient(135deg,
        var(--yellow) 0%, var(--peach) 45%, #ff8fd6 100%);
    background-attachment: fixed;
    position: relative;
    overflow-x: hidden;
}

/* Blob gradasi dengan Gaussian blur halus */
body::before, body::after {
    content: "";
    position: fixed;
    border-radius: 50%;
    filter: blur(90px);
    z-index: 0;
    pointer-events: none;
}
body::before {
    width: 460px; height: 460px;
    background: var(--pink);
    opacity: .45;
    top: -120px; left: -100px;
}
body::after {
    width: 520px; height: 520px;
    background: var(--purple);
    opacity: .35;
    bottom: -160px; right: -120px;
}

a { text-decoration: none; }

.ico { flex-shrink: 0; vertical-align: middle; }

.glass {
    background: var(--glass);
    backdrop-filter: blur(18px) saturate(140%);
    -webkit-backdrop-filter: blur(18px) saturate(140%);
    border: 1px solid var(--border);
    box-shadow: var(--shadow);
}

/* ---------- LOGIN ---------- */
.login-page {
    position: relative; z-index: 1;
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 24px;
}

.login-wrap {
    display: flex;
    width: 880px;
    max-width: 100%;
    border-radius: 28px;
    overflow: hidden;
}

.brand {
    flex: 5;
    background: linear-gradient(160deg,
        rgba(68,17,62,.92), rgba(106,20,82,.88));
    color: white;
    display: flex;
    flex-direction: column;
    justify-content: center;
    padding: 48px;
}

.brand-icon {
    width: 64px; height: 64px;
    border-radius: 18px;
    background: linear-gradient(135deg, var(--pink), var(--peach));
    display: flex; align-items: center; justify-content: center;
    color: white;
    margin-bottom: 30px;
    box-shadow: 0 10px 30px rgba(255,73,193,.45);
}

.brand h1 { font-size: 36px; line-height: 1.3; margin: 0; }
.brand p  { color: var(--yellow); margin-top: 12px; font-size: 15px; }

.login-right {
    flex: 5;
    padding: 44px 40px;
    background: var(--glass-strong);
    display: flex;
    align-items: center;
}

.login-box { width: 100%; }
.login-box h2 { font-size: 26px; margin: 0 0 8px; }

.muted { color: #7a3d6f; font-size: 14px; }

/* pilih role */
.roles {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
    margin: 18px 0 4px;
}
.roles input { display: none; }
.roles label {
    display: flex; align-items: center; justify-content: center;
    gap: 8px;
    padding: 12px;
    margin: 0;
    border-radius: 12px;
    border: 1px solid var(--border);
    background: rgba(255,255,255,.45);
    color: var(--plum);
    font-weight: 600;
    font-size: 14px;
    cursor: pointer;
    transition: .2s;
}
.roles input:checked + label {
    background: linear-gradient(135deg, var(--purple), var(--pink));
    color: white;
    border-color: transparent;
    box-shadow: 0 6px 18px rgba(255,73,193,.35);
}

/* ---------- FORM ---------- */
input, select {
    width: 100%;
    padding: 14px 15px;
    border: 1px solid var(--border);
    border-radius: 12px;
    background: rgba(255,255,255,.7);
    color: var(--plum);
    font-size: 14px;
    outline: none;
    transition: .2s;
}
input:focus, select:focus {
    border-color: var(--pink);
    box-shadow: 0 0 0 3px rgba(255,73,193,.25);
}

label {
    display: block;
    font-size: 13px;
    font-weight: 600;
    color: var(--purple);
    margin-bottom: 8px;
}

.form-group { margin-top: 14px; }

button, .btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    background: linear-gradient(135deg, var(--purple), var(--pink));
    color: white;
    border: none;
    border-radius: 12px;
    padding: 12px 18px;
    cursor: pointer;
    font-weight: 600;
    font-size: 13px;
    transition: .2s;
    box-shadow: 0 6px 16px rgba(106,20,82,.25);
}
button:hover, .btn:hover {
    transform: translateY(-1px);
    filter: brightness(1.08);
}

.btn-dark { background: var(--plum); }
.btn-red  { background: linear-gradient(135deg, #b91c4a, #e11d48); }
.btn-sm   { padding: 8px 12px; font-size: 12px; }

.full { width: 100%; margin-top: 26px; }

/* ---------- LAYOUT ---------- */
.layout {
    position: relative; z-index: 1;
    display: flex;
    min-height: 100vh;
}

.sidebar {
    width: 260px;
    margin: 16px 0 16px 16px;
    border-radius: 24px;
    background: rgba(68,17,62,.82);
    backdrop-filter: blur(18px);
    -webkit-backdrop-filter: blur(18px);
    color: white;
    padding: 22px;
    display: flex;
    flex-direction: column;
    flex-shrink: 0;
    box-shadow: var(--shadow);
}

.side-brand {
    display: flex; align-items: center; gap: 12px;
    margin-bottom: 4px;
}
.side-logo {
    width: 40px; height: 40px;
    border-radius: 12px;
    background: linear-gradient(135deg, var(--pink), var(--peach));
    display: flex; align-items: center; justify-content: center;
}
.side-brand h3 { margin: 0; font-size: 17px; }
.sidebar p { color: var(--peach); font-size: 12px; margin: 4px 0 0; }

.role-badge {
    display: inline-flex; align-items: center; gap: 6px;
    margin: 18px 0 20px;
    padding: 7px 12px;
    border-radius: 999px;
    background: rgba(255,247,173,.15);
    color: var(--yellow);
    font-size: 12px;
    font-weight: 600;
    width: fit-content;
}

.nav {
    display: flex; align-items: center; gap: 12px;
    padding: 13px 14px;
    color: #f3d4ec;
    border-radius: 12px;
    margin-bottom: 6px;
    font-size: 14px;
    transition: .2s;
}
.nav:hover { background: rgba(255,255,255,.12); color: white; }
.nav.active {
    background: linear-gradient(135deg, var(--purple), var(--pink));
    color: white;
}
.logout { margin-top: auto; color: var(--peach); }
.logout:hover { background: rgba(255,73,193,.25); }

.main { flex: 1; padding: 32px; min-width: 0; }
.main h1 { font-size: 26px; margin: 0 0 6px; }

.card {
    padding: 28px;
    border-radius: 22px;
    margin-top: 24px;
    background: var(--glass);
    backdrop-filter: blur(18px) saturate(140%);
    -webkit-backdrop-filter: blur(18px) saturate(140%);
    border: 1px solid var(--border);
    box-shadow: var(--shadow);
}
.card h3 { margin-top: 0; }

.grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 20px;
    margin-top: 15px;
}

.actions { display: flex; gap: 10px; flex-wrap: wrap; align-items: center; }

.toolbar {
    display: flex; gap: 15px; align-items: center;
    margin-top: 24px; flex-wrap: wrap;
}

.search-form { display: flex; gap: 10px; flex-wrap: wrap; }

.table-wrap { overflow-x: auto; border-radius: 14px; }

table {
    width: 100%;
    border-collapse: collapse;
    min-width: 650px;
    background: rgba(255,255,255,.35);
}
th {
    background: rgba(68,17,62,.9);
    color: white;
    text-align: left;
    padding: 14px 15px;
    font-size: 13px;
}
td {
    padding: 14px 15px;
    border-bottom: 1px solid rgba(255,255,255,.6);
    font-size: 13px;
}
tbody tr:hover td { background: rgba(255,255,255,.45); }

.flash {
    display: flex; align-items: center; gap: 10px;
    padding: 13px 16px;
    margin-bottom: 16px;
    border-radius: 12px;
    background: rgba(255,247,173,.75);
    border: 1px solid rgba(255,255,255,.8);
    color: var(--plum);
    font-size: 14px;
}

.upload-box {
    border: 2px dashed var(--pink);
    border-radius: 16px;
    padding: 30px;
    text-align: center;
    background: rgba(255,255,255,.4);
    margin-top: 20px;
}
.upload-box input { margin-top: 15px; }

hr { border: 0; border-top: 1px solid rgba(255,255,255,.7); margin: 25px 0; }

@media (max-width: 800px) {
    .login-wrap { flex-direction: column; }
    .brand { padding: 30px; }
    .brand h1 { font-size: 28px; }
    .login-right { padding: 30px 24px; }

    .layout { flex-direction: column; }
    .sidebar { width: auto; margin: 12px; }
    .main { padding: 18px; }
    .grid { grid-template-columns: 1fr; }
}
"""


# ==========================================
# 7. TEMPLATE UTAMA
# ==========================================

BASE_HTML = """
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{{app_title}}</title>
    <style>{{css|safe}}</style>
</head>
<body>

{% if login_page %}

<div class="login-page">
  <div class="login-wrap glass">

    <div class="brand">
        <div class="brand-icon">{{ icon('cap', 32) }}</div>
        <h1>Pendaftaran<br>Kader IPM</h1>
        <p>{{periode}}</p>
    </div>

    <div class="login-right">
        <div class="login-box">

            <h2>Selamat Datang</h2>
            <p class="muted">
                Pilih peran lalu masuk untuk melanjutkan.
            </p>

            {% for pesan in get_flashed_messages() %}
                <div class="flash">{{ icon('shield', 16) }} {{pesan}}</div>
            {% endfor %}

            <form method="POST">

                <div class="roles">
                    <div>
                        <input type="radio" name="role" id="r-user"
                               value="user"
                               {% if role_dipilih != 'admin' %}checked{% endif %}>
                        <label for="r-user">
                            {{ icon('userico', 16) }} User
                        </label>
                    </div>
                    <div>
                        <input type="radio" name="role" id="r-admin"
                               value="admin"
                               {% if role_dipilih == 'admin' %}checked{% endif %}>
                        <label for="r-admin">
                            {{ icon('shield', 16) }} Admin
                        </label>
                    </div>
                </div>

                <div class="form-group">
                    <input name="username" placeholder="Username"
                           autocomplete="username" required>
                </div>

                <div class="form-group">
                    <input name="password" type="password"
                           placeholder="Password"
                           autocomplete="current-password" required>
                </div>

                <button class="full">
                    {{ icon('login', 18) }} Masuk
                </button>
            </form>

        </div>
    </div>

  </div>
</div>

{% else %}

<div class="layout">

    <aside class="sidebar">

        <div class="side-brand">
            <div class="side-logo">{{ icon('cap', 22) }}</div>
            <h3>Kader IPM</h3>
        </div>
        <p>{{periode}}</p>

        <div class="role-badge">
            {% if session.get('role') == 'admin' %}
                {{ icon('shield', 14) }} Admin
            {% else %}
                {{ icon('userico', 14) }} User
            {% endif %}
        </div>

        <a class="nav {{ 'active' if active == 'input' }}"
           href="{{url_for('input_data')}}">
            {{ icon('edit') }} Input Data
        </a>

        <a class="nav {{ 'active' if active == 'data' }}"
           href="{{url_for('data')}}">
            {{ icon('list') }}
            {{ 'Kelola Data' if session.get('role') == 'admin'
               else 'Lihat Data' }}
        </a>

        {% if session.get('role') == 'admin' %}
        <a class="nav {{ 'active' if active == 'upload' }}"
           href="{{url_for('upload')}}">
            {{ icon('folder') }} Upload Dokumen
        </a>
        {% endif %}

        <a class="nav logout" href="{{url_for('logout')}}">
            {{ icon('logout') }} Keluar
        </a>

    </aside>

    <main class="main">

        {% for pesan in get_flashed_messages() %}
            <div class="flash">{{ icon('shield', 16) }} {{pesan}}</div>
        {% endfor %}

        {{content|safe}}

    </main>

</div>

{% endif %}

</body>
</html>
"""


def tampil(content="", login_page=False, active="", **kwargs):
    halaman = render_template_string(content, **kwargs)

    return render_template_string(
        BASE_HTML,
        css=CSS,
        content=halaman,
        login_page=login_page,
        active=active,
        app_title=APP_TITLE,
        periode=PERIODE,
        role_dipilih=kwargs.get("role_dipilih", "user")
    )


# ==========================================
# 8. HALAMAN LOGIN / LOGOUT
# ==========================================

@app.route("/", methods=["GET", "POST"])
def login():

    if session.get("login"):
        return redirect(url_for("input_data"))

    role = "user"

    if request.method == "POST":
        role = request.form.get("role", "user")
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        akun = AKUN.get(role)

        if (
            akun
            and username == akun["username"]
            and password == akun["password"]
        ):
            session.clear()
            session["login"] = True
            session["role"] = role
            return redirect(url_for("input_data"))

        flash("Username, password, atau peran tidak sesuai.")

    return tampil(login_page=True, role_dipilih=role)


@app.route("/logout")
def logout():
    session.clear()
    flash("Anda telah keluar.")
    return redirect(url_for("login"))


# ==========================================
# 9. FORM PENDAFTARAN
# ==========================================

FORM_HTML = """
<h1>
    {{ 'Ubah Data Pendaftar' if item
       else 'Form Pendaftaran Kader' }}
</h1>

<p class="muted">Lengkapi data pendaftaran kader IPM.</p>

<div class="card">

<form method="POST">

    <h3>Identitas Kader</h3>

    <div class="grid">
        <div>
            <label>Nama Lengkap</label>
            <input name="nama" maxlength="100"
                   value="{{item.nama if item else ''}}" required>
        </div>

        <div>
            <label>ID Pendaftaran</label>
            <input type="number" name="id_pendaftaran"
                   min="1" max="2147483647"
                   value="{{item.id_pendaftaran if item else ''}}"
                   required>
        </div>
    </div>

    <hr>

    <h3>Bidang dan Kelas</h3>

    <div class="grid">

        <div>
            <label>Bidang</label>
            <select name="bidang" required>
                <option value="">Pilih Bidang</option>
                {% for b in bidang %}
                <option value="{{b}}"
                    {% if item and item.bidang == b %}selected{% endif %}>
                    {{b}}
                </option>
                {% endfor %}
            </select>
        </div>

        <div>
            <label>Tingkat Kelas</label>
            <select name="kelas" id="kelas" required>
                <option value="">Pilih Kelas</option>
                <option value="10"
                    {% if item and item.kelas|string == '10' %}selected{% endif %}>
                    Kelas 10
                </option>
                <option value="11"
                    {% if item and item.kelas|string == '11' %}selected{% endif %}>
                    Kelas 11
                </option>
            </select>
        </div>

        <div>
            <label>Jurusan / Rombel</label>
            <select name="jurusan" id="jurusan" required>
                <option value="">Pilih kelas dahulu</option>
            </select>
        </div>

    </div>

    <div class="actions" style="margin-top:25px">

        <button type="submit">
            {{ icon('save') }} Simpan Data
        </button>

        <a class="btn btn-dark"
           href="{{ url_for('data') if item else url_for('input_data') }}">
            Batal / Reset
        </a>

    </div>

</form>
</div>

<script>
const daftarJurusan = {{ daftar_jurusan|tojson }};
const jurusanAwal = {{ (item.Jurusan if item else '')|tojson }};

function ubahJurusan(pakaiAwal) {
    const kelas = document.getElementById("kelas").value;
    const jurusan = document.getElementById("jurusan");

    jurusan.innerHTML = "";

    const awal = document.createElement("option");
    awal.value = "";
    awal.textContent = kelas ? "Pilih Jurusan" : "Pilih kelas dahulu";
    jurusan.appendChild(awal);

    (daftarJurusan[kelas] || []).forEach(function (nama) {
        const opt = document.createElement("option");
        opt.value = nama;
        opt.textContent = nama;

        if (pakaiAwal && nama === jurusanAwal) {
            opt.selected = true;
        }

        jurusan.appendChild(opt);
    });
}

document.getElementById("kelas").addEventListener(
    "change", function () { ubahJurusan(false); }
);

ubahJurusan(true);
</script>
"""


def baca_form():
    nilai = {
        "id_pendaftaran": request.form.get("id_pendaftaran", "").strip(),
        "nama": request.form.get("nama", "").strip(),
        "bidang": request.form.get("bidang", "").strip(),
        "kelas": request.form.get("kelas", "").strip(),
        "jurusan": request.form.get("jurusan", "").strip()
    }

    if not all(nilai.values()):
        return None, "Semua kolom wajib diisi."

    try:
        nomor = int(nilai["id_pendaftaran"])

        if not 1 <= nomor <= 2147483647:
            raise ValueError

        nilai["id_pendaftaran"] = nomor

    except ValueError:
        return None, "ID Pendaftaran harus berupa angka positif."

    if nilai["bidang"] not in BIDANG:
        return None, "Bidang tidak valid."

    if nilai["kelas"] not in KELAS:
        return None, "Pilih kelas 10 atau 11."

    if nilai["jurusan"] not in KELAS[nilai["kelas"]]:
        return None, "Jurusan tidak sesuai dengan kelas."

    if len(nilai["nama"]) > 100:
        return None, "Nama terlalu panjang."

    return nilai, None


# ==========================================
# 10. INPUT DATA (Admin & User)
# ==========================================

@app.route("/input", methods=["GET", "POST"])
@wajib_login
def input_data():

    if request.method == "POST":

        nilai, error = baca_form()

        if error:
            flash(error)

        else:
            try:
                query("""
                    INSERT INTO anggota
                    (id_pendaftaran, nama, bidang, kelas, Jurusan)
                    VALUES (%s, %s, %s, %s, %s)
                """, (
                    nilai["id_pendaftaran"],
                    nilai["nama"],
                    nilai["bidang"],
                    nilai["kelas"],
                    nilai["jurusan"]
                ))

                flash("Data berhasil disimpan.")
                return redirect(url_for("input_data"))

            except pymysql.err.IntegrityError:
                flash("ID Pendaftaran sudah digunakan.")

            except Exception as err:
                flash(f"Gagal menyimpan data: {err}")

    return tampil(
        FORM_HTML,
        active="input",
        item=None,
        bidang=BIDANG,
        daftar_jurusan=KELAS
    )


# ==========================================
# 11. LIHAT / KELOLA DATA
# ==========================================

DATA_HTML = """
{% set admin = session.get('role') == 'admin' %}

<h1>{{ 'Kelola Data Pendaftar' if admin else 'Data Pendaftar' }}</h1>

<p class="muted">
    {{ 'Cari, ubah, dan hapus data kader IPM.' if admin
       else 'Cari dan lihat data kader IPM yang sudah diinput.' }}
</p>

<div class="toolbar">

    <form method="GET" action="{{url_for('data')}}" class="search-form">
        <input name="cari"
               placeholder="Cari nama, ID, bidang, kelas"
               value="{{keyword}}" style="width:320px">
        <button type="submit">{{ icon('search', 16) }} Cari</button>
    </form>

    <span class="muted">Total {{rows|length}} pendaftar</span>

</div>

<div class="card">
    <div class="table-wrap">
        <table>

            <thead>
                <tr>
                    <th>No</th>
                    <th>Nama Lengkap</th>
                    <th>ID Pendaftaran</th>
                    <th>Bidang</th>
                    <th>Kelas</th>
                    <th>Jurusan</th>
                    {% if admin %}<th>Aksi</th>{% endif %}
                </tr>
            </thead>

            <tbody>
                {% for r in rows %}
                <tr>
                    <td>{{loop.index}}</td>
                    <td>{{r.nama}}</td>
                    <td>{{r.id_pendaftaran}}</td>
                    <td>{{r.bidang}}</td>
                    <td>Kelas {{r.kelas}}</td>
                    <td>{{r.Jurusan}}</td>

                    {% if admin %}
                    <td>
                        <div class="actions">

                            <a class="btn btn-sm"
                               href="{{ url_for('edit', pk=r.id_pendaftaran) }}">
                                {{ icon('edit', 14) }} Edit
                            </a>

                            <form method="POST"
                                  action="{{ url_for('delete', pk=r.id_pendaftaran) }}"
                                  onsubmit="return confirm('Yakin ingin menghapus data ini?')">
                                <button class="btn-red btn-sm">
                                    {{ icon('trash', 14) }} Hapus
                                </button>
                            </form>

                        </div>
                    </td>
                    {% endif %}
                </tr>

                {% else %}

                <tr>
                    <td colspan="{{ 7 if admin else 6 }}"
                        style="text-align:center">
                        Belum ada data pendaftar.
                    </td>
                </tr>

                {% endfor %}
            </tbody>

        </table>
    </div>
</div>
"""


@app.route("/data")
@wajib_login
def data():

    keyword = request.args.get("cari", "").strip()

    if keyword:
        cari = "%" + keyword + "%"

        rows = query("""
            SELECT * FROM anggota
            WHERE nama LIKE %s
               OR CAST(id_pendaftaran AS CHAR) LIKE %s
               OR bidang LIKE %s
               OR kelas LIKE %s
               OR Jurusan LIKE %s
            ORDER BY id_pendaftaran DESC
        """, (cari, cari, cari, cari, cari))

    else:
        rows = query("""
            SELECT * FROM anggota
            ORDER BY id_pendaftaran DESC
        """)

    return tampil(
        DATA_HTML,
        active="data",
        rows=rows,
        keyword=keyword
    )


# ==========================================
# 12. EDIT & HAPUS (khusus Admin)
# ==========================================

@app.route("/edit/<int:pk>", methods=["GET", "POST"])
@wajib_admin
def edit(pk):

    item = query("""
        SELECT * FROM anggota
        WHERE id_pendaftaran=%s
    """, (pk,), one=True)

    if not item:
        abort(404)

    if request.method == "POST":

        nilai, error = baca_form()

        if error:
            flash(error)

        else:
            try:
                query("""
                    UPDATE anggota
                    SET id_pendaftaran=%s,
                        nama=%s,
                        bidang=%s,
                        kelas=%s,
                        Jurusan=%s
                    WHERE id_pendaftaran=%s
                """, (
                    nilai["id_pendaftaran"],
                    nilai["nama"],
                    nilai["bidang"],
                    nilai["kelas"],
                    nilai["jurusan"],
                    pk
                ))

                # Jika ID berubah, perbarui relasi dokumen
                if nilai["id_pendaftaran"] != pk:
                    query("""
                        UPDATE dokumen_anggota
                        SET anggota_id=%s
                        WHERE anggota_id=%s
                    """, (nilai["id_pendaftaran"], pk))

                flash("Data berhasil diperbarui.")
                return redirect(url_for("data"))

            except pymysql.err.IntegrityError:
                flash("ID Pendaftaran sudah digunakan.")

            except Exception as err:
                flash(f"Gagal mengubah data: {err}")

    return tampil(
        FORM_HTML,
        active="data",
        item=item,
        bidang=BIDANG,
        daftar_jurusan=KELAS
    )


@app.route("/delete/<int:pk>", methods=["POST"])
@wajib_admin
def delete(pk):

    try:
        query("""
            DELETE FROM anggota
            WHERE id_pendaftaran=%s
        """, (pk,))

        flash("Data berhasil dihapus.")

    except Exception as err:
        flash(f"Gagal menghapus data: {err}")

    return redirect(url_for("data"))


# ==========================================
# 13. UPLOAD & DOWNLOAD DOKUMEN (khusus Admin)
# ==========================================

UPLOAD_HTML = """
<h1>Upload Dokumen</h1>

<p class="muted">Unggah dokumen pendaftaran kader IPM.</p>

<div class="card">

    <form method="POST" enctype="multipart/form-data">

        <h3>Upload Dokumen Kader</h3>

        <div class="form-group">
            <label>Pilih Anggota</label>
            <select name="anggota_id" required>
                <option value="">Pilih anggota</option>
                {% for a in anggota %}
                <option value="{{a.id_pendaftaran}}">
                    {{a.nama}} ({{a.id_pendaftaran}})
                </option>
                {% endfor %}
            </select>
        </div>

        <div class="upload-box">
            <h3>{{ icon('upload', 22) }} Pilih Dokumen</h3>

            <p class="muted">
                Mendukung PDF, Word, Excel, PowerPoint,
                gambar, ZIP, dan berbagai jenis file lainnya.
            </p>

            <input type="file" name="dokumen" multiple required>

            <p class="muted">Maksimal 50 MB per upload.</p>
        </div>

        <button style="margin-top:20px">
            {{ icon('upload', 16) }} Upload Dokumen
        </button>

    </form>

</div>

<div class="card">

    <h3>Dokumen yang Sudah Diupload</h3>

    <div class="table-wrap">
        <table>

            <thead>
                <tr>
                    <th>No</th>
                    <th>Nama Anggota</th>
                    <th>Nama Dokumen</th>
                    <th>Ukuran</th>
                    <th>Aksi</th>
                </tr>
            </thead>

            <tbody>
                {% for d in dokumen %}
                <tr>
                    <td>{{loop.index}}</td>
                    <td>{{d.nama_anggota}}</td>
                    <td>{{d.nama_asli}}</td>
                    <td>{{(d.ukuran / 1024)|round(1)}} KB</td>
                    <td>
                        <a class="btn btn-sm"
                           href="{{ url_for('download', pk=d.id) }}">
                            {{ icon('download', 14) }} Download
                        </a>
                    </td>
                </tr>

                {% else %}

                <tr>
                    <td colspan="5" style="text-align:center">
                        Belum ada dokumen.
                    </td>
                </tr>

                {% endfor %}
            </tbody>

        </table>
    </div>

</div>
"""


@app.route("/upload", methods=["GET", "POST"])
@wajib_admin
def upload():

    if request.method == "POST":

        anggota_id = request.form.get("anggota_id", "")
        files = request.files.getlist("dokumen")

        anggota = query("""
            SELECT id_pendaftaran
            FROM anggota
            WHERE id_pendaftaran=%s
        """, (anggota_id,), one=True)

        if not anggota:
            flash("Pilih anggota yang valid.")
            return redirect(url_for("upload"))

        if not files or all(not f.filename for f in files):
            flash("Pilih dokumen terlebih dahulu.")
            return redirect(url_for("upload"))

        berhasil = 0

        for file in files:

            if not file.filename:
                continue

            nama_asli = secure_filename(file.filename) or "dokumen"
            nama_file = uuid.uuid4().hex + "_" + nama_asli
            path = UPLOAD_DIR / nama_file

            try:
                file.save(path)
                ukuran = path.stat().st_size

                query("""
                    INSERT INTO dokumen_anggota
                    (anggota_id, nama_asli, nama_file, ukuran)
                    VALUES (%s, %s, %s, %s)
                """, (anggota_id, nama_asli, nama_file, ukuran))

                berhasil += 1

            except Exception as err:
                if path.exists():
                    path.unlink()

                flash(f"Gagal upload {nama_asli}: {err}")

        if berhasil:
            flash(f"{berhasil} dokumen berhasil diupload.")

        return redirect(url_for("upload"))

    anggota = query("""
        SELECT id_pendaftaran, nama
        FROM anggota
        ORDER BY nama
    """)

    dokumen = query("""
        SELECT
            d.id,
            d.nama_asli,
            d.ukuran,
            d.dibuat,
            a.nama AS nama_anggota
        FROM dokumen_anggota d
        JOIN anggota a
          ON a.id_pendaftaran=d.anggota_id
        ORDER BY d.id DESC
    """)

    return tampil(
        UPLOAD_HTML,
        active="upload",
        anggota=anggota,
        dokumen=dokumen
    )


@app.route("/download/<int:pk>")
@wajib_admin
def download(pk):

    dokumen = query("""
        SELECT *
        FROM dokumen_anggota
        WHERE id=%s
    """, (pk,), one=True)

    if not dokumen:
        abort(404)

    return send_from_directory(
        str(UPLOAD_DIR),
        dokumen["nama_file"],
        as_attachment=True,
        download_name=dokumen["nama_asli"]
    )


@app.errorhandler(RequestEntityTooLarge)
def file_terlalu_besar(error):
    flash("File terlalu besar. Maksimal 50 MB.")
    return redirect(url_for("upload"))


# ==========================================
# 14. MENJALANKAN APLIKASI
# ==========================================

if __name__ == "__main__":

    try:
        buat_database()

        print("=" * 45)
        print("PENDAFTARAN KADER IPM")
        print("Database:", DB_NAME)
        print("Tabel: anggota")
        print("Akses Lokal (PC): http://127.0.0.1:8000")
        print("Akses HP/Jaringan: http://<IP-PC-KAMU>:8000")
        print("=" * 45)

        # Mengubah host ke "0.0.0.0" dan port ke 8000
        app.run(host="0.0.0.0", port=8000, debug=False)

    except pymysql.MySQLError as err:
        print("Koneksi MySQL gagal:", err)
        print("Pastikan MySQL (XAMPP/Laragon) aktif.")
        print("Periksa DB_USER, DB_PASSWORD, dan DB_NAME.")
