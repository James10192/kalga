#!/usr/bin/env python3
"""
KALGA - Script de backup automatique de la base de données
Usage: python backup_db.py

Peut être exécuté via cron/Task Scheduler:
- Linux: 0 2 * * * /path/to/python /path/to/backup_db.py
- Windows: schtasks /create /tn "KALGA Backup" /tr "python backup_db.py" /sc daily /st 02:00
"""
import os
import shutil
from datetime import datetime
from pathlib import Path

# Configuration
DB_PATH = Path(__file__).parent.parent / "app" / "database" / "kalga.db"
BACKUP_DIR = Path(__file__).parent.parent / "backups"
MAX_BACKUPS = 7  # Garder les 7 derniers backups


def backup_database():
    """Crée une copie de la base de données avec timestamp"""

    # Créer le dossier de backup s'il n'existe pas
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    if not DB_PATH.exists():
        print(f"[ERREUR] Base de données non trouvée: {DB_PATH}")
        return False

    # Nom du fichier avec timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"kalga_backup_{timestamp}.db"
    backup_path = BACKUP_DIR / backup_name

    try:
        # Copier la base de données
        shutil.copy2(DB_PATH, backup_path)
        print(f"[OK] Backup créé: {backup_path}")

        # Nettoyer les anciens backups
        cleanup_old_backups()

        return True
    except Exception as e:
        print(f"[ERREUR] Échec du backup: {e}")
        return False


def cleanup_old_backups():
    """Supprime les backups au-delà de MAX_BACKUPS"""
    backups = sorted(BACKUP_DIR.glob("kalga_backup_*.db"), reverse=True)

    if len(backups) > MAX_BACKUPS:
        for old_backup in backups[MAX_BACKUPS:]:
            try:
                old_backup.unlink()
                print(f"[NETTOYAGE] Supprimé: {old_backup.name}")
            except Exception as e:
                print(f"[ERREUR] Impossible de supprimer {old_backup.name}: {e}")


def list_backups():
    """Liste les backups existants"""
    if not BACKUP_DIR.exists():
        print("Aucun backup trouvé")
        return

    backups = sorted(BACKUP_DIR.glob("kalga_backup_*.db"), reverse=True)

    if not backups:
        print("Aucun backup trouvé")
        return

    print(f"\n=== Backups KALGA ({len(backups)}) ===")
    for backup in backups:
        size_mb = backup.stat().st_size / (1024 * 1024)
        print(f"  - {backup.name} ({size_mb:.2f} MB)")
    print()


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--list":
        list_backups()
    else:
        print("=== KALGA Database Backup ===")
        print(f"Source: {DB_PATH}")
        print(f"Destination: {BACKUP_DIR}")
        print()
        backup_database()
        list_backups()
