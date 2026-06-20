from flask import Blueprint, redirect, session, flash
from flask import render_template, request, url_for
from models.database import get_db_connection
from models.perpustakaan import Buku, Peminjaman, Anggota

auth_bp = Blueprint('auth', __name__)


# ==================== LOGIN/REGISTER ====================

@auth_bp.route('/')
@auth_bp.route('/login', methods=['GET'])
def login_page():
    if 'user_id' in session:
        return redirect(url_for('auth.dashboard'))
    return render_template('login.html')

@auth_bp.route('/login', methods=['POST'])
def login():
    identifier = request.form.get('identifier')
    password = request.form.get('password')

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM anggota WHERE email = %s", (identifier,))
        user = cursor.fetchone()
        if user:
            anggota = Anggota(
                user['nama_lengkap'], user['hak_akses'],
                user['password'], user['id_anggota']
            )
            if anggota.cek_password(password):
                session['user_id'] = anggota.get_id()
                session['nama'] = anggota.get_nama()
                session['role'] = anggota.get_hak_akses()
                return redirect(url_for('auth.dashboard'))
            else:
                flash("Email atau password salah.", "error")
                return redirect(url_for('auth.login_page'))
        else:
            flash("Email atau password salah.", "error")
            return redirect(url_for('auth.login_page'))
    except Exception as e:
        print(f"Login Error: {e}")
        flash("Terjadi kesalahan saat login.", "error")
        return redirect(url_for('auth.login_page'))
    finally:
        cursor.close()
        db.close()

@auth_bp.route('/register', methods=['GET'])
def register_page():
    return render_template('register.html')

@auth_bp.route('/register', methods=['POST'])
def register():
    nama = request.form.get('nama_lengkap')
    email = request.form.get('email')
    password = request.form.get('password')
    hak_akses = request.form.get('hak_akses') or 'Anggota'

    if not nama or not email or not password:
        flash("Semua kolom wajib diisi.", "error")
        return redirect(url_for('auth.register_page'))

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute("SELECT id_anggota FROM anggota WHERE email = %s", (email,))
        if cursor.fetchone():
            flash("Email sudah terdaftar. Silakan gunakan email lain.", "error")
            return redirect(url_for('auth.register_page'))

        hashed_password = Anggota.buat_password(password)
        cursor.execute(
            "INSERT INTO anggota (nama_lengkap, email, password, hak_akses) "
            "VALUES (%s, %s, %s, %s)",
            (nama, email, hashed_password, hak_akses)
        )
        db.commit()
        flash("Registrasi berhasil. Silakan login.", "success")
        return redirect(url_for('auth.login_page'))
    except Exception as e:
        db.rollback()
        print(f"Register Error: {e}")
        flash("Gagal mendaftar. Silakan coba lagi.", "error")
        return redirect(url_for('auth.register_page'))
    finally:
        cursor.close()
        db.close()

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login_page'))


# ==================== DASHBOARD ====================

@auth_bp.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash("Silakan login terlebih dahulu.", "error")
        return redirect(url_for('auth.login_page'))

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute("SELECT COUNT(*) AS total FROM buku")
        total_buku = cursor.fetchone()['total']

        cursor.execute("SELECT COUNT(*) AS total FROM anggota")
        total_anggota = cursor.fetchone()['total']

        cursor.execute("SELECT COUNT(*) AS total FROM peminjaman WHERE status = 'Dipinjam'")
        total_dipinjam = cursor.fetchone()['total']

        cursor.execute("""
            SELECT p.tanggal_pinjam, p.status, a.nama_lengkap, b.judul_buku
            FROM peminjaman p
            JOIN anggota a ON p.id_anggota = a.id_anggota
            JOIN buku b ON p.id_buku = b.id_buku
            ORDER BY p.id_peminjaman DESC
            LIMIT 5
        """)
        peminjaman_terbaru = cursor.fetchall()

        return render_template('dashboard.html',
                               total_buku=total_buku,
                               total_anggota=total_anggota,
                               total_dipinjam=total_dipinjam,
                               peminjaman_terbaru=peminjaman_terbaru)
    except Exception as e:
        print(f"Dashboard Error: {e}")
        flash("Gagal memuat data dashboard.", "error")
        return render_template('dashboard.html', total_buku=0, total_anggota=0, total_dipinjam=0, peminjaman_terbaru=[])
    finally:
        cursor.close()
        db.close()


