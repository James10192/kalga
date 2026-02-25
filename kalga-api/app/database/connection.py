"""
Gestionnaire de connexion SQLite asynchrone
Fournit un context manager réutilisable pour les connexions à la base de données
"""
import aiosqlite
from pathlib import Path
from contextlib import asynccontextmanager
from typing import AsyncGenerator

# Chemin de la base de données
DB_PATH = Path(__file__).parent / "kalga.db"


@asynccontextmanager
async def get_connection() -> AsyncGenerator[aiosqlite.Connection, None]:
    """
    Context manager pour obtenir une connexion à la base de données.

    Usage:
        async with get_connection() as db:
            cursor = await db.execute("SELECT * FROM merchants")
            rows = await cursor.fetchall()
    """
    db = await aiosqlite.connect(str(DB_PATH))
    db.row_factory = aiosqlite.Row
    try:
        yield db
    finally:
        await db.close()


async def init_database():
    """
    Initialise la base de données avec les tables requises.
    Appelé au démarrage de l'application.
    """
    async with get_connection() as db:
        # Table des marchands
        await db.execute("""
            CREATE TABLE IF NOT EXISTS merchants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone TEXT UNIQUE NOT NULL,
                business_name TEXT,
                address TEXT,
                latitude REAL,
                longitude REAL,
                away_mode_enabled BOOLEAN DEFAULT 0,
                working_hours TEXT,
                away_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Migration: ajouter colonnes mode absence si elles n'existent pas
        try:
            await db.execute("ALTER TABLE merchants ADD COLUMN away_mode_enabled BOOLEAN DEFAULT 0")
        except:
            pass
        try:
            await db.execute("ALTER TABLE merchants ADD COLUMN working_hours TEXT")
        except:
            pass
        try:
            await db.execute("ALTER TABLE merchants ADD COLUMN away_message TEXT")
        except:
            pass

        # Migration: ajouter colonnes vitrine storefront
        try:
            await db.execute("ALTER TABLE merchants ADD COLUMN logo_path TEXT")
        except:
            pass
        try:
            await db.execute("ALTER TABLE merchants ADD COLUMN about TEXT")
        except:
            pass
        try:
            await db.execute("ALTER TABLE merchants ADD COLUMN tagline TEXT")
        except:
            pass
        try:
            await db.execute("ALTER TABLE merchants ADD COLUMN banner_path TEXT")
        except:
            pass

        # Table des produits
        await db.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                merchant_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                code TEXT UNIQUE NOT NULL,
                price REAL NOT NULL,
                min_price REAL NOT NULL,
                description TEXT,
                image_path TEXT,
                group_id TEXT,
                variant_name TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (merchant_id) REFERENCES merchants(id)
            )
        """)

        # Table des conversations
        await db.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                merchant_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                client_phone TEXT NOT NULL,
                status TEXT DEFAULT 'active',
                current_offer REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (merchant_id) REFERENCES merchants(id),
                FOREIGN KEY (product_id) REFERENCES products(id)
            )
        """)

        # Table des messages
        await db.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                is_from_client BOOLEAN NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id)
            )
        """)

        # Table des statistiques quotidiennes (analytics)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS daily_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                merchant_id INTEGER NOT NULL,
                date DATE NOT NULL,
                conversations_count INTEGER DEFAULT 0,
                messages_count INTEGER DEFAULT 0,
                sales_count INTEGER DEFAULT 0,
                revenue REAL DEFAULT 0,
                unique_clients INTEGER DEFAULT 0,
                avg_response_time REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (merchant_id) REFERENCES merchants(id),
                UNIQUE(merchant_id, date)
            )
        """)

        # Table des événements (pour tracking détaillé)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS analytics_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                merchant_id INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                product_id INTEGER,
                conversation_id INTEGER,
                client_phone TEXT,
                data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (merchant_id) REFERENCES merchants(id)
            )
        """)

        # Table des relances automatiques
        await db.execute("""
            CREATE TABLE IF NOT EXISTS follow_ups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id INTEGER NOT NULL,
                merchant_id INTEGER NOT NULL,
                client_phone TEXT NOT NULL,
                scheduled_at TIMESTAMP NOT NULL,
                message TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                sent_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id),
                FOREIGN KEY (merchant_id) REFERENCES merchants(id)
            )
        """)

        # Table des catégories de produits
        await db.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                merchant_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                icon TEXT DEFAULT '📦',
                color TEXT DEFAULT '#667eea',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (merchant_id) REFERENCES merchants(id),
                UNIQUE(merchant_id, name)
            )
        """)

        # Table de l'historique client (pour négociations)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS client_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                merchant_id INTEGER NOT NULL,
                client_phone TEXT NOT NULL,
                total_conversations INTEGER DEFAULT 0,
                total_purchases INTEGER DEFAULT 0,
                total_spent REAL DEFAULT 0,
                avg_negotiation_discount REAL DEFAULT 0,
                last_purchase_date TIMESTAMP,
                last_interaction_date TIMESTAMP,
                preferred_categories TEXT,
                negotiation_style TEXT DEFAULT 'normal',
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (merchant_id) REFERENCES merchants(id),
                UNIQUE(merchant_id, client_phone)
            )
        """)

        # ============================================
        # TABLES AUTHENTIFICATION & ABONNEMENTS
        # ============================================

        # Table des utilisateurs (Admin + Marchands)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT DEFAULT 'merchant',
                merchant_id INTEGER,
                is_active BOOLEAN DEFAULT 1,
                is_verified BOOLEAN DEFAULT 0,
                verification_token TEXT,
                reset_token TEXT,
                reset_token_expires TIMESTAMP,
                last_login TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (merchant_id) REFERENCES merchants(id)
            )
        """)

        # Table des abonnements marchands
        await db.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                merchant_id INTEGER NOT NULL UNIQUE,
                plan TEXT DEFAULT 'trial',
                status TEXT DEFAULT 'active',
                start_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                end_date TIMESTAMP,
                trial_ends_at TIMESTAMP,
                messages_limit INTEGER DEFAULT 500,
                messages_used INTEGER DEFAULT 0,
                products_limit INTEGER DEFAULT 10,
                features TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (merchant_id) REFERENCES merchants(id)
            )
        """)

        # Table des sessions actives (pour tracking connexions)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS active_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                token_hash TEXT NOT NULL,
                device_info TEXT,
                ip_address TEXT,
                last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        # Table des logs d'audit admin
        await db.execute("""
            CREATE TABLE IF NOT EXISTS admin_audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_user_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                target_type TEXT,
                target_id INTEGER,
                details TEXT,
                ip_address TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (admin_user_id) REFERENCES users(id)
            )
        """)

        # Table des codes d'activation (pour paiement marchand)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS activation_codes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                merchant_id INTEGER NOT NULL,
                code VARCHAR(8) NOT NULL UNIQUE,
                status VARCHAR(20) DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                used_at TIMESTAMP,
                expires_at TIMESTAMP,
                created_by INTEGER,
                FOREIGN KEY (merchant_id) REFERENCES merchants(id),
                FOREIGN KEY (created_by) REFERENCES users(id)
            )
        """)

        # Table des commandes vitrine web
        await db.execute("""
            CREATE TABLE IF NOT EXISTS storefront_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                merchant_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                client_name TEXT NOT NULL,
                client_phone TEXT NOT NULL,
                message TEXT,
                status TEXT DEFAULT 'new',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (merchant_id) REFERENCES merchants(id),
                FOREIGN KEY (product_id) REFERENCES products(id)
            )
        """)

        # Migration: ajouter colonnes paiement à subscriptions
        try:
            await db.execute("ALTER TABLE subscriptions ADD COLUMN payment_method VARCHAR(50)")
        except:
            pass
        try:
            await db.execute("ALTER TABLE subscriptions ADD COLUMN payment_reference VARCHAR(100)")
        except:
            pass
        try:
            await db.execute("ALTER TABLE subscriptions ADD COLUMN activated_by INTEGER")
        except:
            pass

        # Migration: ajouter la table client_history si elle n'existe pas
        try:
            await db.execute("SELECT 1 FROM client_history LIMIT 1")
        except:
            pass

        # Index pour les performances
        await db.execute("CREATE INDEX IF NOT EXISTS idx_merchants_phone ON merchants(phone)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_products_merchant ON products(merchant_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_products_code ON products(code)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_products_group ON products(group_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_conversations_merchant ON conversations(merchant_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_conversations_client ON conversations(client_phone)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_conversations_status ON conversations(status)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_daily_stats_merchant_date ON daily_stats(merchant_id, date)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_analytics_events_merchant ON analytics_events(merchant_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_analytics_events_type ON analytics_events(event_type)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_follow_ups_scheduled ON follow_ups(scheduled_at, status)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_follow_ups_conversation ON follow_ups(conversation_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_categories_merchant ON categories(merchant_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_client_history_merchant ON client_history(merchant_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_client_history_client ON client_history(client_phone)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_client_history_merchant_client ON client_history(merchant_id, client_phone)")

        # Migration: infos de paiement marchand (C2 — send_payment_info)
        try:
            await db.execute("ALTER TABLE merchants ADD COLUMN payment_methods TEXT")
        except:
            pass

        # Migration: mémoire sémantique client (LTM — système mémoire 3 couches)
        try:
            await db.execute("ALTER TABLE client_history ADD COLUMN memory_facts TEXT")
        except:
            pass
        try:
            await db.execute("ALTER TABLE client_history ADD COLUMN last_session_summary TEXT")
        except:
            pass
        try:
            await db.execute("ALTER TABLE client_history ADD COLUMN preferences TEXT")
        except:
            pass
        try:
            await db.execute("ALTER TABLE client_history ADD COLUMN conversation_summaries TEXT")
        except:
            pass

        # Index pour authentification
        await db.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_users_merchant ON users(merchant_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_users_role ON users(role)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_subscriptions_merchant ON subscriptions(merchant_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_subscriptions_status ON subscriptions(status)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_active_sessions_user ON active_sessions(user_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_active_sessions_token ON active_sessions(token_hash)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_admin_audit_admin ON admin_audit_logs(admin_user_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_activation_codes_merchant ON activation_codes(merchant_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_activation_codes_code ON activation_codes(code)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_activation_codes_status ON activation_codes(status)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_storefront_orders_merchant ON storefront_orders(merchant_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_storefront_orders_status ON storefront_orders(status)")

        await db.commit()
        print("[DB] Base de données initialisée avec succès")
