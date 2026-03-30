"""auth throttle persistent

Revision ID: 20260323_0003
Revises: 20260323_0002
Create Date: 2026-03-23 17:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260323_0003"
down_revision: Union[str, Sequence[str], None] = "20260323_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "auth_login_attempts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("throttle_key", sa.String(length=512), nullable=False),
        sa.Column("failure_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("window_started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("blocked_until", sa.DateTime(timezone=True), nullable=True),
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
    op.create_index("ix_auth_login_attempts_throttle_key", "auth_login_attempts", ["throttle_key"], unique=True)
    op.create_index(
        "ix_auth_login_attempts_last_attempt_at",
        "auth_login_attempts",
        ["last_attempt_at"],
        unique=False,
    )
    op.create_index("ix_auth_login_attempts_blocked_until", "auth_login_attempts", ["blocked_until"], unique=False)
    op.create_index("ix_auth_login_attempts_created_at", "auth_login_attempts", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_auth_login_attempts_created_at", table_name="auth_login_attempts")
    op.drop_index("ix_auth_login_attempts_blocked_until", table_name="auth_login_attempts")
    op.drop_index("ix_auth_login_attempts_last_attempt_at", table_name="auth_login_attempts")
    op.drop_index("ix_auth_login_attempts_throttle_key", table_name="auth_login_attempts")
    op.drop_table("auth_login_attempts")

