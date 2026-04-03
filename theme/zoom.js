(function () {
  "use strict";

  var STORAGE_KEY = "mdbook-zoom-level";
  var MIN = 0.7;
  var MAX = 1.6;
  var STEP = 0.1;
  var DEFAULT = 1.0;

  function getZoom() {
    try {
      var val = parseFloat(localStorage.getItem(STORAGE_KEY));
      return isNaN(val) ? DEFAULT : Math.min(MAX, Math.max(MIN, val));
    } catch (_) {
      return DEFAULT;
    }
  }

  function setZoom(level) {
    level = Math.round(level * 100) / 100;
    level = Math.min(MAX, Math.max(MIN, level));
    try { localStorage.setItem(STORAGE_KEY, level); } catch (_) {}
    applyZoom(level);
    updateLabel(level);
    return level;
  }

  function applyZoom(level) {
    var content = document.querySelector(".content main");
    if (content) {
      content.style.fontSize = level + "em";
    }
  }

  function updateLabel(level) {
    var label = document.getElementById("zoom-level");
    if (label) {
      label.textContent = Math.round(level * 100) + "%";
    }
  }

  function createControls() {
    var container = document.createElement("div");
    container.id = "zoom-controls";
    container.setAttribute("aria-label", "Zoom controls");

    var btnMinus = document.createElement("button");
    btnMinus.id = "zoom-out";
    btnMinus.textContent = "\u2212";
    btnMinus.title = "Zoom out";
    btnMinus.setAttribute("aria-label", "Zoom out");

    var label = document.createElement("span");
    label.id = "zoom-level";
    label.textContent = "100%";

    var btnPlus = document.createElement("button");
    btnPlus.id = "zoom-in";
    btnPlus.textContent = "+";
    btnPlus.title = "Zoom in";
    btnPlus.setAttribute("aria-label", "Zoom in");

    var btnReset = document.createElement("button");
    btnReset.id = "zoom-reset";
    btnReset.textContent = "\u21BA";
    btnReset.title = "Reset zoom";
    btnReset.setAttribute("aria-label", "Reset zoom");

    container.appendChild(btnMinus);
    container.appendChild(label);
    container.appendChild(btnPlus);
    container.appendChild(btnReset);

    var currentLevel = getZoom();

    btnMinus.addEventListener("click", function () {
      currentLevel = setZoom(currentLevel - STEP);
    });
    btnPlus.addEventListener("click", function () {
      currentLevel = setZoom(currentLevel + STEP);
    });
    btnReset.addEventListener("click", function () {
      currentLevel = setZoom(DEFAULT);
    });

    // Insert into the right-side menu bar icons
    var menuBar = document.querySelector(".right-buttons");
    if (menuBar) {
      menuBar.insertBefore(container, menuBar.firstChild);
    }

    // Apply saved zoom
    applyZoom(currentLevel);
    updateLabel(currentLevel);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", createControls);
  } else {
    createControls();
  }
})();
