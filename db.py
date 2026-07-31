import sqlite3
import os
import hashlib
from typing import Optional, Dict, Any, List
import datetime

DB_PATH = "data/veldwys.db"

LSU_FACTORS = {"cattle": 1.0, "goat": 0.15, "sheep": 0.15, "other": 0.5}


def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    os.makedirs("data/uploads", exist_ok=True)
    with _conn() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                region TEXT DEFAULT '',
                lat REAL DEFAULT NULL,
                lon REAL DEFAULT NULL,
                camp_area_ha REAL DEFAULT 0,
                cattle_count INTEGER DEFAULT 0,
                goat_count INTEGER DEFAULT 0,
                sheep_count INTEGER DEFAULT 0
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS farm_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                description TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS animals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                tag TEXT DEFAULT '',
                name TEXT DEFAULT '',
                species TEXT NOT NULL DEFAULT 'cattle',
                breed TEXT DEFAULT '',
                sex TEXT DEFAULT '',
                dob TEXT DEFAULT '',
                photo_path TEXT DEFAULT '',
                status TEXT DEFAULT 'active',
                notes TEXT DEFAULT '',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS animal_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                animal_id INTEGER DEFAULT NULL,
                event_type TEXT NOT NULL,
                description TEXT DEFAULT '',
                event_date TEXT DEFAULT '',
                due_date TEXT DEFAULT NULL,
                completed INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id),
                FOREIGN KEY(animal_id) REFERENCES animals(id)
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT DEFAULT '',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                filename TEXT DEFAULT '',
                content TEXT DEFAULT '',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        ''')
        # Additive migrations for pre-existing dev databases
        for stmt in (
            "ALTER TABLE users ADD COLUMN language TEXT DEFAULT 'en'",
            "ALTER TABLE users ADD COLUMN farm_name TEXT DEFAULT ''",
            "ALTER TABLE users ADD COLUMN full_name TEXT DEFAULT ''",
            "ALTER TABLE users ADD COLUMN role TEXT DEFAULT ''",
            "ALTER TABLE users ADD COLUMN voice_gender TEXT DEFAULT 'female'",
            "ALTER TABLE users ADD COLUMN voice_speed REAL DEFAULT 1.0",
            "ALTER TABLE users ADD COLUMN created_at DATETIME DEFAULT NULL",
            # Protocol-generated reminders carry a key so the UI can translate them
            "ALTER TABLE animal_events ADD COLUMN tkey TEXT DEFAULT ''",
            "ALTER TABLE chat_history ADD COLUMN chat_id INTEGER DEFAULT NULL",
        ):
            try:
                cursor.execute(stmt)
            except sqlite3.OperationalError:
                pass
        conn.commit()


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def create_user(username: str, password: str) -> bool:
    try:
        with _conn() as conn:
            conn.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                (username, hash_password(password))
            )
            conn.commit()
            return True
    except sqlite3.IntegrityError:
        return False


def verify_user(username: str, password: str) -> Optional[int]:
    with _conn() as conn:
        row = conn.execute(
            "SELECT id FROM users WHERE username = ? AND password_hash = ?",
            (username, hash_password(password))
        ).fetchone()
        return row["id"] if row else None


def update_profile(user_id: int, region: str, lat: Optional[float], lon: Optional[float],
                   camp_area_ha: float, cattle_count: int, goat_count: int, sheep_count: int,
                   language: Optional[str] = None, farm_name: Optional[str] = None,
                   full_name: Optional[str] = None, role: Optional[str] = None,
                   voice_gender: Optional[str] = None, voice_speed: Optional[float] = None) -> bool:
    with _conn() as conn:
        conn.execute('''
            UPDATE users SET region=?, lat=?, lon=?, camp_area_ha=?, cattle_count=?, goat_count=?, sheep_count=?,
                language=COALESCE(?, language), farm_name=COALESCE(?, farm_name),
                full_name=COALESCE(?, full_name), role=COALESCE(?, role),
                voice_gender=COALESCE(?, voice_gender), voice_speed=COALESCE(?, voice_speed),
                created_at=COALESCE(created_at, CURRENT_TIMESTAMP)
            WHERE id=?
        ''', (region, lat, lon, camp_area_ha, cattle_count, goat_count, sheep_count,
              language, farm_name, full_name, role, voice_gender, voice_speed, user_id))
        conn.commit()
        return True


def get_profile(user_id: int) -> Optional[Dict[str, Any]]:
    with _conn() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return dict(row) if row else None


# --- Farm logs ---

def add_farm_log(user_id: int, event_type: str, description: str):
    with _conn() as conn:
        conn.execute("INSERT INTO farm_logs (user_id, event_type, description) VALUES (?, ?, ?)",
                     (user_id, event_type, description))
        conn.commit()


def get_farm_logs(user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM farm_logs WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, limit)).fetchall()
        return [dict(r) for r in rows]


# --- Chat history ---

def add_chat_message(user_id: int, role: str, content: str, chat_id: Optional[int] = None):
    with _conn() as conn:
        conn.execute("INSERT INTO chat_history (user_id, role, content, chat_id) VALUES (?, ?, ?, ?)",
                     (user_id, role, content, chat_id))
        if chat_id:
            conn.execute("UPDATE chats SET updated_at=CURRENT_TIMESTAMP WHERE id=? AND user_id=?",
                         (chat_id, user_id))
        conn.commit()


def get_chat_history(user_id: int, limit: int = 20, chat_id: Optional[int] = None) -> List[Dict[str, Any]]:
    sql = "SELECT role, content FROM chat_history WHERE user_id = ?"
    params: list = [user_id]
    if chat_id:
        sql += " AND chat_id = ?"
        params.append(chat_id)
    sql += " ORDER BY id DESC LIMIT ?"
    params.append(limit)
    with _conn() as conn:
        rows = conn.execute(sql, params).fetchall()
        return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]


# --- Chats ---

def create_chat(user_id: int, title: str = "") -> int:
    with _conn() as conn:
        cur = conn.execute("INSERT INTO chats (user_id, title) VALUES (?, ?)", (user_id, title))
        conn.commit()
        return cur.lastrowid


def list_chats(user_id: int, query: Optional[str] = None) -> List[Dict[str, Any]]:
    """Chats newest first, with a preview. `query` searches titles and message text."""
    sql = '''SELECT c.*,
                    (SELECT content FROM chat_history m WHERE m.chat_id=c.id ORDER BY m.id DESC LIMIT 1) AS preview,
                    (SELECT COUNT(*) FROM chat_history m WHERE m.chat_id=c.id) AS messages
             FROM chats c WHERE c.user_id = ?'''
    params: list = [user_id]
    if query:
        sql += ''' AND (c.title LIKE ? OR EXISTS
                   (SELECT 1 FROM chat_history m WHERE m.chat_id=c.id AND m.content LIKE ?))'''
        params += [f"%{query}%", f"%{query}%"]
    sql += " ORDER BY c.updated_at DESC, c.id DESC"
    with _conn() as conn:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


def rename_chat(user_id: int, chat_id: int, title: str):
    with _conn() as conn:
        conn.execute("UPDATE chats SET title=? WHERE id=? AND user_id=?", (title, chat_id, user_id))
        conn.commit()


def delete_chat(user_id: int, chat_id: int):
    with _conn() as conn:
        conn.execute("DELETE FROM chat_history WHERE chat_id=? AND user_id=?", (chat_id, user_id))
        conn.execute("DELETE FROM chats WHERE id=? AND user_id=?", (chat_id, user_id))
        conn.commit()


def ensure_chat(user_id: int, chat_id: Optional[int]) -> int:
    """Return a usable chat id, adopting any pre-existing loose history once."""
    if chat_id:
        return chat_id
    existing = list_chats(user_id)
    if existing:
        return existing[0]["id"]
    new_id = create_chat(user_id)
    with _conn() as conn:
        conn.execute("UPDATE chat_history SET chat_id=? WHERE user_id=? AND chat_id IS NULL",
                     (new_id, user_id))
        conn.commit()
    return new_id


# --- Documents ---

def add_document(user_id: int, filename: str, content: str) -> int:
    with _conn() as conn:
        cur = conn.execute("INSERT INTO documents (user_id, filename, content) VALUES (?, ?, ?)",
                           (user_id, filename, content))
        conn.commit()
        return cur.lastrowid


def get_documents(user_id: int, query: Optional[str] = None) -> List[Dict[str, Any]]:
    sql = "SELECT * FROM documents WHERE user_id = ?"
    params: list = [user_id]
    if query:
        sql += " AND (filename LIKE ? OR content LIKE ?)"
        params += [f"%{query}%", f"%{query}%"]
    sql += " ORDER BY id DESC"
    with _conn() as conn:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


def delete_document(user_id: int, doc_id: int):
    with _conn() as conn:
        conn.execute("DELETE FROM documents WHERE id=? AND user_id=?", (doc_id, user_id))
        conn.commit()


# --- Animals ---

def add_animal(user_id: int, tag: str = "", name: str = "", species: str = "cattle",
               breed: str = "", sex: str = "", dob: str = "", notes: str = "",
               photo_path: str = "", status: str = "active") -> int:
    with _conn() as conn:
        cur = conn.execute('''
            INSERT INTO animals (user_id, tag, name, species, breed, sex, dob, notes, photo_path, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, tag, name, species.lower(), breed, sex, dob, notes, photo_path, status))
        conn.commit()
        return cur.lastrowid


