<?php
// app/controllers/EncuestaController.php

class EncuestaController {
    
    public function crear() {
        if (!isLoggedIn()) {
            redirect('login');
        }
        
        if ($_SERVER['REQUEST_METHOD'] === 'POST') {
            $titulo = sanitize($_POST['titulo'] ?? '');
            $descripcion = sanitize($_POST['descripcion'] ?? '');
            
            if (empty($titulo)) {
                setFlash('error', 'El título es obligatorio');
                redirect('crear-encuesta');
            }
            
            $conn = getConnection();
            $sql = "INSERT INTO encuestas (titulo, descripcion, usuario_id) VALUES (?, ?, ?)";
            $stmt = $conn->prepare($sql);
            $stmt->execute([$titulo, $descripcion, $_SESSION['usuario_id']]);
            
            $encuestaId = $conn->lastInsertId();
            logAuditoria('crear_encuesta', "Creó la encuesta ID: $encuestaId - $titulo");
            
            setFlash('success', 'Encuesta creada exitosamente');
            redirect('ver-encuesta&id=' . $encuestaId);
        } else {
            require_once __DIR__ . '/../views/encuestas/crear.php';
        }
    }
    
    public function listar() {
        if (!isLoggedIn()) {
            redirect('login');
        }
        
        $conn = getConnection();
        $sql = "SELECT * FROM encuestas WHERE usuario_id = ? ORDER BY created_at DESC";
        $stmt = $conn->prepare($sql);
        $stmt->execute([$_SESSION['usuario_id']]);
        $encuestas = $stmt->fetchAll();
        
        require_once __DIR__ . '/../views/encuestas/listar.php';
    }
    
    public function ver() {
        if (!isLoggedIn()) {
            redirect('login');
        }
        
        $id = $_GET['id'] ?? 0;
        $conn = getConnection();
        
        $sql = "SELECT * FROM encuestas WHERE id = ? AND usuario_id = ?";
        $stmt = $conn->prepare($sql);
        $stmt->execute([$id, $_SESSION['usuario_id']]);
        $encuesta = $stmt->fetch();
        
        if (!$encuesta) {
            setFlash('error', 'Encuesta no encontrada');
            redirect('listar-encuestas');
        }
        
        $sql = "SELECT * FROM preguntas WHERE encuesta_id = ? ORDER BY orden";
        $stmt = $conn->prepare($sql);
        $stmt->execute([$id]);
        $preguntas = $stmt->fetchAll();
        
        require_once __DIR__ . '/../views/encuestas/ver.php';
    }
    
    public function analizar() {
        if (!isLoggedIn()) {
            redirect('login');
        }
        
        $id = $_GET['id'] ?? 0;
        // Aquí irá la lógica de análisis
        require_once __DIR__ . '/../views/encuestas/analisis.php';
    }
    
    public function cargarRespuestas() {
        if (!isLoggedIn()) {
            redirect('login');
        }
        
        if ($_SERVER['REQUEST_METHOD'] === 'POST') {
            $encuestaId = $_POST['encuesta_id'] ?? 0;
            
            if (!isset($_FILES['archivo']) || $_FILES['archivo']['error'] !== UPLOAD_ERR_OK) {
                setFlash('error', 'Error al subir el archivo');
                redirect('ver-encuesta&id=' . $encuestaId);
            }
            
            $result = uploadFile($_FILES['archivo']);
            if (isset($result['error'])) {
                setFlash('error', $result['error']);
                redirect('ver-encuesta&id=' . $encuestaId);
            }
            
            // Aquí va la lógica de procesamiento del archivo
            setFlash('success', 'Archivo cargado exitosamente: ' . $result['filename']);
            redirect('ver-encuesta&id=' . $encuestaId);
        }
    }
}
?>