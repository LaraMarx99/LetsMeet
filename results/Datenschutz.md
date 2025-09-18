# Datenschutz in der Let's Meet Datenbank

## 1. Übersicht

Die Datenbank der Let's Meet GmbH verarbeitet personenbezogene Daten im Rahmen einer Dating- und Meeting-Plattform.  
Es gelten die Vorgaben der DSGVO. Besondere Aufmerksamkeit liegt auf sensiblen Daten wie sexueller Orientierung („interessiert an“) und Kommunikationsinhalten (Nachrichten, Likes, Freundschaften, Profilbilder).

---

## 2. Arten von Daten

### Stammdaten (Excel)
- Name, Adresse, Telefonnummer, E-Mail
- Geburtsdatum
- Geschlecht
- Interessiert an (Geschlechtsidentität)

→ **personenbezogene Daten**, inkl. **besonderer Kategorie** (sexuelle Orientierung).

### Nutzungsdaten (MongoDB)
- Likes (mit Zustand und Zeitstempel)
- Nachrichten (Inhalt, Empfänger, Zeitstempel)
- Freundeslisten

→ **Kommunikationsdaten**, ebenfalls sensibel.

### Hobbydaten (Excel + XML)
- Eigene Hobbys (XML, max. 5 pro Nutzer)
- Präferenzen für Hobbys bei anderen (Excel, Wert −100 bis +100)

→ **Interessen- und Profildaten**, personenbezogen.

### Profildaten
- Profilbild, weitere Bilder (BLOB / Link)

→ **biometrische Daten** (Fotos), besonders schützenswert.

---

## 3. Technische Maßnahmen im Datenmodell

### Fremdschlüssel und ON DELETE Verhalten
- **`nutzer`** ist Zentraltabelle; alle abhängigen Daten sind per FK verknüpft.  
- Bei Löschung eines Nutzers greifen **ON DELETE CASCADE** bzw. **ON DELETE SET NULL**, um Daten automatisch zu bereinigen oder zu anonymisieren.

### Nachrichten (messages)
- `sending_nutzer_id` und `receiving_nutzer_id` sind mit **ON DELETE SET NULL** verknüpft.  
- **Vorteil:** Wenn ein Nutzer sein Konto löscht, bleiben Nachrichteninhalte für bis zu **12 Monate** erhalten, aber ohne Bezug zu einer Person → **anonymisierte Aufbewahrung** für Missbrauchserkennung oder Rechtsansprüche. Danach können Nachrichten endgültig gelöscht werden.

### Likes & Freundschaften
- Fremdschlüssel stehen auf **ON DELETE CASCADE**.  
- **Vorteil:** Werden Nutzer*innen gelöscht, verschwinden auch deren Likes/Freundschaften. Keine isolierten Datensätze, keine unnötige Speicherung.

### Hobbys & Präferenzen
- `nutzer_hobby` (max. 5 Einträge/Nutzer) → eigene Hobbys, werden bei Nutzerlöschung automatisch entfernt.  
- `nutzer_hobby_praeferenz` → Bewertungen, bleiben nicht erhalten, da FK mit **ON DELETE CASCADE** verknüpft.

### Geschlecht
- Eigene Lookup-Tabelle (`geschlecht`) mit festen Werten.  
- Normalisierung → weniger Redundanz, einfachere Löschung/Korrektur möglich.

### Bilder (Profilbilder)
- Tabelle `bild` mit booleschem Feld `ist_profilbild`.  
- Bilder referenzieren Nutzer via FK → **ON DELETE CASCADE** löscht Bilder automatisch bei Nutzerlöschung.  
- Speicherung als `BYTEA` oder Link, optional verschlüsselt.

---

## 4. Weitere Schutzmaßnahmen

### Zugriffskontrolle
- Datenbankzugriff nur für autorisierte Rollen.  
- Trennung zwischen Administrationsrollen und Reportingrollen.  
- Sensible Tabellen wie `messages` oder `bild` nur für minimal berechtigte Accounts.

### Verschlüsselung
- Datenbankzugriff ausschließlich über TLS.  
- Optionale Verschlüsselung von BLOBs (Profilbilder) in der Anwendungsschicht.  
- Backups sind verschlüsselt.

### Protokollierung
- Zugriffe auf sensible Tabellen (`messages`, `likes`, `freundschaften`, `bild`) werden geloggt.  
- Änderungsprotokolle (z. B. Löschung eines Nutzers) sind nachvollziehbar.

### Lösch- und Speicherfristen
- **Stammdaten**: sofort löschen bei Accountlöschung.  
- **Kommunikationsdaten (messages)**: bis zu 12 Monate anonymisiert aufbewahren (dank ON DELETE SET NULL), danach endgültig löschen.  
- **Backups**: maximal 6 Monate vorhalten, dann überschreiben.  
- **Profilbilder**: sofort löschen bei Accountlöschung.

---

## 5. Rechte der Betroffenen

- **Auskunftsrecht (Art. 15 DSGVO)**: Nutzer*innen können einen Export aller Daten verlangen.  
- **Berichtigung (Art. 16 DSGVO)**: Fehlerhafte Stammdaten können korrigiert werden.  
- **Löschung (Art. 17 DSGVO)**: Account-Löschung entfernt alle personenbezogenen Daten oder anonymisiert (z. B. Nachrichten).  
- **Datenübertragbarkeit (Art. 20 DSGVO)**: Export im maschinenlesbaren Format (z. B. CSV, JSON).

---

## 6. Zusammenfassung

Die Datenbankstruktur wurde so entworfen, dass:
- Daten **minimiert** und **normalisiert** gespeichert werden.  
- Durch **ON DELETE CASCADE/SET NULL** eine **automatische Umsetzung des Rechts auf Vergessenwerden** erfolgt.  
- Besonders sensible Daten (Nachrichten, Bilder, sexuelle Orientierung) mit **zusätzlichen Schutzmaßnahmen** behandelt werden.  
- Eine **anonymisierte Aufbewahrung** von Nachrichten durch ON DELETE SET NULL für bis zu 12 Monate möglich ist, bevor die endgültige Löschung erfolgt.  
