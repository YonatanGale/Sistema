 
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
define('APP_ENV', getenv('APP_ENV') ?: 'development');

// ============================================
// 3. RUTAS DINÁMICAS
// ============================================
function getBaseUrl() {
    $protocol = isset($_SERVER['HTTPS']) && $_SERVER['HTTPS'] === 'on' ? 'https' : 'http';
    $host = $_SERVER['HTTP_HOST'];
    $scriptName = $_SERVER['SCRIPT_NAME'];
    
    $basePath = dirname(dirname($scriptName));
    $basePath = str_replace('\\', '/', $basePath);
    
    if ($basePath === '/' || $basePath === '') {
        $basePath = '';
    }
    
    return $protocol . '://' . $host . $basePath;
}

define('BASE_URL', getBaseUrl());
define('BASE_PATH', dirname(dirname(__DIR__)));
define('PUBLIC_PATH', BASE_PATH . '/public');
define('UPLOAD_PATH', PUBLIC_PATH . '/uploads');

// ============================================
// 4. SEGURIDAD
// ============================================
define('SALT', getenv('APP_SALT') ?: 'default_salt_change_me_in_production');
define('JWT_SECRET', getenv('JWT_SECRET') ?: 'default_jwt_secret_change_me');

// ============================================
// 5. CORS
// ============================================
define('CORS_ALLOWED_ORIGINS', getenv('CORS_ALLOWED_ORIGINS') ?: '*');

// ============================================
// 6. PYTHON NLP
// ============================================
define('PYTHON_PATH', getenv('PYTHON_PATH') ?: 'python');
define('PYTHON_SCRIPTS_PATH', BASE_PATH . '/python-scripts');
define('PYTHON_API_URL', getenv('PYTHON_API_URL') ?: 'http://localhost:5000');

// ============================================
// 7. LOGS
// ============================================
define('LOG_PATH', BASE_PATH . '/logs');
define('LOG_LEVEL', getenv('LOG_LEVEL') ?: 'info');

if (!file_exists(LOG_PATH)) {
    mkdir(LOG_PATH, 0777, true);
}
?>