# ==================== DATA BUKU ====================

@auth_bp.route('/buku')
def buku():
    if 'user_id' not in session:
        flash("Silakan login terlebih dahulu.", "error")
        return redirect(url_for('auth.login_page'))

    cari = request.args.get('cari', '')
    kategori = request.args.get('kategori', '')
    kata = "%" + cari + "%"

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT b.*, k.nama_kategori
            FROM buku b
            LEFT JOIN kategori k ON b.id_kategori = k.id_kategori
            WHERE (b.judul_buku LIKE %s OR b.penulis LIKE %s OR b.penerbit LIKE %s)
              AND (b.id_kategori = %s OR %s = '')
            ORDER BY b.id_buku DESC
        """, (kata, kata, kata, kategori, kategori))
        books = cursor.fetchall()

        for row in books:
            b = Buku(row['stok'])
            row['warna_stok'] = b.warna_stok()

        cursor.execute("SELECT * FROM kategori ORDER BY nama_kategori ASC")
        daftar_kategori = cursor.fetchall()

        return render_template('buku.html', daftar_buku=books, daftar_kategori=daftar_kategori, cari=cari, kategori=kategori)
    except Exception as e:
        print(f"Error fetching books: {e}")
        flash("Gagal mengambil data buku.", "error")
        return redirect(url_for('auth.dashboard'))
    finally:
        cursor.close()
        db.close()

@auth_bp.route('/buku/tambah')
def tambah_buku():
    pengguna = Anggota(session.get('nama'), session.get('role'))
    if not pengguna.is_admin():
        flash("Hanya admin yang bisa mengelola data buku.", "error")
        return redirect(url_for('auth.buku'))

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM kategori ORDER BY nama_kategori ASC")
        categories = cursor.fetchall()
        return render_template('tambah_buku.html', daftar_kategori=categories)
    except Exception as e:
        print(f"Error loading form: {e}")
        return redirect(url_for('auth.buku'))
    finally:
        cursor.close()
        db.close()

@auth_bp.route('/buku/tambah_buku', methods=['POST'])
def ctambah_buku():
    pengguna = Anggota(session.get('nama'), session.get('role'))
    if not pengguna.is_admin():
        flash("Hanya admin yang bisa mengelola data buku.", "error")
        return redirect(url_for('auth.buku'))

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    judul = request.form.get('judul_buku')
    id_kategori = request.form.get('id_kategori')
    penulis = request.form.get('penulis')
    penerbit = request.form.get('penerbit')
    tahun = request.form.get('tahun_terbit')
    stok = request.form.get('stok')
    try:
        cursor.execute(
            "INSERT INTO buku (judul_buku, id_kategori, tahun_terbit, penulis, penerbit, stok) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (judul, id_kategori, tahun, penulis, penerbit, stok)
        )
        db.commit()
        flash("Buku berhasil ditambahkan.", "success")
        return redirect(url_for('auth.buku'))
    except Exception as e:
        db.rollback()
        print(f"Error saving book: {e}")
        flash("Gagal menyimpan buku.", "error")
        return redirect(url_for('auth.tambah_buku'))
    finally:
        cursor.close()
        db.close()

@auth_bp.route('/buku/edit/<int:id_buku>')
def edit_buku(id_buku):
    pengguna = Anggota(session.get('nama'), session.get('role'))
    if not pengguna.is_admin():
        flash("Hanya admin yang bisa mengelola data buku.", "error")
        return redirect(url_for('auth.buku'))

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM buku WHERE id_buku = %s", (id_buku,))
        buku = cursor.fetchone()
        cursor.execute("SELECT * FROM kategori ORDER BY nama_kategori ASC")
        categories = cursor.fetchall()
        if not buku:
            flash("Buku tidak ditemukan.", "error")
            return redirect(url_for('auth.buku'))
        return render_template('update_buku.html', buku=buku, daftar_kategori=categories)
    except Exception as e:
        print(f"Error loading edit form: {e}")
        return redirect(url_for('auth.buku'))
    finally:
        cursor.close()
        db.close()

@auth_bp.route('/buku/update/<int:id_buku>', methods=['POST'])
def cedit_buku(id_buku):
    pengguna = Anggota(session.get('nama'), session.get('role'))
    if not pengguna.is_admin():
        flash("Hanya admin yang bisa mengelola data buku.", "error")
        return redirect(url_for('auth.buku'))

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    judul = request.form.get('judul_buku')
    id_kategori = request.form.get('id_kategori')
    penulis = request.form.get('penulis')
    penerbit = request.form.get('penerbit')
    tahun = request.form.get('tahun_terbit')
    stok = request.form.get('stok')
    try:
        cursor.execute(
            "UPDATE buku SET judul_buku=%s, id_kategori=%s, tahun_terbit=%s, penulis=%s, penerbit=%s, stok=%s WHERE id_buku=%s",
            (judul, id_kategori, tahun, penulis, penerbit, stok, id_buku)
        )
        db.commit()
        flash("Buku berhasil diperbarui.", "success")
        return redirect(url_for('auth.buku'))
    except Exception as e:
        db.rollback()
        print(f"Error updating book: {e}")
        flash("Gagal memperbarui buku.", "error")
        return redirect(url_for('auth.edit_buku', id_buku=id_buku))
    finally:
        cursor.close()
        db.close()

@auth_bp.route('/buku/hapus/<int:id_buku>', methods=['POST'])
def hapus_buku(id_buku):
    pengguna = Anggota(session.get('nama'), session.get('role'))
    if not pengguna.is_admin():
        flash("Hanya admin yang bisa mengelola data buku.", "error")
        return redirect(url_for('auth.buku'))

    db = get_db_connection()
    cursor = db.cursor()
    try:
        cursor.execute("DELETE FROM buku WHERE id_buku = %s", (id_buku,))
        db.commit()
        flash("Buku berhasil dihapus dari koleksi.", "success")
    except Exception as e:
        print(f"Delete Error: {e}")
        db.rollback()
        flash("Gagal menghapus buku. Buku mungkin masih terkait dengan data peminjaman.", "error")
    finally:
        cursor.close()
        db.close()
    return redirect(url_for('auth.buku'))


# ==================== DATA ANGGOTA ====================

@auth_bp.route('/anggota')
def anggota():
    if 'user_id' not in session:
        flash("Silakan login terlebih dahulu.", "error")
        return redirect(url_for('auth.login_page'))

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM anggota ORDER BY id_anggota DESC")
        daftar = cursor.fetchall()
        return render_template('anggota.html', daftar_anggota=daftar)
    except Exception as e:
        print(f"Error fetching members: {e}")
        flash("Gagal mengambil data anggota.", "error")
        return redirect(url_for('auth.dashboard'))
    finally:
        cursor.close()
        db.close()

@auth_bp.route('/anggota/tambah')
def tambah_anggota():
    if 'user_id' not in session:
        flash("Silakan login terlebih dahulu.", "error")
        return redirect(url_for('auth.login_page'))
    pengguna = Anggota(session.get('nama'), session.get('role'))
    if not pengguna.is_admin():
        flash("Hanya admin yang bisa mengelola data anggota.", "error")
        return redirect(url_for('auth.anggota'))
    return render_template('tambah_anggota.html')

@auth_bp.route('/anggota/tambah_anggota', methods=['POST'])
def ctambah_anggota():
    pengguna = Anggota(session.get('nama'), session.get('role'))
    if not pengguna.is_admin():
        flash("Hanya admin yang bisa mengelola data anggota.", "error")
        return redirect(url_for('auth.anggota'))

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    nama = request.form.get('nama_lengkap')
    email = request.form.get('email')
    password = request.form.get('password')
    hak_akses = request.form.get('hak_akses') or 'Anggota'
    try:
        cursor.execute("SELECT id_anggota FROM anggota WHERE email = %s", (email,))
        if cursor.fetchone():
            flash("Email sudah terdaftar.", "error")
            return redirect(url_for('auth.tambah_anggota'))

        hashed_password = Anggota.buat_password(password)
        cursor.execute(
            "INSERT INTO anggota (nama_lengkap, email, password, hak_akses) "
            "VALUES (%s, %s, %s, %s)",
            (nama, email, hashed_password, hak_akses)
        )
        db.commit()
        flash("Anggota berhasil ditambahkan.", "success")
        return redirect(url_for('auth.anggota'))
    except Exception as e:
        db.rollback()
        print(f"Error saving member: {e}")
        flash("Gagal menyimpan anggota.", "error")
        return redirect(url_for('auth.tambah_anggota'))
    finally:
        cursor.close()
        db.close()

@auth_bp.route('/anggota/edit/<int:id_anggota>')
def edit_anggota(id_anggota):
    if 'user_id' not in session:
        flash("Silakan login terlebih dahulu.", "error")
        return redirect(url_for('auth.login_page'))
    pengguna = Anggota(session.get('nama'), session.get('role'))
    if not pengguna.is_admin():
        flash("Hanya admin yang bisa mengelola data anggota.", "error")
        return redirect(url_for('auth.anggota'))

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM anggota WHERE id_anggota = %s", (id_anggota,))
        anggota = cursor.fetchone()
        if not anggota:
            flash("Anggota tidak ditemukan.", "error")
            return redirect(url_for('auth.anggota'))
        return render_template('update_anggota.html', anggota=anggota)
    except Exception as e:
        print(f"Error loading edit form: {e}")
        return redirect(url_for('auth.anggota'))
    finally:
        cursor.close()
        db.close()

@auth_bp.route('/anggota/update/<int:id_anggota>', methods=['POST'])
def cedit_anggota(id_anggota):
    pengguna = Anggota(session.get('nama'), session.get('role'))
    if not pengguna.is_admin():
        flash("Hanya admin yang bisa mengelola data anggota.", "error")
        return redirect(url_for('auth.anggota'))

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    nama = request.form.get('nama_lengkap')
    email = request.form.get('email')
    hak_akses = request.form.get('hak_akses')
    try:
        cursor.execute(
            "UPDATE anggota SET nama_lengkap=%s, email=%s, hak_akses=%s WHERE id_anggota=%s",
            (nama, email, hak_akses, id_anggota)
        )
        db.commit()
        flash("Data anggota berhasil diperbarui.", "success")
        return redirect(url_for('auth.anggota'))
    except Exception as e:
        db.rollback()
        print(f"Error updating member: {e}")
        flash("Gagal memperbarui anggota.", "error")
        return redirect(url_for('auth.edit_anggota', id_anggota=id_anggota))
    finally:
        cursor.close()
        db.close()

@auth_bp.route('/anggota/hapus/<int:id_anggota>', methods=['POST'])
def hapus_anggota(id_anggota):
    pengguna = Anggota(session.get('nama'), session.get('role'))
    if not pengguna.is_admin():
        flash("Hanya admin yang bisa mengelola data anggota.", "error")
        return redirect(url_for('auth.anggota'))

    db = get_db_connection()
    cursor = db.cursor()
    try:
        cursor.execute("DELETE FROM anggota WHERE id_anggota = %s", (id_anggota,))
        db.commit()
        flash("Anggota berhasil dihapus.", "success")
    except Exception as e:
        print(f"Delete Error: {e}")
        db.rollback()
        flash("Gagal menghapus anggota. Mungkin masih terkait dengan data peminjaman.", "error")
    finally:
        cursor.close()
        db.close()
    return redirect(url_for('auth.anggota'))


# ==================== DATA PEMINJAMAN ====================

@auth_bp.route('/peminjaman')
def peminjaman():
    if 'user_id' not in session:
        flash("Silakan login terlebih dahulu.", "error")
        return redirect(url_for('auth.login_page'))

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT p.*, a.nama_lengkap, b.judul_buku
            FROM peminjaman p
            JOIN anggota a ON p.id_anggota = a.id_anggota
            JOIN buku b ON p.id_buku = b.id_buku
            WHERE (p.id_anggota = %s OR %s = 'Admin')
            ORDER BY p.id_peminjaman DESC
        """, (session['user_id'], session.get('role')))
        daftar = cursor.fetchall()

        for row in daftar:
            pinjam = Peminjaman(row['tanggal_pinjam'], row['status'])
            row['jatuh_tempo'] = pinjam.jatuh_tempo()

        return render_template('peminjaman.html', daftar_peminjaman=daftar)
    except Exception as e:
        print(f"Error fetching loans: {e}")
        flash("Gagal mengambil data peminjaman.", "error")
        return redirect(url_for('auth.dashboard'))
    finally:
        cursor.close()
        db.close()

