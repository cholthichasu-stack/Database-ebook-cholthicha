# -*- coding: utf-8 -*-
"""
PhraDhamma E-Book Hub - Database Mini Project Backend
3NF Relational Architecture (ebookstore.db)
"""

import http.server
import socketserver
import sqlite3
import json
import os
import re
import urllib.parse
from datetime import datetime
import datetime as dt

PORT = 8000
DB_FILE = os.path.join(os.path.dirname(__file__), 'ebookstore.db')
STATIC_DIR = os.path.dirname(__file__)

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_db()
    cur = conn.cursor()

    # 1. roles
    cur.execute("""
    CREATE TABLE IF NOT EXISTS roles (
        role_id INTEGER PRIMARY KEY AUTOINCREMENT,
        role_name TEXT NOT NULL UNIQUE
    )
    """)

    # 2. users (พร้อมรองรับ PDPA)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        full_name TEXT NOT NULL,
        phone TEXT,
        pdpa_consent INTEGER NOT NULL DEFAULT 1,
        pdpa_consent_date DATETIME DEFAULT CURRENT_TIMESTAMP,
        role_id INTEGER NOT NULL DEFAULT 2,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (role_id) REFERENCES roles(role_id)
    )
    """)

    # 3. categories
    cur.execute("""
    CREATE TABLE IF NOT EXISTS categories (
        category_id INTEGER PRIMARY KEY AUTOINCREMENT,
        category_name TEXT NOT NULL UNIQUE
    )
    """)

    # 4. authors
    cur.execute("""
    CREATE TABLE IF NOT EXISTS authors (
        author_id INTEGER PRIMARY KEY AUTOINCREMENT,
        author_name TEXT NOT NULL,
        bio TEXT
    )
    """)

    # 5. ebooks
    cur.execute("""
    CREATE TABLE IF NOT EXISTS ebooks (
        ebook_id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT,
        price REAL NOT NULL CHECK (price >= 0),
        cover_image_url TEXT,
        is_active INTEGER NOT NULL DEFAULT 1,
        category_id INTEGER NOT NULL,
        author_id INTEGER NOT NULL,
        FOREIGN KEY (category_id) REFERENCES categories(category_id),
        FOREIGN KEY (author_id) REFERENCES authors(author_id)
    )
    """)

    # 6. carts & cart_items
    cur.execute("""
    CREATE TABLE IF NOT EXISTS carts (
        cart_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL UNIQUE,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS cart_items (
        cart_item_id INTEGER PRIMARY KEY AUTOINCREMENT,
        cart_id INTEGER NOT NULL,
        ebook_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL DEFAULT 1 CHECK (quantity > 0),
        FOREIGN KEY (cart_id) REFERENCES carts(cart_id) ON DELETE CASCADE,
        FOREIGN KEY (ebook_id) REFERENCES ebooks(ebook_id) ON DELETE CASCADE,
        UNIQUE(cart_id, ebook_id)
    )
    """)

    # 7. orders & order_items
    cur.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        order_id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_code TEXT NOT NULL UNIQUE,
        user_id INTEGER NOT NULL,
        order_date DATETIME DEFAULT CURRENT_TIMESTAMP,
        total_amount REAL NOT NULL CHECK (total_amount >= 0),
        status TEXT NOT NULL CHECK (status IN ('pending', 'paid', 'confirmed', 'cancelled')),
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS order_items (
        order_item_id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL,
        ebook_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL DEFAULT 1 CHECK (quantity > 0),
        unit_price REAL NOT NULL CHECK (unit_price >= 0),
        FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE,
        FOREIGN KEY (ebook_id) REFERENCES ebooks(ebook_id)
    )
    """)

    # 8. payments
    cur.execute("""
    CREATE TABLE IF NOT EXISTS payments (
        payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL UNIQUE,
        payment_method TEXT NOT NULL,
        proof_image TEXT,
        status TEXT NOT NULL DEFAULT 'pending_review',
        paid_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE
    )
    """)

    # 9. download_links
    cur.execute("""
    CREATE TABLE IF NOT EXISTS download_links (
        download_id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL,
        ebook_id INTEGER NOT NULL,
        file_name TEXT NOT NULL,
        file_size TEXT NOT NULL,
        download_url TEXT NOT NULL,
        expires_at DATETIME,
        FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE,
        FOREIGN KEY (ebook_id) REFERENCES ebooks(ebook_id),
        UNIQUE(order_id, ebook_id)
    )
    """)

    conn.commit()

    try:
        cur.execute("ALTER TABLE users ADD COLUMN pdpa_consent INTEGER NOT NULL DEFAULT 1")
    except Exception:
        pass
    try:
        cur.execute("ALTER TABLE users ADD COLUMN pdpa_consent_date DATETIME DEFAULT CURRENT_TIMESTAMP")
    except Exception:
        pass
    try:
        cur.execute("ALTER TABLE users ADD COLUMN avatar_url TEXT")
    except Exception:
        pass
    conn.commit()

    cur.execute("SELECT COUNT(*) FROM roles")
    if cur.fetchone()[0] == 0:
        seed_mock_data(conn)

    conn.close()

