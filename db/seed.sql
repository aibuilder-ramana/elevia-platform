-- Seed: Orange Psychiatry Association

INSERT INTO clinics (name, address, phone, email, mcp_endpoint)
VALUES (
    'Orange Psychiatry Association',
    '600 Ridge Rd, Orange, Connecticut, 06477',
    '+16509067224',
    'info@orangepsychiatry.com',
    'http://localhost:8001'
)
ON CONFLICT DO NOTHING;

-- Provider 1
INSERT INTO providers (
    clinic_id, provider_id, name, specializations, description,
    email, phone, mailing_address,
    insurance, accepting_new_patients, rating, reviews,
    calendar_type, calendar_id
)
SELECT
    c.id,
    '410348',
    'Coyote Moon',
    'Anxiety, Burnout, Coping Skills',
    'I believe in treating your whole being - mind, body, and spirit. As both a guide and a witness to your healing, I want to give you the tools to help you see yourself, your experiences, and your emotions through a lens of self-compassion and curiosity.',
    NULL,
    '+12036251982',
    'Essex, Connecticut, 06426',
    ARRAY['Not accepting Insurance'],
    TRUE, 4, 4.1,
    'google', NULL
FROM clinics c WHERE c.name = 'Orange Psychiatry Association'
ON CONFLICT (provider_id) DO NOTHING;

-- Provider 2
INSERT INTO providers (
    clinic_id, provider_id, name, specializations, description,
    email, phone, mailing_address,
    insurance, accepting_new_patients, rating, reviews,
    calendar_type, calendar_id
)
SELECT
    c.id,
    '100',
    'Srinivas Muvvalla',
    'Addiction, Anxiety, Burnout, Coping Skills',
    'I believe in treating your whole being - mind, body, and spirit. As both a guide and a witness to your healing, I want to give you the tools to help you see yourself, your experiences, and your emotions through a lens of self-compassion and curiosity.',
    'msbleo@gmail.com',
    '+16509067224',
    '600 Ridge Rd, Orange, Connecticut, 06426',
    ARRAY['Anthem','BlueCross and BlueShield','Cigna and Evernorth','ConnectiCare','HUSKY Health','Medicare','Optum','Oxford','UnitedHealthcare UHC | UBH'],
    TRUE, 10, 4.6,
    'google', 'msbleo@gmail.com'
FROM clinics c WHERE c.name = 'Orange Psychiatry Association'
ON CONFLICT (provider_id) DO NOTHING;