@auth_bp.route('/peminjaman/tambah')
def tambah_peminjaman():
    if 'user_id' not in session:
        flash("Silakan login terlebih dahulu.", "error")
        return redirect(url_for('auth.login_page'))

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    try:
        pengguna = Anggota(session.get('nama'), session.get('role'))
        if pengguna.is_admin():
            cursor.execute("SELECT id_anggota, nama_lengkap FROM anggota ORDER BY nama_lengkap ASC")
        else:
            cursor.execute("SELECT id_anggota, nama_lengkap FROM anggota WHERE id_anggota = %s", (session['user_id'],))
        daftar_anggota = cursor.fetchall()
        cursor.execute("SELECT id_buku, judul_buku, stok FROM buku ORDER BY judul_buku ASC")
        daftar_buku = cursor.fetchall()
        return render_template('tambah_peminjaman.html', daftar_anggota=daftar_anggota, daftar_buku=daftar_buku)
    except Exception as e:
        print(f"Error loading form: {e}")
        return redirect(url_for('auth.peminjaman'))
    finally:
        cursor.close()
        db.close()

@auth_bp.route('/peminjaman/tambah_peminjaman', methods=['POST'])
def ctambah_peminjaman():
    if 'user_id' not in session:
        flash("Silakan login terlebih dahulu.", "error")
        return redirect(url_for('auth.login_page'))

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    pengguna = Anggota(session.get('nama'), session.get('role'))
    if pengguna.is_admin():
        id_anggota = request.form.get('id_anggota')
    else:
        id_anggota = session['user_id']
    id_buku = request.form.get('id_buku')
    tanggal_pinjam = request.form.get('tanggal_pinjam')
    tanggal_kembali = request.form.get('tanggal_kembali') or None
    status = request.form.get('status') or 'Dipinjam'
    try:
        if status == 'Dipinjam':
            cursor.execute("SELECT stok FROM buku WHERE id_buku = %s", (id_buku,))
            data_buku = cursor.fetchone()
            if not data_buku or data_buku['stok'] <= 0:
                flash("Stok buku habis, tidak bisa dipinjam.", "error")
                return redirect(url_for('auth.tambah_peminjaman'))

        cursor.execute(
            "INSERT INTO peminjaman (id_anggota, id_buku, tanggal_pinjam, tanggal_kembali, status) "
            "VALUES (%s, %s, %s, %s, %s)",
            (id_anggota, id_buku, tanggal_pinjam, tanggal_kembali, status)
        )
        if status == 'Dipinjam':
            cursor.execute("UPDATE buku SET stok = stok - 1 WHERE id_buku = %s", (id_buku,))
        db.commit()
        flash("Data peminjaman berhasil ditambahkan.", "success")
        return redirect(url_for('auth.peminjaman'))
    except Exception as e:
        db.rollback()
        print(f"Error saving loan: {e}")
        flash("Gagal menyimpan data peminjaman.", "error")
        return redirect(url_for('auth.tambah_peminjaman'))
    finally:
        cursor.close()
        db.close()

