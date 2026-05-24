"""
BotDB v2 — Base de datos SQLite para Wanadi Vision.
Gestiona usuarios, planes, pagos, teams y referidos.
"""
import asyncio
import sqlite3
import secrets
from pathlib import Path
from datetime import date, datetime

from bot.config import FREE_BUSQUEDAS_DIA, STARTER_BUSQUEDAS_MES

DB_PATH = Path(__file__).parent / "nexus_bot.db"


def _conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


class BotDB:
    def __init__(self):
        self._init_db()

    # ──────────────────────────────────────────────────────────────────────────
    # Schema / Migration
    # ──────────────────────────────────────────────────────────────────────────
    def _init_db(self):
        with _conn() as conn:
            # Tabla base usuarios
            conn.execute("""
                CREATE TABLE IF NOT EXISTS bot_users (
                    user_id       INTEGER PRIMARY KEY,
                    full_name     TEXT,
                    is_premium    INTEGER DEFAULT 0,
                    searches_used INTEGER DEFAULT 0,
                    created_at    TEXT DEFAULT (datetime('now'))
                )
            """)

            # Migraciones seguras (idempotentes)
            new_cols = [
                ("plan",          "TEXT DEFAULT 'free'"),
                ("busquedas_hoy", "INTEGER DEFAULT 0"),
                ("busquedas_mes", "INTEGER DEFAULT 0"),
                ("reset_dia",     "TEXT DEFAULT ''"),
                ("reset_mes",     "TEXT DEFAULT ''"),
                ("team_id",       "INTEGER"),
                ("username",      "TEXT DEFAULT ''"),
            ]
            existing = {row[1] for row in conn.execute("PRAGMA table_info(bot_users)")}
            for col, typedef in new_cols:
                if col not in existing:
                    conn.execute(f"ALTER TABLE bot_users ADD COLUMN {col} {typedef}")

            # Tabla pagos
            conn.execute("""
                CREATE TABLE IF NOT EXISTS pagos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    telegram_payment_charge_id TEXT UNIQUE,
                    total_stars INTEGER NOT NULL,
                    plan TEXT NOT NULL,
                    fecha TEXT DEFAULT (datetime('now')),
                    status TEXT DEFAULT 'completed'
                )
            """)

            # Tabla teams
            conn.execute("""
                CREATE TABLE IF NOT EXISTS teams (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    admin_user_id INTEGER NOT NULL,
                    team_name TEXT,
                    api_key TEXT UNIQUE,
                    api_requests_hoy INTEGER DEFAULT 0,
                    fecha_creacion TEXT DEFAULT (datetime('now')),
                    activo INTEGER DEFAULT 1
                )
            """)

            # Tabla miembros de equipo
            conn.execute("""
                CREATE TABLE IF NOT EXISTS team_members (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    team_id INTEGER,
                    user_id INTEGER NOT NULL,
                    fecha_union TEXT DEFAULT (datetime('now'))
                )
            """)

            # Tabla referidos
            conn.execute("""
                CREATE TABLE IF NOT EXISTS referrals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    new_user_id INTEGER NOT NULL,
                    referrer_id INTEGER NOT NULL,
                    converted INTEGER DEFAULT 0,
                    fecha TEXT DEFAULT (datetime('now'))
                )
            """)

            conn.commit()

    # ──────────────────────────────────────────────────────────────────────────
    # Usuarios
    # ──────────────────────────────────────────────────────────────────────────
    async def get_or_create_user(self, user_id: int, full_name: str, username: str = "") -> dict:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._get_or_create_sync, user_id, full_name, username)

    def _get_or_create_sync(self, user_id: int, full_name: str, username: str = "") -> dict:
        with _conn() as conn:
            row = conn.execute("SELECT * FROM bot_users WHERE user_id=?", (user_id,)).fetchone()
            if not row:
                conn.execute(
                    "INSERT INTO bot_users (user_id, full_name, username) VALUES (?,?,?)",
                    (user_id, full_name, username or "")
                )
                conn.commit()
                row = conn.execute("SELECT * FROM bot_users WHERE user_id=?", (user_id,)).fetchone()
            else:
                user = dict(row)
                if user.get("username") != username:
                    conn.execute("UPDATE bot_users SET username=? WHERE user_id=?", (username or "", user_id))
                    conn.commit()
                    row = conn.execute("SELECT * FROM bot_users WHERE user_id=?", (user_id,)).fetchone()
            return dict(row)

    async def get_user_by_username(self, username: str) -> dict | None:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._get_user_by_username_sync, username)

    def _get_user_by_username_sync(self, username: str) -> dict | None:
        username = username.lstrip("@").strip()
        with _conn() as conn:
            row = conn.execute("SELECT * FROM bot_users WHERE username=?", (username,)).fetchone()
            return dict(row) if row else None

    async def upgrade_to_premium(self, user_id: int):
        """Compat legacy: marca is_premium=1 y plan='pro'."""
        await self.activate_plan(user_id, "pro")

    async def increment_searches(self, user_id: int):
        """Compat legacy."""
        await self.increment_searches_counter(user_id)

    async def stats(self) -> dict:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._stats_sync)

    def _stats_sync(self) -> dict:
        with _conn() as conn:
            total    = conn.execute("SELECT COUNT(*) FROM bot_users").fetchone()[0]
            premium  = conn.execute("SELECT COUNT(*) FROM bot_users WHERE is_premium=1").fetchone()[0]
            searches = conn.execute("SELECT SUM(searches_used) FROM bot_users").fetchone()[0] or 0
            pagos    = conn.execute("SELECT COUNT(*) FROM pagos").fetchone()[0]
            revenue  = conn.execute("SELECT SUM(total_stars) FROM pagos").fetchone()[0] or 0
            return {
                "total_users": total,
                "premium_users": premium,
                "total_searches": searches,
                "total_pagos": pagos,
                "total_stars": revenue,
            }

    # ──────────────────────────────────────────────────────────────────────────
    # Control de acceso
    # ──────────────────────────────────────────────────────────────────────────
    async def puede_buscar(self, user_id: int, full_name: str = "") -> tuple[bool, str]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._puede_buscar_sync, user_id, full_name)

    def _puede_buscar_sync(self, user_id: int, full_name: str) -> tuple[bool, str]:
        with _conn() as conn:
            row = conn.execute("SELECT * FROM bot_users WHERE user_id=?", (user_id,)).fetchone()
            if not row:
                conn.execute("INSERT INTO bot_users (user_id, full_name) VALUES (?,?)", (user_id, full_name))
                conn.commit()
                row = conn.execute("SELECT * FROM bot_users WHERE user_id=?", (user_id,)).fetchone()
            user = dict(row)

        plan = user.get("plan", "free")

        if plan == "pro":
            return True, "ok"

        if plan == "teams":
            with _conn() as conn:
                team = conn.execute(
                    "SELECT * FROM teams WHERE id=? AND activo=1", (user.get("team_id"),)
                ).fetchone()
            if team:
                return True, "ok"
            return False, "limite_teams"

        if plan == "starter":
            self._reset_mensual_sync(user_id, user)
            with _conn() as conn:
                row = conn.execute("SELECT busquedas_mes FROM bot_users WHERE user_id=?", (user_id,)).fetchone()
            return (True, "ok") if row["busquedas_mes"] < STARTER_BUSQUEDAS_MES else (False, "limite_starter")

        # free
        self._reset_diario_sync(user_id, user)
        with _conn() as conn:
            row = conn.execute("SELECT busquedas_hoy FROM bot_users WHERE user_id=?", (user_id,)).fetchone()
        return (True, "ok") if row["busquedas_hoy"] < FREE_BUSQUEDAS_DIA else (False, "paywall_free")

    def _reset_diario_sync(self, user_id: int, user: dict):
        hoy = str(date.today())
        if user.get("reset_dia") != hoy:
            with _conn() as conn:
                conn.execute(
                    "UPDATE bot_users SET busquedas_hoy=0, reset_dia=? WHERE user_id=?",
                    (hoy, user_id)
                )
                conn.commit()

    def _reset_mensual_sync(self, user_id: int, user: dict):
        mes = str(date.today())[:7]
        if user.get("reset_mes") != mes:
            with _conn() as conn:
                conn.execute(
                    "UPDATE bot_users SET busquedas_mes=0, reset_mes=? WHERE user_id=?",
                    (mes, user_id)
                )
                conn.commit()

    async def increment_searches_counter(self, user_id: int):
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._increment_sync, user_id)

    def _increment_sync(self, user_id: int):
        with _conn() as conn:
            conn.execute("""
                UPDATE bot_users
                SET searches_used   = searches_used + 1,
                    busquedas_hoy   = busquedas_hoy + 1,
                    busquedas_mes   = busquedas_mes + 1
                WHERE user_id=?
            """, (user_id,))
            conn.commit()

    async def get_plan(self, user_id: int) -> str:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._get_plan_sync, user_id)

    def _get_plan_sync(self, user_id: int) -> str:
        with _conn() as conn:
            row = conn.execute("SELECT plan FROM bot_users WHERE user_id=?", (user_id,)).fetchone()
        return row["plan"] if row else "free"

    # ──────────────────────────────────────────────────────────────────────────
    # Planes y Pagos
    # ──────────────────────────────────────────────────────────────────────────
    async def activate_plan(self, user_id: int, plan: str, team_id: int = None):
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._activate_plan_sync, user_id, plan, team_id)

    def _activate_plan_sync(self, user_id: int, plan: str, team_id=None):
        is_premium = 1 if plan in ("pro", "starter", "teams") else 0
        with _conn() as conn:
            if team_id:
                conn.execute(
                    "UPDATE bot_users SET plan=?, is_premium=?, team_id=? WHERE user_id=?",
                    (plan, is_premium, team_id, user_id)
                )
            else:
                conn.execute(
                    "UPDATE bot_users SET plan=?, is_premium=? WHERE user_id=?",
                    (plan, is_premium, user_id)
                )
            conn.commit()

    async def save_payment(self, user_id: int, charge_id: str, stars: int, plan: str):
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._save_payment_sync, user_id, charge_id, stars, plan)

    def _save_payment_sync(self, user_id: int, charge_id: str, stars: int, plan: str):
        with _conn() as conn:
            try:
                conn.execute(
                    "INSERT INTO pagos (user_id, telegram_payment_charge_id, total_stars, plan) VALUES (?,?,?,?)",
                    (user_id, charge_id, stars, plan)
                )
                conn.commit()
            except sqlite3.IntegrityError:
                pass  # charge_id duplicado

    # ──────────────────────────────────────────────────────────────────────────
    # Teams
    # ──────────────────────────────────────────────────────────────────────────
    async def create_team(self, admin_user_id: int, api_key: str) -> int:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._create_team_sync, admin_user_id, api_key)

    def _create_team_sync(self, admin_user_id: int, api_key: str) -> int:
        with _conn() as conn:
            cur = conn.execute(
                "INSERT INTO teams (admin_user_id, api_key) VALUES (?,?)",
                (admin_user_id, api_key)
            )
            conn.commit()
            return cur.lastrowid

    async def add_team_member(self, team_id: int, user_id: int) -> bool:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._add_member_sync, team_id, user_id)

    def _add_member_sync(self, team_id: int, user_id: int) -> bool:
        with _conn() as conn:
            count = conn.execute(
                "SELECT COUNT(*) FROM team_members WHERE team_id=?", (team_id,)
            ).fetchone()[0]
            if count >= 5:
                return False
            existing = conn.execute(
                "SELECT id FROM team_members WHERE team_id=? AND user_id=?", (team_id, user_id)
            ).fetchone()
            if existing:
                return True
            conn.execute(
                "INSERT INTO team_members (team_id, user_id) VALUES (?,?)", (team_id, user_id)
            )
            conn.execute(
                "UPDATE bot_users SET plan='teams', is_premium=1, team_id=? WHERE user_id=?",
                (team_id, user_id)
            )
            conn.commit()
            return True

    async def get_team_by_user(self, user_id: int) -> dict | None:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._get_team_sync, user_id)

    def _get_team_sync(self, user_id: int) -> dict | None:
        with _conn() as conn:
            user = conn.execute("SELECT team_id FROM bot_users WHERE user_id=?", (user_id,)).fetchone()
            if not user or not user["team_id"]:
                return None
            team = conn.execute("SELECT * FROM teams WHERE id=?", (user["team_id"],)).fetchone()
            return dict(team) if team else None

    async def get_team_members(self, team_id: int) -> list:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._get_members_sync, team_id)

    def _get_members_sync(self, team_id: int) -> list:
        with _conn() as conn:
            rows = conn.execute(
                "SELECT u.user_id, u.full_name FROM team_members tm JOIN bot_users u ON u.user_id=tm.user_id WHERE tm.team_id=?",
                (team_id,)
            ).fetchall()
        return [dict(r) for r in rows]

    # ──────────────────────────────────────────────────────────────────────────
    # Referidos
    # ──────────────────────────────────────────────────────────────────────────
    async def save_referral(self, new_user_id: int, referrer_id: int):
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._save_referral_sync, new_user_id, referrer_id)

    def _save_referral_sync(self, new_user_id: int, referrer_id: int):
        with _conn() as conn:
            existing = conn.execute(
                "SELECT id FROM referrals WHERE new_user_id=?", (new_user_id,)
            ).fetchone()
            if not existing:
                conn.execute(
                    "INSERT INTO referrals (new_user_id, referrer_id) VALUES (?,?)",
                    (new_user_id, referrer_id)
                )
                conn.commit()

    async def mark_referral_converted(self, user_id: int):
        """Marcar que el usuario referido hizo una compra."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._mark_converted_sync, user_id)

    def _mark_converted_sync(self, user_id: int):
        with _conn() as conn:
            conn.execute(
                "UPDATE referrals SET converted=1 WHERE new_user_id=?", (user_id,)
            )
            conn.commit()
            # Ver si el referidor acumuló 5 conversiones
            row = conn.execute(
                "SELECT referrer_id FROM referrals WHERE new_user_id=?", (user_id,)
            ).fetchone()
            if row:
                referrer_id = row["referrer_id"]
                count = conn.execute(
                    "SELECT COUNT(*) FROM referrals WHERE referrer_id=? AND converted=1",
                    (referrer_id,)
                ).fetchone()[0]
                # Cada 5 conversiones → activar Starter gratis
                if count > 0 and count % 5 == 0:
                    conn.execute(
                        "UPDATE bot_users SET plan='starter', is_premium=1 WHERE user_id=? AND plan='free'",
                        (referrer_id,)
                    )
                    conn.commit()

    async def get_referral_count(self, user_id: int) -> dict:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._referral_count_sync, user_id)

    def _referral_count_sync(self, user_id: int) -> dict:
        with _conn() as conn:
            total = conn.execute(
                "SELECT COUNT(*) FROM referrals WHERE referrer_id=?", (user_id,)
            ).fetchone()[0]
            converted = conn.execute(
                "SELECT COUNT(*) FROM referrals WHERE referrer_id=? AND converted=1", (user_id,)
            ).fetchone()[0]
        return {"total": total, "converted": converted}
