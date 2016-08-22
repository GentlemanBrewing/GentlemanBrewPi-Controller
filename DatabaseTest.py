import sqlite3

conn = sqlite3.connect('NewLog.db')
cur = conn.cursor()

try:
    print('db1')
    with conn:
        print('db2')
        conn.execute("INSERT INTO PIDOutput VALUES ('1', '2')")
        print('db3')
except sqlite3.IntegrityError:
    print('db error')