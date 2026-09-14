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

    function actualizarResumenFoto(contenedor) {
        var inputs = contenedor.querySelectorAll('input[type="file"]');
        var resumen = contenedor.querySelector("[data-foto-resumen]");
        var botonQuitar = contenedor.querySelector("[data-foto-quitar]");
        var maxFotos = parseInt(contenedor.getAttribute("data-max-fotos"), 10) || null;
        var total = 0;
        inputs.forEach(function (input) { total += input.files ? input.files.length : 0; });

        if (total === 0) {
            resumen.hidden = true;
            botonQuitar.hidden = true;
            return;
        }
        var texto = total === 1 ? "Se agregará 1 foto nueva." : "Se agregarán " + total + " fotos nuevas.";
        if (maxFotos && total > maxFotos) {
            texto += " El máximo permitido es " + maxFotos + "; el servidor rechazará el resto.";
        }
        resumen.textContent = texto;
        resumen.hidden = false;
        botonQuitar.hidden = false;
    }

    document.addEventListener("change", function (event) {
        if (event.target.type !== "file") return;
        var contenedor = event.target.closest("[data-foto-input]");
        if (contenedor) actualizarResumenFoto(contenedor);
    });

    document.addEventListener("click", function (event) {
        var botonAbrir = event.target.closest("[data-foto-abrir]");
        if (botonAbrir) {
            var contenedorAbrir = botonAbrir.closest("[data-foto-input]");
            var rol = botonAbrir.getAttribute("data-foto-abrir");
            var input = contenedorAbrir && contenedorAbrir.querySelector('[data-foto-rol="' + rol + '"]');
            if (input) input.click();
            return;
        }
        var botonQuitar = event.target.closest("[data-foto-quitar]");
        if (botonQuitar) {
            var contenedorQuitar = botonQuitar.closest("[data-foto-input]");
            if (contenedorQuitar) {
                contenedorQuitar.querySelectorAll('input[type="file"]').forEach(function (input) { input.value = ""; });
                actualizarResumenFoto(contenedorQuitar);
            }
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
            actualizarResumenVenta();
        });
    }

    // El neto de IVA sale siempre del detalle de productos (cantidad*precio
    // de cada linea visible), nunca de un monto tipeado aparte: se
    // recalcula cada vez que se agrega/quita una linea o cambia la forma de
    // pago. Es solo vista previa -el calculo real y guardado lo hace
    // Venta.actualizar_montos() en el servidor, despues de guardar el
    // formset-.
    var formaPagoSelect = document.getElementById("id_forma_pago");
    var formasPagoIvaEl = document.getElementById("formas-pago-iva");
    var resumenIva = document.getElementById("resumen-iva");
    var resumenNetoValor = document.getElementById("resumen-neto-valor");
    var resumenIvaValor = document.getElementById("resumen-iva-valor");
    var resumenTotalValor = document.getElementById("resumen-total-valor");
    var formasPagoIva = formasPagoIvaEl ? JSON.parse(formasPagoIvaEl.textContent) : {};

    function formatearCLP(valor) {
        return "$" + Math.round(valor).toLocaleString("es-CL");
    }

    function actualizarResumenVenta() {
        if (!formaPagoSelect || !resumenIva || !cuerpoFormset) return;
        var activa = !!formasPagoIva[formaPagoSelect.value];
        resumenIva.hidden = !activa;
        if (!activa) return;
        var neto = 0;
        cuerpoFormset.querySelectorAll(".formset-row").forEach(function (fila) {
            if (fila.hidden) return;
            var cantidad = parseFloat(fila.querySelector('[name$="-cantidad"]').value) || 0;
            var precio = parseFloat(fila.querySelector('[name$="-precio"]').value) || 0;
            neto += cantidad * precio;
        });
        var iva = neto * 0.19;
        resumenNetoValor.textContent = formatearCLP(neto);
        resumenIvaValor.textContent = formatearCLP(iva);
        resumenTotalValor.textContent = formatearCLP(neto + iva);
    }

    if (formaPagoSelect) {
        formaPagoSelect.addEventListener("change", actualizarResumenVenta);
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
        var precioEstimadoNuevaLineaEl = document.getElementById("precio-estimado-nueva-linea");
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
                    (!normalizado ||
                        normalizarProducto(producto.nombre).indexOf(normalizado) !== -1 ||
                        normalizarProducto(producto.vehiculo).indexOf(normalizado) !== -1)
                );
            });

            listaProductosModal.innerHTML = "";
            if (!disponibles.length) {
                var filaVacia = document.createElement("tr");
                filaVacia.innerHTML = '<td colspan="4" class="empty-state">Sin productos que coincidan.</td>';
                listaProductosModal.appendChild(filaVacia);
                return;
            }
            disponibles.forEach(function (producto) {
                var fila = document.createElement("tr");
                fila.className = "modal-producto__fila";
                fila.dataset.id = producto.id_producto;
                fila.dataset.nombre = producto.nombre;
                fila.dataset.vehiculo = producto.vehiculo || "";
                fila.dataset.precio = producto.precio_venta != null ? producto.precio_venta : "";

                var celdaNombre = document.createElement("td");
                celdaNombre.textContent = producto.nombre;

                var celdaVehiculo = document.createElement("td");
                celdaVehiculo.className = "modal-producto__col-vehiculo";
                celdaVehiculo.textContent = producto.vehiculo || "Sin vehículo (plantilla)";

                var celdaPrecio = document.createElement("td");
                celdaPrecio.className = "modal-producto__col-precio";
                celdaPrecio.textContent = textoPrecioEstimado(producto.precio_venta);

                var celdaStock = document.createElement("td");
                celdaStock.className = "modal-producto__col-stock";
                celdaStock.textContent = producto.stock_disponible;
                if (producto.stock_disponible <= umbralBajoStock) {
                    celdaStock.classList.add("modal-producto__stock--bajo");
                }

                fila.appendChild(celdaNombre);
                fila.appendChild(celdaVehiculo);
                fila.appendChild(celdaPrecio);
                fila.appendChild(celdaStock);
                listaProductosModal.appendChild(fila);
            });
        }

        // `precio_venta` viaja como string ("15000.00") porque DjangoJSONEncoder
        // serializa los Decimal asi; puede venir null si el producto no tiene
        // precio estimado cargado.
        function textoPrecioEstimado(precioVenta) {
            if (precioVenta == null || precioVenta === "") return "Sin precio";
            return formatearCLP(parseFloat(precioVenta));
        }

        function elegirProductoDesdeModal(id, nombre, vehiculo, precioVenta) {
            var precio = precioVenta != null && precioVenta !== "" ? parseFloat(precioVenta) : null;
            productoElegido = { id: id, nombre: nombre, vehiculo: vehiculo, precioVenta: precio };
            inputBuscadorNuevo.value = vehiculo ? nombre + " · " + vehiculo : nombre;
            if (precioEstimadoNuevaLineaEl) {
                precioEstimadoNuevaLineaEl.textContent =
                    "Precio estimado: " + textoPrecioEstimado(precioVenta);
            }
            ocultarErrorNuevaLinea();
            setModal(modalBuscarProducto, false);
            inputCantidadNuevo.focus();
        }

        function actualizarSubtotalFila(fila) {
            var cantidad = parseFloat(fila.querySelector('[name$="-cantidad"]').value) || 0;
            var precio = parseFloat(fila.querySelector('[name$="-precio"]').value) || 0;
            fila.querySelector(".detalle-subtotal").textContent = formatearCLP(cantidad * precio);
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
            fila.querySelector(".detalle-producto-nombre").textContent = productoElegido.vehiculo
                ? productoElegido.nombre + " · " + productoElegido.vehiculo
                : productoElegido.nombre;
            fila.querySelector(".detalle-cantidad-valor").textContent = cantidad;
            fila.querySelector(".detalle-precio-estimado-valor").textContent =
                productoElegido.precioVenta != null ? formatearCLP(productoElegido.precioVenta) : "—";
            fila.querySelector(".detalle-precio-valor").textContent = formatearCLP(precio);
            actualizarSubtotalFila(fila);
            actualizarResumenVenta();

            var filaVaciaDetalle = document.getElementById("detalle-vacio");
            if (filaVaciaDetalle) filaVaciaDetalle.hidden = true;

            productoElegido = null;
            inputBuscadorNuevo.value = "";
            inputCantidadNuevo.value = "";
            inputPrecioNuevo.value = "";
            if (precioEstimadoNuevaLineaEl) precioEstimadoNuevaLineaEl.textContent = "";
            ocultarErrorNuevaLinea();
        }

        cuerpoFormset.querySelectorAll(".formset-row").forEach(actualizarSubtotalFila);
        actualizarResumenVenta();

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
                elegirProductoDesdeModal(
                    filaProducto.dataset.id,
                    filaProducto.dataset.nombre,
                    filaProducto.dataset.vehiculo,
                    filaProducto.dataset.precio
                );
                return;
            }
            if (event.target.closest("[data-agregar-linea]")) {
                agregarLineaAlDetalle();
            }
        });
    }

    // Pantalla unica de Inventario (Existencias + Valorizado fusionados):
    // filtro por categoria/marca/modelo, orden por columna y paginacion,
    // todo instantaneo sobre las filas ya renderizadas. Va en su propio
    // IIFE (no dentro del bloque de `.product-filtros` de abajo) para que
    // corra igual en esta pagina, donde ese otro formulario no existe.
    (function inicializarInventarioUnificado() {
        var form = document.querySelector(".inventario-filtros");
        if (!form) return;

        var tabla = form.querySelector(".inventario-tabla");
        var tbody = tabla.querySelector("tbody");
        var countEl = form.querySelector(".table-count");
        var encabezados = tabla.querySelectorAll("thead th");
        var COLS = {};
        Array.prototype.forEach.call(encabezados, function (th, indice) {
            var nombre = th.getAttribute("data-col");
            if (nombre) COLS[nombre] = indice;
        });
        var TOTAL_COLUMNAS = encabezados.length || 8;

        // Los valores crudos (ids de categoria/marca/modelo, cantidades y el
        // valor en stock) viajan aparte via json_script: el texto de las
        // celdas ya esta formateado ($ con puntos de miles) y parsearlo de
        // vuelta es fragil (ver nota de "costo" mas abajo, en el bloque de
        // Productos).
        var datosEl = document.getElementById("inventario-datos");
        var datosPorId = {};
        if (datosEl) {
            JSON.parse(datosEl.textContent).forEach(function (item) {
                datosPorId[item.id] = item;
            });
        }

        var selects = {
            categoria: form.querySelector('select[name="categoria"]'),
            marca: form.querySelector('select[name="marca"]'),
            modelo: form.querySelector('select[name="modelo"]')
        };

        var filas = Array.prototype.filter.call(tbody.querySelectorAll("tr"), function (tr) {
            return tr.hasAttribute("data-id");
        });
        if (!filas.length) return;

        var DIACRITICOS_INV = new RegExp("[\\u0300-\\u036f]", "g");
        function normalizarInv(texto) {
            return (texto || "").toLowerCase().normalize("NFD").replace(DIACRITICOS_INV, "").trim();
        }
        function textoCeldaInv(tr, indice) {
            var celda = tr.children[indice];
            return celda ? celda.textContent : "";
        }

        filas.forEach(function (tr) {
            tr._datos = datosPorId[tr.getAttribute("data-id")] || {};
            tr._buscar = {
                nombre: normalizarInv(textoCeldaInv(tr, COLS.nombre)),
                categoria: normalizarInv(textoCeldaInv(tr, COLS.categoria))
            };
        });

        var filaVacia = null;
        function actualizarVacia(cantidadVisible) {
            if (cantidadVisible > 0) {
                if (filaVacia) filaVacia.hidden = true;
                return;
            }
            if (!filaVacia) {
                filaVacia = document.createElement("tr");
                filaVacia.innerHTML =
                    '<td colspan="' + TOTAL_COLUMNAS + '" class="empty-state">Ningún producto coincide con los filtros.</td>';
                tbody.appendChild(filaVacia);
            }
            filaVacia.hidden = false;
        }

        var tarjetas = {
            disponibles: document.querySelector('[data-metric="disponibles"]'),
            con_stock: document.querySelector('[data-metric="con_stock"]'),
            vendidas: document.querySelector('[data-metric="vendidas"]'),
            valor: document.querySelector('[data-metric="valor"]')
        };

        function actualizarTarjetas(visibles) {
            var disponibles = 0, conStock = 0, vendidas = 0, valor = 0;
            visibles.forEach(function (tr) {
                var d = tr._datos;
                disponibles += d.disponible || 0;
                if ((d.disponible || 0) > 0) conStock += 1;
                vendidas += d.vendidas || 0;
                valor += parseFloat(d.valor) || 0;
            });
            if (tarjetas.disponibles) tarjetas.disponibles.textContent = String(disponibles);
            if (tarjetas.con_stock) tarjetas.con_stock.textContent = String(conStock);
            if (tarjetas.vendidas) tarjetas.vendidas.textContent = String(vendidas);
            if (tarjetas.valor) tarjetas.valor.textContent = formatearCLP(valor);
        }

        var pager = form.querySelector("[data-pager]");
        var pagerTam = form.querySelector("[data-pager-tamano]");
        var pagerInfo = form.querySelector("[data-pager-info]");
        var pagerAnterior = form.querySelector("[data-pager-anterior]");
        var pagerSiguiente = form.querySelector("[data-pager-siguiente]");
        var paginaActual = 1;

        function aplicarPaginacion(visibles) {
            if (!pager) return;
            pager.hidden = visibles.length === 0;
            var tam = pagerTam ? (parseInt(pagerTam.value, 10) || 10) : 10;
            var totalPaginas = Math.max(1, Math.ceil(visibles.length / tam));
            if (paginaActual > totalPaginas) paginaActual = totalPaginas;
            if (paginaActual < 1) paginaActual = 1;
            var inicio = (paginaActual - 1) * tam;
            visibles.forEach(function (tr, indice) {
                tr.hidden = indice < inicio || indice >= inicio + tam;
            });
            if (pagerInfo) pagerInfo.textContent = "Página " + paginaActual + " de " + totalPaginas;
            if (pagerAnterior) pagerAnterior.disabled = paginaActual <= 1;
            if (pagerSiguiente) pagerSiguiente.disabled = paginaActual >= totalPaginas;
        }

        function actualizarVista() {
            var visibles = [];
            filas.forEach(function (tr) {
                tr.hidden = !tr._coincide;
                if (tr._coincide) visibles.push(tr);
            });
            if (countEl) {
                countEl.textContent = visibles.length + (visibles.length === 1 ? " producto" : " productos");
            }
            actualizarTarjetas(visibles);
            aplicarPaginacion(visibles);
            actualizarVacia(visibles.length);
        }

        function aplicarFiltro() {
            var catSel = selects.categoria ? selects.categoria.value : "";
            var marcaSel = selects.marca ? selects.marca.value : "";
            var modeloSel = selects.modelo ? selects.modelo.value : "";
            filas.forEach(function (tr) {
                var d = tr._datos;
                var ok = true;
                if (catSel && String(d.categoria) !== catSel) ok = false;
                if (ok && marcaSel && String(d.marca) !== marcaSel) ok = false;
                if (ok && modeloSel && String(d.modelo) !== modeloSel) ok = false;
                tr._coincide = ok;
            });
            paginaActual = 1;
            actualizarVista();
        }

        var ordenActual = { campo: "nombre", dir: 1 };

        function valorOrdenInv(tr, campo) {
            if (campo === "disponible") return tr._datos.disponible || 0;
            if (campo === "valor") return parseFloat(tr._datos.valor) || 0;
            if (campo === "categoria") return tr._buscar.categoria;
            return tr._buscar.nombre;
        }

        function ordenar(campo, dir) {
            ordenActual = { campo: campo, dir: dir };
            var numerico = campo === "disponible" || campo === "valor";
            filas.sort(function (a, b) {
                var av = valorOrdenInv(a, campo);
                var bv = valorOrdenInv(b, campo);
                var r = numerico ? av - bv : av < bv ? -1 : av > bv ? 1 : 0;
                if (r === 0) {
                    r = a._buscar.nombre < b._buscar.nombre ? -1 : a._buscar.nombre > b._buscar.nombre ? 1 : 0;
                }
                return r * dir;
            });
            var frag = document.createDocumentFragment();
            filas.forEach(function (tr) { frag.appendChild(tr); });
            tbody.appendChild(frag);
            if (filaVacia) tbody.appendChild(filaVacia);
            marcarBotones();
            paginaActual = 1;
            actualizarVista();
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

        Object.keys(selects).forEach(function (clave) {
            if (selects[clave]) selects[clave].addEventListener("change", aplicarFiltro);
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
                Object.keys(selects).forEach(function (clave) {
                    if (selects[clave]) selects[clave].value = "";
                });
                aplicarFiltro();
            });
        }

        if (pagerTam) {
            pagerTam.addEventListener("change", function () {
                paginaActual = 1;
                actualizarVista();
            });
        }
        if (pagerAnterior) {
            pagerAnterior.addEventListener("click", function () {
                paginaActual -= 1;
                actualizarVista();
            });
        }
        if (pagerSiguiente) {
            pagerSiguiente.addEventListener("click", function () {
                paginaActual += 1;
                actualizarVista();
            });
        }

        aplicarFiltro();
    })();

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
