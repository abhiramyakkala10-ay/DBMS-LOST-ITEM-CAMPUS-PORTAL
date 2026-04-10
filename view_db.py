import sqlite3, os

db_path = os.path.join('instance', 'campus_lf.db')
conn = sqlite3.connect(db_path)
cur = conn.cursor()

cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = [r[0] for r in cur.fetchall()]

output = []

for t in tables:
    cur.execute(f"PRAGMA table_info({t})")
    cols = [r[1] for r in cur.fetchall()]
    cur.execute(f"SELECT * FROM {t}")
    rows = cur.fetchall()

    output.append(f"\n{'=' * 80}")
    output.append(f" TABLE: {t.upper()} ({len(rows)} rows)")
    output.append(f"{'=' * 80}")

    if not rows:
        output.append("  (empty)")
        continue

    widths = [len(c) for c in cols]
    for row in rows:
        for i, v in enumerate(row):
            s = str(v) if v is not None else "NULL"
            if len(s) > 45:
                s = s[:42] + "..."
            widths[i] = max(widths[i], len(s))

    header = " | ".join(c.ljust(widths[i]) for i, c in enumerate(cols))
    output.append(f"  {header}")
    output.append(f"  {'-+-'.join('-' * w for w in widths)}")

    for row in rows:
        vals = []
        for i, v in enumerate(row):
            s = str(v) if v is not None else "NULL"
            if len(s) > 45:
                s = s[:42] + "..."
            vals.append(s.ljust(widths[i]))
        output.append(f"  {' | '.join(vals)}")

conn.close()

result = "\n".join(output)
with open("db_output.txt", "w", encoding="utf-8") as f:
    f.write(result)
print(result)
