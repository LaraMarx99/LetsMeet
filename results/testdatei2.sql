-- Gesamtanzahl Nutzer
SELECT COUNT(*) FROM nutzer;

-- Stichprobe: gibt es den Nutzer "Ursula Gehlen"?
SELECT * FROM nutzer WHERE email ILIKE 'ursula.gehlen%@%';

-- Wieviele Nutzer pro Geschlecht?
SELECT g.geschlechtsidentitaet, COUNT(*)
FROM nutzer n
LEFT JOIN geschlecht g ON n.geschlecht_id = g.id
GROUP BY g.geschlechtsidentitaet;

-- Anzahl aller Hobbys
SELECT COUNT(*) FROM hobby;

-- Wieviele Hobbys pro Nutzer?
SELECT n.email, COUNT(nh.hobby_id) AS hobby_count
FROM nutzer n
JOIN nutzer_hobby nh ON n.id = nh.nutzer_id
GROUP BY n.email
ORDER BY hobby_count DESC;

-- Stichprobe: Hobbys und Präferenzen von "Kai Gehrmann"
SELECT h.hobby_name, nhp.praeferenz
FROM nutzer n
JOIN nutzer_hobby nh ON n.id = nh.nutzer_id
JOIN hobby h ON nh.hobby_id = h.id
LEFT JOIN nutzer_hobby_praeferenz nhp
  ON nh.nutzer_id = nhp.nutzer_id AND nh.hobby_id = nhp.hobby_id
WHERE n.email ILIKE 'kai.gehrmann%@%';

-- Gesamtanzahl Likes
SELECT COUNT(*) FROM likes;

-- Alle Likes eines bestimmten Nutzers
SELECT n1.email AS liker, n2.email AS liked, l.zustand, l.zeitstempel
FROM likes l
JOIN nutzer n1 ON l.liker_id = n1.id
JOIN nutzer n2 ON l.liked_nutzer_id = n2.id
WHERE n1.email ILIKE 'ansgar.kötter%@%';

-- Gesamtanzahl Messages
SELECT COUNT(*) FROM messages;

-- Nachrichten von einem bestimmten Sender
SELECT n1.email AS sender, n2.email AS receiver, m.content, m.zeitstempel
FROM messages m
JOIN nutzer n1 ON m.sending_nutzer_id = n1.id
JOIN nutzer n2 ON m.receiving_nutzer_id = n2.id
WHERE n1.email ILIKE 'ansgar.kötter%@%';

-- Wer ist an wem interessiert?
SELECT n.email AS nutzer, g.geschlechtsidentitaet AS interessiert_an
FROM interessiert_an ia
JOIN nutzer n ON ia.nutzer_id = n.id
JOIN geschlecht g ON ia.interesse = g.id
ORDER BY n.email;
