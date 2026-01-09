(() => {
  const MAX_SCALE = 2;

  const getFilename = (btn) => {
    const preset = btn.getAttribute("data-screenshot-name");
    if (preset) {
      return preset;
    }
    const ts = new Date().toISOString().replace(/[:.]/g, "-");
    return `screenshot-${ts}.png`;
  };

  const resolveTarget = (btn) => {
    const selector = btn.getAttribute("data-screenshot-target");
    if (!selector) {
      return document.body;
    }
    return document.querySelector(selector) || document.body;
  };

  const captureScreenshot = async (btn) => {
    if (typeof window.html2canvas !== "function") {
      alert("Screenshot library not available.");
      return;
    }

    const target = resolveTarget(btn);
    const filename = getFilename(btn);
    const originalHtml = btn.getAttribute("data-screenshot-original") || btn.innerHTML;
    btn.setAttribute("data-screenshot-original", originalHtml);

    btn.disabled = true;
    btn.textContent = "Saving...";

    try {
      const scale = Math.min(window.devicePixelRatio || 1, MAX_SCALE);
      const canvas = await window.html2canvas(target, {
        backgroundColor: "#ffffff",
        useCORS: true,
        scale,
        scrollX: -window.scrollX,
        scrollY: -window.scrollY,
        windowWidth: document.documentElement.scrollWidth,
        windowHeight: document.documentElement.scrollHeight,
      });

      if (canvas.toBlob) {
        canvas.toBlob((blob) => {
          if (!blob) {
            return;
          }
          const url = URL.createObjectURL(blob);
          const link = document.createElement("a");
          link.href = url;
          link.download = filename;
          link.click();
          setTimeout(() => URL.revokeObjectURL(url), 1000);
        }, "image/png");
      } else {
        const link = document.createElement("a");
        link.href = canvas.toDataURL("image/png");
        link.download = filename;
        link.click();
      }
    } finally {
      btn.disabled = false;
      btn.innerHTML = originalHtml;
    }
  };

  document.addEventListener("click", (event) => {
    const btn = event.target.closest("[data-screenshot]");
    if (!btn) {
      return;
    }
    event.preventDefault();
    captureScreenshot(btn);
  });
})();
