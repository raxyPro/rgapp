// modules/chat/static/chat/chat.js

(function () {
  const cfg = window.RG_CHAT || {};
  const msgsEl = document.getElementById("chat-msgs");
  const bodyEl = document.getElementById("chat-body");
  const sendBtn = document.getElementById("chat-send");
  const replyInput = document.getElementById("reply_to");
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
    return m.label || `User ${id}`;
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

  function renderReactions(m) {
    const counts = m?.reactions || {};
    const topCount = Object.values(counts).reduce((acc, n) => Math.max(acc, Number(n) || 0), 0);
    const chips = Object.entries(counts).map(([emoji, cnt]) => {
      const highlight = (Number(cnt) || 0) === topCount && topCount > 0 ? 'unread' : '';
      // Use rg-pill so it matches chat_reui.html styling.
      return `<span class="rg-pill ${highlight}" data-emoji="${escapeHtml(emoji)}">${escapeHtml(emoji)} <span class="text-muted">${escapeHtml(String(cnt))}</span></span>`;
    });

    const buttons = [];
    if (cfg.canReact) {
      const choices = Array.isArray(cfg.reactionChoices) ? cfg.reactionChoices : [];
      choices.forEach((e) => {
        const isMine = m?.user_reaction === e;
        const url = `/chat/t/${cfg.threadId}/m/${m.message_id}/react`;
        buttons.push(
          `<form method="post" action="${url}">
             <input type="hidden" name="emoji" value="${isMine ? '' : escapeHtml(e)}">
             <button class="btn btn-sm ${isMine ? "btn-primary" : "btn-outline-primary"} pill" type="submit">${escapeHtml(e)}</button>
           </form>`
        );
      });
    }

    const chipRow = chips.length
      ? `<div class="reaction-row mt-2" style="display:flex; gap:6px; flex-wrap:wrap;">${chips.join("")}</div>`
      : "";
    const actionRow = buttons.length
      ? `<div class="reaction-actions mt-2" style="display:none; gap:8px; flex-wrap:wrap;">${buttons.join("")}</div>`
      : "";
    if (!chipRow && !actionRow) return "";
    return `${chipRow}${actionRow}`;
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
    const isMe = Number(m.sender_id) === Number(cfg.currentUserId);
    div.className = `chat-msg${isMe ? " me" : ""}`;
    div.dataset.mid = m.message_id;
    const replyLabel = m.reply_to_message_id ? `replying to #${escapeHtml(String(m.reply_to_message_id))}` : "";
    const reactHtml = renderReactions(m);
    const canReact = !!cfg.canReact;
    // Broadcast: subscribers can't reply unless owner (server enforces too).
    const canReply = cfg.threadType === "broadcast" ? !!cfg.isOwner : true;
    const canEdit = Number(m.sender_id) === Number(cfg.currentUserId);

    const actionBar = `
      <div class="actions">
        ${canReply ? `<button class="btn btn-outline-primary" type="button" onclick="setReply('${m.message_id}', '${escapeHtml(senderLabel(m.sender_id))}')">Reply</button>` : ""}
        ${canReact ? `<button class="btn btn-outline-secondary react-toggle" type="button" onclick="toggleReactions('${m.message_id}')">😊</button>` : ""}
        ${canEdit ? `<button class="btn btn-outline-secondary" type="button" onclick="toggleEdit('${m.message_id}')">Edit</button>` : ""}
      </div>`;

    div.innerHTML = `
      <div class="meta">
        <span><b>${escapeHtml(senderLabel(m.sender_id))}</b></span>
        <span>·</span>
        <span>${escapeHtml(fmtTime(m.created_at))}${escapeHtml(latencyLabel)}</span>
        ${replyLabel ? `<span class="text-muted" style="margin-left:8px;">${replyLabel}</span>` : ""}
        ${actionBar}
      </div>

      <div class="bubble">
        <div class="body" id="body_display_${m.message_id}">${escapeHtml(m.body || "")}</div>

        <form id="edit_form_${m.message_id}" class="mt-2" method="post" action="/chat/t/${cfg.threadId}/m/${m.message_id}/edit" style="display:none;">
          <textarea class="form-control" name="body" rows="2">${escapeHtml(m.body || "")}</textarea>
          <div class="mt-2 d-flex gap-2">
            <button class="btn btn-sm btn-primary pill" type="submit">Save</button>
            <button class="btn btn-sm btn-outline-secondary pill" type="button" onclick="toggleEdit('${m.message_id}')">Cancel</button>
          </div>
        </form>

        ${reactHtml}
      </div>
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
    const replyToId = replyInput && replyInput.value ? Number(replyInput.value) : null;
    try {
      const res = await fetch(cfg.sendUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ body, reply_to_message_id: replyToId || undefined }),
      });
      const data = await res.json();
      if (data?.message) {
        appendMessage(data.message);
        publishToFirebase(data.message);
        if (typeof clearReply === "function") {
          clearReply();
        } else if (replyInput) {
          replyInput.value = "";
        }
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
