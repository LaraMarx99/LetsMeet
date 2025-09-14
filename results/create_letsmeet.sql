drop table if exists interessiert_an;
drop table if exists bild;
drop table if exists messages;
drop table if exists likes;
drop table if exists freundschaften;
drop table if exists nutzer_hobby;
drop table if exists nutzer_hobby_präferenz;
drop table if exists hobby;
drop table if exists nutzer;
drop table if exists geschlecht;


CREATE TABLE geschlecht(
    id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    geschlechtsidentität VARCHAR(100) NOT NULL UNIQUE
);

CREATE TABLE hobby(
    id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY, 
    hobby_name VARCHAR(100) NOT NULL UNIQUE
);

CREATE TABLE nutzer(
    id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nachname VARCHAR(100),
    vorname VARCHAR(100),
    geburtsdatum DATE,
    telefonnummer VARCHAR(30),
    email VARCHAR(100) UNIQUE,
    straße VARCHAR(100),
    hausnummer VARCHAR(100),
    plz VARCHAR(10),
    ort VARCHAR(100),
    geschlecht_id INT REFERENCES geschlecht(id),
    updated_at TIMESTAMP,
    created_at TIMESTAMP
);

CREATE TABLE interessiert_an(
    nutzer_id INT REFERENCES nutzer(id),
    interesse INT REFERENCES geschlecht(id),
    PRIMARY KEY (nutzer_id, interesse)
);

CREATE TABLE bild(
    id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    bild_in_bytes BYTEA NOT NULL,
    ist_profilbild BOOLEAN NOT NULL DEFAULT FALSE,
    link TEXT,
    nutzer_id INT REFERENCES nutzer(id)
);

CREATE TABLE messages(
    id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    receiving_nutzer_id INT REFERENCES nutzer(id),
    sending_nutzer_id INT REFERENCES nutzer(id),
    content TEXT,
    zeitstempel TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE likes(
    liker_id INT REFERENCES nutzer(id),
    liked_nutzer_id INT REFERENCES nutzer(id),
    PRIMARY KEY (liker_id, liked_nutzer_id),
    zustand VARCHAR(100),
    zeitstempel TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE freundschaften(
    nutzer_id_1 INT REFERENCES nutzer(id),
    nutzer_id_2 INT REFERENCES nutzer(id),
    PRIMARY KEY (nutzer_id_1, nutzer_id_2),
    zustand VARCHAR(100),
    send_at TIMESTAMPTZ DEFAULT NOW(),
    responded_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE nutzer_hobby(
    nutzer_id INT REFERENCES nutzer(id),
    hobby_id INT REFERENCES hobby(id),
    PRIMARY KEY (nutzer_id, hobby_id)
);

CREATE TABLE nutzer_hobby_präferenz(
    nutzer_id INT REFERENCES nutzer(id),
    hobby_id INT REFERENCES hobby(id),
    PRIMARY KEY (nutzer_id, hobby_id),
    präferenz INT CHECK (präferenz BETWEEN -100 AND 100)
);