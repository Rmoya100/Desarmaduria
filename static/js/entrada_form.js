/* Encadena los <select> del formulario de ingreso (marca -> modelo -> vehiculo
 * -> producto) usando los atributos data-* que renderizan los widgets
 * `_DataAttrSelect` del backend. Tambien maneja el alta/baja de lineas del
 * formset de detalle. Sin llamadas AJAX: todo el catalogo viaja en el HTML.
 */
(function () {
    "use strict";

    var form = document.getElementById("entrada-form");
    if (!form) return;

    var marca = document.getElementById("id_marca");
    var modelo = document.getElementById("id_modelo");
    var vehiculo = document.getElementById("id_vehiculo");
    var body = document.getElementById("detalle-body");
    var tpl = document.getElementById("fila-vacia");
    var prefix = form.dataset.formsetPrefix;
    var totalForms = document.getElementById("id_" + prefix + "-TOTAL_FORMS");

    function filtrar(select, attr, valor) {
        if (!select) return;
        var reset = false;
        Array.prototype.forEach.call(select.options, function (opt) {
            if (opt.value === "") return; // deja el placeholder "---------"
            var ok = !valor || opt.dataset[attr] === String(valor);
            opt.hidden = !ok;
            opt.disabled = !ok;
            if (!ok && opt.selected) reset = true;
        });
        if (reset) select.value = "";
    }

    function productoSelects() {
        return body ? body.querySelectorAll('select[name$="-producto"]') : [];
    }

    function syncProductos() {
        Array.prototype.forEach.call(productoSelects(), function (sel) {
            filtrar(sel, "vehiculo", vehiculo.value);
        });
    }

    function syncVehiculo() {
        filtrar(vehiculo, "modelo", modelo.value);
        syncProductos();
    }

    function syncModelo() {
        filtrar(modelo, "marca", marca.value);
        syncVehiculo();
    }

    if (marca) marca.addEventListener("change", syncModelo);
    if (modelo) modelo.addEventListener("change", syncVehiculo);
    if (vehiculo) vehiculo.addEventListener("change", syncProductos);

    var addBtn = document.getElementById("add-fila");
    if (addBtn && tpl && totalForms) {
        addBtn.addEventListener("click", function () {
            var idx = parseInt(totalForms.value, 10);
            var fila = tpl.content.firstElementChild.cloneNode(true);
            fila.innerHTML = fila.innerHTML.replace(/__prefix__/g, idx);
            body.appendChild(fila);
            totalForms.value = idx + 1;
            filtrar(
                fila.querySelector('select[name$="-producto"]'),
                "vehiculo",
                vehiculo ? vehiculo.value : ""
            );
        });
    }

    // Estado inicial: si el POST fallo la validacion, conserva los filtros.
    if (marca && marca.value) filtrar(modelo, "marca", marca.value);
    if (modelo && modelo.value) filtrar(vehiculo, "modelo", modelo.value);
    if (vehiculo && vehiculo.value) syncProductos();
})();
