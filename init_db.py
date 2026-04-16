import sqlite3


conn = sqlite3.connect("database.db")
c = conn.cursor()

# c.execute("""
# CREATE TABLE IF NOT EXISTS users(
# id INTEGER PRIMARY KEY AUTOINCREMENT,
# fullname TEXT,
# email TEXT UNIQUE,
# password TEXT,
# role TEXT,
# points INTEGER DEFAULT 0
# )
# """)

# c.execute("""
# CREATE TABLE IF NOT EXISTS problems(
# id INTEGER PRIMARY KEY AUTOINCREMENT,
# title TEXT,
# description TEXT,
# level INTEGER
# )
# """)

# c.execute("""
# CREATE TABLE IF NOT EXISTS testcases(
# id INTEGER PRIMARY KEY AUTOINCREMENT,
# problem_id INTEGER,
# input TEXT,
# expected_output TEXT
# )
# """)

# c.execute("""
# CREATE TABLE IF NOT EXISTS submissions(
# id INTEGER PRIMARY KEY AUTOINCREMENT,
# user TEXT,
# problem_id INTEGER,
# code TEXT,
# result TEXT
# )
# """)

#c.execute("""insert into users(fullname,email,password,role) values('Admin','admin@admin.com','admin123','admin')""")
#c.execute("ALTER TABLE problems ADD COLUMN teacher_id INTEGER")
# c.execute("update problems set teacher_id=2")
c.execute("update users set fullname='ivan', email='ivan@gmail.com' where id=2")
conn.commit()
conn.close()