def update_animal(user_id: int, animal_id: int, **fields) -> bool:
    allowed = {"tag", "name", "species", "breed", "sex", "dob", "notes", "photo_path", "status"}
    updates = {k: v for k, v in fields.items() if k in allowed and v is not None}
    if not updates:
        return False
    sets = ", ".join(f"{k}=?" for k in updates)
    with _conn() as conn:
        conn.execute(f"UPDATE animals SET {sets} WHERE id=? AND user_id=?",
                     (*updates.values(), animal_id, user_id))
        conn.commit()
        return True


def get_animals(user_id: int, status: Optional[str] = None,
                species: Optional[str] = None, query: Optional[str] = None) -> List[Dict[str, Any]]:
    sql = "SELECT * FROM animals WHERE user_id = ?"
    params: list = [user_id]
    if status:
        sql += " AND status = ?"
        params.append(status)
    if species:
        sql += " AND species = ?"
        params.append(species.lower())
    if query:
        sql += " AND (tag LIKE ? OR name LIKE ? OR breed LIKE ? OR notes LIKE ?)"
        params += [f"%{query}%"] * 4
    sql += " ORDER BY id DESC"
    with _conn() as conn:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


def get_animal(user_id: int, animal_id: int) -> Optional[Dict[str, Any]]:
    with _conn() as conn:
        row = conn.execute("SELECT * FROM animals WHERE id=? AND user_id=?",
                           (animal_id, user_id)).fetchone()
        return dict(row) if row else None


