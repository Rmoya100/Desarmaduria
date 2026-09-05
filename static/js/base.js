document.addEventListener("DOMContentLoaded", function () {
    // --- Sidebar: abrir/cerrar en mobile ---
    var toggle = document.getElementById("sidebarToggle");
    var sidebar = document.getElementById("sidebar");
    var backdrop = document.getElementById("sidebarBackdrop");

    function closeSidebar() {
        sidebar.classList.remove("sidebar--open");
        backdrop.classList.remove("sidebar-backdrop--visible");
        toggle.setAttribute("aria-expanded", "false");
    }

    function toggleSidebar() {
        var isOpen = sidebar.classList.toggle("sidebar--open");
        backdrop.classList.toggle("sidebar-backdrop--visible", isOpen);
        toggle.setAttribute("aria-expanded", String(isOpen));
    }

    if (toggle && sidebar && backdrop) {
        toggle.addEventListener("click", toggleSidebar);
        backdrop.addEventListener("click", closeSidebar);
    }

    // --- Alertas: cierre manual y auto-cierre a los 5 segundos ---
    document.querySelectorAll(".alert").forEach(function (alertEl) {
        var closeBtn = alertEl.querySelector(".alert__close");
        if (closeBtn) {
            closeBtn.addEventListener("click", function () {
                alertEl.remove();
            });
        }
        setTimeout(function () {
            alertEl.remove();
        }, 5000);
    });
});
