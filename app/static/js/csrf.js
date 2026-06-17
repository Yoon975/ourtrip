(function () {
  function getCsrfToken() {
    return document.querySelector('meta[name="csrf-token"]')?.content || "";
  }

  window.getCsrfToken = getCsrfToken;

  const originalFetch = window.fetch.bind(window);
  window.fetch = function (input, init) {
    const options = init ? { ...init } : {};
    const method = (options.method || "GET").toUpperCase();
    if (["POST", "PUT", "PATCH", "DELETE"].includes(method)) {
      const headers = new Headers(options.headers || {});
      if (!headers.has("X-CSRF-Token")) {
        headers.set("X-CSRF-Token", getCsrfToken());
      }
      options.headers = headers;
    }
    return originalFetch(input, options);
  };
})();
