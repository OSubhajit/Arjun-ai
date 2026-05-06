/**
 * csrf.js — auto-inject CSRF token into every non-GET fetch request.
 *
 * Loaded synchronously in <head> via base.html so it runs before any
 * other script makes a fetch call. No dependencies.
 */
(function () {
  var _orig = window.fetch;
  window.fetch = function (url, opts) {
    opts   = opts || {};
    var method = (opts.method || "GET").toUpperCase();
    if (method !== "GET" && method !== "HEAD") {
      var meta = document.querySelector("meta[name=csrf-token]");
      if (meta) {
        opts.headers = Object.assign({}, opts.headers || {}, {
          "X-CSRF-Token": meta.content,
        });
      }
    }
    return _orig.call(this, url, opts);
  };
})();