@auth_bp.route('/peminjaman/edit/<int:id_peminjaman>')
def edit_peminjaman(id_peminjaman):
    if 'user_id' not in session:
        flash("Silakan login terlebih dahulu.", "error")
        return redirect(url_for('auth.login_page'))

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM peminjaman WHERE id_peminjaman = %s", (id_peminjaman,))
        pinjam = cursor.fetchone()
        if not pinjam:
            flash("Data peminjaman tidak ditemukan.", "error")
            return redirect(url_for('auth.peminjaman'))
        pengguna = Anggota(session.get('nama'), session.get('role'))
        if not pengguna.is_admin() and pinjam['id_anggota'] != session['user_id']:
            flash("Anda tidak punya akses ke data ini.", "error")
            return redirect(url_for('auth.peminjaman'))
        cursor.execute("SELECT id_anggota, nama_lengkap FROM anggota ORDER BY nama_lengkap ASC")
        daftar_anggota = cursor.fetchall()
        cursor.execute("SELECT id_buku, judul_buku, stok FROM buku ORDER BY judul_buku ASC")
        daftar_buku = cursor.fetchall()
        return render_template('update_peminjaman.html', pinjam=pinjam, daftar_anggota=daftar_anggota, daftar_buku=daftar_buku)
    except Exception as e:
        print(f"Error loading edit form: {e}")
        return redirect(url_for('auth.peminjaman'))
    finally:
        cursor.close()
        db.close()

