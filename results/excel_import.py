import argparse
import re
from pathlib import Path
from typing import Optional, Tuple

import pandas as pd
import psycopg2
from psycopg2 import sql, errors


# ---- Helfer: Parsen & Normalisieren ----------------------------------------
def split_name(name: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    """Erwartet 'Nachname, Vorname'. Gibt (Nachname, Vorname) zurück."""
    if not isinstance(name, str):
        return None, None
    parts = [p.strip() for p in name.split(",")]
    if len(parts) >= 2:
        return parts[0] or None, parts[1] or None
    return name.strip() or None, None  # Fallback

def split_address(addr: Optional[str]) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
    """Erwartet 'Straße Hausnummer, PLZ Ort'. Gibt (Straße, Hausnummer, PLZ, Ort) zurück."""
    if not isinstance(addr, str):
        return None, None, None, None
    parts = [p.strip() for p in addr.split(",")]
    street_part = parts[0] if parts else ""
    city_part = parts[1] if len(parts) > 1 else ""

    street, hausnr = None, None
    m = re.match(r"^(.*\S)\s+(\S+)$", street_part)  # z.B. 'Musterstraße 12a'
    if m:
        street, hausnr = m.group(1), m.group(2)
    elif street_part:
        street = street_part

    plz, ort = None, None
    m2 = re.match(r"^\s*(\d{4,5})\s+(.+)$", city_part)
    if m2:
        plz, ort = m2.group(1), m2.group(2)
    elif city_part:
        ort = city_part

    def nn(x): return x if (x and str(x).strip()) else None
    return nn(street), nn(hausnr), nn(plz), nn(ort)

def normalize_gender(raw: Optional[str]) -> Optional[str]:
    """m/w (auch Varianten) -> 'männlich'/'weiblich'"""
    if raw is None:
        return None
    s = str(raw).strip().lower()
    if s in {"m", "männl.", "männlich", "mannlich"}:
        return "männlich"
    if s in {"w", "weibl.", "weiblich"}:
        return "weiblich"
    if s in {"", "none", "null"}:
        return None
    return s  # lässt bereits 'männlich'/'weiblich' durch


# ---- Hauptprogramm ----------------------------------------------------------
def main():
    #ap = argparse.ArgumentParser(description="Excel → Postgres (nur INSERT INTO …)")
    #ap.add_argument("--excel", required=True, help="Pfad zur Excel-Datei")
    #ap.add_argument("--sheet", default=0, help="Sheet-Name oder -Index (Standard 0)")
    #ap.add_argument("--pg-url", required=True, help="postgresql://user:pass@host:5432/dbname")
    #args = ap.parse_args()

    # 1) Excel lesen — erwartete Spalten:
    #    Name, Adresse, Geburtsdatum, Telefon, E-Mail, Geschlecht, Interessiert an
    
    df = pd.read_excel("Lets Meet DB Dump.xlsx")
    print(f"Geladene Spalten: {list(df.columns)}"
          f" ({len(df)} Zeilen)")
    # 2) Vorverarbeitung
    df = df.applymap(lambda x: None if (isinstance(x, str) and x.strip() == "") else x)
    if "E-Mail" in df.columns:
        df["E-Mail"] = df["E-Mail"].apply(lambda s: s.lower().strip() if isinstance(s, str) else s)
    if "Geburtsdatum" in df.columns:
        df["Geburtsdatum"] = pd.to_datetime(df["Geburtsdatum"], errors="coerce").dt.date

    # Name & Adresse splitten
    df["Nachname"], df["Vorname"] = zip(*df.get("Name", pd.Series([None]*len(df))).map(split_name))
    cols = list(zip(*df.get("Adresse", pd.Series([None]*len(df))).map(split_address)))
    if cols:
        df["Straße"], df["Hausnummer"], df["PLZ"], df["Ort"] = [list(c) for c in cols]
    else:
        df["Straße"] = df["Hausnummer"] = df["PLZ"] = df["Ort"] = None

    # Geschlecht normalisieren
    df["Geschlecht"] = df.get("Geschlecht").apply(normalize_gender)
    df["Interessiert an"] = df.get("Interessiert an").apply(normalize_gender)

    inserted_users = 0
    inserted_interests = 0
    skipped_rows = 0
    duplicate_emails = 0

    with psycopg2.connect(args.pg_url) as conn:
        with conn.cursor() as cur:
            for _, row in df.iterrows():
                email = row.get("E-Mail")
                if not email:
                    skipped_rows += 1
                    continue

                g = row.get("Geschlecht")
                ia = row.get("Interessiert an")
                if g not in {"männlich", "weiblich"} or ia not in {"männlich", "weiblich"}:
                    skipped_rows += 1
                    continue

                # --- Geschlecht-Einträge sicherstellen (nur INSERT; Unique-Verletzung wird abgefangen)
                for val in (g, ia):
                    try:
                        cur.execute(
                            'INSERT INTO "Geschlecht" ("Geschlechtsidentität") VALUES (%s);',
                            (val,),
                        )
                    except errors.UniqueViolation:
                        conn.rollback()  # Rollback nur der fehlgeschlagenen Anweisung
                        conn.autocommit = False  # sicherstellen
                    # ID besorgen
                cur.execute('SELECT "ID" FROM "Geschlecht" WHERE "Geschlechtsidentität" = %s;', (g,))
                geschlecht_id = cur.fetchone()[0]
                cur.execute('SELECT "ID" FROM "Geschlecht" WHERE "Geschlechtsidentität" = %s;', (ia,))
                interesse_id = cur.fetchone()[0]

                # --- Nutzer einfügen (nur INSERT). Bei doppelter E-Mail → Unique-Fehler -> Zeile überspringen.
                try:
                    cur.execute(
                        'INSERT INTO "Nutzer" '
                        '("Nachname","Vorname","Geburtsdatum","Telefonnummer","EMail","Straße","Hausnummer","PLZ","Ort","Geschlecht_id") '
                        'VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) '
                        'RETURNING "ID";',
                        (
                            row.get("Nachname"),
                            row.get("Vorname"),
                            row.get("Geburtsdatum"),
                            row.get("Telefon"),
                            email,
                            row.get("Straße"),
                            row.get("Hausnummer"),
                            row.get("PLZ"),
                            row.get("Ort"),
                            geschlecht_id,
                        ),
                    )
                    nutzer_id = cur.fetchone()[0]
                    inserted_users += 1
                except errors.UniqueViolation:
                    # Nutzer existiert bereits (EMail ist UNIQUE) → diese Excel-Zeile überspringen
                    conn.rollback()
                    conn.autocommit = False
                    duplicate_emails += 1
                    continue

                # --- interessiert_an einfügen (nur INSERT). Doppelte Relation → Unique-Fehler -> überspringen.
                try:
                    cur.execute(
                        'INSERT INTO "interessiert_an" ("Nutzer_ID","Interesse") VALUES (%s,%s);',
                        (nutzer_id, interesse_id),
                    )
                    inserted_interests += 1
                except errors.UniqueViolation:
                    conn.rollback()
                    conn.autocommit = False
                    # Relation existiert schon → ok, weiter
                    continue

    print("Fertig.")
    print(f"Nutzer eingefügt: {inserted_users}")
    print(f"'interessiert_an' eingefügt: {inserted_interests}")
    print(f"Übersprungen (fehlende/ungültige Pflichtwerte): {skipped_rows}")
    print(f"Übersprungen (doppelte E-Mail in DB): {duplicate_emails}")


if __name__ == "__main__":
    main()
