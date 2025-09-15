-- ===========================================
-- MIGRATION VALIDATION TESTS
-- ===========================================

-- 1. IMPORT COUNT CHECKS - Wurden Daten aus allen Quellen importiert?
SELECT 'excel_nutzer_mit_adressdaten' as test_name, COUNT(*) as result 
FROM nutzer WHERE telefonnummer IS NOT NULL AND straße IS NOT NULL;

SELECT 'xml_nutzer_mit_hobbies_ohne_adresse' as test_name, COUNT(*) as result 
FROM nutzer n 
JOIN nutzer_hobby nh ON n.id = nh.nutzer_id 
WHERE n.telefonnummer IS NULL AND n.straße IS NULL AND n.created_at IS NULL;

SELECT 'mongo_nutzer_mit_timestamps' as test_name, COUNT(*) as result 
FROM nutzer WHERE created_at IS NOT NULL;

SELECT 'mongo_messages_importiert' as test_name, COUNT(*) as result FROM messages;

-- 2. DATA INTEGRITY - Kritische Validierungen
SELECT 'nutzer_ohne_email' as test_name, COUNT(*) as result 
FROM nutzer WHERE email IS NULL OR email = '';

SELECT 'doppelte_emails' as test_name, COUNT(*) - COUNT(DISTINCT email) as result 
FROM nutzer;

-- 3. REFERENTIAL INTEGRITY - Verknüpfungen korrekt?
SELECT 'nutzer_hobby_ohne_gueltige_nutzer' as test_name, COUNT(*) as result 
FROM nutzer_hobby nh 
LEFT JOIN nutzer n ON nh.nutzer_id = n.id 
WHERE n.id IS NULL;

SELECT 'nutzer_hobby_ohne_gueltige_hobbies' as test_name, COUNT(*) as result 
FROM nutzer_hobby nh 
LEFT JOIN hobby h ON nh.hobby_id = h.id 
WHERE h.id IS NULL;

SELECT 'messages_mit_ungueltigem_sender' as test_name, COUNT(*) as result 
FROM messages m 
LEFT JOIN nutzer sender ON m.sending_nutzer_id = sender.id 
WHERE sender.id IS NULL;

SELECT 'messages_mit_ungueltigem_empfaenger' as test_name, COUNT(*) as result 
FROM messages m 
LEFT JOIN nutzer empfaenger ON m.receiving_nutzer_id = empfaenger.id 
WHERE empfaenger.id IS NULL;

-- 4. EXCEL SPECIFIC - Hobby-Prioritäten
SELECT 'hobby_prioritaeten_ohne_nutzer' as test_name, COUNT(*) as result 
FROM nutzer_hobby_präferenz nhp 
LEFT JOIN nutzer n ON nhp.nutzer_id = n.id 
WHERE n.id IS NULL;

-- 5. FORMAT VALIDATION - Datenqualität
SELECT 'ungueltige_email_formate' as test_name, COUNT(*) as result 
FROM nutzer WHERE email NOT LIKE '%@%.%';