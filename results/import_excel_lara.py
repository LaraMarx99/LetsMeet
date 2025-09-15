"""
Excel -> Postgres Import (Let's Meet)
- Ziel: nutzer, geschlecht, interessiert_an, hobby, nutzer_hobby, nutzer_hobby_praeferenz
- Excel-Spalten:
  1) "Nachname, Vorname" (Beispiel zeigt Nachname zuerst; Code kann beides)
  2) "Straße Nr, PLZ, Ort"
  3) "Telefon" (ggf. mehrere, durch Komma getrennt) -> wir nehmen die erste Nummer
  4) "Hobby1 %Prio1%; ... Hobby5 %Prio5%" -> parse; Prio int(0-100)
  5) "E-Mail"
  6) "Geschlecht" (m/w/nicht binär)
  7) "Interessiert an" (m/w/nicht binär, mehrere möglich)
  8) "Geburtsdatum" (z. B. 13.05.1983)
"""

from __future__ import annotations

import re
import pandas as pd
from dateutil import parser as dtparse
import psycopg
from psycopg.rows import dict_row

# -----------------------------
# Konfig
# -----------------------------
EXCEL_PATH = "Lets Meet DB Dump.xlsx"   # anpassen
SHEET_NAME = 0                           # 0=erste Tabelle oder explizit Name
PG_DSN = "host=localhost port=5432 dbname=lf8_lets_meet_db user=user password=secret"

# -----------------------------
# Helpers (kurz & robust)
# -----------------------------
def norm_str(s: str | None) -> str | None:
    return s.strip() if isinstance(s, str) else None

def norm_email(s: str | None) -> str | None:
    return s.strip().lower() if isinstance(s, str) else None

def parse_name(raw: str | None) -> tuple[str | None, str | None]:
    # erwartet "Nachname, Vorname" (Beispiel Readme), toleriert "Vorname, Nachname"
    raw = norm_str(raw) or ""
    parts = [p.strip() for p in raw.split(",")]
    if len(parts) == 2:
        left, right = parts[0], parts[1]
        # Heuristik: wenn rechts nur 1 Wort -> wahrscheinlich Vorname rechts (Nachname, Vorname)
        # Wir geben (vorname, nachname) zurück
        if " " not in right:
            return right, left
        # sonst unsicher -> trotzdem (right als Vorname, left als Nachname)
        return right, left
    # kein Komma -> best effort
    toks = raw.split()
    if len(toks) >= 2:
        return toks[0], " ".join(toks[1:])
    return raw, None

def parse_address(raw: str | None) -> tuple[str | None, str | None, str | None, str | None]:
    # "Straße Nr, PLZ, Ort"
    raw = norm_str(raw) or ""
    parts = [p.strip() for p in raw.split(",")]
    street_nr, plz, ort = (parts + [None, None, None])[:3]
    # Straße/Hausnr trennen
    street, hausnr = None, None
    if street_nr:
        # Hausnummer = letztes "Token" mit Ziffern (inkl. Zusätze wie 12a)
        m = re.search(r"\s(\d+\w*)\s*$", street_nr)
        if m:
            hausnr = m.group(1)
            street = street_nr[: m.start()].strip()
        else:
            street = street_nr
    return street, hausnr, plz, ort

def parse_phone(raw: str | None) -> str | None:
    """
    - nimmt die erste Telefonnummer (falls mehrere durch Komma getrennt)
    - entfernt Klammern, Leerzeichen, Bindestriche
    - erlaubt nur Ziffern und ein optionales '+' am Anfang
    """
    if not raw:
        return None
    # Erste Nummer, falls mehrere
    phone = raw.split(",")[0].strip()
    # Alles außer Ziffern und '+' löschen
    phone = re.sub(r"[^0-9+]", "", phone)
    # Falls leer nach Bereinigung → None
    return phone if phone else None


def parse_date(raw: str | None):
    # dtparse mit dayfirst=True für "13.05.1983"
    raw = norm_str(raw)
    if not raw:
        return None
    try:
        return dtparse.parse(raw, dayfirst=True).date()
    except Exception:
        return None

def parse_hobbies(raw: str | None) -> list[tuple[str, int | None]]:
    # "Hobby %Prio%; Hobby2 %88%; ..." -> [(hobby, prio), ...]
    raw = norm_str(raw) or ""
    items = [x.strip() for x in raw.split(";") if x.strip()]
    out = []
    for it in items:
        # finde %NN% am Ende / irgendwo
        m = re.search(r"%(?P<prio>-?\d+)%", it)
        prio = int(m.group("prio")) if m else None
        # hobbyname = ohne %…%
        hobby = re.sub(r"%\s*-?\d+\s*%", "", it).strip(" ;")
        if hobby:
            out.append((hobby, prio))
    return out

