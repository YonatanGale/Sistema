<?php
if (!isLoggedIn()) {
    redirect('login');
}
$id = $_GET['id'] ?? 0;
?>
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Análisis - <?= APP_NAME ?></title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="<?= url('css/style.css') ?>">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-primary">
        <div class="container">
            <a class="navbar-brand" href="<?= url('home') ?>">📊 <?= APP_NAME ?></a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarNav">
                <ul class="navbar-nav ms-auto">
                    <li class="nav-item">
                        <a class="nav-link" href="<?= url('home') ?>">Dashboard</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link active" href="<?= url('listar-encuestas') ?>">Encuestas</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="<?= url('crear-encuesta') ?>">Nueva Encuesta</a>
                    </li>
                    <li class="nav-item dropdown">
                        <a class="nav-link dropdown-toggle" href="#" id="userDropdown" role="button" data-bs-toggle="dropdown">
                            👤 <?= $_SESSION['usuario_nombre'] ?>
                        </a>
                        <ul class="dropdown-menu dropdown-menu-end">
                            <li><span class="dropdown-item-text">Rol: <?= $_SESSION['rol'] ?></span></li>
                            <li><hr class="dropdown-divider"></li>
                            <li><a class="dropdown-item" href="<?= url('logout') ?>">Cerrar Sesión</a></li>
                        </ul>
                    </li>
                </ul>
            </div>
        </div>
    </nav>

    <div class="container mt-4 fade-in">
        <div class="row">
            <div class="col-12">
                <div class="d-flex justify-content-between align-items-center mb-3">
                    <h1>📊 Análisis de Encuesta #<?= $id ?></h1>
                    <a href="<?= url('ver-encuesta&id=' . $id) ?>" class="btn btn-secondary">← Volver</a>
                </div>

                <div class="row">
                    <div class="col-md-6">
                        <div class="card">
                            <div class="card-header">
                                <h5>Distribución de Sentimientos</h5>
                            </div>
                            <div class="card-body">
                                <canvas id="sentimentChart" height="200"></canvas>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-6">
                        <div class="card">
                            <div class="card-header">
                                <h5>Métricas Clave</h5>
                            </div>
                            <div class="card-body">
                                <div class="row">
                                    <div class="col-6">
                                        <div class="stat-card text-center">
                                            <div class="number text-success">0</div>
                                            <div class="label">Positivos</div>
                                        </div>
                                    </div>
                                    <div class="col-6">
                                        <div class="stat-card text-center">
                                            <div class="number text-danger">0</div>
                                            <div class="label">Negativos</div>
                                        </div>
                                    </div>
                                </div>
                                <div class="row mt-2">
                                    <div class="col-6">
                                        <div class="stat-card text-center">
                                            <div class="number text-warning">0</div>
                                            <div class="label">Neutral</div>
                                        </div>
                                    </div>
                                    <div class="col-6">
                                        <div class="stat-card text-center">
                                            <div class="number text-info">0</div>
                                            <div class="label">Total</div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="card mt-4">
                    <div class="card-header">
                        <h5>Nube de Palabras</h5>
                    </div>
                    <div class="card-body text-center">
                        <p class="text-muted">Los resultados del análisis NLP se mostrarán aquí una vez procesados.</p>
                        <div class="alert alert-info">
                            🚀 Próximamente: Integración con Python para análisis de sentimiento y extracción de temas.
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script src="<?= url('js/main.js') ?>"></script>
    <script>
        // Gráfico de ejemplo
        const ctx = document.getElementById('sentimentChart').getContext('2d');
        new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Positivo', 'Neutral', 'Negativo'],
                datasets: [{
                    data: [0, 0, 0],
                    backgroundColor: ['#28a745', '#ffc107', '#dc3545']
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        position: 'bottom'
                    }
                }
            }
        });
    </script>
</body>
</html>