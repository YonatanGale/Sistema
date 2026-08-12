<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Login - <?= APP_NAME ?></title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="<?= url('css/style.css') ?>">
</head>
<body class="bg-light">
    <div class="container">
        <div class="row justify-content-center mt-5">
            <div class="col-md-6 col-lg-4">
                <div class="card shadow">
                    <div class="card-body">
                        <h2 class="text-center mb-4">🔐 <?= APP_NAME ?></h2>
                        
                        <?php $flash = getFlash(); ?>
                        <?php if ($flash): ?>
                            <div class="alert alert-<?= $flash['tipo'] === 'error' ? 'danger' : 'success' ?> alert-dismissible fade show">
                                <?= $flash['mensaje'] ?>
                                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                            </div>
                        <?php endif; ?>
                        
                        <form method="POST" action="<?= url('login') ?>">
                            <div class="mb-3">
                                <label for="email" class="form-label">Email</label>
                                <input type="email" class="form-control" id="email" name="email" required>
                            </div>
                            <div class="mb-3">
                                <label for="password" class="form-label">Contraseña</label>
                                <input type="password" class="form-control" id="password" name="password" required>
                            </div>
                            <button type="submit" class="btn btn-primary w-100">Iniciar Sesión</button>
                        </form>
                        <div class="text-center mt-3">
                            <a href="<?= url('registro') ?>">¿No tienes cuenta? Regístrate</a>
                        </div>
                        <div class="text-center mt-2">
                            <small class="text-muted">Admin: admin@encuestas.com / admin123</small>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script src="<?= url('js/main.js') ?>"></script>
</body>
</html>