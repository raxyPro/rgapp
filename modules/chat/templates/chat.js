// modules/chat/static/chat/chat.js

(function () {
  const cfg = window.RG_CHAT || {};
  const msgsEl = document.getElementById("chat-msgs");
  const bodyEl = document.getElementById("chat-body");
  const sendBtn = document.getElementById("chat-send");
  let lastId = 0;

  function scrollToBottom() {
    if (!msgsEl) return;
    msgsEl.scrollTop = msgsEl.scrollHeight;
  }

  function escapeHtml(s) {
    return (s || "").replace(/[&<>"']/g, function (c) {
      return ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" })[c];
    });
  }

  function senderLabel(id) {
    const m = cfg.senderEmails?.[String(id)] || {};
    return m.handle || m.email || `User ${id}`;
  }

  function fmtTime(ts) {
    try {
      return new Date(ts).toLocaleString();
    } catch (e) {
      return ts || "";
    }
  }

  function appendMessage(m) {
    if (!msgsEl) return;
    const div = document.createElement("div");
    div.className = "chat-msg";
    div.dataset.mid = m.message_id;
    div.innerHTML = `
      <div class="meta">
        <span><b>${escapeHtml(senderLabel(m.sender_id))}</b></span>
        <span style="margin-left:6px;">${escapeHtml(fmtTime(m.created_at))}</span>
      </div>
      <div class="body">${escapeHtml(m.body || "")}</div>
    `;
    msgsEl.appendChild(div);
    lastId = Math.max(lastId, Number(m.message_id) || 0);
    scrollToBottom();
  }

  async function sendMessage() {
    const body = (bodyEl?.value || "").trim();
    if (!body) return;
    if (bodyEl) bodyEl.value = "";
    try {
      const res = await fetch(cfg.sendUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ body }),
      });
      const data = await res.json();
      if (data?.message) {
        appendMessage(data.message);
      }
    } catch (err) {
      console.error("Send failed", err);
    }
  }

  async function pollLoop() {
    while (true) {
      try {
        const res = await fetch(`${cfg.pollUrl}?since=${lastId}`, { credentials: "include", cache: "no-store" });
        const data = await res.json();
        if (data?.messages?.length) {
          data.messages.forEach(appendMessage);
        }
      } catch (err) {
        console.warn("Poll error", err);
        await new Promise((r) => setTimeout(r, 1500));
      }
    }
  }

  function init() {
    // seed lastId from DOM
    if (msgsEl) {
      msgsEl.querySelectorAll("[data-mid]").forEach((el) => {
        const mid = Number(el.getAttribute("data-mid")) || 0;
        lastId = Math.max(lastId, mid);
      });
    }

    if (sendBtn) {
      sendBtn.addEventListener("click", (e) => {
        e.preventDefault();
        sendMessage();
      });
    }
    if (bodyEl) {
      bodyEl.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
          e.preventDefault();
          sendMessage();
        }
      });
    }

    scrollToBottom();
    pollLoop();
  }

  if (cfg.pollUrl && cfg.sendUrl) {
    init();
  }
})();
