<?php
// app/controllers/AuthController.php

class AuthController {
    
    public function login() {
        if ($_SERVER['REQUEST_METHOD'] === 'POST') {
            $email = $_POST['email'] ?? '';
            $password = $_POST['password'] ?? '';
            
            if (empty($email) || empty($password)) {
                setFlash('error', 'Todos los campos son obligatorios');
                redirect('login');
            }
            
            $conn = getConnection();
            $sql = "SELECT * FROM usuarios WHERE email = ?";
            $stmt = $conn->prepare($sql);
            $stmt->execute([$email]);
            $user = $stmt->fetch();
            
            if ($user && password_verify($password, $user['password'])) {
                $_SESSION['usuario_id'] = $user['id'];
                $_SESSION['usuario_nombre'] = $user['nombre'];
                $_SESSION['usuario_email'] = $user['email'];
                $_SESSION['rol'] = $user['rol'];
                
                logAuditoria('login', 'Inicio de sesión exitoso');
                setFlash('success', 'Bienvenido ' . $user['nombre']);
                redirect('home');
            } else {
                setFlash('error', 'Email o contraseña incorrectos');
                redirect('login');
            }
        } else {
            // Mostrar formulario de login
            require_once '../app/views/auth/login.php';
        }
    }
    
    public function logout() {
        logAuditoria('logout', 'Cierre de sesión');
        session_destroy();
        setFlash('success', 'Has cerrado sesión correctamente');
        redirect('login');
    }
    
    public function registro() {
        if ($_SERVER['REQUEST_METHOD'] === 'POST') {
            $nombre = $_POST['nombre'] ?? '';
            $email = $_POST['email'] ?? '';
            $password = $_POST['password'] ?? '';
            $confirm_password = $_POST['confirm_password'] ?? '';
            
            // Validaciones
            $errores = [];
            if (strlen($nombre) < 3) $errores[] = 'El nombre debe tener al menos 3 caracteres';
            if (!isValidEmail($email)) $errores[] = 'Email inválido';
            if (strlen($password) < 6) $errores[] = 'La contraseña debe tener al menos 6 caracteres';
            if ($password !== $confirm_password) $errores[] = 'Las contraseñas no coinciden';
            
            if (!empty($errores)) {
                setFlash('error', implode('<br>', $errores));
                redirect('registro');
            }
            
            $conn = getConnection();
            
            // Verificar si el email ya existe
            $sql = "SELECT id FROM usuarios WHERE email = ?";
            $stmt = $conn->prepare($sql);
            $stmt->execute([$email]);
            if ($stmt->fetch()) {
                setFlash('error', 'Este email ya está registrado');
                redirect('registro');
            }
            
            // Hash de la contraseña
            $hashedPassword = password_hash($password, PASSWORD_DEFAULT);
            
            // Insertar usuario
            $sql = "INSERT INTO usuarios (nombre, email, password, rol) VALUES (?, ?, ?, 'lector')";
            $stmt = $conn->prepare($sql);
            $stmt->execute([$nombre, $email, $hashedPassword]);
            
            setFlash('success', 'Usuario registrado exitosamente. Ahora puedes iniciar sesión.');
            redirect('login');
        } else {
            require_once '../app/views/auth/registro.php';
        }
    }
}
?>