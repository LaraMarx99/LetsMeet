drop table if exists interessiert_an;
drop table if exists Bild;
drop table if exists Messages;
drop table if exists Likes;
drop table if exists Freundschaften;
drop table if exists Nutzer_Hobby;
drop table if exists Nutzer_Hobby_Präferenz;
drop table if exists Hobby;
drop table if exists Nutzer;
drop table if exists Geschlecht;


CREATE TABLE Geschlecht(
    ID INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    Geschlechtsidentität VARCHAR(100) NOT NULL UNIQUE
);

CREATE TABLE Hobby(
    ID INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY, 
    Hobby VARCHAR(100) NOT NULL UNIQUE
);

CREATE TABLE Nutzer(
    ID INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    Nachname VARCHAR(100),
    Vorname VARCHAR(100),
    Geburtsdatum DATE,
    Telefonnummer VARCHAR(30),
    EMail VARCHAR(100) UNIQUE,
    Straße VARCHAR(100),
    Hausnummer VARCHAR(100),
    PLZ VARCHAR(10),
    Ort VARCHAR(100),
    Geschlecht_id INT REFERENCES Geschlecht(id),
    UpdatedAt TIMESTAMP,
    CreatedAt TIMESTAMP
);

CREATE TABLE interessiert_an(
    Nutzer_ID INT REFERENCES Nutzer(id),
    Interesse INT REFERENCES Geschlecht(id),
    PRIMARY KEY (Nutzer_ID, Interesse)
);

CREATE TABLE Bild(
    ID INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    Bild_in_bytes BYTEA NOT NULL,
    ist_Profilbild BOOLEAN NOT NULL DEFAULT FALSE,
    link TEXT,
    Nutzer_ID INT REFERENCES Nutzer(id)
);

CREATE TABLE Messages(
    ID INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    receiving_Nutzer_ID INT REFERENCES Nutzer(id),
    sending_Nutzer_ID INT REFERENCES Nutzer(id),
    Content TEXT,
    Zeitstempel TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE Likes(
    liker_ID INT REFERENCES Nutzer(id),
    liked_Nutzer_ID INT REFERENCES Nutzer(id),
    PRIMARY KEY (liker_ID, liked_Nutzer_ID),
    Zustand VARCHAR(100),
    Zeitstempel TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE Freundschaften(
    Nutzer_ID_1 INT REFERENCES Nutzer(id),
    Nutzer_ID_2 INT REFERENCES Nutzer(id),
    PRIMARY KEY (Nutzer_ID_1, Nutzer_ID_2),
    Zustand VARCHAR(100),
    sendAt TIMESTAMPTZ DEFAULT NOW(),
    respondedAt TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE Nutzer_Hobby(
    Nutzer_ID INT REFERENCES Nutzer(id),
    Hobby_ID INT REFERENCES Hobby(id),
    PRIMARY KEY (Nutzer_ID, Hobby_ID)
);

CREATE TABLE Nutzer_Hobby_Präferenz(
    Nutzer_ID INT REFERENCES Nutzer(id),
    Hobby_ID INT REFERENCES Hobby(id),
    PRIMARY KEY (Nutzer_ID, Hobby_ID),
    Präferenz INT CHECK (Präferenz BETWEEN -100 AND 100)
);