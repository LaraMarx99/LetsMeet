import re
from pathlib import Path
from typing import Optional, Tuple, List

import pandas as pd
import psycopg2
from psycopg2 import sql, errors


# ---- Helfer: Parsen & Normalisieren ----------------------------------------
def split_name(full_name: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    """Erwartet 'Nachname, Vorname'. Gibt (Nachname, Vorname) zurück."""
    if not isinstance(full_name, str):
        return None, None
    name_parts = [part.strip() for part in full_name.split(",")]
    if len(name_parts) >= 2:
        return name_parts[0] or None, name_parts[1] or None
    return full_name.strip() or None, None  # Fallback

def split_address(address: Optional[str]) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
    """Erwartet 'Straße Hausnummer, PLZ Ort'. Gibt (Straße, Hausnummer, PLZ, Ort) zurück."""
    if not isinstance(address, str):
        return None, None, None, None
    address_parts = [part.strip() for part in address.split(",")]
    street_part = address_parts[0] if address_parts else ""
    city_part = address_parts[1] if len(address_parts) > 1 else ""

    street_name, house_number = None, None
    street_match = re.match(r"^(.*\S)\s+(\S+)$", street_part)  # z.B. 'Musterstraße 12a'
    if street_match:
        street_name, house_number = street_match.group(1), street_match.group(2)
    elif street_part:
        street_name = street_part

    postal_code, city_name = None, None
    city_match = re.match(r"^\s*(\d{4,5})\s+(.+)$", city_part)
    if city_match:
        postal_code, city_name = city_match.group(1), city_match.group(2)
    elif city_part:
        city_name = city_part

    def normalize_none(value): 
        return value if (value and str(value).strip()) else None
    return normalize_none(street_name), normalize_none(house_number), normalize_none(postal_code), normalize_none(city_name)

def normalize_gender(raw_gender: Optional[str]) -> Optional[str]:
    """m/w/nb -> 'männlich'/'weiblich'/'nonbinary'"""
    if raw_gender is None:
        return None
    gender_string = str(raw_gender).strip().lower()
    if gender_string in {"m", "männl.", "männlich", "mannlich"}:
        return "männlich"
    if gender_string in {"w", "weibl.", "weiblich"}:
        return "weiblich"
    if gender_string in {"nb", "nonbinary", "non-binary"}:
        return "nonbinary"
    if gender_string in {"", "none", "null"}:
        return None
    return gender_string  # lässt bereits normalisierte Werte durch

def normalize_interest(raw_interest: Optional[str]) -> List[str]:
    """m/w/nb/mw -> ['männlich'] oder ['weiblich'] oder ['nonbinary'] oder ['männlich', 'weiblich']"""
    if raw_interest is None:
        return []
    interest_string = str(raw_interest).strip().lower()
    if interest_string in {"m", "männl.", "männlich", "mannlich"}:
        return ["männlich"]
    if interest_string in {"w", "weibl.", "weiblich"}:
        return ["weiblich"]
    if interest_string in {"nb", "nonbinary", "non-binary"}:
        return ["nonbinary"]
    if interest_string in {"mw", "männlich/weiblich", "männlich weiblich"}:
        return ["männlich", "weiblich"]
    if interest_string in {"", "none", "null"}:
        return []
    return [interest_string]  # Fallback


# ---- Hauptprogramm ----------------------------------------------------------
def main():
    # Hartkodierte Werte
    EXCEL_FILE = "Lets Meet DB Dump.xlsx"
    PG_URL = "postgresql://user:secret@localhost:5432/lf8_lets_meet_db"  # ANPASSEN!

    # Excel einlesen mit den korrekten Spaltennamen
    df = pd.read_excel(EXCEL_FILE)
    print(f"Geladene Spalten: {list(df.columns)} ({len(df)} Zeilen)")
    
    # 2) Vorverarbeitung
    df = df.map(lambda cell_value: None if (isinstance(cell_value, str) and cell_value.strip() == "") else cell_value)
    if "E-Mail" in df.columns:
        df["E-Mail"] = df["E-Mail"].apply(lambda email_value: email_value.lower().strip() if isinstance(email_value, str) else email_value)
    if "Geburtsdatum" in df.columns:
        df["Geburtsdatum"] = pd.to_datetime(df["Geburtsdatum"], errors="coerce").dt.date

    # Name & Adresse splitten
    df["Nachname"], df["Vorname"] = zip(*df.get("Nachname, Vorname", pd.Series([None]*len(df))).map(split_name))
    address_columns = list(zip(*df.get("Straße Nr, PLZ Ort", pd.Series([None]*len(df))).map(split_address)))
    if address_columns:
        df["Straße"], df["Hausnummer"], df["PLZ"], df["Ort"] = [list(column) for column in address_columns]
    else:
        df["Straße"] = df["Hausnummer"] = df["PLZ"] = df["Ort"] = None

    # Geschlecht normalisieren
    df["Geschlecht_normalisiert"] = df.get("Geschlecht (m/w/nonbinary)").apply(normalize_gender)
    df["Interessiert_an_liste"] = df.get("Interessiert an").apply(normalize_interest)

    inserted_users = 0
    inserted_interests = 0
    skipped_rows = 0
    duplicate_emails = 0

    with psycopg2.connect(PG_URL) as connection:
        with connection.cursor() as cursor:
            for row_index, row in df.iterrows():
                email = row.get("E-Mail")
                if not email:
                    skipped_rows += 1
                    continue

                user_gender = row.get("Geschlecht_normalisiert")
                interested_in_list = row.get("Interessiert_an_liste") or []
                
                if user_gender not in {"männlich", "weiblich", "nonbinary"}:
                    skipped_rows += 1
                    continue
                
                if not interested_in_list:
                    skipped_rows += 1
                    continue

                # --- Geschlecht-Einträge sicherstellen (nur INSERT; Unique-Verletzung wird abgefangen)
                all_genders = {user_gender} | set(interested_in_list)
                for gender_value in all_genders:
                    try:
                        cursor.execute(
                            'INSERT INTO "Geschlecht" ("Geschlechtsidentität") VALUES (%s);',
                            (gender_value,),
                        )
                    except errors.UniqueViolation:
                        connection.rollback()
                
                # IDs besorgen
                cursor.execute('SELECT "ID" FROM "Geschlecht" WHERE "Geschlechtsidentität" = %s;', (user_gender,))
                user_gender_id = cursor.fetchone()[0]

                # --- Nutzer einfügen (nur INSERT). Bei doppelter E-Mail → Unique-Fehler -> Zeile überspringen.
                try:
                    cursor.execute(
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
                            user_gender_id,
                        ),
                    )
                    nutzer_id = cursor.fetchone()[0]
                    inserted_users += 1
                except errors.UniqueViolation:
                    connection.rollback()
                    duplicate_emails += 1
                    continue

                # --- interessiert_an einfügen für jedes Interesse
                for interest_gender in interested_in_list:
                    cursor.execute('SELECT "ID" FROM "Geschlecht" WHERE "Geschlechtsidentität" = %s;', (interest_gender,))
                    interest_gender_id = cursor.fetchone()[0]
                    
                    try:
                        cursor.execute(
                            'INSERT INTO "interessiert_an" ("Nutzer_ID","Interesse") VALUES (%s,%s);',
                            (nutzer_id, interest_gender_id),
                        )
                        inserted_interests += 1
                    except errors.UniqueViolation:
                        connection.rollback()

    print("Fertig.")
    print(f"Nutzer eingefügt: {inserted_users}")
    print(f"'interessiert_an' eingefügt: {inserted_interests}")
    print(f"Übersprungen (fehlende/ungültige Pflichtwerte): {skipped_rows}")
    print(f"Übersprungen (doppelte E-Mail in DB): {duplicate_emails}")


if __name__ == "__main__":
    main()