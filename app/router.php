<?php
// app/Router.php

class Router {
    private $routes = [];
    
    public function add($method, $route, $action) {
        // Convertir la ruta a expresión regular
        $route = preg_replace('/\//', '\\/', $route);
        $route = '/^' . $route . '$/i';
        
        $this->routes[$route] = [
            'method' => $method,
            'action' => $action
        ];
    }
    
    public function run() {
        $requestMethod = $_SERVER['REQUEST_METHOD'];
        $requestUri = strtok($_SERVER['REQUEST_URI'], '?');
        
        // Remover la base path de la URL
        $basePath = dirname($_SERVER['SCRIPT_NAME']);
        if ($basePath !== '/') {
            $requestUri = str_replace($basePath, '', $requestUri);
        }
        
        if ($requestUri === '' || $requestUri === '/') {
            $requestUri = '/home';
        }
        
        foreach ($this->routes as $route => $routeInfo) {
            if (preg_match($route, $requestUri, $matches)) {
                if ($routeInfo['method'] === $requestMethod || $routeInfo['method'] === 'ANY') {
                    $this->callAction($routeInfo['action']);
                    return;
                }
            }
        }
        
        // Ruta no encontrada
        header('HTTP/1.0 404 Not Found');
        echo 'Página no encontrada';
    }
    
    private function callAction($action) {
        if (is_callable($action)) {
            $action();
            return;
        }
        
        // Manejar acciones específicas
        switch ($action) {
            case 'home':
                $controller = new DashboardController();
                $controller->index();
                break;
            case 'login':
                $controller = new AuthController();
                $controller->login();
                break;
            case 'logout':
                $controller = new AuthController();
                $controller->logout();
                break;
            case 'registro':
                $controller = new AuthController();
                $controller->registro();
                break;
            case 'crearEncuesta':
                $controller = new EncuestaController();
                $controller->crear();
                break;
            case 'listarEncuestas':
                $controller = new EncuestaController();
                $controller->listar();
                break;
            case 'verEncuesta':
                $controller = new EncuestaController();
                $controller->ver();
                break;
            case 'analizarEncuesta':
                $controller = new EncuestaController();
                $controller->analizar();
                break;
            case 'cargarRespuestas':
                $controller = new EncuestaController();
                $controller->cargarRespuestas();
                break;
            case 'apiStats':
                $controller = new DashboardController();
                $controller->apiStats();
                break;
            default:
                header('HTTP/1.0 404 Not Found');
                echo 'Página no encontrada';
        }
    }
}
?>