<?php
// Verificar si el usuario está logueado
if (!isLoggedIn()) {
    redirect('login');
}
?>
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard - Encuestas Platform</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="/Sistema/public/css/style.css">
</head>
<body>
    <!-- Navbar -->
    <nav class="navbar navbar-expand-lg navbar-dark bg-primary">
        <div class="container">
            <a class="navbar-brand" href="/Sistema/public/home">📊 Encuestas Platform</a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarNav">
                <ul class="navbar-nav ms-auto">
                    <li class="nav-item">
                        <a class="nav-link active" href="/Sistema/public/home">Dashboard</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="/Sistema/public/listar-encuestas">Encuestas</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="/Sistema/public/crear-encuesta">Nueva Encuesta</a>
                    </li>
                    <li class="nav-item dropdown">
                        <a class="nav-link dropdown-toggle" href="#" id="userDropdown" role="button" data-bs-toggle="dropdown">
                            👤 <?= $_SESSION['usuario_nombre'] ?>
                        </a>
                        <ul class="dropdown-menu dropdown-menu-end">
                            <li><span class="dropdown-item-text">Rol: <?= $_SESSION['rol'] ?></span></li>
                            <li><hr class="dropdown-divider"></li>
                            <li><a class="dropdown-item" href="/Sistema/public/logout">Cerrar Sesión</a></li>
                        </ul>
                    </li>
                </ul>
            </div>
        </div>
    </nav>

    <!-- Contenido Principal -->
    <div class="container mt-4 fade-in">
        <div class="row">
            <div class="col-12">
                <h1 class="display-4">Bienvenido, <?= $_SESSION['usuario_nombre'] ?> 👋</h1>
                <p class="text-muted">Panel de control de tu plataforma de análisis de encuestas</p>
                
                <!-- Estadísticas Rápidas -->
                <div class="row mt-4">
                    <div class="col-md-3">
                        <div class="stat-card text-center">
                            <div class="number" id="totalEncuestas">0</div>
                            <div class="label">Total Encuestas</div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="stat-card text-center">
                            <div class="number" id="totalRespuestas">0</div>
                            <div class="label">Total Respuestas</div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="stat-card text-center">
                            <div class="number" id="totalUsuarios">0</div>
                            <div class="label">Usuarios Registrados</div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="stat-card text-center">
                            <div class="number" id="tasaAnalisis">0%</div>
                            <div class="label">Tasa de Análisis</div>
                        </div>
                    </div>
                </div>

                <!-- Acciones Rápidas -->
                <div class="row mt-4">
                    <div class="col-md-6">
                        <div class="card">
                            <div class="card-body">
                                <h5 class="card-title">🚀 Acciones Rápidas</h5>
                                <div class="d-grid gap-2">
                                    <a href="/Sistema/public/crear-encuesta" class="btn btn-primary">
                                        📝 Crear Nueva Encuesta
                                    </a>
                                    <a href="/Sistema/public/listar-encuestas" class="btn btn-outline-primary">
                                        📋 Ver Mis Encuestas
                                    </a>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-6">
                        <div class="card">
                            <div class="card-body">
                                <h5 class="card-title">📊 Próximos Pasos</h5>
                                <p>1. Crea una encuesta</p>
                                <p>2. Carga las respuestas</p>
                                <p>3. Analiza los resultados</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script src="/Sistema/public/js/main.js"></script>
    <script>
        // Cargar estadísticas vía AJAX
        fetch('/Sistema/api/stats.php')
            .then(response => response.json())
            .then(data => {
                document.getElementById('totalEncuestas').textContent = data.total_encuestas || 0;
                document.getElementById('totalRespuestas').textContent = data.total_respuestas || 0;
                document.getElementById('totalUsuarios').textContent = data.total_usuarios || 0;
            })
            .catch(error => console.error('Error:', error));
    </script>
</body>
</html>