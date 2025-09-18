"""
Mongo -> Postgres Import (Likes & Messages)
-------------------------------------------

- Nutzer-Stammdaten kommen nur aus Excel
- Mongo enthält nur Likes + Nachrichten
- Import klappt nur, wenn Nutzer in Postgres schon existieren
- Wenn Nutzer fehlt -> Datensatz überspringen + loggen
"""

from pymongo import MongoClient
import psycopg
from psycopg.rows import dict_row
from dateutil import parser as dtparse

# -----------------------------
# Verbindungsdaten
# -----------------------------
PG_DSN = "host=localhost port=5432 dbname=lf8_lets_meet_db user=user password=secret"
MONGO_URI = "mongodb://localhost:27017"
MONGO_DB = "LetsMeet"
MONGO_COL = "users"



# -----------------------------
# Hilfsfunktionen
# -----------------------------
def norm_email(value):
    # E-Mail vereinheitlichen: klein + getrimmt
    return value.strip().lower() if value else None

def to_ts(value):
    # Mongo Zeitstring -> datetime (für timestamptz)
    return dtparse.parse(value) if value else None

def load_email_map(conn):
    # Nutzer-Tabelle einmal auslesen: email -> id
    sql = "SELECT id, lower(trim(email)) AS email_norm FROM nutzer"
    return {row["email_norm"]: row["id"] for row in conn.execute(sql)}


# -----------------------------
# Likes importieren
# -----------------------------
def import_likes(conn, users_coll, email2id, stats):
    sql = """
        INSERT INTO likes (liker_id, liked_nutzer_id, zustand, zeitstempel)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT DO NOTHING
    """
    for u in users_coll.find({}, {"_id": 1, "likes": 1}):
        liker_id = email2id.get(norm_email(u["_id"]))
        if not liker_id:
            if u.get("likes"):
                stats["likes_skipped"].append((u["_id"], "liker fehlt"))
            continue

        for like in u.get("likes", []):
            liked_id = email2id.get(norm_email(like.get("liked_email")))
            if not liked_id:
                stats["likes_skipped"].append((like.get("liked_email"), "liked fehlt"))
                continue

            params = (liker_id, liked_id, like.get("status"), to_ts(like.get("timestamp")))
            conn.execute(sql, params)
            stats["likes_inserted"] += 1


# -----------------------------
# Messages importieren
# -----------------------------
def import_messages(conn, users_coll, email2id, stats):
    sql = """
        INSERT INTO messages (receiving_nutzer_id, sending_nutzer_id, content, zeitstempel, conversation_id)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT DO NOTHING
    """
    for u in users_coll.find({}, {"_id": 1, "messages": 1}):
        sender_id = email2id.get(norm_email(u["_id"]))
        if not sender_id:
            if u.get("messages"):
                stats["messages_skipped"].append((u["_id"], "sender fehlt"))
            continue

        for m in u.get("messages", []):
            recv_id = email2id.get(norm_email(m.get("receiver_email")))
            if not recv_id:
                stats["messages_skipped"].append((m.get("receiver_email"), "empfänger fehlt"))
                continue

            params = (recv_id, sender_id, m.get("message"), to_ts(m.get("timestamp")), m.get("conversation_id"))
            conn.execute(sql, params)
            stats["messages_inserted"] += 1


# -----------------------------
# Main
# -----------------------------
def main():
    mongo = MongoClient(MONGO_URI)
    users_coll = mongo[MONGO_DB][MONGO_COL]

    stats = {"likes_inserted": 0, "messages_inserted": 0,
             "likes_skipped": [], "messages_skipped": []}

    with psycopg.connect(PG_DSN, row_factory=dict_row) as conn:

        try:
            email2id = load_email_map(conn)
            import_likes(conn, users_coll, email2id, stats)
            import_messages(conn, users_coll, email2id, stats)
            conn.execute("COMMIT")
        except:
            conn.execute("ROLLBACK")
            raise


    # Ergebnisübersicht
    print("Likes eingefügt:", stats["likes_inserted"])
    print("Messages eingefügt:", stats["messages_inserted"])
    print("Übersprungen Likes:", stats["likes_skipped"])
    print("Übersprungen Messages:", stats["messages_skipped"])


if __name__ == "__main__":
    main()
