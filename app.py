# app.py - A small web application (web page + REST backend) built with Flask and MySQL.

# 'os' lets us read environment variables (how Docker passes settings into the container).
import os
# 'time' gives us sleep(), used to wait while the database is still starting up.
import time

# Flask is the web framework; 'jsonify' turns Python dicts into JSON responses;
# 'request' gives access to the data the client sent.
from flask import Flask, jsonify, request
# PyMySQL is the driver that lets Python talk to a MySQL database.
import pymysql

# Create the web application object. __name__ tells Flask where this file lives.
app = Flask(__name__)

# Read the database settings from environment variables.
# The second value in each call is a default used when the variable is not set.
DB_HOST = os.environ.get("DB_HOST", "db")          # 'db' = service name in docker-compose.yml
DB_USER = os.environ.get("DB_USER", "notesuser")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "notespass")
DB_NAME = os.environ.get("DB_NAME", "notesdb")

# The web page (frontend). It is plain HTML + JavaScript kept in one string,
# so the project needs no extra files. The JavaScript calls the REST API below.
PAGE = """<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Notes App</title>
  <style>
    body { font-family: Arial, sans-serif; max-width: 640px; margin: 40px auto; padding: 0 16px; }
    h1 { color: #1f3b73; }
    input, textarea { width: 100%; padding: 8px; margin: 4px 0 10px; box-sizing: border-box; }
    button { padding: 8px 16px; background: #1f3b73; color: white; border: 0; cursor: pointer; }
    .note { border: 1px solid #ccc; padding: 10px; margin: 10px 0; border-radius: 4px; }
    .note button { background: #b33; float: right; }
  </style>
</head>
<body>
  <h1>Notes App</h1>
  <p>Web page (Flask) + database (MySQL), running in Docker Compose.</p>
  <input id="title" placeholder="Title">
  <textarea id="content" rows="3" placeholder="Content"></textarea>
  <button onclick="addNote()">Add note</button>
  <div id="list"></div>
  <script>
    // Ask the backend for all notes and draw them on the page.
    async function loadNotes() {
      const res = await fetch('/notes');
      const notes = await res.json();
      const box = document.getElementById('list');
      box.innerHTML = '';
      for (let i = 0; i < notes.length; i++) {
        const n = notes[i];
        const div = document.createElement('div');
        div.className = 'note';
        div.innerHTML = '<button onclick="delNote(' + n.id + ')">Delete</button><b></b><p></p>';
        div.querySelector('b').textContent = n.title;       // textContent avoids HTML injection
        div.querySelector('p').textContent = n.content || '';
        box.appendChild(div);
      }
    }
    // Send the form values to the backend, then refresh the list.
    async function addNote() {
      const title = document.getElementById('title').value;
      const content = document.getElementById('content').value;
      await fetch('/notes', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({title: title, content: content})
      });
      document.getElementById('title').value = '';
      document.getElementById('content').value = '';
      loadNotes();
    }
    // Delete one note by id, then refresh the list.
    async function delNote(id) {
      await fetch('/notes/' + id, {method: 'DELETE'});
      loadNotes();
    }
    loadNotes();
  </script>
</body>
</html>
"""


def get_connection():
    """Open and return a new connection to MySQL."""
    return pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        # DictCursor returns each row as a dictionary (column name -> value).
        cursorclass=pymysql.cursors.DictCursor,
        # autocommit saves every INSERT/DELETE immediately, no manual commit needed.
        autocommit=True,
    )


def init_db():
    """Create the 'notes' table if it does not exist yet.
    MySQL may take a few seconds to start, so we retry a few times."""
    # Classic indexed loop: try up to 30 times.
    for attempt in range(30):
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute(
                "CREATE TABLE IF NOT EXISTS notes ("
                "id INT AUTO_INCREMENT PRIMARY KEY, "
                "title VARCHAR(100) NOT NULL, "
                "content TEXT)"
            )
            conn.close()
            print("Database ready")
            return
        except Exception as error:
            # Database not ready yet: print the reason, wait 2 seconds, try again.
            print("Waiting for database... attempt", attempt + 1, error)
            time.sleep(2)
    raise RuntimeError("Could not connect to the database")


@app.route("/", methods=["GET"])
def home():
    """Serve the web page."""
    return PAGE


@app.route("/health", methods=["GET"])
def health():
    """Health check: used by CI/CD and Docker to confirm the app is alive."""
    return jsonify({"status": "ok"})


@app.route("/notes", methods=["GET"])
def list_notes():
    """Return every note stored in the database."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, title, content FROM notes ORDER BY id")
    rows = cur.fetchall()
    conn.close()
    return jsonify(rows)


@app.route("/notes", methods=["POST"])
def add_note():
    """Create a new note from the JSON body {"title": "...", "content": "..."}."""
    # silent=True returns None instead of crashing when the body is not valid JSON.
    data = request.get_json(silent=True)
    # Validate BEFORE touching the database: a title is required.
    if not data or not data.get("title"):
        return jsonify({"error": "title is required"}), 400
    conn = get_connection()
    cur = conn.cursor()
    # %s placeholders let the driver escape values safely (prevents SQL injection).
    cur.execute(
        "INSERT INTO notes (title, content) VALUES (%s, %s)",
        (data["title"], data.get("content", "")),
    )
    new_id = cur.lastrowid
    conn.close()
    return jsonify({"id": new_id, "title": data["title"]}), 201


@app.route("/notes/<int:note_id>", methods=["DELETE"])
def delete_note(note_id):
    """Delete the note with the given id."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM notes WHERE id = %s", (note_id,))
    deleted = cur.rowcount          # how many rows were removed (0 or 1)
    conn.close()
    if deleted == 0:
        return jsonify({"error": "note not found"}), 404
    return jsonify({"deleted": note_id})


# This block runs only when we start the file directly (python app.py),
# not when pytest imports it. That keeps tests independent of MySQL.
if __name__ == "__main__":
    init_db()
    # host 0.0.0.0 makes the server reachable from outside the container.
    app.run(host="0.0.0.0", port=5000)
