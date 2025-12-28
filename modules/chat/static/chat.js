// modules/chat/static/chat/chat.js

(function () {
  const cfg = window.RG_CHAT;
  const msgsEl = document.getElementById("chat-msgs");
  const bodyEl = document.getElementById("chat-body");
  const sendBtn = document.getElementById("chat-send");

  function scrollToBottom() {
    if (!msgsEl) return;
    msgsEl.scrollTop = msgsEl.scrollHeight;
  }

  function escapeHtml(s) {
    return (s || "").replace(/[&<>"']/g, function (c) {
      return ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" })[c];
    });
  }

  function renderRich(text) {
    const urlRe = /(https?:\/\/[^\s]+)/gi;
    const imgExts = [".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"];
    const escaped = escapeHtml(text || "");
    const linked = escaped.replace(urlRe, (url) => {
      const lower = url.split("?")[0].toLowerCase();
      const isImg = imgExts.some((ext) => lower.endsWith(ext));
      if (isImg) {
        return `
          <a href="${url}" target="_blank" rel="noopener">
            <img src="${url}" alt="Image" style="max-width:240px;max-height:240px;border-radius:8px;display:block;margin-top:6px;">
          </a>
        `;
      }
      return `<a href="${url}" target="_blank" rel="noopener">${url}</a>`;
    });
    return linked.replace(/\n/g, "<br>");
  }

  function appendMessage(m) {
    const meta = cfg.senderEmails && cfg.senderEmails[m.sender_id];
    const name = (meta && (meta.handle || meta.email)) || `User ${m.sender_id}`;
    const div = document.createElement("div");
    div.className = "chat-msg";
    div.innerHTML = `
      <div class="meta">
        <span><b>${escapeHtml(name)}</b></span>
        · <span>${escapeHtml(m.created_at || "")}</span>
      </div>
      <div class="body">${renderRich(m.body || "")}</div>
    `;
    msgsEl.appendChild(div);
    scrollToBottom();
  }

  async function sendHttp(body) {
    const form = new FormData();
    form.append("body", body);
    await fetch(cfg.httpSendUrl, { method: "POST", body: form, credentials: "include" });
    window.location.reload();
  }

  function wireHttpOnly() {
    sendBtn.addEventListener("click", async (e) => {
      e.preventDefault();
      const body = (bodyEl.value || "").trim();
      if (!body) return;
      await sendHttp(body);
    });
    bodyEl.addEventListener("keydown", async (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        const body = (bodyEl.value || "").trim();
        if (!body) return;
        await sendHttp(body);
      }
    });
  }

  // Socket.IO (optional). If you don't include socketio client, it will fall back.
  function wireSocket() {
    if (!window.io) return false;

    const socket = window.io({ transports: ["websocket", "polling"] });

    socket.on("connect", () => {
      socket.emit("chat:join", { thread_id: cfg.threadId });
    });

    socket.on("chat:new_message", (m) => {
      if (Number(m.thread_id) !== Number(cfg.threadId)) return;
      appendMessage(m);
    });

    async function doSend() {
      const body = (bodyEl.value || "").trim();
      if (!body) return;
      bodyEl.value = "";
      socket.emit("chat:send", { thread_id: cfg.threadId, body });
    }

    sendBtn.addEventListener("click", (e) => {
      e.preventDefault();
      doSend();
    });

    bodyEl.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        doSend();
      }
    });

    scrollToBottom();
    return true;
  }

  // Prefer socket; otherwise fallback to HTTP reload behavior
  const socketWired = wireSocket();
  if (!socketWired) {
    wireHttpOnly();
    scrollToBottom();
  }
})();
