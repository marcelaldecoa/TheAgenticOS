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

    var darkVars = {
      primaryColor: "#1a3a30",
      primaryTextColor: "#e0f5ec",
      primaryBorderColor: "#3aaf7a",
      lineColor: "#3aaf7a",
      secondaryColor: "#0f2a20",
      tertiaryColor: "#163028",
      noteBkgColor: "#1a3a30",
      noteTextColor: "#e0f5ec",
      noteBorderColor: "#3aaf7a",
      actorBkg: "#1a3a30",
      actorTextColor: "#e0f5ec",
      actorBorder: "#3aaf7a",
      actorLineColor: "#3aaf7a",
      signalColor: "#e0f5ec",
      signalTextColor: "#e0f5ec",
      labelBoxBkgColor: "#1a3a30",
      labelBoxBorderColor: "#3aaf7a",
      labelTextColor: "#e0f5ec",
      loopTextColor: "#e0f5ec",
      activationBorderColor: "#3aaf7a",
      activationBkgColor: "#1a3a30",
      sequenceNumberColor: "#e0f5ec",
      sectionBkgColor: "#163028",
      altSectionBkgColor: "#0f2a20",
      sectionBkgColor2: "#1a3a30",
      excludeBkgColor: "#0a1a14",
      taskBorderColor: "#3aaf7a",
      taskBkgColor: "#1a3a30",
      taskTextColor: "#e0f5ec",
      taskTextLightColor: "#e0f5ec",
      cScale0: "#1a5740",
      cScale1: "#2a8a6a",
      cScale2: "#3aaf7a",
      cScale3: "#4aff9e",
      fontFamily: "'Segoe UI', system-ui, sans-serif",
      fontSize: "14px"
    };

    var lightVars = {
      primaryColor: "#d1fae5",
      primaryTextColor: "#064e3b",
      primaryBorderColor: "#10b981",
      lineColor: "#10b981",
      secondaryColor: "#ecfdf5",
      tertiaryColor: "#f0fdf4",
      noteBkgColor: "#d1fae5",
      noteTextColor: "#064e3b",
      noteBorderColor: "#10b981",
      actorBkg: "#d1fae5",
      actorTextColor: "#064e3b",
      actorBorder: "#10b981",
      actorLineColor: "#10b981",
      signalColor: "#064e3b",
      signalTextColor: "#064e3b",
      labelBoxBkgColor: "#d1fae5",
      labelBoxBorderColor: "#10b981",
      labelTextColor: "#064e3b",
      loopTextColor: "#064e3b",
      activationBorderColor: "#10b981",
      activationBkgColor: "#d1fae5",
      sequenceNumberColor: "#064e3b",
      fontFamily: "'Segoe UI', system-ui, sans-serif",
      fontSize: "14px"
    };

    window.mermaid.initialize({
      startOnLoad: false,
      theme: isDark ? "dark" : "default",
      themeVariables: isDark ? darkVars : lightVars
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
