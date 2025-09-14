import re
from typing import Optional, Tuple, List

import pandas as pd
import psycopg2


def split_name(full_name: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    if not isinstance(full_name, str):
        return None, None
    name_parts = [part.strip() for part in full_name.split(",")]
    if len(name_parts) >= 2:
        return name_parts[0] or None, name_parts[1] or None
    return full_name.strip() or None, None

def split_address(address: Optional[str]) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
    if not isinstance(address, str):
        return None, None, None, None
    address_parts = [part.strip() for part in address.split(",")]

    street_part = address_parts[0] if address_parts else ""
    postal_code_part = address_parts[1] if len(address_parts) > 1 else ""
    city_part = address_parts[2] if len(address_parts) > 2 else ""

    street_name, house_number = None, None
    street_match = re.match(r"^(.*\S)\s+(\S+)$", street_part)
    if street_match:
        street_name, house_number = street_match.group(1), street_match.group(2)
    elif street_part:
        street_name = street_part

    postal_code = None
    if postal_code_part:
        postal_code_match = re.match(r"^\s*(\d{4,5})\s*$", postal_code_part)
        if postal_code_match:
            postal_code = postal_code_match.group(1)

    city_name = city_part if city_part else None

    def normalize_none(value): 
        return value if (value and str(value).strip()) else None
    return normalize_none(street_name), normalize_none(house_number), normalize_none(postal_code), normalize_none(city_name)

def normalize_gender(raw_gender: Optional[str]) -> Optional[str]:
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
    return gender_string

def normalize_interest(raw_interest: Optional[str]) -> List[str]:
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
    return [interest_string]

def parse_hobbies(hobby_string: Optional[str]) -> List[Tuple[str,int]]:
    if pd.isna(hobby_string) or not hobby_string:
        return []

    hobby_string = str(hobby_string).strip()
    if not hobby_string:
        return []
    
    hobbies = []
    hobby_parts = [part.strip() for part in hobby_string.split(";") if part.strip()]

    for part in hobby_parts:
        match = re.match(r'^(.+?)\s*%(\d+)%$', part.strip())
        if match:
            hobby_name = match.group(1).strip()
            präferenz = int(match.group(2))
            hobbies.append((hobby_name, präferenz))
    return hobbies

def main():
    EXCEL_FILE = "Lets Meet DB Dump.xlsx"
    PG_URL = "postgresql://user:secret@localhost:5432/lf8_lets_meet_db"

    df = pd.read_excel(EXCEL_FILE)
    
    df = df.map(lambda cell_value: None if (isinstance(cell_value, str) and cell_value.strip() == "") else cell_value)
    if "E-Mail" in df.columns:
        df["E-Mail"] = df["E-Mail"].apply(lambda email_value: email_value.lower().strip() if isinstance(email_value, str) else email_value)
    if "Geburtsdatum" in df.columns:
        df["Geburtsdatum"] = pd.to_datetime(df["Geburtsdatum"], format="%d.%m.%Y", errors="coerce").dt.date

    df["Nachname"], df["Vorname"] = zip(*df.get("Nachname, Vorname", pd.Series([None]*len(df))).map(split_name))
    address_columns = list(zip(*df.get("Straße Nr, PLZ Ort", pd.Series([None]*len(df))).map(split_address)))
    if address_columns:
        df["Straße"], df["Hausnummer"], df["PLZ"], df["Ort"] = [list(column) for column in address_columns]
    else:
        df["Straße"] = df["Hausnummer"] = df["PLZ"] = df["Ort"] = None

    df["Geschlecht_normalisiert"] = df.get("Geschlecht (m/w/nonbinary)").apply(normalize_gender)
    df["Interessiert_an_liste"] = df.get("Interessiert an").apply(normalize_interest)

    with psycopg2.connect(PG_URL) as connection:
        with connection.cursor() as cursor:
            for row_index, row in df.iterrows():
                
                all_genders = {row.get("Geschlecht_normalisiert")} | set(row.get("Interessiert_an_liste") or [])
                for gender_value in all_genders:
                    if gender_value:
                        cursor.execute(
                            'INSERT INTO "geschlecht" ("geschlechtsidentität") VALUES (%s) ON CONFLICT (geschlechtsidentität) DO NOTHING;',
                            (gender_value,),
                        )
                
                if row.get("Geschlecht_normalisiert"):
                    cursor.execute('SELECT "id" FROM "geschlecht" WHERE "geschlechtsidentität" = %s;', (row.get("Geschlecht_normalisiert"),))
                    user_gender_result = cursor.fetchone()
                    user_gender_id = user_gender_result[0] if user_gender_result else None
                else:
                    user_gender_id = None

                cursor.execute(
                    'INSERT INTO "nutzer" '
                    '("nachname","vorname","geburtsdatum","telefonnummer","email","straße","hausnummer","plz","ort","geschlecht_id") '
                    'VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) '
                    'ON CONFLICT (email) DO UPDATE SET '
                    '"nachname" = COALESCE(EXCLUDED.nachname, nutzer.nachname), '
                    '"vorname" = COALESCE(EXCLUDED.vorname, nutzer.vorname),'
                    '"geburtsdatum" = COALESCE(EXCLUDED.geburtsdatum, nutzer.geburtsdatum),'
                    '"telefonnummer" = COALESCE(EXCLUDED.telefonnummer, nutzer.telefonnummer),'
                    '"straße" = COALESCE(EXCLUDED.straße, nutzer.straße),'
                    '"hausnummer" = COALESCE(EXCLUDED.hausnummer, nutzer.hausnummer),'
                    '"plz" = COALESCE(EXCLUDED.plz, nutzer.plz),'
                    '"ort" = COALESCE(EXCLUDED.ort, nutzer.ort),'
                    '"geschlecht_id" = COALESCE(EXCLUDED.geschlecht_id, nutzer.geschlecht_id) '
                    'RETURNING "id";',
                    (
                        row.get("Nachname"),
                        row.get("Vorname"),
                        row.get("Geburtsdatum"),
                        row.get("Telefon"),
                        row.get("E-Mail"),
                        row.get("Straße"),
                        row.get("Hausnummer"),
                        row.get("PLZ"),
                        row.get("Ort"),
                        user_gender_id,
                    ),
                )
                result = cursor.fetchone()
                if result is None:
                    cursor.execute('SELECT "id" FROM "nutzer" WHERE "email" = %s;', (row.get("E-Mail"),))
                    result = cursor.fetchone()

                if result:
                    nutzer_id = result[0]

                for interest_gender in (row.get("Interessiert_an_liste") or []):
                    if interest_gender:
                        cursor.execute('SELECT "id" FROM "geschlecht" WHERE "geschlechtsidentität" = %s;', (interest_gender,))
                        interest_result = cursor.fetchone()
                        if interest_result:
                            interest_gender_id = interest_result[0]
                            cursor.execute(
                                'INSERT INTO "interessiert_an" ("nutzer_id","interesse") VALUES (%s,%s) ON CONFLICT DO NOTHING;',
                                (nutzer_id, interest_gender_id),
                            )

                hobbies = parse_hobbies(row.get("Hobby1 %Prio1%; Hobby2 %Prio2%; Hobby3 %Prio3%; Hobby4 %Prio4%; Hobby5 %Prio5%;"))

                for hobby_name, präferenz in hobbies:
                    cursor.execute(
                        'INSERT INTO hobby (hobby_name) VALUES (%s) ON CONFLICT (hobby_name) DO NOTHING;',
                        (hobby_name,)
                    )

                    cursor.execute('SELECT id FROM hobby WHERE hobby_name = %s;', (hobby_name,))
                    hobby_id = cursor.fetchone()[0]

                    cursor.execute(
                        'INSERT INTO nutzer_hobby(nutzer_id, hobby_id) VALUES (%s,%s) ON CONFLICT DO NOTHING;',
                        (nutzer_id, hobby_id)
                    )

                    cursor.execute(
                        'INSERT INTO nutzer_hobby_präferenz (nutzer_id, hobby_id, präferenz) VALUES (%s,%s,%s) ON CONFLICT DO NOTHING;',
                        (nutzer_id, hobby_id, präferenz)
                    )


if __name__ == "__main__":
    main()
    print("Datenimport abgeschlossen.")