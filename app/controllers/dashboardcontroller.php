<?php
// app/controllers/DashboardController.php

class DashboardController {
    
    public function index() {
        if (!isLoggedIn()) {
            redirect('login');
        }
        
        require_once __DIR__ . '/../views/dashboard/index.php';
    }
    
    public function apiStats() {
        header('Content-Type: application/json');
        
        if (!isLoggedIn()) {
            echo json_encode(['error' => 'No autorizado']);
            return;
        }
        
        try {
            $conn = getConnection();
            
            $sql = "SELECT COUNT(*) as total FROM encuestas WHERE usuario_id = ?";
            $stmt = $conn->prepare($sql);
            $stmt->execute([$_SESSION['usuario_id']]);
            $totalEncuestas = $stmt->fetch()['total'];
            
            $sql = "SELECT COUNT(*) as total FROM respuestas r 
                    INNER JOIN encuestas e ON r.encuesta_id = e.id 
                    WHERE e.usuario_id = ?";
            $stmt = $conn->prepare($sql);
            $stmt->execute([$_SESSION['usuario_id']]);
            $totalRespuestas = $stmt->fetch()['total'];
            
            $totalUsuarios = 0;
            if (hasRole('admin')) {
                $sql = "SELECT COUNT(*) as total FROM usuarios";
                $stmt = $conn->query($sql);
                $totalUsuarios = $stmt->fetch()['total'];
            }
            
            echo json_encode([
                'total_encuestas' => $totalEncuestas,
                'total_respuestas' => $totalRespuestas,
                'total_usuarios' => $totalUsuarios,
                'success' => true
            ]);
        } catch (Exception $e) {
            echo json_encode(['error' => $e->getMessage()]);
        }
    }
}
?>