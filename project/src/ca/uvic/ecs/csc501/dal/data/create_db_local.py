import os
import sqlite3

# Ermittelt den exakten Ordnerpfad, in dem dieses Skript liegt
current_dir = os.path.dirname(os.path.abspath(__file__))

# Name der Datenbankdatei
db_name = "pluggedin.db"
db_path = os.path.join(current_dir, db_name)


def create_database():
  print(f"Creating database in the same directory: {db_path}")

  # Verbindung zur Datenbank herstellen (erstellt die Datei automatisch, falls sie nicht existiert)
  conn = sqlite3.connect(db_path)
  cursor = conn.cursor()

  # 1. Tabelle für Operating Hours (Betriebszeiten)
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS operating_hours (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            station_id INTEGER,
            day_of_week TEXT NOT NULL,
            open_time TEXT NOT NULL,
            close_time TEXT NOT NULL
        )
    """)

  # 2. Tabelle für Membership (Start- und Enddatum sind NOT NULL)
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS membership (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            tier_name TEXT NOT NULL,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL
        )
    """)

  # Änderungen speichern und Verbindung schließen
  conn.commit()
  conn.close()
  print(
      "Database was successfully created with operating hours and memberships"
      "!"
  )


if __name__ == "__main__":
  create_database()