def seed_mock_data(conn):
    cur = conn.cursor()
    # 1. Roles
    cur.executemany("INSERT INTO roles (role_id, role_name) VALUES (?, ?)", [
        (1, 'admin'),
        (2, 'customer')
    ])

    # 2. บัญชีผู้ใช้ทดสอบ
    cur.executemany("""
    INSERT INTO users (user_id, email, password_hash, full_name, phone, pdpa_consent, pdpa_consent_date, role_id, created_at)
    VALUES (?, ?, ?, ?, ?, 1, '2026-01-01 08:00:00', ?, ?)
    """, [
        (1, 'admin@phradhamma.com', 'admin123', 'ผู้ดูแลศูนย์หนังสือพุทธธรรม (Admin)', '081-999-8888', 1, '2026-01-01 09:00:00'),
        (2, 'somchai@dhamma.com', 'pass123', 'สมชาย ใฝ่ธรรมะ', '089-111-2222', 2, '2026-01-05 10:15:00'),
        (3, 'kanya.dev@outlook.com', 'pass123', 'กัญญา ผู้ปฏิบัติธรรม', '086-333-4444', 2, '2026-01-10 14:20:00'),
        (4, 'thanawat.amulet@yahoo.com', 'pass123', 'ธนวัฒน์ นักสะสมพระเครื่อง', '085-555-6666', 2, '2026-01-15 11:00:00'),
        (5, 'nareerat.merit@gmail.com', 'pass123', 'นารีรัตน์ ชอบทำบุญ', '082-777-9999', 2, '2026-02-01 08:30:00')
    ])

    # 3. หมวดหมู่หนังสือพระ & ธรรมะ
    categories = [
        (1, "พระเครื่องและวัตถุมงคลยอดนิยม"),
        (2, "พระคาถาและบทสวดมนต์ศักดิ์สิทธิ์"),
        (3, "ประวัติและคำสอนพระเกจิอาจารย์"),
        (4, "หลักธรรมและการปฏิบัติวิปัสสนา"),
        (5, "นิทานชาดกและประวัติพุทธศาสนา")
    ]
    cur.executemany("INSERT INTO categories (category_id, category_name) VALUES (?, ?)", categories)

    # 4. ผู้แต่ง / สำนักพิมพ์
    authors = [
        (1, "สมเด็จพระพุฒาจารย์ (โต พรหมรังสี)", "ตำนานพระเกจิแห่งวัดระฆังโฆสิตาราม"),
        (2, "พุทธทาสภิกขุ", "สำนักสวนโมกขพลาราม อำเภอไชยา"),
        (3, "หลวงพ่อฤาษีลิงดำ", "วัดท่าซุง จ.อุทัยธานี"),
        (4, "ศูนย์ศึกษาพระเครื่องและมวลสาร", "รวบรวมข้อมูลพระเครื่องและตำราดูพระ"),
        (5, "สำนักพิมพ์ธรรมะรุ่งเรือง", "ตำราสวดมนต์และนิทานธรรมะ")
    ]
    cur.executemany("INSERT INTO authors (author_id, author_name, bio) VALUES (?, ?, ?)", authors)

    # 5. E-Book หนังสือพระ
    ebooks = [
        (1, "คู่มือชี้จุดจ่ายเงิน พระสมเด็จวัดระฆัง Vol. 1", "เจาะลึกมวลสาร พิมพ์ทรง และตำหนิสำคัญของพระสมเด็จวัดระฆังพิมพ์ใหญ่", 199.00, "https://media.tarad.com/l/lungkitti/img-lib/spd_2012021511952_b.jpg", 1, 1, 4),
        (2, "คัมภีร์พระคาถาชินบัญชร และพระคาถามหาจักรพรรดิ", "พร้อมบทสวดมนต์ทำวัตรเช้า-เย็น คำแปลฉบับสมบูรณ์ และอานุภาพการสวด", 99.00, "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcToirggxcs85qwGltKhgBFyMbpjGzIYdHqqG3MAYKpmaQ&s", 1, 2, 1),
        (3, "วิปัสสนากรรมฐานสำหรับผู้เริ่มต้น", "หลักการฝึกสติและสมาธิเบื้องต้น เพื่อความสงบแห่งจิตใจในชีวิตประจำวัน", 150.00, "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcT1kguUMFrQiK2jUx9Tp7hya9r38DwI_I-EmHYbS0TY3w&s", 1, 4, 2),
        (4, "ประวัติและวัตถุมงคล หลวงปู่ทวด วัดช้างให้", "รวบรวมประวัติการสร้างพระเนื้อว่านปี 2497 และเหรียญยอดนิยม", 250.00, "https://inwfile.com/s-cs/lu90e9.jpg", 1, 1, 4),
        (5, "คู่มือมโนมยิทธิ และการฝึกจิตสัมผัส", "แนวทางการฝึกกรรมฐานสายหลวงพ่อฤาษีลิงดำ วัดท่าซุง", 180.00, "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQ8B_YU710YFacBxqYdum-_HIujkCVYR7F1leEaE9CP5wKa3lI-EpvpZBk&s=10", 1, 4, 3),
        (6, "นิทานชาดก 50 เรื่อง สอนใจได้ข้อคิด", "เรื่องเล่าชาดกพร้อมอธิบายธรรมะเข้าใจง่าย สำหรับทุกวัย", 120.00, "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRmnymqj1IqKeAcy1BQWHZ1xWz-ZQCpw7raTtDihlW6CMmMPufJqtDwItI&s=10", 1, 5, 5),
        (7, "ตำราสวดมนต์ข้ามปี เสริมบารมีและโชคลาภ", "รวมบทสวดเจริญพระพุทธมนต์ คาถาบูชาดวงชะตา", 89.00, "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQI4ohxmqRRL3n4htSHTOlVReYF-4HBnyTXAH4nSH7dYGtYgh45qBKYTieL&s=10", 1, 2, 5),
        (8, "ส่องพระยอดนิยมภาคกลาง และวิธีดูพระแท้", "วิเคราะห์เนื้อหา คราบกรุ และพิมพ์ทรงพระยอดขุนพล", 220.00, "https://fm.lnwfile.com/_/fm/_raw/dk/26/sq.jpg", 1, 1, 4),
        (9, "อานุภาพแห่งการเจริญสติปัฏฐาน 4", "แนวทางการปฏิบัติตามหลักสติปัฏฐานเพื่อการดับทุกข์", 160.00, "https://d3dyak49qszsk5.cloudfront.net/_1ed6b23a9d.png", 1, 4, 2),
        (10, "คัมภีร์แก่นพุทธศาสน์ โดย พุทธทาสภิกขุ", "คำสอนเกี่ยวกับความว่าง (สุญญตา) และหัวใจพุทธศาสนา", 140.00, "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQC0CV9skstWzLV_3BqpqAmoNXZ6C32FR8_HhpT4u03MH9NhLBujH3jyoc&s=10", 1, 4, 2),
        (11, "ตำนานวัตถุมงคลหลวงพ่อเดิม วัดหนองโพ", "เจาะลึกมีดหมอและสิงห์มหาอำนาจ ยอดนิยม", 210.00, "https://inwfile.com/s-ds/bnqgs2.jpg", 1, 1, 4),
        (12, "สรุปธรรมะเข้าใจง่าย สำหรับชีวิตคนทำงาน", "หลักการใช้ธรรมะดับความเครียดและพัฒนาชีวิต", 135.00, "https://d3dyak49qszsk5.cloudfront.net/_2ab90da030.jpg", 1, 4, 5),
        (13, "คู่มือไขปริศนาธรรมะและชาดก เล่ม 1", "อธิบายหลักธรรมคำสอนผ่านคติชาดกโบราณ", 110.00, "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSHYE7z6ZRVuH6gvsaVaxkgiBkt-zDRpOXH6llReNxw4Vo2gsCWX-iL8wJN&s=10", 1, 5, 5),
        (14, "คัมภีร์เจริญจิตตภาวนาวิปัสสนา ขั้นสูง", "วิธีฝึกสมาธิแนวกรรมฐานและลำดับญาณ", 175.00, "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQAlHV-NMDQ2CI76eyXoX6TExAa1xCRVH7EOMCdPPUmJA&s", 1, 4, 3),
        (15, "พระสมเด็จวัดระฆัง Vol. 2 เจาะลึกเนื้อหา", "วิเคราะห์เนื้อหามวลสารและคราบกรุอย่างเป็นระบบ", 215.00, "https://cdn-ookbee.okbcdn.net/Books/HUAJANRUANGSAKGMAILC/2021/20211129113621131659/Thumbnails/Cover.jpg", 1, 1, 4),
        (16, "คัมภีร์พระคาถามหาจักรพรรดิและบทสวดมนต์", "รวมบทสวดมนต์เจริญภาวนาและพระคาถาต่างๆ", 105.00, "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRW9FTd55ftCsYPRex_kQblmLMBhx8XYN7vUNbeM2MuKNQKcpymHRweSvU&s=10", 1, 2, 1),
        (17, "ส่องพระยอดนิยม เล่ม 2 พระกรุยอดเยี่ยม", "ตำราพิจารณาพระกรุโบราณและพระเนื้อชิน", 190.00, "https://filebroker-cdn.lazada.co.th/kf/S376bddaaac0943f595b7adbd6b9162631.jpg", 1, 1, 4),
        (18, "คู่มือฝึกจิตสัมผัส เล่ม 2", "แนวทางปฏิบัติเจริญสติสายวัดท่าซุง", 185.00, "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcThjIO2qcoExkVfB-vEvSJxMc02DkHkcrC-zLnEWZxKi5lyyQ8Zzh4tBdY&s=10", 1, 4, 3),
        (19, "ตำนานวัตถุมงคลและเหรียญเกจิดัง", "รวบรวมเหรียญยอดนิยมและประวัติการสร้าง", 165.00, "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTw4ZUZRynEQlQso2iR0AbBilhOce9AJ1uBjLnuhHF69OP8uqObb3Z1KaXE&s=10", 1, 1, 4)
    ]
    cur.executemany("INSERT INTO ebooks (ebook_id, title, description, price, cover_image_url, is_active, category_id, author_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", ebooks)

    # 6. Seed ออเดอร์จำลอง
    mock_orders = [
        (1, "ORD-20260115-0001", 2, "2026-01-15 10:30:00", 250.00, 'confirmed'),
        (2, "ORD-20260120-0002", 3, "2026-01-20 14:15:00", 195.00, 'confirmed'),
        (3, "ORD-20260128-0003", 4, "2026-01-28 16:45:00", 135.00, 'confirmed'),
        (4, "ORD-20260205-0004", 5, "2026-02-05 09:20:00", 320.00, 'confirmed'),
        (5, "ORD-20260212-0005", 2, "2026-02-12 11:10:00", 125.00, 'confirmed'),
        (6, "ORD-20260218-0006", 3, "2026-02-18 19:30:00", 140.00, 'confirmed'),
        (7, "ORD-20260225-0007", 4, "2026-02-25 13:00:00", 260.00, 'confirmed'),
        (8, "ORD-20260302-0008", 5, "2026-03-02 15:40:00", 125.00, 'confirmed'),
        (9, "ORD-20260310-0009", 2, "2026-03-10 18:25:00", 330.00, 'confirmed'),
        (10, "ORD-20260315-0010", 3, "2026-03-15 20:10:00", 115.00, 'confirmed'),
        (11, "ORD-20260322-0011", 4, "2026-03-22 12:45:00", 195.00, 'confirmed'),
        (12, "ORD-20260404-0012", 5, "2026-04-04 10:15:00", 250.00, 'confirmed'),
        (13, "ORD-20260411-0013", 2, "2026-04-11 14:00:00", 135.00, 'confirmed'),
        (14, "ORD-20260419-0014", 3, "2026-04-19 16:30:00", 125.00, 'confirmed'),
        (15, "ORD-20260427-0015", 4, "2026-04-27 11:20:00", 140.00, 'confirmed'),
        (16, "ORD-20260503-0016", 5, "2026-05-03 09:50:00", 320.00, 'confirmed'),
        (17, "ORD-20260512-0017", 2, "2026-05-12 17:15:00", 195.00, 'confirmed'),
        (18, "ORD-20260520-0018", 3, "2026-05-20 21:00:00", 250.00, 'confirmed'),
        (19, "ORD-20260601-0019", 4, "2026-06-01 13:40:00", 125.00, 'confirmed'),
        (20, "ORD-20260610-0020", 5, "2026-06-10 15:30:00", 115.00, 'confirmed'),
        (21, "ORD-20260618-0021", 2, "2026-06-18 18:45:00", 265.00, 'confirmed'),
        (22, "ORD-20260705-0022", 3, "2026-07-05 10:20:00", 135.00, 'confirmed'),
        (23, "ORD-20260714-0023", 4, "2026-07-14 14:50:00", 195.00, 'confirmed'),
        (24, "ORD-20260722-0024", 5, "2026-07-22 16:10:00", 250.00, 'confirmed'),
        (25, "ORD-20260802-0025", 2, "2026-08-02 11:30:00", 140.00, 'confirmed'),
        (26, "ORD-20260815-0026", 3, "2026-08-15 19:00:00", 125.00, 'confirmed'),
        (27, "ORD-20260825-0027", 4, "2026-08-25 12:15:00", 240.00, 'confirmed'),
        (28, "ORD-20260905-0028", 5, "2026-09-05 15:00:00", 320.00, 'confirmed'),
        (29, "ORD-20260912-0029", 2, "2026-09-12 17:40:00", 125.00, 'confirmed'),
        (30, "ORD-20260920-0030", 3, "2026-09-20 20:30:00", 195.00, 'paid'),
        (31, "ORD-20260925-0031", 4, "2026-09-25 14:10:00", 135.00, 'pending'),
        (32, "ORD-20260927-0032", 5, "2026-09-27 16:50:00", 140.00, 'cancelled')
    ]
    cur.executemany("INSERT INTO orders (order_id, order_code, user_id, order_date, total_amount, status) VALUES (?, ?, ?, ?, ?, ?)", mock_orders)

    # 7. Order Items
    mock_order_items = [
        (1, 1, 1, 2, 125.00), (2, 2, 4, 1, 195.00), (3, 3, 2, 1, 135.00),
        (4, 4, 1, 1, 125.00), (5, 4, 4, 1, 195.00), (6, 5, 3, 1, 125.00),
        (7, 6, 6, 1, 140.00), (8, 7, 1, 1, 125.00), (9, 7, 2, 1, 135.00),
        (10, 8, 3, 1, 125.00), (11, 9, 2, 1, 135.00), (12, 9, 4, 1, 195.00),
        (13, 10, 5, 1, 115.00), (14, 11, 4, 1, 195.00), (15, 12, 1, 2, 125.00),
        (16, 13, 2, 1, 135.00), (17, 14, 3, 1, 125.00), (18, 15, 6, 1, 140.00),
        (19, 16, 1, 1, 125.00), (20, 16, 4, 1, 195.00), (21, 17, 4, 1, 195.00),
        (22, 18, 1, 2, 125.00), (23, 19, 3, 1, 125.00), (24, 20, 5, 1, 115.00),
        (25, 21, 1, 1, 125.00), (26, 21, 6, 1, 140.00), (27, 22, 2, 1, 135.00),
        (28, 23, 4, 1, 195.00), (29, 24, 1, 2, 125.00), (30, 25, 6, 1, 140.00),
        (31, 26, 3, 1, 125.00), (32, 27, 5, 1, 115.00), (33, 27, 1, 1, 125.00),
        (34, 28, 1, 1, 125.00), (35, 28, 4, 1, 195.00), (36, 29, 3, 1, 125.00),
        (37, 30, 4, 1, 195.00), (38, 31, 2, 1, 135.00), (39, 32, 6, 1, 140.00)
    ]
    cur.executemany("INSERT INTO order_items (order_item_id, order_id, ebook_id, quantity, unit_price) VALUES (?, ?, ?, ?, ?)", mock_order_items)

    # 8. Payments
    mock_payments = []
    for ord_id in range(1, 33):
        st = 'verified' if ord_id <= 29 else ('pending_review' if ord_id == 30 else ('pending' if ord_id == 31 else 'rejected'))
        mock_payments.append((ord_id, ord_id, 'PromptPay QR Transfer', 'https://images.unsplash.com/photo-1559526324-4b87b5e36e44?auto=format&fit=crop&w=400&q=80', st))
    cur.executemany("INSERT INTO payments (payment_id, order_id, payment_method, proof_image, status) VALUES (?, ?, ?, ?, ?)", mock_payments)

    # 9. Download Links
    mock_dl = []
    dl_id = 1
    for row in mock_order_items:
        o_id, eb_id = row[1], row[2]
        if o_id <= 29:
            mock_dl.append((dl_id, o_id, eb_id, f"phradhamma_ebook_{eb_id}.pdf", "14.2 MB", f"/api/download/{o_id}/{eb_id}", "2026-12-31 23:59:59"))
            dl_id += 1
    cur.executemany("INSERT INTO download_links (download_id, order_id, ebook_id, file_name, file_size, download_url, expires_at) VALUES (?, ?, ?, ?, ?, ?, ?)", mock_dl)

    conn.commit()

