drop table if exists Hobbys;
drop table if exists Nutzer;
drop table if exists Geschlecht;


CREATE TABLE Geschlecht(
    ID INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    Geschlechtsindentität VARCHAR(100) UNIQUE
);

CREATE TABLE Hobbys(
    ID INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY, 
    Hobbys VARCHAR(100) UNIQUE
);

CREATE TABLE Nutzer(
    ID INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    Nachname VARCHAR(100),
    Vorname VARCHAR(100),
    Geburtsdatum DATE,
    Telefonnummer INT,
    EMail VARCHAR(100) UNIQUE,
    Straße VARCHAR(100),
    Hausnummer VARCHAR(100),
    PLZ INT,
    Ort VARCHAR(100),
    Geschlecht_id INT REFERENCES Geschlecht(id),
    UpdatedAt TIMESTAMP,
    CreatedAt TIMESTAMP
);

CREATE TABLE interessiert_an(
    Nutzer_ID INT REFERENCES Nutzer(id),
    Interesse INT REFERENCES Geschlecht(id)
);


