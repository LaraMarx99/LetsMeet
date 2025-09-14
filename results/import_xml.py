import xml.etree.ElementTree as ET
from typing import Optional, Tuple
import psycopg2

def split_name(full_name: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    if not isinstance(full_name, str):
        return None, None
    name_parts = [part.strip() for part in full_name.split(",")]
    if len(name_parts) >= 2:
        return name_parts[0] or None, name_parts[1] or None
    return full_name.strip() or None, None


def main():
    XML_FILE = "Lets_Meet_Hobbies.xml"
    PG_URL = "postgresql://user:secret@localhost:5432/lf8_lets_meet_db"

    tree = ET.parse(XML_FILE)
    root = tree.getroot()

    with psycopg2.connect(PG_URL) as connection:
        with connection.cursor() as cursor:
            for user_element in root.findall('user'):
                email_element = user_element.find('email')
                name_element = user_element.find('name')
                hobbies_element = user_element.find('hobbies')

                email = email_element.text.lower().strip() if email_element is not None and email_element.text else None
                name = name_element.text.strip() if name_element is not None and name_element.text else None
                nachname, vorname = split_name(name)

                cursor.execute(
                    'INSERT INTO "nutzer" '
                    '("nachname", "vorname", "email") '
                    'VALUES (%s,%s,%s) '
                    'ON CONFLICT (email) DO NOTHING '
                    'RETURNING "id";',
                    (nachname, vorname, email)
                )

                result = cursor.fetchone()
                if result is None:
                    cursor.execute('SELECT "id" FROM "nutzer" WHERE "email" = %s;', (email,))
                    result = cursor.fetchone()
                
                if result:
                    nutzer_id = result[0]
                
                    if hobbies_element is not None:
                        for hobby_element in hobbies_element.findall('hobby'):
                            hobby_name = hobby_element.text
                            if hobby_name:
                                hobby_name = hobby_name.strip()

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

if __name__ == "__main__":
    main()
    print("Datenimport abgeschlossen.")