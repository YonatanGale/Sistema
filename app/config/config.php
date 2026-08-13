<?php
// app/config/config.php - Configuración central del sistema

// ============================================
// 1. CONFIGURACIÓN DE LA BASE DE DATOS
// ============================================
define('DB_HOST', getenv('DB_HOST') ?: 'localhost');
define('DB_USER', getenv('DB_USER') ?: 'root');
define('DB_PASS', getenv('DB_PASS') ?: '');
define('DB_NAME', getenv('DB_NAME') ?: 'encuestas_platform');

// ============================================
// 2. CONFIGURACIÓN DE LA APLICACIÓN
// ============================================
define('APP_NAME', 'Encuestas Platform');
define('APP_VERSION', '1.0.0');
define('APP_ENV', getenv('APP_ENV') ?: 'development'); // development | production

// ============================================
// 3. RUTAS DINÁMICAS (Detección automática)
// ============================================
// Detectar la URL base automáticamente
function getBaseUrl() {
    $protocol = isset($_SERVER['HTTPS']) && $_SERVER['HTTPS'] === 'on' ? 'https' : 'http';
    $host = $_SERVER['HTTP_HOST'];
    $scriptName = $_SERVER['SCRIPT_NAME'];
    
    // Remover /public/index.php o /index.php de la ruta
    $basePath = dirname(dirname($scriptName));
    $basePath = str_replace('\\', '/', $basePath);
    
    // Si estamos en la raíz del servidor, usar '/'
    if ($basePath === '/' || $basePath === '') {
        $basePath = '';
    }
    
    return $protocol . '://' . $host . $basePath;
}

define('BASE_URL', getBaseUrl());
define('BASE_PATH', dirname(dirname(__DIR__))); // Ruta física del proyecto

// Subdirectorios
define('PUBLIC_PATH', BASE_PATH . '/public');
define('UPLOAD_PATH', PUBLIC_PATH . '/uploads');

// ============================================
// 4. CONFIGURACIÓN DE SEGURIDAD
// ============================================
define('SALT', getenv('APP_SALT') ?: 'default_salt_change_me_in_production');
define('JWT_SECRET', getenv('JWT_SECRET') ?: 'default_jwt_secret_change_me');

// ============================================
// 5. CONFIGURACIÓN DE CORS (para API)
// ============================================
define('CORS_ALLOWED_ORIGINS', getenv('CORS_ALLOWED_ORIGINS') ?: '*');

// ============================================
// 6. CONFIGURACIÓN DE PYTHON (NLP)
// ============================================
define('PYTHON_PATH', getenv('PYTHON_PATH') ?: 'python');
define('PYTHON_SCRIPTS_PATH', BASE_PATH . '/python-scripts');
define('PYTHON_API_URL', getenv('PYTHON_API_URL') ?: 'http://localhost:5000');

// ============================================
// 7. CONFIGURACIÓN DE LOGS
// ============================================
define('LOG_PATH', BASE_PATH . '/logs');
define('LOG_LEVEL', getenv('LOG_LEVEL') ?: 'info'); // debug, info, warning, error

// Crear directorio de logs si no existe
if (!file_exists(LOG_PATH)) {
    mkdir(LOG_PATH, 0777, true);
}
?>