class AppRequestHandler(http.server.SimpleHTTPRequestHandler):
    def send_json_response(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, PATCH, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-User-Id")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))

    def send_error_response(self, message, status=400):
        self.send_json_response({"error": message, "success": False}, status=status)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, PATCH, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-User-Id")
        self.end_headers()

    def get_request_body(self):
        content_len = int(self.headers.get('Content-Length', 0))
        if content_len == 0:
            return {}
        raw = self.rfile.read(content_len).decode('utf-8')
        try:
            return json.loads(raw)
        except Exception:
            return {}

    def get_current_user_id(self):
        user_id_hdr = self.headers.get('X-User-Id')
        if user_id_hdr and user_id_hdr.isdigit():
            return int(user_id_hdr)
        return None

    def is_current_user_admin(self, conn):
        user_id = self.get_current_user_id()
        if not user_id:
            return False
        cur = conn.cursor()
        cur.execute("SELECT role_id FROM users WHERE user_id = ?", (user_id,))
        row = cur.fetchone()
        return bool(row and row['role_id'] == 1)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        if path in ('/', '/index.html', '/admin.html'):
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            file_name = 'admin.html' if path == '/admin.html' else 'index.html'
            with open(os.path.join(STATIC_DIR, file_name), 'rb') as f:
                self.wfile.write(f.read())
            return

        conn = get_db()
        cur = conn.cursor()

        try:
            if path == '/api/auth/me':
                user_id = self.get_current_user_id()
                if not user_id:
                    self.send_json_response({"user": None, "success": True})
                    return
                cur.execute("SELECT u.user_id, u.email, u.full_name, u.phone, u.avatar_url, u.role_id, u.created_at, r.role_name FROM users u JOIN roles r ON u.role_id = r.role_id WHERE u.user_id = ?", (user_id,))
                user = cur.fetchone()
                self.send_json_response({"user": dict(user) if user else None, "success": True})
                return

            if path == '/api/library':
                user_id = self.get_current_user_id()
                if not user_id:
                    self.send_error_response("กรุณาเข้าสู่ระบบ", status=401)
                    return
                cur.execute("""
                SELECT e.ebook_id, e.title, e.cover_image_url, e.description, c.category_name, a.author_name, dl.file_name, dl.file_size, dl.download_url
                FROM download_links dl
                JOIN ebooks e ON dl.ebook_id = e.ebook_id
                JOIN categories c ON e.category_id = c.category_id
                JOIN authors a ON e.author_id = a.author_id
                WHERE dl.order_id IN (SELECT order_id FROM orders WHERE user_id = ? AND status = 'confirmed')
                GROUP BY e.ebook_id
                ORDER BY dl.download_id DESC
                """, (user_id,))
                books = [dict(r) for r in cur.fetchall()]
                self.send_json_response({"library": books, "success": True})
                return

            if path == '/api/categories':
                cur.execute("SELECT category_id, category_name FROM categories ORDER BY category_id ASC")
                cats = [dict(r) for r in cur.fetchall()]
                self.send_json_response({"categories": cats, "success": True})
                return

            if path == '/api/authors':
                cur.execute("SELECT author_id, author_name, bio FROM authors ORDER BY author_id ASC")
                authors = [dict(r) for r in cur.fetchall()]
                self.send_json_response({"authors": authors, "success": True})
                return

            if path == '/api/ebooks':
                search_term = query.get('search', [''])[0].strip()
                cat_id = query.get('category', [''])[0].strip()
                sql = """
                SELECT e.ebook_id, e.title, e.description, e.price, e.cover_image_url, 
                       e.is_active, e.category_id, e.author_id,
                       c.category_name, a.author_name, a.bio as author_bio
                FROM ebooks e
                JOIN categories c ON e.category_id = c.category_id
                JOIN authors a ON e.author_id = a.author_id
                WHERE 1=1
                """
                params = []
                if search_term:
                    sql += " AND (e.title LIKE ? OR a.author_name LIKE ? OR e.description LIKE ?)"
                    p = f"%{search_term}%"
                    params.extend([p, p, p])
                if cat_id and cat_id.isdigit():
                    sql += " AND e.category_id = ?"
                    params.append(int(cat_id))

                sql += " ORDER BY e.ebook_id ASC"
                cur.execute(sql, params)
                books = [dict(r) for r in cur.fetchall()]
                self.send_json_response({"ebooks": books, "success": True})
                return

            if path == '/api/cart':
                user_id = self.get_current_user_id()
                if not user_id:
                    self.send_json_response({"items": [], "total": 0, "success": True})
                    return
                cur.execute("SELECT cart_id FROM carts WHERE user_id = ?", (user_id,))
                cart = cur.fetchone()
                if not cart:
                    self.send_json_response({"items": [], "total": 0, "success": True})
                    return
                cart_id = cart['cart_id']
                cur.execute("""
                SELECT ci.cart_item_id, ci.cart_id, ci.ebook_id, ci.quantity,
                       e.title, e.price, e.cover_image_url, e.is_active,
                       a.author_name, c.category_name, (ci.quantity * e.price) AS subtotal
                FROM cart_items ci
                JOIN ebooks e ON ci.ebook_id = e.ebook_id
                JOIN authors a ON e.author_id = a.author_id
                JOIN categories c ON e.category_id = c.category_id
                WHERE ci.cart_id = ?
                ORDER BY ci.cart_item_id ASC
                """, (cart_id,))
                items = [dict(r) for r in cur.fetchall()]
                total = sum(i['subtotal'] for i in items)
                self.send_json_response({"items": items, "total": total, "cart_id": cart_id, "success": True})
                return

            if path == '/api/orders/my':
                user_id = self.get_current_user_id()
                if not user_id:
                    self.send_error_response("กรุณาเข้าสู่ระบบก่อนดูคำสั่งซื้อ", status=401)
                    return
                cur.execute("""
                SELECT o.order_id, o.order_code, o.order_date, o.total_amount, o.status,
                       p.payment_method, p.proof_image, p.status as payment_status
                FROM orders o
                LEFT JOIN payments p ON o.order_id = p.order_id
                WHERE o.user_id = ?
                ORDER BY o.order_id DESC
                """, (user_id,))
                orders = [dict(r) for r in cur.fetchall()]
                for ord_entry in orders:
                    o_id = ord_entry['order_id']
                    cur.execute("""
                    SELECT oi.order_item_id, oi.ebook_id, oi.quantity, oi.unit_price, e.title, e.cover_image_url
                    FROM order_items oi
                    JOIN ebooks e ON oi.ebook_id = e.ebook_id
                    WHERE oi.order_id = ?
                    """, (o_id,))
                    ord_entry['items'] = [dict(r) for r in cur.fetchall()]
                    if ord_entry['status'] == 'confirmed':
                        cur.execute("SELECT download_id, ebook_id, file_name, file_size, download_url FROM download_links WHERE order_id = ?", (o_id,))
                        ord_entry['downloads'] = [dict(r) for r in cur.fetchall()]
                    else:
                        ord_entry['downloads'] = []
                self.send_json_response({"orders": orders, "success": True})
                return

            if path == '/api/orders/all':
                if not self.is_current_user_admin(conn):
                    self.send_error_response("สิทธิ์การใช้งานถูกปฏิเสธ: เฉพาะ Admin เท่านั้น", status=403)
                    return
                cur.execute("""
                SELECT o.order_id, o.order_code, o.order_date, o.total_amount, o.status,
                       u.user_id, u.full_name, u.email, u.phone,
                       p.payment_method, p.proof_image, p.status as payment_status, p.paid_at
                FROM orders o
                JOIN users u ON o.user_id = u.user_id
                LEFT JOIN payments p ON o.order_id = p.order_id
                ORDER BY o.order_id DESC
                """)
                orders = [dict(r) for r in cur.fetchall()]
                for ord_entry in orders:
                    cur.execute("""
                    SELECT oi.order_item_id, oi.ebook_id, oi.quantity, oi.unit_price, e.title
                    FROM order_items oi
                    JOIN ebooks e ON oi.ebook_id = e.ebook_id
                    WHERE oi.order_id = ?
                    """, (ord_entry['order_id'],))
                    ord_entry['items'] = [dict(r) for r in cur.fetchall()]
                self.send_json_response({"orders": orders, "success": True})
                return

            if path == '/api/users':
                if not self.is_current_user_admin(conn):
                    self.send_error_response("สิทธิ์การใช้งานถูกปฏิเสธ: เฉพาะ Admin เท่านั้น", status=403)
                    return
                cur.execute("""
                SELECT u.user_id, u.email, u.full_name, u.phone, u.role_id, u.created_at, u.pdpa_consent,
                       r.role_name, COUNT(o.order_id) as total_orders,
                       COALESCE(SUM(CASE WHEN o.status = 'confirmed' THEN o.total_amount ELSE 0 END), 0) as total_spent,
                       COALESCE(SUM(CASE WHEN o.status = 'cancelled' THEN 1 ELSE 0 END), 0) as rejected_orders_count
                FROM users u
                JOIN roles r ON u.role_id = r.role_id
                LEFT JOIN orders o ON u.user_id = o.user_id
                GROUP BY u.user_id, u.email, u.full_name, u.phone, u.role_id, u.created_at, r.role_name, u.pdpa_consent
                ORDER BY u.user_id ASC
                """)
                users = [dict(r) for r in cur.fetchall()]
                self.send_json_response({"users": users, "success": True})
                return

            if path.startswith('/api/reports/'):
                report_id = path.replace('/api/reports/', '').strip()

                if report_id == '1':
                    cur.execute("""
                    SELECT 
                        strftime('%Y-%m', order_date) AS month,
                        COUNT(order_id) AS total_orders,
                        COALESCE(ROUND(SUM(total_amount), 2), 0) AS total_revenue,
                        COALESCE(ROUND(AVG(total_amount), 2), 0) AS avg_order_value
                    FROM orders
                    WHERE status = 'confirmed'
                    GROUP BY strftime('%Y-%m', order_date)
                    ORDER BY month ASC
                    """)
                    rows = [dict(r) for r in cur.fetchall()]
                    self.send_json_response({
                        "report_id": 1,
                        "title": "ยอดขายตามช่วงเวลา (Sales Over Time)",
                        "description": "ยอดขายรวม, จำนวนคำสั่งซื้อ และค่าเฉลี่ยต่อคำสั่งซื้อ (นับเฉพาะออเดอร์ที่อนุมัติแล้ว)",
                        "sql_used": "JOIN, GROUP BY, SUM(), COUNT(), AVG(), Date Filters",
                        "data": rows,
                        "success": True
                    })
                    return

                if report_id == '2':
                    cur.execute("""
                    SELECT 
                        e.ebook_id, e.title, c.category_name, a.author_name,
                        COALESCE(SUM(oi.quantity), 0) AS total_units_sold,
                        COALESCE(ROUND(SUM(oi.quantity * oi.unit_price), 2), 0) AS total_revenue
                    FROM order_items oi
                    JOIN orders o ON oi.order_id = o.order_id
                    JOIN ebooks e ON oi.ebook_id = e.ebook_id
                    JOIN categories c ON e.category_id = c.category_id
                    JOIN authors a ON e.author_id = a.author_id
                    WHERE o.status = 'confirmed'
                    GROUP BY e.ebook_id, e.title, c.category_name, a.author_name
                    ORDER BY total_units_sold DESC, total_revenue DESC
                    LIMIT 5
                    """)
                    rows = [dict(r) for r in cur.fetchall()]
                    self.send_json_response({
                        "report_id": 2,
                        "title": "E-Book ขายดีที่สุด (Top 5 Best-Sellers)",
                        "description": "หนังสือพระและตำราธรรมะที่ขายได้จำนวนเล่มและยอดขายสูงสุด 5 อันดับแรก (เฉพาะออเดอร์ confirmed)",
                        "sql_used": "JOIN, GROUP BY, SUM(), LIMIT",
                        "data": rows,
                        "success": True
                    })
                    return

                if report_id == '3':
                    cur.execute("""
                    SELECT 
                        c.category_id,
                        c.category_name,
                        COUNT(DISTINCT CASE WHEN o.status = 'confirmed' THEN o.order_id END) AS order_count,
                        COALESCE(SUM(CASE WHEN o.status = 'confirmed' THEN oi.quantity ELSE 0 END), 0) AS total_books_sold,
                        COALESCE(ROUND(SUM(CASE WHEN o.status = 'confirmed' THEN (oi.quantity * oi.unit_price) ELSE 0 END), 2), 0) AS total_category_revenue,
                        COALESCE(SUM(CASE WHEN o.status = 'cancelled' THEN 1 ELSE 0 END), 0) AS rejected_orders_count
                    FROM categories c
                    LEFT JOIN ebooks e ON c.category_id = e.category_id
                    LEFT JOIN order_items oi ON e.ebook_id = oi.ebook_id
                    LEFT JOIN orders o ON oi.order_id = o.order_id
                    GROUP BY c.category_id, c.category_name
                    ORDER BY total_category_revenue DESC
                    """)
                    cats = [dict(r) for r in cur.fetchall()]

                    for cat in cats:
                        cur.execute("""
                        SELECT 
                            e.title,
                            COALESCE(SUM(CASE WHEN o.status = 'confirmed' THEN oi.quantity ELSE 0 END), 0) as units_sold,
                            COALESCE(ROUND(SUM(CASE WHEN o.status = 'confirmed' THEN (oi.quantity * oi.unit_price) ELSE 0 END), 2), 0) as book_revenue
                        FROM ebooks e
                        LEFT JOIN order_items oi ON e.ebook_id = oi.ebook_id
                        LEFT JOIN orders o ON oi.order_id = o.order_id
                        WHERE e.category_id = ?
                        GROUP BY e.ebook_id, e.title
                        ORDER BY units_sold DESC
                        """, (cat['category_id'],))
                        cat['sub_books'] = [dict(r) for r in cur.fetchall()]

                    self.send_json_response({
                        "report_id": 3,
                        "title": "ยอดขายตามหมวดหมู่พร้อมแจกแจงรายเล่ม (Sales by Category & Books Drilldown)",
                        "description": "สรุปยอดขายหมวดหมู่ พร้อมแตกแถวรายชื่อหนังสือที่ขายได้จริงใต้หมวด (ตัดยอดออเดอร์ที่ถูกยกเลิกแล้ว)",
                        "sql_used": "Multi-table JOIN, GROUP BY, SUM(), Conditional Aggregations",
                        "data": cats,
                        "success": True
                    })
                    return

                if report_id == '4':
                    cur.execute("""
                    SELECT 
                        u.user_id, u.full_name, u.email,
                        COUNT(o.order_id) AS total_orders,
                        COALESCE(ROUND(SUM(CASE WHEN o.status = 'confirmed' THEN o.total_amount ELSE 0 END), 2), 0) AS confirmed_spending,
                        SUM(CASE WHEN o.status = 'confirmed' THEN 1 ELSE 0 END) AS confirmed_orders,
                        SUM(CASE WHEN o.status = 'cancelled' THEN 1 ELSE 0 END) AS cancelled_orders,
                        SUM(CASE WHEN o.status IN ('pending', 'paid') THEN 1 ELSE 0 END) AS pending_orders
                    FROM users u
                    LEFT JOIN orders o ON u.user_id = o.user_id
                    WHERE u.role_id = 2
                    GROUP BY u.user_id, u.full_name, u.email
                    ORDER BY confirmed_spending DESC
                    """)
                    rows = [dict(r) for r in cur.fetchall()]
                    self.send_json_response({
                        "report_id": 4,
                        "title": "พฤติกรรมลูกค้าและยอดซื้อสะสม (Customer Analytics)",
                        "description": "วิเคราะห์ลูกค้า จำแนกยอดซื้อที่อนุมัติสำเร็จ และจำนวนออเดอร์ที่ถูกปฏิเสธสลิป",
                        "sql_used": "JOIN, GROUP BY, SUM(), CASE WHEN",
                        "data": rows,
                        "success": True
                    })
                    return

            m_dl = re.match(r'^/api/download/(\d+)/(\d+)$', path)
            if m_dl:
                order_id = int(m_dl.group(1))
                ebook_id = int(m_dl.group(2))
                user_id = self.get_current_user_id()

                if not user_id:
                    self.send_error_response("กรุณาเข้าสู่ระบบก่อนดาวน์โหลด", status=401)
                    return

                cur.execute("SELECT order_id, user_id, status FROM orders WHERE order_id = ?", (order_id,))
                order = cur.fetchone()
                if not order:
                    self.send_error_response("ไม่พบคำสั่งซื้อนี้", status=404)
                    return

                is_admin = self.is_current_user_admin(conn)
                if not is_admin and order['user_id'] != user_id:
                    self.send_error_response("🔒 สิทธิ์ถูกปฏิเสธ: คุณไม่มีสิทธิ์เข้าถึงไฟล์ของออเดอร์ผู้อื่น", status=403)
                    return

                if order['status'] != 'confirmed':
                    self.send_error_response("🔒 ไม่อนุญาตให้ดาวน์โหลด: คำสั่งซื้อนี้ยังไม่ได้รับการอนุมัติ", status=403)
                    return

                cur.execute("SELECT * FROM download_links WHERE order_id = ? AND ebook_id = ?", (order_id, ebook_id))
                dl = cur.fetchone()
                if not dl:
                    self.send_error_response("ไม่พบสิทธิ์การดาวน์โหลด E-Book เล่มนี้ในคำสั่งซื้อของคุณ", status=404)
                    return

                self.send_response(200)
                self.send_header('Content-Type', 'application/pdf')
                self.send_header('Content-Disposition', f'attachment; filename="{dl["file_name"]}"')
                self.end_headers()
                
                file_path = os.path.join(STATIC_DIR, 'protected_files', dl['file_name'])
                if os.path.exists(file_path):
                    with open(file_path, 'rb') as f:
                        self.wfile.write(f.read())
                else:
                    sample_data = f"%PDF-1.4 Secured E-Book Content for Order #{order_id}".encode('utf-8')
                    self.wfile.write(sample_data)
                return

            self.send_error_response(f"Endpoint not found: {path}", status=404)

        except Exception as e:
            self.send_error_response(f"Internal Server Error: {str(e)}", status=500)
        finally:
            conn.close()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        body = self.get_request_body()

        conn = get_db()
        cur = conn.cursor()

        try:
            if path == '/api/auth/register':
                email = body.get('email', '').strip().lower()
                full_name = body.get('full_name', '').strip()
                phone = body.get('phone', '').strip()
                password = body.get('password', '').strip()
                pdpa_consent = body.get('pdpa_consent', False)

                if not pdpa_consent:
                    self.send_error_response("คุณต้องยอมรับเงื่อนไขนโยบายความเป็นส่วนตัว (PDPA) ก่อนสมัครสมาชิก", status=400)
                    return

                if not email or not full_name or not password:
                    self.send_error_response("กรุณากรอกข้อมูลให้ครบถ้วน", status=400)
                    return

                cur.execute("SELECT user_id FROM users WHERE email = ?", (email,))
                if cur.fetchone():
                    self.send_error_response(f"อีเมล '{email}' มีผู้ใช้งานในระบบแล้ว (UNIQUE Constraint)", status=400)
                    return

                cur.execute("""
                INSERT INTO users (email, password_hash, full_name, phone, pdpa_consent, pdpa_consent_date, role_id)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, 2)
                """, (email, password, full_name, phone, 1))
                conn.commit()

                user_id = cur.lastrowid
                cur.execute("SELECT u.user_id, u.email, u.full_name, u.phone, u.avatar_url, u.role_id, u.created_at, r.role_name FROM users u JOIN roles r ON u.role_id = r.role_id WHERE u.user_id = ?", (user_id,))
                user = dict(cur.fetchone())
                self.send_json_response({"user": user, "message": "สมัครสมาชิกสำเร็จ", "success": True})
                return

            if path == '/api/auth/login':
                email = body.get('email', '').strip().lower()
                password = body.get('password', '').strip()

                cur.execute("SELECT u.user_id, u.email, u.full_name, u.phone, u.avatar_url, u.role_id, u.created_at, r.role_name, u.password_hash FROM users u JOIN roles r ON u.role_id = r.role_id WHERE u.email = ?", (email,))
                user = cur.fetchone()
                if not user or user['password_hash'] != password:
                    self.send_error_response("อีเมลหรือรหัสผ่านไม่ถูกต้อง", status=401)
                    return

                user_dict = dict(user)
                del user_dict['password_hash']
                self.send_json_response({"user": user_dict, "message": "เข้าสู่ระบบสำเร็จ", "success": True})
                return

            if path == '/api/cart/add':
                user_id = self.get_current_user_id()
                if not user_id:
                    self.send_error_response("กรุณาเข้าสู่ระบบก่อนเพิ่มสินค้า", status=401)
                    return

                ebook_id = body.get('ebook_id')
                cur.execute("SELECT ebook_id, title, is_active FROM ebooks WHERE ebook_id = ?", (ebook_id,))
                ebook = cur.fetchone()
                if not ebook or not ebook['is_active']:
                    self.send_error_response("หนังสือเล่มนี้ไม่พร้อมจำหน่าย", status=400)
                    return

                thai_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                cur.execute("SELECT cart_id FROM carts WHERE user_id = ?", (user_id,))
                cart = cur.fetchone()
                if not cart:
                    cur.execute("INSERT INTO carts (user_id, updated_at) VALUES (?, ?)", (user_id, thai_time))
                    conn.commit()
                    cart_id = cur.lastrowid
                else:
                    cart_id = cart['cart_id']
                    cur.execute("UPDATE carts SET updated_at = ? WHERE cart_id = ?", (thai_time, cart_id))
                    conn.commit()

                cur.execute("SELECT cart_item_id FROM cart_items WHERE cart_id = ? AND ebook_id = ?", (cart_id, ebook_id))
                if cur.fetchone():
                    self.send_error_response("สินค้านี้อยู่ในตะกร้าแล้ว", status=400)
                    return

                cur.execute("INSERT INTO cart_items (cart_id, ebook_id, quantity) VALUES (?, ?, 1)", (cart_id, ebook_id))
                conn.commit()
                self.send_json_response({"message": f"เพิ่ม '{ebook['title']}' ลงในตะกร้าแล้ว", "success": True})
                return

            if path == '/api/checkout':
                user_id = self.get_current_user_id()
                if not user_id:
                    self.send_error_response("กรุณาเข้าสู่ระบบก่อนสั่งซื้อ", status=401)
                    return

                payment_method = body.get('payment_method', 'PromptPay QR Transfer')
                proof_image = body.get('proof_image', '')

                if not proof_image:
                    self.send_error_response("กรุณาแนบรูปภาพสลิปการโอนเงินเพื่อตรวจสอบ", status=400)
                    return

                cur.execute("SELECT cart_id FROM carts WHERE user_id = ?", (user_id,))
                cart = cur.fetchone()
                if not cart:
                    self.send_error_response("ไม่มีสินค้าในตะกร้า", status=400)
                    return

                cart_id = cart['cart_id']
                cur.execute("""
                SELECT ci.ebook_id, ci.quantity, e.price, e.title, e.is_active
                FROM cart_items ci
                JOIN ebooks e ON ci.ebook_id = e.ebook_id
                WHERE ci.cart_id = ?
                """, (cart_id,))
                cart_items = [dict(r) for r in cur.fetchall()]

                if not cart_items:
                    self.send_error_response("ไม่มีรายการสินค้าในตะกร้า", status=400)
                    return

                total_amount = sum(i['price'] * i['quantity'] for i in cart_items)
                now_str = datetime.now().strftime('%Y%m%d')
                order_code = f"ORD-{now_str}-{int(datetime.now().timestamp() * 1000) % 10000:04d}"

                cur.execute("""
                INSERT INTO orders (order_code, user_id, total_amount, status)
                VALUES (?, ?, ?, 'paid')
                """, (order_code, user_id, total_amount))
                order_id = cur.lastrowid

                for item in cart_items:
                    cur.execute("""
                    INSERT INTO order_items (order_id, ebook_id, quantity, unit_price)
                    VALUES (?, ?, ?, ?)
                    """, (order_id, item['ebook_id'], item['quantity'], item['price']))

                cur.execute("""
                INSERT INTO payments (order_id, payment_method, proof_image, status)
                VALUES (?, ?, ?, 'pending_review')
                """, (order_id, payment_method, proof_image))

                cur.execute("DELETE FROM cart_items WHERE cart_id = ?", (cart_id,))
                conn.commit()

                self.send_json_response({
                    "order_id": order_id,
                    "order_code": order_code,
                    "total_amount": total_amount,
                    "status": "paid",
                    "message": "ส่งคำสั่งซื้อและแนบสลิปเรียบร้อย รอแอดมินตรวจสอบความถูกต้อง",
                    "success": True
                })
                return

            if path == '/api/ebooks':
                if not self.is_current_user_admin(conn):
                    self.send_error_response("เฉพาะ Admin เท่านั้น", status=403)
                    return
                
                title = body.get('title', '').strip()
                price = float(body.get('price', 0))
                category_id = int(body.get('category_id', 1))
                author_id = int(body.get('author_id', 1))
                cover_image_url = body.get('cover_image_url', '').strip()
                description = body.get('description', '').strip()

                if not title:
                    self.send_error_response("กรุณาระบุชื่อหนังสือ", status=400)
                    return

                cur.execute("SELECT ebook_id FROM ebooks WHERE title = ? AND author_id = ?", (title, author_id))
                if cur.fetchone():
                    self.send_error_response("หนังสือชื่อนี้และผู้แต่งท่านนี้ มีอยู่ในระบบแล้ว ไม่สามารถเพิ่มซ้ำได้", status=400)
                    return

                cur.execute("""
                INSERT INTO ebooks (title, description, price, cover_image_url, is_active, category_id, author_id)
                VALUES (?, ?, ?, ?, 1, ?, ?)
                """, (title, description, price, cover_image_url, category_id, author_id))
                conn.commit()
                self.send_json_response({"ebook_id": cur.lastrowid, "message": "เพิ่ม E-Book สำเร็จ", "success": True})
                return

            if path == '/api/categories':
                if not self.is_current_user_admin(conn):
                    self.send_error_response("เฉพาะ Admin เท่านั้น", status=403)
                    return
                category_name = body.get('category_name', '').strip()
                cur.execute("INSERT INTO categories (category_name) VALUES (?)", (category_name,))
                conn.commit()
                self.send_json_response({"category_id": cur.lastrowid, "message": "เพิ่มหมวดหมู่สำเร็จ", "success": True})
                return

            self.send_error_response(f"Endpoint not found: {path}", status=404)

        except Exception as e:
            self.send_error_response(str(e), status=400)
        finally:
            conn.close()

    def do_PUT(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        body = self.get_request_body()

        conn = get_db()
        cur = conn.cursor()

        try:
            if path == '/api/auth/profile':
                user_id = self.get_current_user_id()
                if not user_id:
                    self.send_error_response("กรุณาเข้าสู่ระบบก่อนแก้ไขข้อมูล", status=401)
                    return

                full_name = body.get('full_name', '').strip()
                phone = body.get('phone', '').strip()
                avatar_url = body.get('avatar_url', None)
                current_password = body.get('current_password', '').strip()
                new_password = body.get('new_password', '').strip()

                if not full_name:
                    self.send_error_response("กรุณากรอกชื่อ-นามสกุล", status=400)
                    return

                if new_password:
                    if not current_password:
                        self.send_error_response("กรุณากรอกรหัสผ่านเดิมเพื่อยืนยันความปลอดภัย", status=400)
                        return
                    cur.execute("SELECT password_hash FROM users WHERE user_id = ?", (user_id,))
                    u_row = cur.fetchone()
                    if not u_row or u_row['password_hash'] != current_password:
                        self.send_error_response("รหัสผ่านเดิมไม่ถูกต้อง ไม่อนุญาตให้เปลี่ยนรหัสผ่าน", status=400)
                        return

                updates = ["full_name = ?", "phone = ?"]
                params = [full_name, phone]

                if avatar_url is not None:
                    updates.append("avatar_url = ?")
                    params.append(avatar_url)

                if new_password:
                    updates.append("password_hash = ?")
                    params.append(new_password)

                params.append(user_id)
                sql = "UPDATE users SET " + ", ".join(updates) + " WHERE user_id = ?"
                cur.execute(sql, params)
                conn.commit()

                cur.execute("SELECT u.user_id, u.email, u.full_name, u.phone, u.avatar_url, u.role_id, u.created_at, r.role_name FROM users u JOIN roles r ON u.role_id = r.role_id WHERE u.user_id = ?", (user_id,))
                user = dict(cur.fetchone())
                self.send_json_response({"user": user, "message": "อัปเดตข้อมูลส่วนตัวเรียบร้อยแล้ว", "success": True})
                return

            m_cat = re.match(r'^/api/categories/(\d+)$', path)
            if m_cat:
                if not self.is_current_user_admin(conn):
                    self.send_error_response("เฉพาะ Admin เท่านั้น", status=403)
                    return
                category_id = int(m_cat.group(1))
                category_name = body.get('category_name', '').strip()
                if not category_name:
                    self.send_error_response("กรุณาระบุชื่อหมวดหมู่", status=400)
                    return
                cur.execute("UPDATE categories SET category_name = ? WHERE category_id = ?", (category_name, category_id))
                conn.commit()
                self.send_json_response({"message": "อัปเดตชื่อหมวดหมู่สำเร็จ", "success": True})
                return

            m_cart = re.match(r'^/api/cart/item/(\d+)$', path)
            if m_cart:
                cart_item_id = int(m_cart.group(1))
                qty = int(body.get('quantity', 1))
                
                cur.execute("SELECT cart_id FROM cart_items WHERE cart_item_id = ?", (cart_item_id,))
                item_row = cur.fetchone()
                
                if qty <= 0:
                    cur.execute("DELETE FROM cart_items WHERE cart_item_id = ?", (cart_item_id,))
                else:
                    cur.execute("UPDATE cart_items SET quantity = ? WHERE cart_item_id = ?", (qty, cart_item_id))
                
                if item_row:
                    cart_id = item_row['cart_id']
                    cur.execute("SELECT COUNT(*) AS cnt FROM cart_items WHERE cart_id = ?", (cart_id,))
                    count_row = cur.fetchone()
                    if count_row['cnt'] == 0:
                        cur.execute("DELETE FROM carts WHERE cart_id = ?", (cart_id,))
                    else:
                        thai_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        cur.execute("UPDATE carts SET updated_at = ? WHERE cart_id = ?", (thai_time, cart_id))

                conn.commit()
                self.send_json_response({"message": "อัปเดตจำนวนสำเร็จ", "success": True})
                return

            m_eb_update = re.match(r'^/api/ebooks/(\d+)$', path)
            if m_eb_update:
                if not self.is_current_user_admin(conn):
                    self.send_error_response("เฉพาะ Admin เท่านั้น", status=403)
                    return
                ebook_id = int(m_eb_update.group(1))
                title = body.get('title', '').strip()
                price = float(body.get('price', 0))
                author_id = int(body.get('author_id', 1))
                cover_image_url = body.get('cover_image_url', '').strip()
                description = body.get('description', '').strip()
                
                cur.execute("""
                UPDATE ebooks SET title = ?, price = ?, author_id = ?, cover_image_url = ?, description = ?
                WHERE ebook_id = ?
                """, (title, price, author_id, cover_image_url, description, ebook_id))
                conn.commit()
                self.send_json_response({"message": "บันทึกข้อมูลสำเร็จ", "success": True})
                return

            self.send_error_response(f"Endpoint not found: {path}", status=404)

        except Exception as e:
            self.send_error_response(str(e), status=400)
        finally:
            conn.close()

    def do_PATCH(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        body = self.get_request_body()

        conn = get_db()
        cur = conn.cursor()

        try:
            m_ord = re.match(r'^/api/orders/(\d+)/status$', path)
            if m_ord:
                if not self.is_current_user_admin(conn):
                    self.send_error_response("เฉพาะ Admin เท่านั้น", status=403)
                    return
                order_id = int(m_ord.group(1))
                new_status = body.get('status', '').strip()

                if new_status not in ('pending', 'paid', 'confirmed', 'cancelled'):
                    self.send_error_response("สถานะไม่ถูกต้อง", status=400)
                    return

                cur.execute("UPDATE orders SET status = ? WHERE order_id = ?", (new_status, order_id))

                if new_status == 'confirmed':
                    cur.execute("UPDATE payments SET status = 'verified' WHERE order_id = ?", (order_id,))
                    cur.execute("SELECT ebook_id FROM order_items WHERE order_id = ?", (order_id,))
                    items = cur.fetchall()
                    for item in items:
                        eb_id = item['ebook_id']
                        fname = f"phradhamma_ebook_{eb_id}.pdf"
                        cur.execute("""
                        INSERT OR IGNORE INTO download_links (order_id, ebook_id, file_name, file_size, download_url, expires_at)
                        VALUES (?, ?, ?, '14.2 MB', ?, '2026-12-31 23:59:59')
                        """, (order_id, eb_id, fname, f"/api/download/{order_id}/{eb_id}"))
                else:
                    cur.execute("DELETE FROM download_links WHERE order_id = ?", (order_id,))
                    if new_status == 'cancelled':
                        cur.execute("UPDATE payments SET status = 'rejected' WHERE order_id = ?", (order_id,))
                    elif new_status == 'paid':
                        cur.execute("UPDATE payments SET status = 'pending_review' WHERE order_id = ?", (order_id,))

                conn.commit()
                self.send_json_response({"message": f"เปลี่ยนสถานะคำสั่งซื้อ #{order_id} เป็น '{new_status}' สำเร็จ", "success": True})
                return

            m_user_role = re.match(r'^/api/users/(\d+)/role$', path)
            if m_user_role:
                if not self.is_current_user_admin(conn):
                    self.send_error_response("เฉพาะ Admin เท่านั้น", status=403)
                    return
                target_user_id = int(m_user_role.group(1))
                new_role_id = body.get('role_id', 2)
                cur.execute("UPDATE users SET role_id = ? WHERE user_id = ?", (new_role_id, target_user_id))
                conn.commit()
                self.send_json_response({"message": "เปลี่ยนสิทธิ์สำเร็จ", "success": True})
                return
                
            m_eb = re.match(r'^/api/ebooks/(\d+)/toggle$', path)
            if m_eb:
                if not self.is_current_user_admin(conn):
                    self.send_error_response("เฉพาะ Admin เท่านั้น", status=403)
                    return
                
                ebook_id = int(m_eb.group(1))
                cur.execute("SELECT is_active FROM ebooks WHERE ebook_id = ?", (ebook_id,))
                eb = cur.fetchone()
                new_val = 0 if eb['is_active'] == 1 else 1
                cur.execute("UPDATE ebooks SET is_active = ? WHERE ebook_id = ?", (new_val, ebook_id))
                conn.commit()
                self.send_json_response({"is_active": new_val, "message": "อัปเดตสถานะสำเร็จ", "success": True})
                return

            self.send_error_response(f"Endpoint not found: {path}", status=404)

        except Exception as e:
            self.send_error_response(str(e), status=400)
        finally:
            conn.close()

    def do_DELETE(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        conn = get_db()
        cur = conn.cursor()

        try:
            m_cart = re.match(r'^/api/cart/item/(\d+)$', path)
            if m_cart:
                cart_item_id = int(m_cart.group(1))
                cur.execute("SELECT cart_id FROM cart_items WHERE cart_item_id = ?", (cart_item_id,))
                item_row = cur.fetchone()
                cur.execute("DELETE FROM cart_items WHERE cart_item_id = ?", (cart_item_id,))
                
                if item_row:
                    cart_id = item_row['cart_id']
                    cur.execute("SELECT COUNT(*) AS cnt FROM cart_items WHERE cart_id = ?", (cart_id,))
                    count_row = cur.fetchone()
                    if count_row['cnt'] == 0:
                        cur.execute("DELETE FROM carts WHERE cart_id = ?", (cart_id,))

                conn.commit()
                self.send_json_response({"message": "ลบสำเร็จ", "success": True})
                return

            m_cat_del = re.match(r'^/api/categories/(\d+)$', path)
            if m_cat_del:
                if not self.is_current_user_admin(conn):
                    self.send_error_response("เฉพาะ Admin เท่านั้น", status=403)
                    return
                cat_id = int(m_cat_del.group(1))
                cur.execute("DELETE FROM categories WHERE category_id = ?", (cat_id,))
                conn.commit()
                self.send_json_response({"message": "ลบหมวดหมู่สำเร็จ", "success": True})
                return

            m_eb_delete = re.match(r'^/api/ebooks/(\d+)$', path)
            if m_eb_delete:
                if not self.is_current_user_admin(conn):
                    self.send_error_response("เฉพาะ Admin เท่านั้น", status=403)
                    return
                ebook_id = int(m_eb_delete.group(1))
                cur.execute("DELETE FROM ebooks WHERE ebook_id = ?", (ebook_id,))
                conn.commit()
                self.send_json_response({"message": "ลบหนังสือสำเร็จ", "success": True})
                return

            self.send_error_response(f"Endpoint not found: {path}", status=404)

        except Exception as e:
            self.send_error_response(str(e), status=400)
        finally:
            conn.close()

def run_server():
    init_db()
    print("=" * 70)
    print("PhraDhamma E-Book Hub Server Running: http://localhost:8000")
    print("Database: ebookstore.db (3NF Schema + PDPA + Warning Flag + Clean CSV)")
    print("=" * 70)
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), AppRequestHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer shutting down gracefully...")
            httpd.server_close()

if __name__ == '__main__':
    run_server()