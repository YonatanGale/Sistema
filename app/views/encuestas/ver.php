<?php
if (!isLoggedIn()) {
    redirect('login');
}
?>
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ver Encuesta - <?= APP_NAME ?></title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="<?= url('css/style.css') ?>">
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
                    <h1>📄 <?= htmlspecialchars($encuesta['titulo']) ?></h1>
                    <div>
                        <a href="<?= url('listar-encuestas') ?>" class="btn btn-secondary">← Volver</a>
                        <a href="<?= url('analizar-encuesta&id=' . $encuesta['id']) ?>" class="btn btn-success">Analizar</a>
                    </div>
                </div>

                <?php $flash = getFlash(); ?>
                <?php if ($flash): ?>
                    <div class="alert alert-<?= $flash['tipo'] === 'error' ? 'danger' : 'success' ?> alert-dismissible fade show">
                        <?= $flash['mensaje'] ?>
                        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                    </div>
                <?php endif; ?>

                <div class="card mb-4">
                    <div class="card-body">
                        <p><strong>Descripción:</strong> <?= htmlspecialchars($encuesta['descripcion'] ?? 'Sin descripción') ?></p>
                        <p><strong>Creada:</strong> <?= date('d/m/Y H:i', strtotime($encuesta['created_at'])) ?></p>
                        <p><strong>Total de Preguntas:</strong> <?= count($preguntas) ?></p>
                    </div>C:\Users\chuva\AppData\Local\Python\pythoncore-3.14-64\python.exe
                </div>

                <div class="card">
                    <div class="card-header">
                        <h5>📝 Preguntas</h5>
                    </div>
                    <div class="card-body">
                        <?php if (empty($preguntas)): ?>
                            <p class="text-muted text-center">Aún no hay preguntas agregadas a esta encuesta.</p>
                            <div class="text-center">
                                <a href="#" class="btn btn-primary btn-sm">+ Agregar Preguntas</a>
                            </div>
                        <?php else: ?>
                            <ul class="list-group">
                                <?php foreach ($preguntas as $pregunta): ?>
                                    <li class="list-group-item">
                                        <strong>Pregunta <?= $pregunta['orden'] + 1 ?>:</strong>
                                        <?= htmlspecialchars($pregunta['texto']) ?>
                                        <span class="badge bg-secondary float-end"><?= $pregunta['tipo'] ?></span>
                                    </li>
                                <?php endforeach; ?>
                            </ul>
                        <?php endif; ?>
                    </div>
                </div>

                <div class="card mt-4">
                    <div class="card-header">
                        <h5>📤 Cargar Respuestas</h5>
                    </div>
                    <div class="card-body">
                        <form method="POST" action="<?= url('cargar-respuestas') ?>" enctype="multipart/form-data">
                            <input type="hidden" name="encuesta_id" value="<?= $encuesta['id'] ?>">
                            <div class="row">
                                <div class="col-md-8">
                                    <div class="mb-3">
                                        <label for="archivo" class="form-label">Seleccionar archivo</label>
                                        <input type="file" class="form-control" id="archivo" name="archivo" 
                                               accept=".xlsx,.xls,.csv,.txt,.json" required>
                                        <div class="form-text">Formatos soportados: Excel (.xlsx, .xls), CSV, TXT, JSON</div>
                                    </div>
                                </div>
                                <div class="col-md-4 d-flex align-items-end">
                                    <button type="submit" class="btn btn-primary w-100">Cargar Respuestas</button>
                                </div>
                            </div>
                        </form>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script src="<?= url('js/main.js') ?>"></script>
</body>
</html>