CREATE TABLE IF NOT EXISTS lecturas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id TEXT NOT NULL,
    temperatura REAL NOT NULL,
    humedad REAL NOT NULL,
    luminosidad REAL NOT NULL,
    timestamp TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS eventos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id TEXT NOT NULL,
    tipo TEXT NOT NULL,
    descripcion TEXT NOT NULL,
    timestamp TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS comandos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id TEXT NOT NULL,
    command_id TEXT,
    actuador TEXT NOT NULL,
    estado TEXT NOT NULL,
    resultado TEXT NOT NULL,
    timestamp TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_lecturas_fecha
ON lecturas(timestamp);

CREATE INDEX IF NOT EXISTS idx_eventos_fecha
ON eventos(timestamp);

CREATE INDEX IF NOT EXISTS idx_comandos_id
ON comandos(command_id);