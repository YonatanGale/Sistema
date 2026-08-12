<?php
// public/index.php - Front Controller

// Cargar configuración
require_once __DIR__ . '/../app/config/database.php';
require_once __DIR__ . '/../app/helpers/functions.php';

// Cargar controladores
require_once __DIR__ . '/../app/controllers/AuthController.php';
require_once __DIR__ . '/../app/controllers/EncuestaController.php';
require_once __DIR__ . '/../app/controllers/DashboardController.php';

// Cargar router
require_once __DIR__ . '/../app/Router.php';

// Inicializar router
$router = new Router();

// Definir rutas
$router->add('GET', '/', 'home');
$router->add('GET', '/home', 'home');
$router->add('GET', '/login', 'login');
$router->add('POST', '/login', 'login');
$router->add('GET', '/logout', 'logout');
$router->add('GET', '/registro', 'registro');
$router->add('POST', '/registro', 'registro');
$router->add('GET', '/crear-encuesta', 'crearEncuesta');
$router->add('POST', '/crear-encuesta', 'crearEncuesta');
$router->add('GET', '/listar-encuestas', 'listarEncuestas');
$router->add('GET', '/ver-encuesta', 'verEncuesta');
$router->add('GET', '/analizar-encuesta', 'analizarEncuesta');
$router->add('POST', '/cargar-respuestas', 'cargarRespuestas');
$router->add('GET', '/api/stats', 'apiStats');

// Ejecutar router
$router->run();
?>