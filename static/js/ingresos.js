/* Formulario de ingreso de inventario.
 *
 * Mejora progresiva: sin JavaScript la pagina muestra el catalogo completo y
 * el formulario funciona igual. Con JavaScript el operador ve solo las piezas
 * de las categorias que marco, puede buscarlas por nombre y ve en vivo cuanto
 * esta ingresando.
 */
(function () {
    "use strict";

    var panel = document.querySelector("[data-piezas]");
    var formulario = document.querySelector("[data-ingreso-form]");
    if (!panel || !formulario) {
        return;
    }

    var categorias = Array.prototype.slice.call(
        formulario.querySelectorAll("[data-categoria]")
    );
    var grupos = Array.prototype.slice.call(panel.querySelectorAll("[data-grupo]"));
    var filas = Array.prototype.slice.call(panel.querySelectorAll("[data-pieza]"));
    var buscador = panel.querySelector("[data-buscar]");
    var limpiar = panel.querySelector("[data-limpiar]");
    var avisoCategorias = panel.querySelector("[data-sin-categorias]");
    var avisoResultados = panel.querySelector("[data-sin-resultados]");
    var tabla = panel.querySelector(".table-scroll");
    var resumen = formulario.querySelector("[data-resumen]");

    // Misma expresion que usa inventario.js: escapes \u para no depender de
    // como se guarde el archivo.
    var DIACRITICOS = new RegExp("[\\u0300-\\u036f]", "g");

    function normalizar(texto) {
        // Sin tildes y en minusculas: "direccion" encuentra "DIRECCIÓN".
        return (texto || "")
            .toString()
            .toLowerCase()
            .normalize("NFD")
            .replace(DIACRITICOS, "")
            .trim();
    }

    function seleccionadas() {
        var marcadas = {};
        categorias.forEach(function (checkbox) {
            if (checkbox.checked) {
                marcadas[checkbox.value] = true;
            }
        });
        return marcadas;
    }

    function cantidadDe(fila) {
        var input = fila.querySelector("[data-cantidad]");
        var valor = parseInt(input && input.value, 10);
        return isNaN(valor) || valor < 0 ? 0 : valor;
    }

    function actualizarResumen() {
        var piezas = 0;
        var unidades = 0;
        filas.forEach(function (fila) {
            var cantidad = cantidadDe(fila);
            if (cantidad > 0) {
                piezas += 1;
                unidades += cantidad;
            }
        });
        if (!resumen) {
            return;
        }
        resumen.textContent = piezas
            ? piezas + (piezas === 1 ? " pieza · " : " piezas · ") + unidades +
              (unidades === 1 ? " unidad" : " unidades")
            : "Sin piezas seleccionadas.";
    }

    function aplicarFiltros() {
        var marcadas = seleccionadas();
        var hayCategorias = Object.keys(marcadas).length > 0;
        var termino = normalizar(buscador ? buscador.value : "");
        var visibles = 0;

        grupos.forEach(function (grupo) {
            var activo = marcadas[grupo.getAttribute("data-grupo")] === true;
            var filasGrupo = Array.prototype.slice.call(
                grupo.querySelectorAll("[data-pieza]")
            );
            var coincidencias = 0;

            filasGrupo.forEach(function (fila) {
                // Se ve si es de la categoria activa O si ya tiene una
                // cantidad anotada: asi lo cargado no desaparece al cambiar
                // de categoria y lo que quedo en cero se oculta.
                var vigente = activo || cantidadDe(fila) > 0;
                var coincide =
                    vigente &&
                    (!termino ||
                        normalizar(fila.getAttribute("data-nombre")).indexOf(termino) !==
                            -1);
                fila.hidden = !coincide;
                if (coincide) {
                    coincidencias += 1;
                }
            });

            grupo.hidden = coincidencias === 0;
            visibles += coincidencias;
        });

        if (avisoCategorias) {
            // Al editar puede haber piezas visibles sin categoria marcada
            // (las que ya trae el ingreso): en ese caso no se muestra el
            // aviso de "elige una categoria".
            avisoCategorias.hidden = hayCategorias || visibles > 0;
        }
        if (avisoResultados) {
            avisoResultados.hidden = (!hayCategorias && !termino) || visibles > 0;
        }
        if (tabla) {
            tabla.hidden = visibles === 0;
        }
    }

    function limpiarGrupo(grupo) {
        Array.prototype.slice
            .call(grupo.querySelectorAll("[data-cantidad]"))
            .forEach(function (input) {
                input.value = "";
            });
    }

    // Se navega de a una categoria: marcar una desmarca las demas. Lo que ya
    // tenga cantidad sigue a la vista aunque su categoria quede sin marcar
    // (ver aplicarFiltros), asi que no hace falta preguntar antes de cambiar.
    categorias.forEach(function (checkbox) {
        checkbox.addEventListener("change", function () {
            if (checkbox.checked) {
                categorias.forEach(function (otro) {
                    if (otro !== checkbox) {
                        otro.checked = false;
                    }
                });
            }
            aplicarFiltros();
            actualizarResumen();
        });
    });

    if (buscador) {
        buscador.addEventListener("input", aplicarFiltros);
        buscador.addEventListener("keydown", function (evento) {
            // Enter en el buscador enviaria el formulario por defecto.
            if (evento.key === "Enter") {
                evento.preventDefault();
            }
        });
    }

    if (limpiar) {
        limpiar.addEventListener("click", function () {
            grupos.forEach(limpiarGrupo);
            aplicarFiltros();
            actualizarResumen();
        });
    }

    panel.addEventListener("input", function (evento) {
        if (evento.target.matches("[data-cantidad]")) {
            actualizarResumen();
        }
    });

    // Al confirmar la cantidad (blur / Enter): si quedo en cero y su categoria
    // no esta activa, la fila se oculta; si quedo > 0 se mantiene aunque
    // cambies de categoria.
    panel.addEventListener("change", function (evento) {
        if (evento.target.matches("[data-cantidad]")) {
            aplicarFiltros();
        }
        if (evento.target.matches("[data-foto-input]")) {
            actualizarBotonFoto(evento.target);
        }
    });

    // Un input de archivo oculto por fila + un boton chico que lo dispara:
    // no se usa el widget completo de camara/galeria de Productos porque acá
    // hay cientos de filas y la mayoria nunca lleva foto.
    function actualizarBotonFoto(input) {
        var celda = input.closest("td");
        var boton = celda && celda.querySelector("[data-foto-abrir]");
        if (!boton) return;
        var tieneArchivo = input.files && input.files.length > 0;
        boton.classList.toggle("is-adjunta", tieneArchivo);
        boton.title = tieneArchivo ? "Foto adjunta: " + input.files[0].name : "Adjuntar foto";
        dibujarMiniatura(celda, tieneArchivo ? input.files[0] : null);
    }

    function dibujarMiniatura(celda, archivo) {
        var contenedor = celda.querySelector("[data-foto-preview]");
        if (!contenedor) return;
        var previa = contenedor.querySelector("img");
        // Sin revoke, cada foto reemplazada deja su blob vivo hasta recargar.
        if (previa) URL.revokeObjectURL(previa.src);
        contenedor.textContent = "";
        if (!archivo) return;

        var imagen = document.createElement("img");
        imagen.src = URL.createObjectURL(archivo);
        imagen.alt = "Vista previa de la foto";
        var quitar = document.createElement("button");
        quitar.type = "button";
        quitar.className = "foto-preview__quitar";
        quitar.setAttribute("data-foto-quitar", "");
        quitar.setAttribute("aria-label", "Quitar foto");
        quitar.textContent = "×";
        contenedor.appendChild(imagen);
        contenedor.appendChild(quitar);
    }

    // --- Hoja "Tomar foto / Elegir de galeria" ----------------------------
    // El atributo `capture` se ajusta antes de disparar el input: con
    // capture=environment el celular abre la camara trasera directo; sin el,
    // muestra el selector del sistema (que incluye la galeria).
    var hoja = formulario.querySelector("[data-foto-sheet]");
    var hojaTitulo = hoja && hoja.querySelector("[data-foto-sheet-titulo]");
    var celdaFotoActiva = null;

    function abrirHoja(boton) {
        celdaFotoActiva = boton.closest("td");
        if (hojaTitulo) {
            hojaTitulo.textContent =
                "Foto de " + (boton.getAttribute("data-pieza-nombre") || "la pieza");
        }
        hoja.hidden = false;
        // Un frame de espera para que la transicion de entrada se vea.
        requestAnimationFrame(function () {
            hoja.classList.add("foto-sheet--abierta");
        });
    }

    function cerrarHoja() {
        hoja.classList.remove("foto-sheet--abierta");
        hoja.hidden = true;
        celdaFotoActiva = null;
    }

    panel.addEventListener("click", function (evento) {
        var quitar = evento.target.closest("[data-foto-quitar]");
        if (quitar) {
            var celdaQuitar = quitar.closest("td");
            var inputQuitar = celdaQuitar.querySelector("[data-foto-input]");
            inputQuitar.value = "";
            actualizarBotonFoto(inputQuitar);
            return;
        }

        var boton = evento.target.closest("[data-foto-abrir]");
        if (!boton) return;
        if (hoja) {
            abrirHoja(boton);
            return;
        }
        // Sin la hoja en el DOM, el boton sigue abriendo el selector del sistema.
        var input = boton.closest("td").querySelector("[data-foto-input]");
        if (input) input.click();
    });

    if (hoja) {
        hoja.addEventListener("click", function (evento) {
            if (evento.target.closest("[data-foto-sheet-cerrar]")) {
                cerrarHoja();
                return;
            }
            var opcion = evento.target.closest("[data-foto-modo]");
            if (!opcion || !celdaFotoActiva) return;
            var input = celdaFotoActiva.querySelector("[data-foto-input]");
            cerrarHoja();
            if (!input) return;
            if (opcion.getAttribute("data-foto-modo") === "camara") {
                input.setAttribute("capture", "environment");
            } else {
                input.removeAttribute("capture");
            }
            input.click();
        });

        document.addEventListener("keydown", function (evento) {
            if (evento.key === "Escape" && !hoja.hidden) cerrarHoja();
        });
    }

    formulario.addEventListener("submit", function () {
        // Son dos: el de la cabecera (asociado por el atributo `form`) y el
        // del pie. Hay que bloquear ambos para evitar el doble envio.
        var botones = document.querySelectorAll(
            '#ingreso-form button[type="submit"], button[form="ingreso-form"]'
        );
        Array.prototype.slice.call(botones).forEach(function (boton) {
            boton.disabled = true;
            boton.textContent = "Guardando…";
        });
    });

    // --- Modal "Agregar piezas" (solo en edicion) -------------------------
    var modal = document.querySelector("[data-modal-agregar]");
    if (modal) {
        var abrirModalBtn = formulario.querySelector("[data-abrir-agregar]");
        var selectCategoria = modal.querySelector("[data-modal-cat]");
        var buscadorModal = modal.querySelector("[data-modal-buscar]");
        var itemsModal = Array.prototype.slice.call(
            modal.querySelectorAll("[data-modal-pieza]")
        );
        var avisoModalVacio = modal.querySelector("[data-modal-vacio]");

        var filtrarModal = function () {
            var cat = selectCategoria.value;
            var termino = normalizar(buscadorModal.value);
            var visibles = 0;
            itemsModal.forEach(function (item) {
                if (item.classList.contains("modal-pieza--agregada")) {
                    item.hidden = true;
                    return;
                }
                var ok =
                    (!cat || item.getAttribute("data-cat") === cat) &&
                    (!termino ||
                        normalizar(item.getAttribute("data-nombre")).indexOf(termino) !== -1);
                item.hidden = !ok;
                if (ok) visibles += 1;
            });
            if (avisoModalVacio) avisoModalVacio.hidden = visibles > 0;
        };

        var abrirModal = function () {
            modal.classList.add("inventory-modal--open");
            modal.setAttribute("aria-hidden", "false");
            filtrarModal();
            buscadorModal.focus();
        };
        var cerrarModal = function () {
            modal.classList.remove("inventory-modal--open");
            modal.setAttribute("aria-hidden", "true");
        };

        if (abrirModalBtn) abrirModalBtn.addEventListener("click", abrirModal);
        modal.addEventListener("click", function (evento) {
            if (evento.target === modal || evento.target.closest("[data-cerrar-agregar]")) {
                cerrarModal();
            }
        });
        selectCategoria.addEventListener("change", filtrarModal);
        buscadorModal.addEventListener("input", filtrarModal);
        buscadorModal.addEventListener("keydown", function (evento) {
            if (evento.key === "Enter") evento.preventDefault();
        });
        document.addEventListener("keydown", function (evento) {
            if (evento.key === "Escape") cerrarModal();
        });

        modal.querySelector("[data-confirmar-agregar]").addEventListener("click", function () {
            var marcados = Array.prototype.slice.call(
                modal.querySelectorAll("[data-agregar-pieza]:checked")
            );
            var primerInput = null;
            marcados.forEach(function (chk) {
                var input = formulario.querySelector(
                    '[name="cantidad_' + chk.value + '"]'
                );
                if (input) {
                    input.value = "1";
                    if (!primerInput) primerInput = input;
                }
                chk.checked = false;
                var item = chk.closest("[data-modal-pieza]");
                if (item) item.classList.add("modal-pieza--agregada");
            });
            cerrarModal();
            aplicarFiltros();
            actualizarResumen();
            if (primerInput) {
                primerInput.scrollIntoView({ block: "center", behavior: "smooth" });
                primerInput.focus();
                primerInput.select();
            }
        });
    }

    aplicarFiltros();
    actualizarResumen();
})();