@auth_bp.route('/peminjaman/update/<int:id_peminjaman>', methods=['POST'])
def cedit_peminjaman(id_peminjaman):
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    id_anggota = request.form.get('id_anggota')
    id_buku = request.form.get('id_buku')
    tanggal_pinjam = request.form.get('tanggal_pinjam')
    tanggal_kembali = request.form.get('tanggal_kembali') or None
    status = request.form.get('status')
    try:
        cursor.execute("SELECT id_buku, status, id_anggota FROM peminjaman WHERE id_peminjaman = %s", (id_peminjaman,))
        lama = cursor.fetchone()

        pengguna = Anggota(session.get('nama'), session.get('role'))
        if not pengguna.is_admin() and lama and lama['id_anggota'] != session['user_id']:
            flash("Anda tidak punya akses ke data ini.", "error")
            return redirect(url_for('auth.peminjaman'))

        if lama and lama['status'] == 'Dipinjam':
            cursor.execute("UPDATE buku SET stok = stok + 1 WHERE id_buku = %s", (lama['id_buku'],))
        if status == 'Dipinjam':
            cursor.execute("SELECT stok FROM buku WHERE id_buku = %s", (id_buku,))
            data_buku = cursor.fetchone()
            if not data_buku or data_buku['stok'] <= 0:
                flash("Stok buku habis, tidak bisa dipinjam.", "error")
                return redirect(url_for('auth.edit_peminjaman', id_peminjaman=id_peminjaman))
            cursor.execute("UPDATE buku SET stok = stok - 1 WHERE id_buku = %s", (id_buku,))

        cursor.execute(
            "UPDATE peminjaman SET id_anggota=%s, id_buku=%s, tanggal_pinjam=%s, tanggal_kembali=%s, status=%s "
            "WHERE id_peminjaman=%s",
            (id_anggota, id_buku, tanggal_pinjam, tanggal_kembali, status, id_peminjaman)
        )
        db.commit()
        flash("Data peminjaman berhasil diperbarui.", "success")
        return redirect(url_for('auth.peminjaman'))
    except Exception as e:
        db.rollback()
        print(f"Error updating loan: {e}")
        flash("Gagal memperbarui data peminjaman.", "error")
        return redirect(url_for('auth.edit_peminjaman', id_peminjaman=id_peminjaman))
    finally:
        cursor.close()
        db.close()

