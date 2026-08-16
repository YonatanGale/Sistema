/**
 * ============================================
 * SISTEMA DE ENCUESTAS - MAIN.JS
 * Módulo principal con todas las funcionalidades AJAX
 * ============================================
 */

const EncuestasApp = {
    /**
     * Inicializa la aplicación
     */
    init() {
        this.initDropZone();
        this.initTooltips();
        this.initAjaxForms();
        this.initDataTables();
        this.initBuscadorEncuestas();
        this.initConfirmDialogs();
        this.initModalCargarRespuestas();
        console.log('✅ EncuestasApp inicializado correctamente');
    },

    /**
     * Obtiene el token CSRF de forma segura
     */
    getCsrfToken() {
        // Buscar en input oculto
        let token = document.querySelector('input[name="csrf_token"]')?.value;
        
        // Buscar en meta tag
        if (!token) {
            token = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
        }
        
        return token || '';
    },

    // ============================================
    // DROP ZONE PARA ARCHIVOS
    // ============================================
    initDropZone() {
        const dropZone = document.getElementById('dropZone');
        const fileInput = document.getElementById('archivo');
        const fileInfo = document.getElementById('fileInfo');
        const fileName = document.getElementById('fileName');
        const btnSubir = document.getElementById('btnSubir');

        if (!dropZone) return;

        dropZone.addEventListener('click', () => fileInput?.click());

        dropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropZone.classList.add('dragover');
        });

        dropZone.addEventListener('dragleave', () => {
            dropZone.classList.remove('dragover');
        });

        dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropZone.classList.remove('dragover');
            if (e.dataTransfer.files.length) {
                fileInput.files = e.dataTransfer.files;
                this.mostrarArchivo(e.dataTransfer.files[0], fileInfo, fileName, btnSubir);
            }
        });

        if (fileInput) {
            fileInput.addEventListener('change', (e) => {
                if (e.target.files.length) {
                    this.mostrarArchivo(e.target.files[0], fileInfo, fileName, btnSubir);
                }
            });
        }

        window.limpiarArchivo = () => {
            if (fileInput) {
                fileInput.value = '';
                if (fileInfo) fileInfo.classList.remove('show');
                if (btnSubir) btnSubir.disabled = true;
                const previewContainer = document.getElementById('previewContainer');
                const mappingContainer = document.getElementById('mappingContainer');
                if (previewContainer) previewContainer.classList.remove('show');
                if (mappingContainer) mappingContainer.classList.remove('show');
            }
        };
    },

    mostrarArchivo(file, fileInfo, fileName, btnSubir) {
        const extensiones = ['xlsx', 'xls', 'csv'];
        const ext = file.name.split('.').pop().toLowerCase();

        if (!extensiones.includes(ext)) {
            alert('Formato no permitido. Use .xlsx, .xls o .csv');
            document.getElementById('archivo').value = '';
            return;
        }

        if (fileInfo) {
            fileInfo.classList.add('show');
            fileName.textContent = file.name + ' (' + (file.size / 1024).toFixed(1) + ' KB)';
        }
        if (btnSubir) btnSubir.disabled = false;

        if (typeof window.previsualizarArchivo === 'function') {
            window.previsualizarArchivo(file);
        }
    },

    // ============================================
    // TOOLTIPS
    // ============================================
    initTooltips() {
        const tooltips = document.querySelectorAll('[data-bs-toggle="tooltip"]');
        if (tooltips.length > 0 && typeof bootstrap !== 'undefined') {
            tooltips.forEach(el => new bootstrap.Tooltip(el));
        }
    },

    // ============================================
    // FORMULARIOS AJAX
    // ============================================
    initAjaxForms() {
        const formEditarEncuesta = document.getElementById('editarEncuestaForm');
        if (formEditarEncuesta) {
            formEditarEncuesta.addEventListener('submit', (e) => {
                e.preventDefault();
                this.enviarFormularioAjax(formEditarEncuesta, '/encuesta/' + this.getEncuestaId() + '/editar-ajax');
            });
        }

        const formEditarPregunta = document.getElementById('editarPreguntaForm');
        if (formEditarPregunta) {
            formEditarPregunta.addEventListener('submit', (e) => {
                e.preventDefault();
                this.enviarFormularioAjax(formEditarPregunta, '/pregunta/' + this.getPreguntaId() + '/editar-ajax');
            });
        }

        const formEditarOpciones = document.getElementById('editarOpcionesForm');
        if (formEditarOpciones) {
            formEditarOpciones.addEventListener('submit', (e) => {
                e.preventDefault();
                this.enviarFormularioAjax(formEditarOpciones, '/pregunta/' + this.getPreguntaId() + '/opciones/editar-ajax');
            });
        }

        const formCrearEncuesta = document.getElementById('crearEncuestaForm');
        if (formCrearEncuesta) {
            formCrearEncuesta.addEventListener('submit', (e) => {
                e.preventDefault();
                this.enviarFormularioAjax(formCrearEncuesta, '/crear-encuesta-ajax');
            });
        }

        const formAgregarPregunta = document.getElementById('agregarPreguntaForm');
        if (formAgregarPregunta) {
            formAgregarPregunta.addEventListener('submit', (e) => {
                e.preventDefault();
                this.enviarFormularioAjax(formAgregarPregunta, '/encuesta/' + this.getEncuestaId() + '/agregar-pregunta-ajax');
            });
        }

        const formAgregarOpciones = document.getElementById('agregarOpcionesForm');
        if (formAgregarOpciones) {
            formAgregarOpciones.addEventListener('submit', (e) => {
                e.preventDefault();
                this.enviarFormularioAjax(formAgregarOpciones, '/pregunta/' + this.getPreguntaId() + '/agregar-opciones-ajax');
            });
        }

        const formCargarRespuestas = document.getElementById('cargarRespuestasForm');
        if (formCargarRespuestas) {
            formCargarRespuestas.addEventListener('submit', (e) => {
                e.preventDefault();
                this.enviarFormularioAjax(formCargarRespuestas, '/encuesta/' + this.getEncuestaId() + '/cargar-respuestas-ajax');
            });
        }
    },

    // ============================================
    // ENVÍO DE FORMULARIOS CON AJAX
    // ============================================
    enviarFormularioAjax(form, url) {
        const formData = new FormData(form);
        const btn = form.querySelector('button[type="submit"]');
        const originalText = btn ? btn.innerHTML : '';

        if (btn) {
            btn.disabled = true;
            btn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Procesando...';
        }

        const csrfToken = this.getCsrfToken();

        fetch(url, {
            method: 'POST',
            body: formData,
            headers: {
                'X-CSRFToken': csrfToken
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                this.mostrarMensaje(data.message || '✅ Operación exitosa', 'success');
                if (data.redirect) {
                    setTimeout(() => {
                        window.location.href = data.redirect;
                    }, 1000);
                } else if (data.reload) {
                    setTimeout(() => {
                        location.reload();
                    }, 1000);
                } else if (data.close_modal) {
                    const modal = document.getElementById('modalCargarRespuestas');
                    if (modal) {
                        const bsModal = bootstrap.Modal.getInstance(modal);
                        if (bsModal) bsModal.hide();
                    }
                    setTimeout(() => location.reload(), 500);
                }
            } else {
                this.mostrarMensaje(data.message || '❌ Error al procesar', 'danger');
                if (btn) {
                    btn.disabled = false;
                    btn.innerHTML = originalText;
                }
            }
        })
        .catch(error => {
            console.error('Error:', error);
            this.mostrarMensaje('❌ Error de conexión: ' + error.message, 'danger');
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = originalText;
            }
        });
    },

    // ============================================
    // ELIMINAR CON AJAX
    // ============================================
    eliminarEncuesta(encuestaId) {
        if (confirm('¿Estás seguro de eliminar esta encuesta? Se eliminarán todas las preguntas y respuestas.')) {
            const csrfToken = this.getCsrfToken();

            fetch('/encuesta/' + encuestaId + '/eliminar-ajax', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrfToken,
                    'Content-Type': 'application/json'
                }
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error('Error en el servidor: ' + response.status);
                }
                return response.json();
            })
            .then(data => {
                if (data.success) {
                    this.mostrarMensaje('✅ Encuesta eliminada exitosamente', 'success');
                    const card = document.querySelector(`[data-encuesta-id="${encuestaId}"]`);
                    if (card) {
                        card.remove();
                        const remaining = document.querySelectorAll('[data-encuesta-id]');
                        if (remaining.length === 0) {
                            const container = document.querySelector('.row.g-4');
                            if (container) {
                                container.innerHTML = `
                                    <div class="col-12 text-center py-5">
                                        <i class="bi bi-clipboard-data" style="font-size: 4rem; color: #ccc;"></i>
                                        <h3 class="mt-3">No tienes encuestas creadas</h3>
                                        <p class="text-muted">Comienza creando tu primera encuesta</p>
                                        <a href="/crear-encuesta" class="btn btn-custom btn-custom-primary btn-lg">
                                            <i class="bi bi-plus-circle"></i> Crear Encuesta
                                        </a>
                                    </div>
                                `;
                            }
                        }
                    }
                } else {
                    this.mostrarMensaje(data.message || '❌ Error al eliminar', 'danger');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                this.mostrarMensaje('❌ Error de conexión: ' + error.message, 'danger');
            });
        }
    },

    eliminarPregunta(preguntaId) {
        if (confirm('¿Estás seguro de eliminar esta pregunta?')) {
            const csrfToken = this.getCsrfToken();

            fetch('/pregunta/' + preguntaId + '/eliminar-ajax', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrfToken,
                    'Content-Type': 'application/json'
                }
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error('Error en el servidor: ' + response.status);
                }
                return response.json();
            })
            .then(data => {
                if (data.success) {
                    this.mostrarMensaje('✅ Pregunta eliminada exitosamente', 'success');
                    const item = document.querySelector(`[data-pregunta-id="${preguntaId}"]`);
                    if (item) {
                        item.remove();
                    }
                    setTimeout(() => location.reload(), 1000);
                } else {
                    this.mostrarMensaje(data.message || '❌ Error al eliminar', 'danger');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                this.mostrarMensaje('❌ Error de conexión: ' + error.message, 'danger');
            });
        }
    },

    eliminarRespuestas(encuestaId) {
        if (confirm('¿Estás seguro de eliminar todas las respuestas? Esta acción no se puede deshacer.')) {
            const csrfToken = this.getCsrfToken();

            fetch('/encuesta/' + encuestaId + '/respuestas/eliminar-ajax', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrfToken,
                    'Content-Type': 'application/json'
                }
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error('Error en el servidor: ' + response.status);
                }
                return response.json();
            })
            .then(data => {
                if (data.success) {
                    this.mostrarMensaje('✅ Todas las respuestas han sido eliminadas', 'success');
                    setTimeout(() => location.reload(), 1000);
                } else {
                    this.mostrarMensaje(data.message || '❌ Error al eliminar', 'danger');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                this.mostrarMensaje('❌ Error de conexión: ' + error.message, 'danger');
            });
        }
    },

    // ============================================
    // MODAL PARA CARGAR RESPUESTAS
    // ============================================
    initModalCargarRespuestas() {
        document.querySelectorAll('[data-bs-toggle="modal"][data-bs-target="#modalSeleccionarEncuesta"]').forEach(btn => {
            btn.addEventListener('click', () => {});
        });
    },

    cargarFormularioCarga(encuestaId) {
        const container = document.getElementById('contenidoCargaRespuestas');
        if (!container) return;

        container.innerHTML = `
            <div class="text-center py-4">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Cargando...</span>
                </div>
                <p class="text-muted mt-2">Cargando formulario...</p>
            </div>
        `;

        fetch('/encuesta/' + encuestaId + '/cargar-respuestas-modal')
            .then(response => response.text())
            .then(html => {
                container.innerHTML = html;
                this.initDropZone();
                this.initTooltips();
                const form = document.getElementById('cargarRespuestasForm');
                if (form) {
                    form.addEventListener('submit', (e) => {
                        e.preventDefault();
                        this.enviarFormularioAjax(form, '/encuesta/' + encuestaId + '/cargar-respuestas-ajax');
                    });
                }
                const modalCarga = document.getElementById('modalCargarRespuestas');
                if (modalCarga) {
                    const bsModal = new bootstrap.Modal(modalCarga);
                    bsModal.show();
                }
            })
            .catch(error => {
                console.error('Error:', error);
                container.innerHTML = `
                    <div class="text-center py-4 text-danger">
                        <i class="bi bi-exclamation-triangle" style="font-size: 2rem;"></i>
                        <p class="mt-2">Error al cargar el formulario</p>
                    </div>
                `;
            });
    },

    // ============================================
    // DIÁLOGOS DE CONFIRMACIÓN
    // ============================================
    initConfirmDialogs() {},

    // ============================================
    // MOSTRAR MENSAJES
    // ============================================
    mostrarMensaje(mensaje, tipo = 'info') {
        let container = document.getElementById('mensajes-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'mensajes-container';
            container.style.position = 'fixed';
            container.style.top = '20px';
            container.style.right = '20px';
            container.style.zIndex = '9999';
            container.style.maxWidth = '400px';
            document.body.appendChild(container);
        }

        const alert = document.createElement('div');
        alert.className = `alert alert-${tipo} alert-dismissible fade show`;
        alert.style.boxShadow = '0 4px 12px rgba(0,0,0,0.15)';
        alert.style.marginBottom = '10px';
        alert.innerHTML = `
            ${mensaje}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;
        container.appendChild(alert);

        setTimeout(() => {
            if (alert) {
                alert.classList.remove('show');
                setTimeout(() => alert.remove(), 300);
            }
        }, 5000);
    },

    // ============================================
    // BUSCADOR EN TIEMPO REAL (página seleccionar_encuesta.html)
    // ============================================
    initBuscadorEncuestas() {
        const buscador = document.getElementById('buscador');
        const items = document.querySelectorAll('.encuesta-item');
        const contador = document.getElementById('contador-resultados');
        const sinResultados = document.getElementById('sin-resultados');
        const resultadoBusqueda = document.getElementById('resultado-busqueda');

        if (!buscador) return;

        let timeoutId = null;

        const filtrarEncuestas = () => {
            const termino = buscador.value.toLowerCase().trim();
            let visibles = 0;

            items.forEach(item => {
                const titulo = item.getAttribute('data-titulo');
                if (titulo && (titulo.includes(termino) || termino === '')) {
                    item.style.display = '';
                    visibles++;
                } else {
                    item.style.display = 'none';
                }
            });

            if (sinResultados) {
                if (visibles === 0 && items.length > 0 && termino !== '') {
                    sinResultados.style.display = 'block';
                } else {
                    sinResultados.style.display = 'none';
                }
            }

            if (contador) {
                if (termino) {
                    contador.textContent = `🔍 ${visibles} encuesta${visibles !== 1 ? 's' : ''} encontrada${visibles !== 1 ? 's' : ''}`;
                } else {
                    contador.textContent = `📌 ${visibles} encuesta${visibles !== 1 ? 's' : ''} disponibles`;
                }
            }

            if (resultadoBusqueda) {
                if (termino && visibles > 0) {
                    resultadoBusqueda.textContent = `⏱️ ${visibles} coincidencia${visibles !== 1 ? 's' : ''}`;
                } else if (termino && visibles === 0) {
                    resultadoBusqueda.textContent = '❌ Sin coincidencias';
                } else {
                    resultadoBusqueda.textContent = '';
                }
            }
        };

        buscador.addEventListener('input', function() {
            clearTimeout(timeoutId);
            timeoutId = setTimeout(filtrarEncuestas, 150);
        });

        filtrarEncuestas();

        window.limpiarBusqueda = () => {
            buscador.value = '';
            buscador.dispatchEvent(new Event('input'));
            buscador.focus();
        };
    },

    // ============================================
    // TABLAS RESPONSIVE
    // ============================================
    initDataTables() {
        const tables = document.querySelectorAll('.table-responsive');
        tables.forEach(table => {
            if (!table.classList.contains('table-responsive-custom')) {
                table.classList.add('table-responsive-custom');
            }
        });
    },

    // ============================================
    // UTILIDADES
    // ============================================
    getEncuestaId() {
        const match = window.location.pathname.match(/\/encuesta\/(\d+)\//);
        return match ? match[1] : null;
    },

    getPreguntaId() {
        const match = window.location.pathname.match(/\/pregunta\/(\d+)\//);
        return match ? match[1] : null;
    },

    validateForm(formId) {
        const form = document.getElementById(formId);
        if (!form) return true;

        const inputs = form.querySelectorAll('input[required], select[required]');
        let valid = true;

        inputs.forEach(input => {
            if (!input.value.trim()) {
                input.classList.add('is-invalid');
                valid = false;
            } else {
                input.classList.remove('is-invalid');
            }
        });

        return valid;
    }
};

// ============================================
// INICIALIZACIÓN
// ============================================
document.addEventListener('DOMContentLoaded', () => {
    EncuestasApp.init();
});

// ============================================
// EXPORTAR PARA USO GLOBAL
// ============================================
window.EncuestasApp = EncuestasApp;
window.eliminarEncuesta = (id) => EncuestasApp.eliminarEncuesta(id);
window.eliminarPregunta = (id) => EncuestasApp.eliminarPregunta(id);
window.eliminarRespuestas = (id) => EncuestasApp.eliminarRespuestas(id);
window.limpiarBusqueda = () => EncuestasApp.limpiarBusqueda();