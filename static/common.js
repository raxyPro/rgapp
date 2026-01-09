(() => {
  const toggleBtn = document.querySelector("[data-feedback-toggle]");
  const panel = document.querySelector("[data-feedback-panel]");
  const form = document.querySelector("[data-feedback-form]");
  const textarea = document.querySelector("[data-feedback-text]");
  const statusEl = document.querySelector("[data-feedback-status]");
  const listEl = document.querySelector("[data-feedback-list]");
  const emptyEl = document.querySelector("[data-feedback-empty]");

  if (!toggleBtn || !panel || !form || !textarea) {
    return;
  }

  const setOpen = (isOpen) => {
    panel.classList.toggle("d-none", !isOpen);
    toggleBtn.setAttribute("aria-expanded", isOpen ? "true" : "false");
    if (isOpen) {
      textarea.focus();
      loadFeedbackList();
    }
  };

  toggleBtn.addEventListener("click", (event) => {
    event.preventDefault();
    const isOpen = panel.classList.contains("d-none");
    setOpen(isOpen);
  });

  document.addEventListener("click", (event) => {
    if (!panel.classList.contains("d-none")) {
      const target = event.target;
      if (!panel.contains(target) && !toggleBtn.contains(target)) {
        setOpen(false);
      }
    }
  });

  const setStatus = (msg, isError) => {
    if (!statusEl) {
      return;
    }
    statusEl.textContent = msg || "";
    statusEl.classList.toggle("text-danger", Boolean(isError));
  };

  const renderList = (items) => {
    if (!listEl || !emptyEl) {
      return;
    }
    listEl.innerHTML = "";
    if (!items || items.length === 0) {
      emptyEl.classList.remove("d-none");
      return;
    }
    emptyEl.classList.add("d-none");
    items.forEach((item) => {
      const wrap = document.createElement("div");
      wrap.className = "border rounded p-2";
      const meta = document.createElement("div");
      meta.className = "text-muted";
      const when = item.created_at ? new Date(item.created_at).toLocaleString() : "";
      const who = item.user_label ? ` - ${item.user_label}` : "";
      meta.textContent = `${when}${who}`;
      const body = document.createElement("div");
      body.textContent = item.body || "";
      wrap.appendChild(meta);
      wrap.appendChild(body);
      listEl.appendChild(wrap);
    });
  };

  const loadFeedbackList = async () => {
    if (!form || !listEl) {
      return;
    }
    const endpoint = form.getAttribute("data-feedback-list-endpoint");
    if (!endpoint) {
      return;
    }
    const scope = form.getAttribute("data-feedback-scope") || "mine";
    const url = `${endpoint}?scope=${encodeURIComponent(scope)}`;
    try {
      const res = await fetch(url, { credentials: "same-origin" });
      if (!res.ok) {
        return;
      }
      const data = await res.json();
      if (!data || !data.ok) {
        return;
      }
      renderList(data.items || []);
    } catch (err) {
      return;
    }
  };

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const body = (textarea.value || "").trim();
    if (!body) {
      setStatus("Feedback required.", true);
      return;
    }

    const payload = {
      body,
      url: window.location.href,
      path: window.location.pathname,
      title: document.title,
      referrer: document.referrer || "",
      userAgent: navigator.userAgent,
      platform: navigator.platform || "",
      language: navigator.language || "",
      languages: navigator.languages || [],
      cookieEnabled: Boolean(navigator.cookieEnabled),
      screen: `${window.screen.width}x${window.screen.height}`,
      viewport: `${window.innerWidth}x${window.innerHeight}`,
      timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || "",
      timestamp: new Date().toISOString(),
    };

    const endpoint = form.getAttribute("data-feedback-endpoint");
    if (!endpoint) {
      setStatus("Missing endpoint.", true);
      return;
    }

    setStatus("Sending...", false);
    const submitBtn = form.querySelector("button[type=\"submit\"]");
    if (submitBtn) {
      submitBtn.disabled = true;
    }

    try {
      const res = await fetch(endpoint, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        credentials: "same-origin",
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        setStatus("Failed to send.", true);
        return;
      }
      textarea.value = "";
      setStatus("Sent. Thank you!", false);
      loadFeedbackList();
      setTimeout(() => setOpen(false), 700);
    } catch (err) {
      setStatus("Failed to send.", true);
    } finally {
      if (submitBtn) {
        submitBtn.disabled = false;
      }
    }
  });
})();
