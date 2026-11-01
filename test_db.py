import sqlite3, os

db_path = os.path.abspath('test.db')
conn = sqlite3.connect(db_path)
cur = conn.cursor()
cur.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT, email TEXT)')
cur.executemany('INSERT INTO users (name, email) VALUES (?, ?)', [
    ('Alice', 'alice@example.com'),
    ('Bob', 'bob@example.com')
])
conn.commit()
# Fetch and print rows
cur.execute('SELECT * FROM users')
rows = cur.fetchall()
print('Inserted rows:')
for row in rows:
    print(row)
conn.close()
