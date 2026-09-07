(function () {
    "use strict";

    document.documentElement.classList.add("inventario-js-cargado");
    function setModal(modal, open) {
        modal.classList.toggle("inventory-modal--open", open);
        modal.setAttribute("aria-hidden", String(!open));
    }

    function cargarEdicion(modal) {
        var cuerpo = modal.querySelector("[data-edit-url]");
        if (!cuerpo || cuerpo.dataset.cargado === "1" || cuerpo.dataset.cargando === "1") {
            return;
        }
        cuerpo.dataset.cargando = "1";
        fetch(cuerpo.dataset.editUrl, { headers: { "X-Requested-With": "XMLHttpRequest" } })
            .then(function (respuesta) {
                if (!respuesta.ok) throw new Error(respuesta.status);
                return respuesta.text();
            })
            .then(function (html) {
                cuerpo.innerHTML = html;
                cuerpo.dataset.cargado = "1";
            })
            .catch(function () {
                cuerpo.innerHTML =
                    '<p class="errorlist">No se pudo cargar el formulario. Recarga la página e inténtalo otra vez.</p>';
            })
            .then(function () {
                cuerpo.dataset.cargando = "0";
            });
    }

    document.addEventListener("click", function (event) {
        var openButton = event.target.closest("[data-modal-open]");
        if (openButton) {
            var modal = document.getElementById(openButton.getAttribute("data-modal-open"));
            if (modal) {
                if (modal.id.indexOf("editar-") === 0) cargarEdicion(modal);
                setModal(modal, true);
            }
            if (openButton.tagName === "A") event.preventDefault();
            return;
        }

        var closeButton = event.target.closest("[data-modal-close]");
        if (closeButton) {
            var modalToClose = closeButton.closest(".inventory-modal");
            if (modalToClose) setModal(modalToClose, false);
            if (closeButton.tagName === "A") event.preventDefault();
            return;
        }

        if (event.target.classList.contains("inventory-modal")) {
            setModal(event.target, false);
        }
    });

    document.addEventListener("keydown", function (event) {
        if (event.key === "Escape") {
            document.querySelectorAll(".inventory-modal--open").forEach(function (modal) {
                setModal(modal, false);
            });
        }
    });

    var formsetTabla = document.querySelector("[data-formset]");
    if (formsetTabla) {
        var cuerpoFormset = formsetTabla.querySelector("[data-formset-body]");
        var plantillaFormset = document.querySelector("[data-formset-empty]");
        var totalFormsInput = document.getElementById(
            "id_" + formsetTabla.getAttribute("data-formset-prefix") + "-TOTAL_FORMS"
        );

        document.addEventListener("click", function (event) {
            var botonQuitar = event.target.closest("[data-formset-remove]");
            if (!botonQuitar) return;
            event.preventDefault();
            var fila = botonQuitar.closest(".formset-row");
            var checkboxEliminar = fila.querySelector('input[type="checkbox"]');
            if (checkboxEliminar) checkboxEliminar.checked = true;
            fila.hidden = true;

            var filaVacia = document.getElementById("detalle-vacio");
            if (filaVacia) {
                var quedanVisibles = Array.prototype.some.call(
                    cuerpoFormset.querySelectorAll(".formset-row"),
                    function (f) { return !f.hidden; }
                );
                filaVacia.hidden = quedanVisibles;
            }
        });
    }

    var productosDataEl = document.getElementById("productos-disponibles");
    var inputBuscadorNuevo = document.getElementById("buscador-producto-nuevo");
    var modalBuscarProducto = document.getElementById("modal-buscar-producto");
    if (productosDataEl && inputBuscadorNuevo && modalBuscarProducto && formsetTabla) {
        var catalogoProductos = JSON.parse(productosDataEl.textContent);
        var umbralBajoStockEl = document.getElementById("umbral-bajo-stock");
        var umbralBajoStock = umbralBajoStockEl ? parseInt(umbralBajoStockEl.textContent, 10) : 5;
        var DIACRITICOS_PRODUCTO = new RegExp("[\\u0300-\\u036f]", "g");
        var productoElegido = null;

        var inputCantidadNuevo = document.getElementById("cantidad-nueva-linea");
        var inputPrecioNuevo = document.getElementById("precio-nueva-linea");
        var errorNuevaLineaEl = document.getElementById("error-nueva-linea");
        var inputBuscadorModal = document.getElementById("buscador-producto-modal");
        var listaProductosModal = document.getElementById("lista-productos-modal");

        function normalizarProducto(texto) {
            return (texto || "")
                .toLowerCase()
                .normalize("NFD")
                .replace(DIACRITICOS_PRODUCTO, "")
                .trim();
        }

        function idsEnCarrito() {
            var ids = [];
            cuerpoFormset.querySelectorAll(".formset-row").forEach(function (fila) {
                if (fila.hidden) return;
                var oculto = fila.querySelector('input[name$="-producto"]');
                if (oculto && oculto.value) ids.push(oculto.value);
            });
            return ids;
        }

        function mostrarErrorNuevaLinea(mensaje) {
            errorNuevaLineaEl.textContent = mensaje;
            errorNuevaLineaEl.hidden = false;
        }

        function ocultarErrorNuevaLinea() {
            errorNuevaLineaEl.hidden = true;
            errorNuevaLineaEl.textContent = "";
        }

        function renderizarListaModal(termino) {
            var normalizado = normalizarProducto(termino);
            var yaEnCarrito = idsEnCarrito();
            var disponibles = catalogoProductos.filter(function (producto) {
                return (
                    yaEnCarrito.indexOf(String(producto.id_producto)) === -1 &&
                    (!normalizado || normalizarProducto(producto.nombre).indexOf(normalizado) !== -1)
                );
            });

            listaProductosModal.innerHTML = "";
            if (!disponibles.length) {
                var filaVacia = document.createElement("tr");
                filaVacia.innerHTML = '<td colspan="2" class="empty-state">Sin productos que coincidan.</td>';
                listaProductosModal.appendChild(filaVacia);
                return;
            }
            disponibles.forEach(function (producto) {
                var fila = document.createElement("tr");
                fila.className = "modal-producto__fila";
                fila.dataset.id = producto.id_producto;
                fila.dataset.nombre = producto.nombre;

                var celdaNombre = document.createElement("td");
                celdaNombre.textContent = producto.nombre;

                var celdaStock = document.createElement("td");
                celdaStock.className = "modal-producto__col-stock";
                celdaStock.textContent = producto.stock_disponible;
                if (producto.stock_disponible <= umbralBajoStock) {
                    celdaStock.classList.add("modal-producto__stock--bajo");
                }

                fila.appendChild(celdaNombre);
                fila.appendChild(celdaStock);
                listaProductosModal.appendChild(fila);
            });
        }

        function elegirProductoDesdeModal(id, nombre) {
            productoElegido = { id: id, nombre: nombre };
            inputBuscadorNuevo.value = nombre;
            ocultarErrorNuevaLinea();
            setModal(modalBuscarProducto, false);
            inputCantidadNuevo.focus();
        }

        function actualizarSubtotalFila(fila) {
            var cantidad = parseFloat(fila.querySelector('[name$="-cantidad"]').value) || 0;
            var precio = parseFloat(fila.querySelector('[name$="-precio"]').value) || 0;
            fila.querySelector(".detalle-subtotal").textContent = "$" + (cantidad * precio).toFixed(2);
        }

        function agregarLineaAlDetalle() {
            var cantidad = parseInt(inputCantidadNuevo.value, 10);
            var precio = parseFloat(inputPrecioNuevo.value);
            if (!productoElegido) {
                mostrarErrorNuevaLinea("Busca y selecciona un producto de la lista.");
                return;
            }
            if (!cantidad || cantidad < 1) {
                mostrarErrorNuevaLinea("Ingresa una cantidad válida.");
                return;
            }
            if (isNaN(precio) || precio < 0) {
                mostrarErrorNuevaLinea("Ingresa un precio válido.");
                return;
            }

            var indice = parseInt(totalFormsInput.value, 10);
            var html = plantillaFormset.innerHTML.split("__prefix__").join(indice);
            cuerpoFormset.insertAdjacentHTML("beforeend", html);
            totalFormsInput.value = indice + 1;

            var fila = cuerpoFormset.lastElementChild;
            fila.querySelector('input[name$="-producto"]').value = productoElegido.id;
            fila.querySelector('input[name$="-cantidad"]').value = cantidad;
            fila.querySelector('input[name$="-precio"]').value = precio;
            fila.querySelector(".detalle-producto-nombre").textContent = productoElegido.nombre;
            fila.querySelector(".detalle-cantidad-valor").textContent = cantidad;
            fila.querySelector(".detalle-precio-valor").textContent = "$" + precio.toFixed(2);
            actualizarSubtotalFila(fila);

            var filaVaciaDetalle = document.getElementById("detalle-vacio");
            if (filaVaciaDetalle) filaVaciaDetalle.hidden = true;

            productoElegido = null;
            inputBuscadorNuevo.value = "";
            inputCantidadNuevo.value = "";
            inputPrecioNuevo.value = "";
            ocultarErrorNuevaLinea();
        }

        cuerpoFormset.querySelectorAll(".formset-row").forEach(actualizarSubtotalFila);

        inputBuscadorModal.addEventListener("input", function () {
            renderizarListaModal(inputBuscadorModal.value);
        });

        document.addEventListener("click", function (event) {
            if (event.target.closest('[data-modal-open="modal-buscar-producto"]')) {
                inputBuscadorModal.value = "";
                renderizarListaModal("");
                inputBuscadorModal.focus();
                return;
            }
            var filaProducto = event.target.closest(".modal-producto__fila");
            if (filaProducto) {
                elegirProductoDesdeModal(filaProducto.dataset.id, filaProducto.dataset.nombre);
                return;
            }
            if (event.target.closest("[data-agregar-linea]")) {
                agregarLineaAlDetalle();
            }
        });
    }

    var ingresoForm = document.querySelector("[data-ingreso-form]");
    if (ingresoForm) {
        var ingresoChecks = ingresoForm.querySelectorAll("[data-cat-check]");
        var ingresoFilas = Array.prototype.slice.call(
            ingresoForm.querySelectorAll("[data-ingreso-tabla] tbody tr[data-categoria]")
        );
        var ingresoVacio = ingresoForm.querySelector("[data-ingreso-vacio]");
        var ingresoContador = ingresoForm.querySelector("[data-ingreso-contador]");

        var refrescarIngreso = function () {
            var elegidas = {};
            Array.prototype.forEach.call(ingresoChecks, function (cb) {
                if (cb.checked) elegidas[cb.value] = true;
            });
            var hayFiltro = Object.keys(elegidas).length > 0;
            var visibles = 0;
            ingresoFilas.forEach(function (tr) {
                var mostrar = hayFiltro && elegidas[tr.getAttribute("data-categoria")];
                tr.hidden = !mostrar;
                if (mostrar) visibles += 1;
            });
            if (ingresoVacio) {
                ingresoVacio.hidden = visibles > 0;
                var celda = ingresoVacio.querySelector("td");
                if (celda) {
                    celda.textContent = hayFiltro
                        ? "Ninguna de las categorías marcadas tiene productos."
                        : "Marca una categoría arriba para ver sus productos.";
                }
            }
            if (ingresoContador) {
                ingresoContador.textContent =
                    visibles + (visibles === 1 ? " producto visible" : " productos visibles");
            }
        };

        Array.prototype.forEach.call(ingresoChecks, function (cb) {
            cb.addEventListener("change", refrescarIngreso);
        });
        refrescarIngreso();
    }

    var form = document.querySelector(".product-filtros");
    if (!form) return;

    var tbody = form.querySelector("tbody");
    var countEl = document.querySelector(".table-count");
    var encabezados = form.querySelectorAll("thead th");
    var COLS = { nombre: 1, categoria: 2, vehiculo: 3, costo: 4 };
    Array.prototype.forEach.call(encabezados, function (th, indice) {
        var nombre = th.getAttribute("data-col");
        if (nombre) COLS[nombre] = indice;
    });
    var TOTAL_COLUMNAS = encabezados.length || 7;

    var inputs = {
        nombre: form.querySelector('input[name="nombre"]'),
        categoria: form.querySelector('input[name="categoria"]'),
        vehiculo: form.querySelector('input[name="vehiculo"]')
    };

    var filas = Array.prototype.filter.call(tbody.querySelectorAll("tr"), function (tr) {
        return !tr.querySelector(".empty-state");
    });
    if (!filas.length) return;

    var DIACRITICOS = new RegExp("[\\u0300-\\u036f]", "g");

    function normalizar(texto) {
        return (texto || "")
            .toLowerCase()
            .normalize("NFD")
            .replace(DIACRITICOS, "")
            .trim();
    }

    function textoCelda(tr, indice) {
        var celda = tr.children[indice];
        return celda ? celda.textContent : "";
    }

    filas.forEach(function (tr) {
        tr._buscar = {
            nombre: normalizar(textoCelda(tr, COLS.nombre)),
            categoria: normalizar(textoCelda(tr, COLS.categoria)),
            vehiculo: normalizar(textoCelda(tr, COLS.vehiculo))
        };
        var numero = parseFloat(textoCelda(tr, COLS.costo).replace(/[^\d.-]/g, ""));
        tr._costo = isNaN(numero) ? 0 : numero;
    });

    var filaVacia = null;
    function actualizarVacia(visibles) {
        if (visibles > 0) {
            if (filaVacia) filaVacia.hidden = true;
            return;
        }
        if (!filaVacia) {
            filaVacia = document.createElement("tr");
            filaVacia.innerHTML =
                '<td colspan="' + TOTAL_COLUMNAS + '" class="empty-state">Ningún producto coincide con la búsqueda.</td>';
            tbody.appendChild(filaVacia);
        }
        filaVacia.hidden = false;
    }

    var exportLink = document.querySelector("[data-export-url]");

    function actualizarExport() {
        if (!exportLink) return;
        var base = exportLink.getAttribute("data-export-url");
        var params = new URLSearchParams();
        Object.keys(inputs).forEach(function (clave) {
            var valor = inputs[clave] ? inputs[clave].value.trim() : "";
            if (valor) params.set(clave, valor);
        });
        var query = params.toString();
        exportLink.href = query ? base + "?" + query : base;
    }

    function aplicarFiltro() {
        var terminos = {
            nombre: inputs.nombre ? normalizar(inputs.nombre.value) : "",
            categoria: inputs.categoria ? normalizar(inputs.categoria.value) : "",
            vehiculo: inputs.vehiculo ? normalizar(inputs.vehiculo.value) : ""
        };
        var visibles = 0;
        filas.forEach(function (tr) {
            var ok =
                tr._buscar.nombre.indexOf(terminos.nombre) !== -1 &&
                tr._buscar.categoria.indexOf(terminos.categoria) !== -1 &&
                tr._buscar.vehiculo.indexOf(terminos.vehiculo) !== -1;
            tr.hidden = !ok;
            if (ok) visibles += 1;
        });
        if (countEl) {
            countEl.textContent =
                visibles + (visibles === 1 ? " producto encontrado" : " productos encontrados");
        }
        actualizarVacia(visibles);
        actualizarExport();
    }

    var ordenActual = { campo: "nombre", dir: 1 };

    function ordenar(campo, dir) {
        ordenActual = { campo: campo, dir: dir };
        var indice = COLS[campo];
        var numerico = campo === "costo";
        var ordenadas = filas.slice().sort(function (a, b) {
            var r;
            if (numerico) {
                r = a._costo - b._costo;
            } else {
                var av = a._buscar[campo] || normalizar(textoCelda(a, indice));
                var bv = b._buscar[campo] || normalizar(textoCelda(b, indice));
                r = av < bv ? -1 : av > bv ? 1 : 0;
            }
            if (r === 0) {
                r = a._buscar.nombre < b._buscar.nombre ? -1 : a._buscar.nombre > b._buscar.nombre ? 1 : 0;
            }
            return r * dir;
        });
        var frag = document.createDocumentFragment();
        ordenadas.forEach(function (tr) {
            frag.appendChild(tr);
        });
        tbody.appendChild(frag);
        if (filaVacia) tbody.appendChild(filaVacia);
        marcarBotones();
    }

    function marcarBotones() {
        form.querySelectorAll("[data-orden]").forEach(function (btn) {
            var valor = btn.getAttribute("data-orden");
            var dir = valor.charAt(0) === "-" ? -1 : 1;
            var campo = valor.replace("-", "");
            btn.classList.toggle("is-active", campo === ordenActual.campo && dir === ordenActual.dir);
        });
    }

    var activoInicial = form.querySelector("[data-orden].is-active");
    if (activoInicial) {
        var v = activoInicial.getAttribute("data-orden");
        ordenActual = { campo: v.replace("-", ""), dir: v.charAt(0) === "-" ? -1 : 1 };
    }

    Object.keys(inputs).forEach(function (clave) {
        if (inputs[clave]) inputs[clave].addEventListener("input", aplicarFiltro);
    });

    form.addEventListener("submit", function (event) {
        event.preventDefault();
    });

    form.querySelectorAll("[data-orden]").forEach(function (btn) {
        btn.addEventListener("click", function (event) {
            event.preventDefault();
            var valor = btn.getAttribute("data-orden");
            ordenar(valor.replace("-", ""), valor.charAt(0) === "-" ? -1 : 1);
        });
    });

    var limpiar = form.querySelector("[data-limpiar]");
    if (limpiar) {
        limpiar.addEventListener("click", function (event) {
            event.preventDefault();
            Object.keys(inputs).forEach(function (clave) {
                if (inputs[clave]) inputs[clave].value = "";
            });
            aplicarFiltro();
        });
    }
    aplicarFiltro();
})();