# Komplexere Parsing-Variante für "Interessiert an", die aber für den Datensatz in der Exceltabelle nicht benötigt wird. 
# Für theorethische Erweiterbarkeit um "nicht binär" etc.
def parse_interested_in(raw: str | None) -> list[str]:
    """
    Erwartete Excel-Werte:
      - 'm'  -> männlich
      - 'w'  -> weiblich
      - 'm,w' (oder 'w,m') -> männlich + weiblich
      - 'mw'  (ohne Trennzeichen) -> männlich + weiblich
    Erweiterbar um 'nb'/'nicht binär', falls später nötig.
    Gibt kanonische Labels zurück: 'm', 'w', 'nicht binär'
    """
    if not raw:
        return []

    s = str(raw).strip().lower()

    # Sonderfall: 'mw' / 'wm' ohne Separator
    if s in {"mw", "wm"}:
        return ["m", "w"]

    # sonst an üblichen Separatoren trennen
    parts = re.split(r"[,/;|&\s]+", s)
    out = []
    for p in parts:
        if not p:
            continue
        if p in {"m", "männl", "männlich"}:
            out.append("m")
        elif p in {"w", "weibl", "weiblich"}:
            out.append("w")
        elif p in {"nb", "nichtbinär", "nicht-binär", "nicht binär", "divers", "nonbinary", "non-binary"}:
            out.append("nicht binär")
        else:
            # falls mal 'männlich,weiblich' ausgeschrieben in einer Zelle steht:
            if "männlich" in p:
                out.append("m")
            if "weiblich" in p:
                out.append("w")
            if "nicht" in p and "binär" in p:
                out.append("nicht binär")

    # Duplikate entfernen, Reihenfolge behalten
    seen, uniq = set(), []
    for x in out:
        if x not in seen:
            seen.add(x)
            uniq.append(x)
    return uniq

def parse_interested_in_simple(raw: str | None) -> list[str]:
    if not raw:
        return []
    s = str(raw).strip().lower()
    if s in {"mw", "wm"}:
        return ["m", "w"]
    if s == "m":
        return ["m"]
    if s == "w":
        return ["w"]
    if s == "m,w" or s == "w,m":
        return ["m", "w"]
    return []  # alles andere ignorieren

def upsert_geschlecht(conn, label: str) -> int:
    # label ∈ {'m', 'w', 'nb'}  (klein)
    # in Tabelle als Klartext speichern:
    mapping = {"m": "männlich", "w": "weiblich", "nb": "nicht binär"}
    val = mapping.get(label, label)  # falls schon Klartext, unverändert
    sql_ins = """
        INSERT INTO geschlecht (geschlechtsidentitaet)
        VALUES (%s)
        ON CONFLICT (geschlechtsidentitaet) DO NOTHING
    """
    with conn.cursor() as cur:
        cur.execute(sql_ins, (val,))
        cur.execute("SELECT id FROM geschlecht WHERE geschlechtsidentitaet=%s", (val,))
        return cur.fetchone()["id"]
    
def upsert_hobby(conn, hobby_name: str) -> int:
    sql_ins = """
        INSERT INTO hobby (hobby_name)
        VALUES (%s)
        ON CONFLICT (hobby_name) DO NOTHING
    """
    with conn.cursor() as cur:
        cur.execute(sql_ins, (hobby_name,))
        cur.execute("SELECT id FROM hobby WHERE hobby_name=%s", (hobby_name,))
        return cur.fetchone()["id"]

def insert_interessiert_an(conn, nutzer_id: int, geschlecht_id: int):
    sql = """
        INSERT INTO interessiert_an (nutzer_id, interesse)
        VALUES (%s, %s)
        ON CONFLICT DO NOTHING
    """
    with conn.cursor() as cur:
        cur.execute(sql, (nutzer_id, geschlecht_id))


def insert_nutzer_hobby_praeferenz(conn, nutzer_id: int, hobby_id: int, prio: int | None):
    # praeferenz in [-100, 100]; Excel liefert 0..100 -> wir übernehmen 0..100
    if prio is None:
        return
    sql = """
        INSERT INTO nutzer_hobby_praeferenz (nutzer_id, hobby_id, praeferenz)
        VALUES (%s, %s, %s)
        ON CONFLICT (nutzer_id, hobby_id) DO UPDATE SET praeferenz = EXCLUDED.praeferenz
    """
    with conn.cursor() as cur:
        cur.execute(sql, (nutzer_id, hobby_id, int(prio)))

