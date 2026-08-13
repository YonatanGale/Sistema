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
    <title>Mis Encuestas - <?= APP_NAME ?></title>
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
                    <h1>📋 Mis Encuestas</h1>
                    <a href="<?= url('crear-encuesta') ?>" class="btn btn-primary">+ Nueva Encuesta</a>
                </div>

                <?php $flash = getFlash(); ?>
                <?php if ($flash): ?>
                    <div class="alert alert-<?= $flash['tipo'] === 'error' ? 'danger' : 'success' ?> alert-dismissible fade show">
                        <?= $flash['mensaje'] ?>
                        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                    </div>
                <?php endif; ?>

                <div class="table-container">
                    <table class="table table-hover">
                        <thead>
                            <tr>
                                <th>ID</th>
                                <th>Título</th>
                                <th>Descripción</th>
                                <th>Fecha</th>
                                <th>Acciones</th>
                            </tr>
                        </thead>
                        <tbody>
                            <?php if (empty($encuestas)): ?>
                                <tr>
                                    <td colspan="5" class="text-center text-muted">
                                        No tienes encuestas creadas. <a href="<?= url('crear-encuesta') ?>">Crea una ahora</a>
                                    </td>
                                </tr>
                            <?php else: ?>
                                <?php foreach ($encuestas as $encuesta): ?>
                                    <tr>
                                        <td>#<?= $encuesta['id'] ?></td>
                                        <td><strong><?= htmlspecialchars($encuesta['titulo']) ?></strong></td>
                                        <td><?= htmlspecialchars(substr($encuesta['descripcion'] ?? '', 0, 50)) ?>...</td>
                                        <td><?= date('d/m/Y', strtotime($encuesta['created_at'])) ?></td>
                                        <td>
                                            <div class="btn-group btn-group-sm">
                                                <a href="<?= url('ver-encuesta&id=' . $encuesta['id']) ?>" class="btn btn-primary">Ver</a>
                                                <a href="<?= url('analizar-encuesta&id=' . $encuesta['id']) ?>" class="btn btn-success">Analizar</a>
                                            </div>
                                        </td>
                                    </tr>
                                <?php endforeach; ?>
                            <?php endif; ?>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script src="<?= url('js/main.js') ?>"></script>
</body>
</html>