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