def upsert_nutzer(conn, vorname, nachname, geburtsdatum, telefonnummer,
                  email, strasse, hausnummer, plz, ort, geschlecht_label: str | None) -> int:
    # Nutzer einfügen (oder ignorieren, falls E-Mail schon existiert), dann ID holen
    sql_ins = """
        INSERT INTO nutzer
            (nachname, vorname, geburtsdatum, telefonnummer, email,
             strasse, hausnummer, plz, ort, geschlecht_id)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,
                COALESCE((SELECT id FROM geschlecht WHERE geschlechtsidentitaet=%s), NULL))
        ON CONFLICT DO NOTHING
    """
    with conn.cursor() as cur:
        cur.execute(sql_ins, (
            nachname, vorname, geburtsdatum, telefonnummer, email,
            strasse, hausnummer, plz, ort, geschlecht_label
        ))
        # ID per E-Mail abrufen (Unique-Index existiert auf lower(trim(email)) -> wir matchen case-insensitiv)
        cur.execute("SELECT id FROM nutzer WHERE lower(trim(email))=lower(trim(%s))", (email,))
        row = cur.fetchone()
        return row["id"]

# -----------------------------
# Main-Import
# -----------------------------
def main():
    # Excel laden
    df = pd.read_excel(EXCEL_PATH, sheet_name=SHEET_NAME, dtype=str)

    # Spaltennamen heuristisch; zur Not: df.columns anschauen
    # Erwartete Spalten (Bezeichner frei, Reihenfolge lt. Readme):
    # 0: Name, 1: Adresse, 2: Telefon, 3: Hobbys, 4: E-Mail, 5: Geschlecht, 6: Interessiert an, 7: Geburtsdatum
    # Wir greifen über Positionsindex zu, um tolerant ggü. Bezeichnungen zu sein.
    print("Zeilen in Excel:", len(df))

    with psycopg.connect(PG_DSN, row_factory=dict_row) as conn:
        conn.execute("BEGIN")
        try:
            for _, row in df.iterrows():
                raw_name   = row.iloc[0] if len(row) > 0 else None
                raw_addr   = row.iloc[1] if len(row) > 1 else None
                raw_phone  = row.iloc[2] if len(row) > 2 else None
                raw_hobby  = row.iloc[3] if len(row) > 3 else None
                raw_email  = row.iloc[4] if len(row) > 4 else None
                raw_gender = row.iloc[5] if len(row) > 5 else None
                raw_intan  = row.iloc[6] if len(row) > 6 else None
                raw_birth  = row.iloc[7] if len(row) > 7 else None

                email = norm_email(raw_email)
                if not email:
                    # ohne E-Mail -> kein eindeutiger Schlüssel -> überspringen
                    continue

                vorname, nachname = parse_name(raw_name)
                strasse, hausnr, plz, ort = parse_address(raw_addr)
                telefon = parse_phone(raw_phone)
                gebdat = parse_date(raw_birth)

                # Geschlecht (für nutzer.geschlecht_id + interessiert_an)
                gender_label = norm_str(raw_gender)
                gender_label = gender_label.lower() if gender_label else None
                if gender_label:
                    geschlecht_id = upsert_geschlecht(conn, gender_label)
                else:
                    geschlecht_id = None  # bleibt NULL in nutzer

                # Nutzer upsert (ON CONFLICT DO NOTHING -> dann via E-Mail ID holen)
                nutzer_id = upsert_nutzer(
                    conn,
                    vorname=vorname, nachname=nachname, geburtsdatum=gebdat,
                    telefonnummer=telefon, email=email, strasse=strasse,
                    hausnummer=hausnr, plz=plz, ort=ort,
                    geschlecht_label=gender_label
                )

                # --- interessiert_an pro Nutzer neu aufbauen ---
                labels = parse_interested_in_simple(raw_intan)  # z. B. ['m', 'w'] für "mw" oder "m,w"

                with conn.cursor() as cur:
                    cur.execute("DELETE FROM interessiert_an WHERE nutzer_id = %s", (nutzer_id,))

                for lab in labels:
                    gi_id = upsert_geschlecht(conn, lab)
                    insert_interessiert_an(conn, nutzer_id, gi_id)

                # Hobbys + Präferenzen
                for hobby_name, prio in parse_hobbies(raw_hobby):
                    h_id = upsert_hobby(conn, hobby_name)
                    # Excel liefert nur positive Präferenzen (0..100) -> in nutzer_hobby_praeferenz aber auch negativ möglich
                    insert_nutzer_hobby_praeferenz(conn, nutzer_id, h_id, prio)

            conn.execute("COMMIT")
        except Exception as ex:
            conn.execute("ROLLBACK")
            raise

    print("Import fertig.")

if __name__ == "__main__":
    main()