@auth_bp.route('/peminjaman/hapus/<int:id_peminjaman>', methods=['POST'])
def hapus_peminjaman(id_peminjaman):
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute("SELECT id_buku, status, id_anggota FROM peminjaman WHERE id_peminjaman = %s", (id_peminjaman,))
        lama = cursor.fetchone()

        pengguna = Anggota(session.get('nama'), session.get('role'))
        if not pengguna.is_admin() and lama and lama['id_anggota'] != session['user_id']:
            flash("Anda tidak punya akses ke data ini.", "error")
            return redirect(url_for('auth.peminjaman'))

        cursor.execute("DELETE FROM peminjaman WHERE id_peminjaman = %s", (id_peminjaman,))

        if lama and lama['status'] == 'Dipinjam':
            cursor.execute("UPDATE buku SET stok = stok + 1 WHERE id_buku = %s", (lama['id_buku'],))
        db.commit()
        flash("Data peminjaman berhasil dihapus.", "success")
    except Exception as e:
        print(f"Delete Error: {e}")
        db.rollback()
        flash("Gagal menghapus data peminjaman.", "error")
    finally:
        cursor.close()
        db.close()
    return redirect(url_for('auth.peminjaman'))


# ==================== DENDA & SANKSI ====================

@auth_bp.route('/laporan')
def laporan():
    if 'user_id' not in session:
        flash("Silakan login terlebih dahulu.", "error")
        return redirect(url_for('auth.login_page'))

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT p.*, a.nama_lengkap, b.judul_buku
            FROM peminjaman p
            JOIN anggota a ON p.id_anggota = a.id_anggota
            JOIN buku b ON p.id_buku = b.id_buku
            WHERE p.status = 'Dipinjam'
            ORDER BY p.id_peminjaman DESC
        """)
        data = cursor.fetchall()

        daftar_denda = []
        total_denda = 0
        for row in data:
            pinjam = Peminjaman(row['tanggal_pinjam'], row['status'])
            if pinjam.hari_telat() > 0:
                row['hari_telat'] = pinjam.hari_telat()
                row['denda'] = pinjam.denda()
                daftar_denda.append(row)
                total_denda = total_denda + row['denda']

        return render_template('laporan.html', daftar_denda=daftar_denda, total_denda=total_denda)
    except Exception as e:
        print(f"Error fetching report: {e}")
        flash("Gagal memuat laporan.", "error")
        return redirect(url_for('auth.dashboard'))
    finally:
        cursor.close()
        db.close()