def get_herd_summary(user_id: int) -> Dict[str, Any]:
    """Counts + LSU from individual animals; falls back to profile quick-counts."""
    with _conn() as conn:
        rows = conn.execute('''
            SELECT species, COUNT(*) as n FROM animals
            WHERE user_id=? AND status='active' GROUP BY species
        ''', (user_id,)).fetchall()
        counts = {r["species"]: r["n"] for r in rows}
        recent = conn.execute('''
            SELECT event_type, COUNT(*) as n FROM animal_events
            WHERE user_id=? AND event_type IN ('birth','sale','death')
              AND created_at >= datetime('now', '-90 days')
            GROUP BY event_type
        ''', (user_id,)).fetchall()
        recent_events = {r["event_type"]: r["n"] for r in recent}

    source = "animal_register"
    if not counts:
        profile = get_profile(user_id) or {}
        counts = {k: v for k, v in {
            "cattle": profile.get("cattle_count", 0),
            "goat": profile.get("goat_count", 0),
            "sheep": profile.get("sheep_count", 0),
        }.items() if v}
        source = "quick_counts"

    total_lsu = round(sum(n * LSU_FACTORS.get(sp, 0.5) for sp, n in counts.items()), 1)
    return {
        "counts": counts,
        "total_animals": sum(counts.values()),
        "total_lsu": total_lsu,
        "recent_90d": recent_events,
        "source": source,
    }


# --- Animal events / reminders ---

