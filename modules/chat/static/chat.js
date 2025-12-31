// modules/chat/static/chat/chat.js

(function () {
  const cfg = window.RG_CHAT || {};
  const msgsEl = document.getElementById("chat-msgs");
  const bodyEl = document.getElementById("chat-body");
  const sendBtn = document.getElementById("chat-send");
  let lastId = 0;
  let fbRef = null;

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
      const d = new Date(ts);
      const ms = String(d.getMilliseconds()).padStart(3, "0");
      return `${d.toLocaleDateString()} ${d.toLocaleTimeString([], { hour12: false })}.${ms}`;
    } catch (e) {
      return ts || "";
    }
  }

  function appendMessage(m) {
    if (!msgsEl) return;
    const recvTs = Date.now();
    const sentTs = m?.created_at ? new Date(m.created_at).getTime() : NaN;
    const latencyMs = isNaN(sentTs) ? null : Math.max(0, recvTs - sentTs);
    const latencyLabel = (() => {
      if (latencyMs === null) return "";
      const secs = latencyMs / 1000;
      if (secs >= 3600) {
        const hrs = secs / 3600;
        return ` (+${hrs.toFixed(1)}h)`;
      }
      if (secs >= 300) {
        const mins = secs / 60;
        return ` (+${mins.toFixed(0)}m)`;
      }
      if (secs >= 10) {
        return ` (+${secs.toFixed(0)}s)`;
      }
      if (secs >= 1) {
        return ` (+${secs.toFixed(1)}s)`;
      }
      return ` (+${latencyMs}ms)`;
    })();

    const div = document.createElement("div");
    div.className = "chat-msg";
    div.dataset.mid = m.message_id;
    div.innerHTML = `
      <div class="meta">
        <span><b>${escapeHtml(senderLabel(m.sender_id))}</b></span>
        <span style="margin-left:6px;">${escapeHtml(fmtTime(m.created_at))}${escapeHtml(latencyLabel)}</span>
      </div>
      <div class="body">${escapeHtml(m.body || "")}</div>
    `;
    msgsEl.appendChild(div);
    lastId = Math.max(lastId, Number(m.message_id) || 0);
    scrollToBottom();
  }

  function publishToFirebase(m) {
    if (!fbRef || !m?.message_id) return;
    try {
      const payload = {
        ...m,
        // Add legacy-friendly fields some RTDB rules expect.
        text: m.body ?? "",
        ts: m.created_at ?? new Date().toISOString(),
        name: m.sender_id ?? cfg.currentUserId ?? "anon",
      };
      fbRef.child(String(m.message_id)).set(payload);
    } catch (err) {
      console.warn("Firebase publish failed", err);
    }
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
        publishToFirebase(data.message);
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

  async function startFirebase() {
    if (!cfg.firebase?.config || !window.firebase || !firebase.initializeApp) {
      return false;
    }
    try {
      const app = firebase.apps?.length ? firebase.app() : firebase.initializeApp(cfg.firebase.config);

      // Ensure we're signed in (anonymous) so RTDB rules requiring auth will pass.
      if (firebase.auth) {
        const auth = firebase.auth();
        if (!auth.currentUser) {
          await auth.signInAnonymously();
        }
      }

      const db = firebase.database(app);
      const path = cfg.firebase.rtdbPath || `threads/${cfg.threadId}/messages`;
      fbRef = db.ref(path);
      fbRef.on("child_added", (snap) => {
        const m = snap.val() || {};
        if (m.message_id === undefined && snap.key) {
          m.message_id = Number(snap.key) || snap.key;
        }
        // Skip messages we've already rendered (initial seed).
        if (m.message_id && Number(m.message_id) <= lastId) return;
        appendMessage(m);
      });
      return true;
    } catch (err) {
      console.warn("Firebase init failed", err);
      fbRef = null;
      return false;
    }
  }

  function init() {
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
    startFirebase();
    // Keep polling as a safety net so messages still flow even if Firebase is blocked
    // (e.g., permission errors, SDK load failure, or offline clients).
    pollLoop();
  }

  if (cfg.pollUrl && cfg.sendUrl) {
    init();
  }
})();
