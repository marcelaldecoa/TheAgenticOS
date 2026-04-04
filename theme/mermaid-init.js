(function () {
  "use strict";

  function loadMermaid() {
    var script = document.createElement("script");
    script.src = "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js";
    script.onload = function () {
      initMermaid();
    };
    document.head.appendChild(script);
  }

  function initMermaid() {
    var isDark = document.documentElement.className.indexOf("navy") !== -1 ||
                 document.documentElement.className.indexOf("coal") !== -1 ||
                 document.documentElement.className.indexOf("ayu") !== -1;

    window.mermaid.initialize({
      startOnLoad: false,
      theme: isDark ? "dark" : "default",
      themeVariables: isDark ? {
        primaryColor: "#1e3a5f",
        primaryTextColor: "#e8f0fe",
        primaryBorderColor: "#4a9eff",
        lineColor: "#4a9eff",
        secondaryColor: "#0f2140",
        tertiaryColor: "#162d50",
        fontFamily: "'Segoe UI', system-ui, sans-serif",
        fontSize: "14px"
      } : {}
    });

    var blocks = document.querySelectorAll("code.language-mermaid");
    var diagrams = [];

    for (var i = 0; i < blocks.length; i++) {
      var code = blocks[i];
      var pre = code.parentElement;
      var container = document.createElement("div");
      container.className = "mermaid";
      container.textContent = code.textContent;
      pre.parentNode.replaceChild(container, pre);
      diagrams.push(container);
    }

    if (diagrams.length > 0) {
      window.mermaid.run({ nodes: diagrams });
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", loadMermaid);
  } else {
    loadMermaid();
  }
})();
