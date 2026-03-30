"""identity phase 1

Revision ID: 20260323_0002
Revises: 20260323_0001
Create Date: 2026-03-23 00:30:00
"""

from datetime import datetime, timezone
from typing import Sequence, Union
import os

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260323_0002"
down_revision: Union[str, Sequence[str], None] = "20260323_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _get_or_create_default_user_id() -> int:
    bind = op.get_bind()
    default_email = os.getenv("ALERT_EMAIL", "you@example.com").strip().lower() or "you@example.com"

    existing_id = bind.execute(
        sa.text("SELECT id FROM users WHERE email = :email"),
        {"email": default_email},
    ).scalar()
    if existing_id is not None:
        return int(existing_id)

    users_table = sa.table(
        "users",
        sa.column("id", sa.Integer),
        sa.column("email", sa.String),
        sa.column("password_hash", sa.String),
        sa.column("is_email_verified", sa.Boolean),
        sa.column("is_active", sa.Boolean),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    now_utc = datetime.now(timezone.utc)
    insert_result = bind.execute(
        sa.insert(users_table).values(
            email=default_email,
            password_hash=None,
            is_email_verified=True,
            is_active=True,
            created_at=now_utc,
            updated_at=now_utc,
        )
    )

    inserted_id = None
    if insert_result.inserted_primary_key:
        inserted_id = insert_result.inserted_primary_key[0]
    if inserted_id is not None:
        return int(inserted_id)

    fallback_id = bind.execute(
        sa.text("SELECT id FROM users WHERE email = :email"),
        {"email": default_email},
    ).scalar()
    if fallback_id is None:
        raise RuntimeError("No se pudo determinar el usuario por defecto durante la migracion.")
    return int(fallback_id)


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=True),
        sa.Column("is_email_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "user_sessions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("refresh_token_hash", sa.String(length=255), nullable=False),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_sessions_created_at", "user_sessions", ["created_at"], unique=False)
    op.create_index("ix_user_sessions_refresh_token_hash", "user_sessions", ["refresh_token_hash"], unique=True)
    op.create_index("ix_user_sessions_user_id", "user_sessions", ["user_id"], unique=False)

    op.create_table(
        "email_verification_tokens",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(length=255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_email_verification_tokens_created_at",
        "email_verification_tokens",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "ix_email_verification_tokens_token_hash",
        "email_verification_tokens",
        ["token_hash"],
        unique=True,
    )
    op.create_index(
        "ix_email_verification_tokens_user_id",
        "email_verification_tokens",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "password_reset_tokens",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(length=255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_password_reset_tokens_created_at",
        "password_reset_tokens",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "ix_password_reset_tokens_token_hash",
        "password_reset_tokens",
        ["token_hash"],
        unique=True,
    )
    op.create_index("ix_password_reset_tokens_user_id", "password_reset_tokens", ["user_id"], unique=False)

    op.create_table(
        "audit_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("details_json", sa.Text(), nullable=True),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_events_event_type", "audit_events", ["event_type"], unique=False)
    op.create_index("ix_audit_events_occurred_at", "audit_events", ["occurred_at"], unique=False)
    op.create_index("ix_audit_events_user_id", "audit_events", ["user_id"], unique=False)

    op.add_column("products", sa.Column("user_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_products_user_id_users",
        "products",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_products_user_id", "products", ["user_id"], unique=False)

    default_user_id = _get_or_create_default_user_id()

    bind = op.get_bind()
    bind.execute(sa.text("UPDATE products SET user_id = :user_id WHERE user_id IS NULL"), {"user_id": default_user_id})
    op.alter_column("products", "user_id", nullable=False)

    # Quitamos la unicidad global por URL y la llevamos al alcance por usuario.
    bind.execute(sa.text("DROP INDEX IF EXISTS ix_products_url"))
    op.create_index("ix_products_url", "products", ["url"], unique=False)
    op.create_unique_constraint("uq_products_user_url", "products", ["user_id", "url"])

    op.add_column("alerts", sa.Column("user_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_alerts_user_id_users",
        "alerts",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_alerts_user_id", "alerts", ["user_id"], unique=False)
    bind.execute(
        sa.text(
            """
            UPDATE alerts
            SET user_id = (
                SELECT products.user_id
                FROM products
                WHERE products.id = alerts.product_id
            )
            WHERE user_id IS NULL
            """
        )
    )
    op.alter_column("alerts", "user_id", nullable=False)

    op.add_column("price_history", sa.Column("user_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_price_history_user_id_users",
        "price_history",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_price_history_user_id", "price_history", ["user_id"], unique=False)
    bind.execute(
        sa.text(
            """
            UPDATE price_history
            SET user_id = (
                SELECT products.user_id
                FROM products
                WHERE products.id = price_history.product_id
            )
            WHERE user_id IS NULL
            """
        )
    )
    op.alter_column("price_history", "user_id", nullable=False)


def downgrade() -> None:
    op.drop_index("ix_price_history_user_id", table_name="price_history")
    op.drop_constraint("fk_price_history_user_id_users", "price_history", type_="foreignkey")
    op.drop_column("price_history", "user_id")

    op.drop_index("ix_alerts_user_id", table_name="alerts")
    op.drop_constraint("fk_alerts_user_id_users", "alerts", type_="foreignkey")
    op.drop_column("alerts", "user_id")

    op.drop_constraint("uq_products_user_url", "products", type_="unique")
    op.drop_index("ix_products_user_id", table_name="products")
    op.drop_constraint("fk_products_user_id_users", "products", type_="foreignkey")
    op.drop_column("products", "user_id")
    op.drop_index("ix_products_url", table_name="products")
    op.create_index("ix_products_url", "products", ["url"], unique=True)

    op.drop_index("ix_audit_events_user_id", table_name="audit_events")
    op.drop_index("ix_audit_events_occurred_at", table_name="audit_events")
    op.drop_index("ix_audit_events_event_type", table_name="audit_events")
    op.drop_table("audit_events")

    op.drop_index("ix_password_reset_tokens_user_id", table_name="password_reset_tokens")
    op.drop_index("ix_password_reset_tokens_token_hash", table_name="password_reset_tokens")
    op.drop_index("ix_password_reset_tokens_created_at", table_name="password_reset_tokens")
    op.drop_table("password_reset_tokens")

    op.drop_index("ix_email_verification_tokens_user_id", table_name="email_verification_tokens")
    op.drop_index("ix_email_verification_tokens_token_hash", table_name="email_verification_tokens")
    op.drop_index("ix_email_verification_tokens_created_at", table_name="email_verification_tokens")
    op.drop_table("email_verification_tokens")

    op.drop_index("ix_user_sessions_user_id", table_name="user_sessions")
    op.drop_index("ix_user_sessions_refresh_token_hash", table_name="user_sessions")
    op.drop_index("ix_user_sessions_created_at", table_name="user_sessions")
    op.drop_table("user_sessions")

    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
