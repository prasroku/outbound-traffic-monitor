import sqlite3
import sys
from pathlib import Path

import matplotlib.pyplot as plt

sys.path.append(str(Path(__file__).resolve().parent.parent))

from paths import db_file  # noqa: E402


def get_country_counts():
    """Fetch connection counts grouped by country."""
    if not db_file().exists():
        print(f"[!] Database not found at {db_file()}")
        return []

    conn = sqlite3.connect(db_file())
    cur = conn.cursor()

    # Ensure table exists
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='traffic_log';")
    if not cur.fetchone():
        print("[!] Table 'traffic_log' not found in database.")
        conn.close()
        return []

    cur.execute("SELECT country, COUNT(*) FROM traffic_log GROUP BY country")
    rows = cur.fetchall()
    conn.close()

    return rows


def plot_pie_chart(rows):
    """Plot pie chart of country distribution."""
    countries = [r[0] or "??" for r in rows]
    counts = [r[1] for r in rows]

    plt.figure(figsize=(8, 8))
    plt.pie(counts, labels=countries, autopct="%1.1f%%", startangle=140)
    plt.title("Traffic Distribution by Country (Pie Chart)")
    plt.show()


def plot_bar_chart(rows):
    """Plot bar chart of absolute counts."""
    countries = [r[0] or "??" for r in rows]
    counts = [r[1] for r in rows]

    plt.figure(figsize=(10, 6))
    plt.bar(countries, counts)
    plt.xlabel("Country")
    plt.ylabel("Number of Connections")
    plt.title("Traffic Distribution by Country (Bar Chart)")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    if rows := get_country_counts():
        plot_pie_chart(rows)
        plot_bar_chart(rows)
    else:
        print("[!] No data available to plot.")
