#!/usr/bin/env python3
"""
KALGA - Script de nettoyage des conversations expirées
Usage: python cleanup_expired.py

Peut être exécuté via cron/Task Scheduler:
- Linux: 0 3 * * * /path/to/python /path/to/cleanup_expired.py
- Windows: schtasks /create /tn "KALGA Cleanup" /tr "python cleanup_expired.py" /sc daily /st 03:00
"""
import asyncio
import aiosqlite
from datetime import datetime, timedelta
from pathlib import Path

# Configuration
DB_PATH = Path(__file__).parent.parent / "app" / "database" / "kalga.db"
EXPIRY_DAYS = 7  # Conversations inactives depuis 7 jours


async def cleanup_expired_conversations():
    """Marque les conversations expirées et nettoie les anciennes données"""

    if not DB_PATH.exists():
        print(f"[ERREUR] Base de données non trouvée: {DB_PATH}")
        return

    print("=== KALGA Cleanup ===")
    print(f"Base: {DB_PATH}")
    print(f"Expiration: {EXPIRY_DAYS} jours")
    print()

    async with aiosqlite.connect(DB_PATH) as db:
        cutoff = datetime.now() - timedelta(days=EXPIRY_DAYS)
        cutoff_str = cutoff.isoformat()

        # 1. Compter les conversations à expirer
        cursor = await db.execute(
            "SELECT COUNT(*) FROM conversations WHERE status = 'active' AND updated_at < ?",
            (cutoff_str,)
        )
        count = (await cursor.fetchone())[0]

        if count > 0:
            # 2. Marquer comme expirées
            await db.execute(
                "UPDATE conversations SET status = 'expired' WHERE status = 'active' AND updated_at < ?",
                (cutoff_str,)
            )
            await db.commit()
            print(f"[OK] {count} conversation(s) marquée(s) comme expirée(s)")
        else:
            print("[OK] Aucune conversation à expirer")

        # 3. Statistiques
        cursor = await db.execute("""
            SELECT status, COUNT(*) as count
            FROM conversations
            GROUP BY status
        """)
        stats = await cursor.fetchall()

        print("\n=== Statistiques ===")
        for status, cnt in stats:
            print(f"  - {status}: {cnt}")

        # 4. Taille de la base
        cursor = await db.execute("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()")
        size = (await cursor.fetchone())[0]
        print(f"\nTaille DB: {size / (1024 * 1024):.2f} MB")


if __name__ == "__main__":
    asyncio.run(cleanup_expired_conversations())
