from datetime import date, timedelta
from werkzeug.security import check_password_hash, generate_password_hash

class Anggota:
    def __init__(self, nama, hak_akses='Anggota', password_hash=None, id_anggota=None):
        self.__id_anggota = id_anggota
        self.__nama = nama
        self.__hak_akses = hak_akses
        self.__password_hash = password_hash

    def get_id(self):
        return self.__id_anggota

    def get_nama(self):
        return self.__nama

    def get_hak_akses(self):
        return self.__hak_akses

    def cek_password(self, password):
        return check_password_hash(self.__password_hash, password)

    def is_admin(self):
        return self.__hak_akses == 'Admin'

    @staticmethod
    def buat_password(password):
        return generate_password_hash(password)

class Buku:
    def __init__(self, stok):
        self.__stok = stok

    def get_stok(self):
        return self.__stok

    def warna_stok(self):
        if self.get_stok() <= 5:
            return "text-red-600"
        else:
            return "text-green-600"

class Transaksi:
    def __init__(self, tanggal, status):
        self.__tanggal = tanggal
        self.__status = status

    def get_tanggal(self):
        return self.__tanggal

    def get_status(self):
        return self.__status


class Peminjaman(Transaksi):
    def jatuh_tempo(self):
        return self.get_tanggal() + timedelta(days=7)

    def hari_telat(self):
        if self.get_status() != 'Dipinjam':
            return 0
        selisih = (date.today() - self.jatuh_tempo()).days
        if selisih > 0:
            return selisih
        else:
            return 0

    def denda(self):
        return self.hari_telat() * 10000

