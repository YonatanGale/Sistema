<?php
// app/helpers/functions.php

require_once __DIR__ . '/../config/config.php';

// Función para sanitizar datos
function sanitize($data) {
    if (is_array($data)) {
        return array_map('sanitize', $data);
    }
    $data = trim($data);
    $data = stripslashes($data);
    $data = htmlspecialchars($data, ENT_QUOTES, 'UTF-8');
    return $data;
}

// Función para generar URL amigable (dinámica)
function url($path = '') {
    $baseUrl = rtrim(BASE_URL, '/');
    $path = ltrim($path, '/');
    return $baseUrl . '/' . $path;
}

// Función para redireccionar
function redirect($path = '') {
    header('Location: ' . url($path));
    exit();
}

// Función para mostrar mensajes flash
function setFlash($tipo, $mensaje) {
    $_SESSION['flash'] = [
        'tipo' => $tipo,
        'mensaje' => $mensaje
    ];
}

function getFlash() {
    if (isset($_SESSION['flash'])) {
        $flash = $_SESSION['flash'];
        unset($_SESSION['flash']);
        return $flash;
    }
    return null;
}

// Función para validar email
function isValidEmail($email) {
    return filter_var($email, FILTER_VALIDATE_EMAIL);
}

// Función para generar token CSRF
function generateCSRFToken() {
    if (empty($_SESSION['csrf_token'])) {
        $_SESSION['csrf_token'] = bin2hex(random_bytes(32));
    }
    return $_SESSION['csrf_token'];
}

function verifyCSRFToken($token) {
    return isset($_SESSION['csrf_token']) && hash_equals($_SESSION['csrf_token'], $token);
}

// Función para subir archivos
function uploadFile($file, $targetDir = null) {
    if ($targetDir === null) {
        $targetDir = UPLOAD_PATH;
    }
    
    if (!file_exists($targetDir)) {
        mkdir($targetDir, 0777, true);
    }
    
    $fileName = time() . '_' . basename($file['name']);
    $targetFile = $targetDir . '/' . $fileName;
    
    // Validar tipo de archivo
    $allowedTypes = ['xlsx', 'xls', 'csv', 'txt', 'json'];
    $ext = strtolower(pathinfo($fileName, PATHINFO_EXTENSION));
    
    if (!in_array($ext, $allowedTypes)) {
        return ['error' => 'Tipo de archivo no permitido'];
    }
    
    if (move_uploaded_file($file['tmp_name'], $targetFile)) {
        return ['success' => true, 'filename' => $fileName, 'path' => $targetFile];
    }
    
    return ['error' => 'Error al subir el archivo'];
}

// Función para debug (solo en desarrollo)
function debug($data) {
    if (APP_ENV === 'development') {
        echo '<pre>';
        print_r($data);
        echo '</pre>';
    }
}

// Función para generar slug
function slugify($text) {
    // Reemplazar caracteres especiales
    $text = preg_replace('~[^\pL\d]+~u', '-', $text);
    $text = iconv('utf-8', 'us-ascii//TRANSLIT', $text);
    $text = preg_replace('~[^-\w]+~', '', $text);
    $text = trim($text, '-');
    $text = strtolower($text);
    return empty($text) ? 'n-a' : $text;
}
?>