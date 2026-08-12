<?php
// app/config/database.php

require_once __DIR__ . '/config.php';

function getConnection() {
    try {
        $conn = new PDO(
            "mysql:host=" . DB_HOST . ";dbname=" . DB_NAME . ";charset=utf8mb4",
            DB_USER,
            DB_PASS,
            [
                PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
                PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
                PDO::ATTR_EMULATE_PREPARES => false,
                PDO::MYSQL_ATTR_INIT_COMMAND => "SET NAMES utf8mb4"
            ]
        );
        return $conn;
    } catch(PDOException $e) {
        // En producción, no mostrar detalles del error
        if (APP_ENV === 'production') {
            die("Error de conexión a la base de datos. Por favor, contacte al administrador.");
        } else {
            die("Error de conexión: " . $e->getMessage());
        }
    }
}

// Iniciar sesión si no está iniciada
if (session_status() === PHP_SESSION_NONE) {
    session_start();
}

// Función para verificar si el usuario está logueado
function isLoggedIn() {
    return isset($_SESSION['usuario_id']);
}

// Función para verificar rol
function hasRole($rol) {
    return isset($_SESSION['rol']) && $_SESSION['rol'] === $rol;
}

// Función para registrar auditoría
function logAuditoria($accion, $descripcion = '') {
    if (!isLoggedIn()) return;
    
    try {
        $conn = getConnection();
        $sql = "INSERT INTO auditoria (usuario_id, accion, descripcion, ip, user_agent) 
                VALUES (?, ?, ?, ?, ?)";
        $stmt = $conn->prepare($sql);
        $ip = $_SERVER['REMOTE_ADDR'] ?? '0.0.0.0';
        $userAgent = $_SERVER['HTTP_USER_AGENT'] ?? '';
        $stmt->execute([$_SESSION['usuario_id'], $accion, $descripcion, $ip, $userAgent]);
    } catch (Exception $e) {
        // No interrumpir la ejecución si falla la auditoría
        error_log("Error en auditoría: " . $e->getMessage());
    }
}

// Función para logging
function logMessage($level, $message) {
    $logFile = LOG_PATH . '/app_' . date('Y-m-d') . '.log';
    $timestamp = date('Y-m-d H:i:s');
    $logEntry = "[$timestamp] [$level] $message" . PHP_EOL;
    file_put_contents($logFile, $logEntry, FILE_APPEND);
}
?>