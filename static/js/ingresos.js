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
    });

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

    aplicarFiltros();
    actualizarResumen();
})();
