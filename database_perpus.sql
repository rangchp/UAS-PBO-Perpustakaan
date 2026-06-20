CREATE TABLE anggota (
    id_anggota INT AUTO_INCREMENT PRIMARY KEY,
    nama_lengkap VARCHAR(100) NOT NULL,
    email VARCHAR(50) UNIQUE NOT NULL,
    password text NOT NULL,
    hak_akses ENUM('Admin', 'Anggota') DEFAULT 'Anggota',
    tanggal_bergabung DATE DEFAULT Current_timestamp
);

CREATE TABLE kategori (
    id_kategori INT AUTO_INCREMENT PRIMARY KEY,
    nama_kategori VARCHAR(50) NOT NULL
);

CREATE TABLE buku (
    id_buku INT AUTO_INCREMENT PRIMARY KEY,
    id_kategori INT,
    judul_buku VARCHAR(255) NOT NULL,
    penulis VARCHAR(100),
    penerbit VARCHAR(100),
    tahun_terbit YEAR,
    stok INT DEFAULT 0,
    -- Menambahkan relasi Foreign Key ke tabel kategori
    CONSTRAINT fk_buku_kategori 
        FOREIGN KEY (id_kategori) 
        REFERENCES kategori(id_kategori)
        ON DELETE SET NULL 
        ON UPDATE CASCADE
);

INSERT INTO kategori (nama_kategori) VALUES 
('Novel'), 
('Sains'), 
('Sejarah'), 
('Teknologi');

INSERT INTO buku (id_kategori, judul_buku, penulis, penerbit, tahun_terbit, stok) VALUES 
-- Kategori Novel (id_kategori: 1)
(1, 'Laskar Pelangi', 'Andrea Hirata', 'Bentang Pustaka', 2005, 10),
(1, 'Bumi Manusia', 'Pramoedya Ananta Toer', 'Hasta Mitra', 1980, 5),
(1, 'Harry Potter and the Philosopher\'s Stone', 'J.K. Rowling', 'Bloomsbury', 1997, 12),
(1, 'Pulang', 'Leila S. Chudori', 'Kepustakaan Populer Gramedia', 2012, 7),
-- Kategori Sains (id_kategori: 2)
(2, 'Kosmos', 'Carl Sagan', 'Random House', 1980, 4),
(2, 'Sapiens: Riwayat Singkat Humankind', 'Yuval Noah Harari', 'Harvill Secker', 2011, 8),
(2, 'A Brief History of Time', 'Stephen Hawking', 'Bantam Books', 1988, 6),
(2, 'Gen: Sebuah Kisah Intim', 'Siddhartha Mukherjee', 'Scribner', 2016, 3),
-- Kategori Sejarah (id_kategori: 3)
(3, 'Madilog', 'Tan Malaka', 'Widjaya', 1943, 2),
(3, 'Revolusi Pemuda', 'Benedict Anderson', 'Pustaka Sinar Harapan', 1972, 5),
(3, 'Api Sejarah', 'Ahmad Mansur Suryanegara', 'Salamadani', 2009, 9),
-- Kategori Teknologi (id_kategori: 4)
(4, 'Clean Code', 'Robert C. Martin', 'Prentice Hall', 2008, 15),
(4, 'The Pragmatic Programmer', 'Andrew Hunt', 'Addison-Wesley', 1999, 10),
(4, 'You Don\'t Know JS', 'Kyle Simpson', 'O\'Reilly Media', 2014, 20),
(4, 'Deep Learning', 'Ian Goodfellow', 'MIT Press', 2016, 5);

CREATE TABLE peminjaman (
    id_peminjaman INT AUTO_INCREMENT PRIMARY KEY,
    id_anggota INT,
    id_buku INT,
    tanggal_pinjam DATE,
    tanggal_kembali DATE,
    status VARCHAR(20) DEFAULT 'Dipinjam',
    FOREIGN KEY (id_anggota) REFERENCES anggota(id_anggota),
    FOREIGN KEY (id_buku) REFERENCES buku(id_buku)
);


