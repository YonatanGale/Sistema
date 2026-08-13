-- Crear la base de datos
CREATE DATABASE IF NOT EXISTS encuestas_platform;
USE encuestas_platform;

-- Tabla de usuarios
CREATE TABLE usuarios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    rol ENUM('admin', 'analista', 'lector') DEFAULT 'lector',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla de encuestas
CREATE TABLE encuestas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    titulo VARCHAR(200) NOT NULL,
    descripcion TEXT,
    usuario_id INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
);

-- Tabla de preguntas
CREATE TABLE preguntas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    encuesta_id INT,
    texto TEXT NOT NULL,
    tipo ENUM('abierta', 'cerrada_unica', 'cerrada_multiple', 'escala') NOT NULL,
    opciones TEXT, -- JSON con opciones
    orden INT DEFAULT 0,
    FOREIGN KEY (encuesta_id) REFERENCES encuestas(id) ON DELETE CASCADE
);

-- Tabla de respuestas
CREATE TABLE respuestas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    encuesta_id INT,
    pregunta_id INT,
    usuario_respuesta VARCHAR(255), -- Para texto libre
    opcion_seleccionada VARCHAR(255), -- Para opciones
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (encuesta_id) REFERENCES encuestas(id) ON DELETE CASCADE,
    FOREIGN KEY (pregunta_id) REFERENCES preguntas(id) ON DELETE CASCADE
);

-- Tabla de análisis NLP
CREATE TABLE analisis_texto (
    id INT AUTO_INCREMENT PRIMARY KEY,
    encuesta_id INT,
    pregunta_id INT,
    texto_original TEXT,
    sentimiento VARCHAR(20),
    confianza_sentimiento FLOAT,
    palabras_clave TEXT,
    temas TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (encuesta_id) REFERENCES encuestas(id) ON DELETE CASCADE,
    FOREIGN KEY (pregunta_id) REFERENCES preguntas(id) ON DELETE CASCADE
);

-- Tabla de auditoría
CREATE TABLE auditoria (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT,
    accion VARCHAR(100),
    descripcion TEXT,
    ip VARCHAR(45),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE SET NULL
);

-- Insertar usuario admin por defecto (password: admin123)
INSERT INTO usuarios (nombre, email, password, rol) 
VALUES ('Administrador', 'admin@encuestas.com', '$2y$10$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2.uheWG/igi', 'admin');