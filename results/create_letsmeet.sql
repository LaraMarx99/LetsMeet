drop table if exists interessiert_an;
drop table if exists bild;
drop table if exists messages;
drop table if exists likes;
drop table if exists freundschaften;
drop table if exists nutzer_hobby;
drop table if exists nutzer_hobby_praeferenz;
drop table if exists hobby;
drop table if exists nutzer;
drop table if exists geschlecht;


CREATE TABLE geschlecht(
    id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    geschlechtsidentitaet VARCHAR(100) NOT NULL UNIQUE
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
    email VARCHAR(320) NOT NULL,
    strasse VARCHAR(100),
    hausnummer VARCHAR(100),
    plz VARCHAR(10),
    ort VARCHAR(100),
    geschlecht_id INT REFERENCES geschlecht(id) ON DELETE SET NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX uq_nutzer_email_norm
  ON nutzer ((lower(trim(email))));

CREATE TABLE interessiert_an(
    nutzer_id INT NOT NULL REFERENCES nutzer(id)  ON DELETE CASCADE,
    interesse INT REFERENCES geschlecht(id) ON DELETE CASCADE,
    PRIMARY KEY (nutzer_id, interesse)
);

CREATE TABLE bild(
    id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    bild_in_bytes BYTEA,
    ist_profilbild BOOLEAN NOT NULL DEFAULT FALSE,
    link TEXT,
    nutzer_id INT NOT NULL REFERENCES nutzer(id) ON DELETE CASCADE,
    CONSTRAINT chk_bild_inhalt CHECK (bild_in_bytes IS NOT NULL OR link IS NOT NULL)
);

CREATE UNIQUE INDEX uq_single_profile_pic
  ON bild (nutzer_id)
  WHERE ist_profilbild IS TRUE;

CREATE TABLE messages(
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    receiving_nutzer_id INT REFERENCES nutzer(id) ON DELETE SET NULL,
    sending_nutzer_id INT REFERENCES nutzer(id) ON DELETE SET NULL,
    content TEXT,
    zeitstempel TIMESTAMPTZ DEFAULT NOW(),
    conversation_id INT
);

CREATE UNIQUE INDEX uq_messages_source
  ON messages (sending_nutzer_id, receiving_nutzer_id, conversation_id, zeitstempel);

CREATE TABLE likes(
    liker_id INT REFERENCES nutzer(id) ON DELETE CASCADE,
    liked_nutzer_id INT REFERENCES nutzer(id) ON DELETE CASCADE,
    PRIMARY KEY (liker_id, liked_nutzer_id),
    CONSTRAINT chk_like_no_self CHECK (liker_id <> liked_nutzer_id),
    zustand VARCHAR(100),
    zeitstempel TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE freundschaften(
    nutzer_id_1 INT REFERENCES nutzer(id) ON DELETE CASCADE,
    nutzer_id_2 INT REFERENCES nutzer(id) ON DELETE CASCADE,
    PRIMARY KEY (nutzer_id_1, nutzer_id_2),
    CONSTRAINT chk_friend_order CHECK (nutzer_id_1 < nutzer_id_2),
    CONSTRAINT chk_friend_no_self CHECK (nutzer_id_1 <> nutzer_id_2),
    zustand VARCHAR(100),
    send_at TIMESTAMPTZ DEFAULT NOW(),
    responded_at TIMESTAMPTZ
);

CREATE TABLE nutzer_hobby(
    nutzer_id INT REFERENCES nutzer(id) ON DELETE CASCADE,
    hobby_id INT REFERENCES hobby(id) ON DELETE CASCADE,
    PRIMARY KEY (nutzer_id, hobby_id)
);

CREATE TABLE nutzer_hobby_praeferenz(
    nutzer_id INT REFERENCES nutzer(id) ON DELETE CASCADE,
    hobby_id INT REFERENCES hobby(id) ON DELETE CASCADE,
    PRIMARY KEY (nutzer_id, hobby_id),
    praferenz INT NOT NULL CHECK (praferenz BETWEEN -100 AND 100)
);