def add_animal_event(user_id: int, event_type: str, description: str = "",
                     animal_id: Optional[int] = None, event_date: str = "",
                     due_date: Optional[str] = None, completed: int = 0,
                     tkey: str = "") -> int:
    """tkey names a built-in protocol reminder so the UI can show it translated."""
    if not event_date and not due_date:
        event_date = datetime.date.today().isoformat()
    with _conn() as conn:
        cur = conn.execute('''
            INSERT INTO animal_events (user_id, animal_id, event_type, description, event_date, due_date, completed, tkey)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, animal_id, event_type, description, event_date, due_date, completed, tkey))
        conn.commit()
        return cur.lastrowid


def get_animal_events(user_id: int, animal_id: Optional[int] = None, limit: int = 50) -> List[Dict[str, Any]]:
    sql = '''SELECT e.*, a.tag as animal_tag, a.name as animal_name, a.species as animal_species
             FROM animal_events e LEFT JOIN animals a ON e.animal_id = a.id
             WHERE e.user_id = ?'''
    params: list = [user_id]
    if animal_id:
        sql += " AND e.animal_id = ?"
        params.append(animal_id)
    sql += " ORDER BY COALESCE(e.due_date, e.event_date) DESC, e.id DESC LIMIT ?"
    params.append(limit)
    with _conn() as conn:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


def get_upcoming_events(user_id: int, days: int = 30) -> List[Dict[str, Any]]:
    """Uncompleted events with a due date up to `days` ahead (overdue included)."""
    horizon = (datetime.date.today() + datetime.timedelta(days=days)).isoformat()
    with _conn() as conn:
        rows = conn.execute('''
            SELECT e.*, a.tag as animal_tag, a.name as animal_name, a.species as animal_species
            FROM animal_events e LEFT JOIN animals a ON e.animal_id = a.id
            WHERE e.user_id = ? AND e.completed = 0 AND e.due_date IS NOT NULL AND e.due_date <= ?
            ORDER BY e.due_date ASC
        ''', (user_id, horizon)).fetchall()
        today = datetime.date.today().isoformat()
        out = []
        for r in rows:
            d = dict(r)
            d["overdue"] = d["due_date"] < today
            out.append(d)
        return out


def set_animal_status(user_id: int, animal_ids: List[int], status: str) -> int:
    with _conn() as conn:
        conn.executemany("UPDATE animals SET status=? WHERE id=? AND user_id=?",
                         [(status, aid, user_id) for aid in animal_ids])
        conn.commit()
        return len(animal_ids)


def pick_animals(user_id: int, species: Optional[str] = None, count: int = 1,
                 tags: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """Choose animals for a bulk status change.

    With tags, match those. Without, take the oldest active animals of that species,
    preferring untagged ones so identified animals stay put unless named explicitly.
    """
    if tags:
        found = []
        for tg in tags:
            m = get_animals(user_id, query=tg.strip())
            if m:
                found.append(m[0])
        return found
    sql = "SELECT * FROM animals WHERE user_id=? AND status='active'"
    params: list = [user_id]
    if species:
        sql += " AND species=?"
        params.append(species.lower())
    sql += " ORDER BY (tag IS NULL OR tag=''), dob ASC, id ASC LIMIT ?"
    params.append(max(1, count))
    with _conn() as conn:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


STOPWORDS = {"the", "a", "an", "for", "of", "my", "our", "did", "done", "i", "we",
             "this", "that", "shot", "shots", "today", "morning", "yesterday"}


def find_open_events(user_id: int, query: str = "", limit: int = 10) -> List[Dict[str, Any]]:
    """Open reminders, optionally matched loosely.

    Farmers say "the anthrax booster" while the reminder reads "Anthrax vaccination",
    so match on any meaningful word rather than the whole phrase, and rank by how
    many words hit.
    """
    sql = '''SELECT e.*, a.tag as animal_tag FROM animal_events e
             LEFT JOIN animals a ON e.animal_id = a.id
             WHERE e.user_id=? AND e.completed=0 AND e.due_date IS NOT NULL
             ORDER BY e.due_date ASC'''
    with _conn() as conn:
        rows = [dict(r) for r in conn.execute(sql, (user_id,)).fetchall()]
    if not query:
        return rows[:limit]

    words = [w for w in "".join(ch if ch.isalnum() else " " for ch in query.lower()).split()
             if w not in STOPWORDS and len(w) > 2]
    if not words:
        return rows[:limit]
    scored = []
    for r in rows:
        hay = f"{r.get('description', '')} {r.get('event_type', '')}".lower()
        hits = sum(1 for w in words if w in hay)
        if hits:
            scored.append((hits, r))
    scored.sort(key=lambda x: (-x[0], x[1].get("due_date") or ""))
    return [r for _, r in scored][:limit]


def complete_event(user_id: int, event_id: int) -> bool:
    with _conn() as conn:
        conn.execute("UPDATE animal_events SET completed=1, event_date=? WHERE id=? AND user_id=?",
                     (datetime.date.today().isoformat(), event_id, user_id))
        conn.commit()
        return True


def delete_event(user_id: int, event_id: int) -> bool:
    with _conn() as conn:
        conn.execute("DELETE FROM animal_events WHERE id=? AND user_id=?", (event_id, user_id))
        conn.commit()
        return True


# Initialize on import
init_db()
