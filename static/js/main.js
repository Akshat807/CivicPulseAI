
(function () {
    const loginLinks = document.querySelectorAll(".admin-login-link");

    if (loginLinks.length === 0) {
        return;
    }

    const reduceMotion = window.matchMedia(
        "(prefers-reduced-motion: reduce)"
    );

    loginLinks.forEach(function (link) {
        link.addEventListener("click", function (event) {
            if (
                event.defaultPrevented ||
                event.button !== 0 ||
                event.ctrlKey ||
                event.metaKey ||
                event.shiftKey ||
                event.altKey ||
                link.target === "_blank" ||
                reduceMotion.matches
            ) {
                return;
            }

            event.preventDefault();

            const destination = link.href;
            document.body.classList.add("page-leaving");

            window.setTimeout(function () {
                window.location.assign(destination);
            }, 320);
        });
    });
})();
