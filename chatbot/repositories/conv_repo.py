import uuid
from repositories.db import query_all, query_one, get_connection


def recover_orphaned_conversations():
    """Recrée des entrées Conversations pour les messages dont la conversation a été supprimée."""
    with get_connection() as conn:
        orphaned = conn.execute(
            "SELECT DISTINCT conversation_id FROM Messages "
            "WHERE conversation_id NOT IN (SELECT id FROM Conversations)"
        ).fetchall()
        for row in orphaned:
            conv_id = row[0]
            first_msg = conn.execute(
                "SELECT content FROM Messages WHERE conversation_id = ? AND role = 'user' ORDER BY id LIMIT 1",
                (conv_id,),
            ).fetchone()
            first_time = conn.execute(
                "SELECT MIN(created_at) FROM Messages WHERE conversation_id = ?",
                (conv_id,),
            ).fetchone()[0]
            if first_msg:
                titre = first_msg[0][:45] + ("…" if len(first_msg[0]) > 45 else "")
            else:
                titre = "Conversation récupérée"
            conn.execute(
                "INSERT INTO Conversations (id, titre, created_at) VALUES (?, ?, ?)",
                (conv_id, titre, first_time),
            )
        conn.commit()
        if orphaned:
            print("[INIT] {} conversation(s) orpheline(s) récupérée(s)".format(len(orphaned)))


class ConversationRepository:

    def create(self):
        conv_id = str(uuid.uuid4())
        with get_connection() as conn:
            conn.execute("INSERT INTO Conversations (id) VALUES (?)", (conv_id,))
            conn.commit()
        return conv_id

    def create_robot(self):
        """Return the single persistent robot conversation, creating it if needed."""
        with get_connection() as conn:
            row = conn.execute(
                "SELECT id FROM Conversations WHERE titre = '🤖 Pepper (robot)' LIMIT 1"
            ).fetchone()
            if row:
                return row[0]
            conv_id = str(uuid.uuid4())
            conn.execute(
                "INSERT INTO Conversations (id, titre) VALUES (?, '🤖 Pepper (robot)')",
                (conv_id,),
            )
            conn.commit()
        return conv_id

    def list_all(self):
        return query_all(
            "SELECT id, titre, created_at FROM Conversations ORDER BY created_at DESC"
        )

    def delete(self, conv_id):
        with get_connection() as conn:
            conn.execute("DELETE FROM Messages WHERE conversation_id = ?", (conv_id,))
            conn.execute("DELETE FROM Conversations WHERE id = ?", (conv_id,))
            conn.commit()

    def get_messages(self, conv_id):
        return query_all(
            "SELECT role, content FROM Messages WHERE conversation_id = ? ORDER BY id",
            (conv_id,),
        )

    def append_message(self, conv_id, role, content):
        with get_connection() as conn:
            conn.execute(
                "INSERT INTO Messages (conversation_id, role, content) VALUES (?, ?, ?)",
                (conv_id, role, content),
            )
            # Titre = premier message utilisateur tronqué
            if role == "user":
                count = conn.execute(
                    "SELECT COUNT(*) FROM Messages WHERE conversation_id = ? AND role = 'user'",
                    (conv_id,),
                ).fetchone()[0]
                if count == 1:
                    titre = content[:45] + ("…" if len(content) > 45 else "")
                    conn.execute(
                        "UPDATE Conversations SET titre = ? WHERE id = ?",
                        (titre, conv_id),
                    )
            conn.commit()
