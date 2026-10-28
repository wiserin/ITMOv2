"""create users credentials and sessions

Revision ID: 43b8dfef97c1
Revises:
Create Date: 2026-10-28 20:13:46.657455

"""
from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '43b8dfef97c1'
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('users',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('email', sa.VARCHAR(length=254), nullable=False),
    sa.Column('username', sa.VARCHAR(length=100), nullable=False),
    sa.Column('display_name', sa.VARCHAR(length=100), nullable=True),
    sa.Column('role', sa.Integer(), server_default=sa.text('1'), nullable=False),
    sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('display_name IS NULL OR char_length(btrim(display_name)) > 0', name='ck_users_display_name_not_blank'),
    sa.CheckConstraint('email = lower(btrim(email)) AND char_length(email) > 0', name='ck_users_email_canonical'),
    sa.CheckConstraint('role IN (1, 2, 3)', name='ck_users_role'),
    sa.CheckConstraint('updated_at >= created_at', name='ck_users_timestamps_order'),
    sa.CheckConstraint('username = btrim(username) AND char_length(username) > 0', name='ck_users_username_canonical'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('email')
    )
    op.create_table('credentials',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('password_hash', sa.TEXT(), nullable=False),
    sa.Column('is_current', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('char_length(btrim(password_hash)) > 0', name='ck_credentials_password_hash_not_blank'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], onupdate='NO ACTION', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_credentials_user_id', 'credentials', ['user_id'], unique=False)
    op.create_index('uq_credentials_current_user', 'credentials', ['user_id'], unique=True, postgresql_where=sa.text('is_current = true'))
    op.create_table('sessions',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('secret', sa.TEXT(), nullable=False),
    sa.Column('secret_hash', sa.TEXT(), nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('last_used_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('closed_at', postgresql.TIMESTAMP(timezone=True), nullable=True),
    sa.Column('expires_at', postgresql.TIMESTAMP(timezone=True), nullable=False),
    sa.CheckConstraint('char_length(btrim(secret)) > 0', name='ck_sessions_secret_not_blank'),
    sa.CheckConstraint('char_length(btrim(secret_hash)) > 0', name='ck_sessions_secret_hash_not_blank'),
    sa.CheckConstraint('closed_at IS NULL OR closed_at >= last_used_at', name='ck_sessions_closed_at'),
    sa.CheckConstraint('expires_at > last_used_at', name='ck_sessions_expires_at'),
    sa.CheckConstraint('last_used_at >= created_at', name='ck_sessions_last_used_at'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], onupdate='NO ACTION', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_sessions_open_expires_at', 'sessions', ['expires_at'], unique=False, postgresql_where=sa.text('closed_at IS NULL'))
    op.create_index('ix_sessions_user_id', 'sessions', ['user_id'], unique=False)
    # Frozen bootstrap data: this revision does not import application models.
    root_id = UUID('899f2a44-9842-4d1a-b951-03bc78d1e6e9')
    users = sa.table(
        'users',
        sa.column('id', sa.UUID()),
        sa.column('email', sa.String()),
        sa.column('username', sa.String()),
        sa.column('display_name', sa.String()),
        sa.column('role', sa.Integer()),
        sa.column('is_active', sa.Boolean()),
    )
    credentials = sa.table(
        'credentials',
        sa.column('id', sa.UUID()),
        sa.column('user_id', sa.UUID()),
        sa.column('password_hash', sa.Text()),
        sa.column('is_current', sa.Boolean()),
    )
    op.bulk_insert(users, [{
        'id': root_id,
        'email': 'root@animemap.local',
        'username': 'root',
        'display_name': 'root',
        'role': 3,
        'is_active': True,
    }])
    op.bulk_insert(credentials, [{
        'id': UUID('84dfe357-59ac-45e9-9f20-3e111ea152eb'),
        'user_id': root_id,
        # Argon2id hash of the agreed bootstrap password "root".
        'password_hash': (
            '$argon2id$v=19$m=65536,t=3,p=4$5hVJN8ysjvYcJaxIvcuEJQ'
            '$o2th3tS0S4R/OUviArV+QsinVgN7kBpaE2TjyT84h1U'
        ),
        'is_current': True,
    }])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_sessions_user_id', table_name='sessions')
    op.drop_index('ix_sessions_open_expires_at', table_name='sessions', postgresql_where=sa.text('closed_at IS NULL'))
    op.drop_table('sessions')
    op.drop_index('uq_credentials_current_user', table_name='credentials', postgresql_where=sa.text('is_current = true'))
    op.drop_index('ix_credentials_user_id', table_name='credentials')
    op.drop_table('credentials')
    op.drop_table('users')
