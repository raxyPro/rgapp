from flask import Flask, request, jsonify, render_template_string
from werkzeug.middleware.proxy_fix import ProxyFix
import os, sqlite3, time

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

# Store SQLite DB in your app folder
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "chat.db")

POLL_TIMEOUT_SEC = 25
SLEEP_STEP_SEC = 0.4
MAX_RETURN = 100

HTML = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>Long Poll Chat</title>
  <style>
    body { font-family:sans-serif; background:#f4f4f9; padding:20px }
    .wrap { max-width:720px; margin:0 auto; }
    #chat { height:360px; border:1px solid #ccc; overflow:auto; padding:10px; background:#fff; border-radius:8px; }
    .row { margin: 8px 0; }
    .meta { color:#777; font-size:12px; }
    .controls { display:flex; gap:10px; margin-top:10px; }
    input { flex:1; padding:12px; border:1px solid #ddd; border-radius:6px; }
    button { padding:12px 18px; border:0; border-radius:6px; background:#28a745; color:#fff; font-weight:600; cursor:pointer; }
    button:hover { background:#218838; }
  </style>
</head>
<body>
  <div class="wrap">
    <h2>💬 Long Poll Chat (DB-backed)</h2>
    <div class="meta" id="status">Connecting…</div>
    <div id="chat"></div>

    <div class="controls">
      <input id="name" placeholder="Name (optional)" />
      <input id="msg" placeholder="Type a message…" />
      <button onclick="sendMsg()">Send</button>
    </div>
  </div>

<script>
  const chatEl = document.getElementById("chat");
  const statusEl = document.getElementById("status");
  const msgEl = document.getElementById("msg");
  const nameEl = document.getElementById("name");

  // Works for /my1 and /my1/
  const base = window.location.pathname.endsWith("/")
    ? window.location.pathname
    : window.location.pathname + "/";

  let lastId = 0;

  function esc(s) {
    return (s ?? "").toString()
      .replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;")
      .replaceAll('"',"&quot;").replaceAll("'","&#039;");
  }

  function addLine(m) {
    const row = document.createElement("div");
    row.className = "row";
    row.innerHTML = `<span class="meta">[${esc(m.ts)}]</span> <b>${esc(m.name)}:</b> ${esc(m.text)}`;
    chatEl.appendChild(row);
    chatEl.scrollTop = chatEl.scrollHeight;
  }

  async function poll() {
    try {
      statusEl.textContent = "Listening…";
      const res = await fetch(base + "poll?since=" + lastId, { cache: "no-store" });
      const data = await res.json();
      if (data.messages && data.messages.length) {
        for (const m of data.messages) {
          addLine(m);
          lastId = Math.max(lastId, m.id);
        }
      }
      statusEl.textContent = "Connected";
    } catch (e) {
      statusEl.textContent = "Reconnect…";
      await new Promise(r => setTimeout(r, 1200));
    }
    poll(); // loop
  }

  async function sendMsg() {
    const text = msgEl.value.trim();
    if (!text) return;
    const name = (nameEl.value.trim() || "User").slice(0, 40);

    msgEl.value = "";

    await fetch(base + "send", {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify({ name, msg: text })
    });
  }

  window.sendMsg = sendMsg;
  msgEl.addEventListener("keyup", (e) => { if (e.key === "Enter") sendMsg(); });

  poll();
</script>
</body>
</html>
"""

def db_conn():
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = db_conn()
    try:
        conn.execute("""
          CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room TEXT NOT NULL,
            name TEXT NOT NULL,
            text TEXT NOT NULL,
            created_at INTEGER NOT NULL
          )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_room_id ON messages(room, id)")
        conn.commit()
    finally:
        conn.close()

@app.route("/")
def index():
    return render_template_string(HTML)

@app.route("/send", methods=["POST"])
def send():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "User").strip()[:40]
    text = (data.get("msg") or "").strip()
    if not text:
        return jsonify({"ok": True})

    room = "general"  # later you can make this dynamic
    now = int(time.time())

    conn = db_conn()
    try:
        conn.execute(
            "INSERT INTO messages(room, name, text, created_at) VALUES (?, ?, ?, ?)",
            (room, name, text[:500], now)
        )
        conn.commit()
        return jsonify({"ok": True})
    finally:
        conn.close()

@app.route("/poll")
def poll():
    room = "general"
    try:
        since = int(request.args.get("since", "0"))
    except ValueError:
        since = 0

    deadline = time.time() + POLL_TIMEOUT_SEC

    while True:
        conn = db_conn()
        try:
            rows = conn.execute(
                "SELECT id, name, text, created_at FROM messages WHERE room=? AND id>? ORDER BY id ASC LIMIT ?",
                (room, since, MAX_RETURN)
            ).fetchall()
        finally:
            conn.close()

        if rows:
            msgs = [{
                "id": r["id"],
                "name": r["name"],
                "text": r["text"],
                "ts": time.strftime("%H:%M:%S", time.localtime(r["created_at"]))
            } for r in rows]
            return jsonify({"messages": msgs})

        if time.time() >= deadline:
            return jsonify({"messages": []})

        time.sleep(SLEEP_STEP_SEC)

# Initialize DB at import time (Passenger-friendly)
init_db()

if __name__ == "__main__":
    app.run(debug=True, threaded=True)
