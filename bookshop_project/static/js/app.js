document.addEventListener("DOMContentLoaded", function () {
    var toggle = document.getElementById("sidebarToggle");
    var sidebar = document.getElementById("sidebar");
    if (toggle && sidebar) {
        toggle.addEventListener("click", function () {
            sidebar.classList.toggle("open");
        });
        document.addEventListener("click", function (e) {
            if (window.innerWidth <= 991 && sidebar.classList.contains("open")) {
                if (!sidebar.contains(e.target) && e.target !== toggle && !toggle.contains(e.target)) {
                    sidebar.classList.remove("open");
                }
            }
        });
    }

    // Activate Bootstrap toasts (auto-hide + dismiss button behaviour).
    document.querySelectorAll(".toast-custom").forEach(function (el) {
        var toast = new bootstrap.Toast(el);
        toast.show();
    });

    // Loading state on form submit: disables the submit button and shows a
    // spinner so users can't double-submit (e.g. double-recording a sale).
    document.querySelectorAll("form").forEach(function (form) {
        form.addEventListener("submit", function () {
            if (form.dataset.skipLoadingState) return;
            var submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn && !submitBtn.classList.contains("is-loading")) {
                submitBtn.dataset.originalText = submitBtn.innerHTML;
                submitBtn.classList.add("is-loading");
                submitBtn.innerHTML = '<span class="btn-spinner"></span>' + submitBtn.textContent.trim();
            }
        });
    });
});
