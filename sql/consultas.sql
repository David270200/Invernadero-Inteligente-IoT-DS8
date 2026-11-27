-- Ultimas 20 lecturas
SELECT *
FROM lecturas
ORDER BY id DESC
LIMIT 20;

-- Promedios de las ultimas 24 horas
SELECT
    ROUND(AVG(temperatura), 2) AS temperatura_promedio,
    ROUND(AVG(humedad), 2) AS humedad_promedio,
    ROUND(AVG(luminosidad), 2) AS luminosidad_promedio
FROM lecturas
WHERE datetime(timestamp) >= datetime('now', '-1 day');

-- Temperaturas elevadas
SELECT *
FROM lecturas
WHERE temperatura > 30
ORDER BY timestamp DESC;

-- Historial de eventos
SELECT *
FROM eventos
ORDER BY id DESC;

-- Comandos remotos confirmados
SELECT *
FROM comandos
WHERE command_id IS NOT NULL
ORDER BY id DESC;

-- Historial de estados automaticos
SELECT *
FROM comandos
WHERE command_id IS NULL
ORDER BY id DESC;