"""create users table, add missing columns, add user_id to all tables

Revision ID: a1b2c3d4e5f6
Revises: 143eb2c881ff
Create Date: 2026-03-27 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '143eb2c881ff'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Create users table ──
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('first_name', sa.String(length=100), nullable=False),
        sa.Column('last_name', sa.String(length=100), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('role', sa.String(length=50), nullable=False, server_default='Staff'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)

    # ── Create appointments table ──
    op.create_table(
        'appointments',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('appointment_id', sa.String(length=50), nullable=False),
        sa.Column('patient_first_name', sa.String(length=100), nullable=False),
        sa.Column('patient_last_name', sa.String(length=100), nullable=False),
        sa.Column('patient_name', sa.String(length=200), nullable=False),
        sa.Column('patient_dob', sa.String(length=20), nullable=True),
        sa.Column('patient_phone', sa.String(length=20), nullable=True),
        sa.Column('member_id', sa.String(length=100), nullable=True),
        sa.Column('payer_id', sa.String(length=50), nullable=True),
        sa.Column('payer_name', sa.String(length=200), nullable=True),
        sa.Column('provider_npi', sa.String(length=20), nullable=True),
        sa.Column('provider_name', sa.String(length=200), nullable=True),
        sa.Column('appointment_date', sa.String(length=20), nullable=False),
        sa.Column('appointment_time', sa.String(length=10), nullable=True),
        sa.Column('appointment_type', sa.String(length=100), nullable=True),
        sa.Column('service_type_code', sa.String(length=10), nullable=True),
        sa.Column('diagnosis_code', sa.String(length=20), nullable=True),
        sa.Column('procedure_code', sa.String(length=20), nullable=True),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='scheduled'),
        sa.Column('eligibility_check_id', sa.String(length=20), nullable=True),
        sa.Column('eligibility_status', sa.String(length=30), nullable=True),
        sa.Column('pa_check_id', sa.String(length=20), nullable=True),
        sa.Column('pa_status', sa.String(length=30), nullable=True),
        sa.Column('copay', sa.Float(), nullable=True),
        sa.Column('deductible', sa.Float(), nullable=True),
        sa.Column('deductible_max', sa.Float(), nullable=True),
        sa.Column('ehr_source', sa.String(length=50), nullable=True),
        sa.Column('ehr_appointment_id', sa.String(length=100), nullable=True),
        sa.Column('last_checked_at', sa.DateTime(), nullable=True),
        sa.Column('check_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_appointments_appointment_id', 'appointments', ['appointment_id'], unique=True)
    op.create_index('ix_appointments_user_id', 'appointments', ['user_id'])

    # ── Create agent_runs table ──
    op.create_table(
        'agent_runs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('run_id', sa.String(length=50), nullable=False),
        sa.Column('trigger', sa.String(length=30), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='running'),
        sa.Column('total_appointments', sa.Integer(), server_default='0'),
        sa.Column('checked', sa.Integer(), server_default='0'),
        sa.Column('eligible', sa.Integer(), server_default='0'),
        sa.Column('inactive', sa.Integer(), server_default='0'),
        sa.Column('pa_required', sa.Integer(), server_default='0'),
        sa.Column('pa_submitted', sa.Integer(), server_default='0'),
        sa.Column('errors', sa.Integer(), server_default='0'),
        sa.Column('execution_time', sa.Float(), server_default='0.0'),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_agent_runs_run_id', 'agent_runs', ['run_id'], unique=True)
    op.create_index('ix_agent_runs_user_id', 'agent_runs', ['user_id'])

    # ── Add missing column to eligibility_checks ──
    op.add_column('eligibility_checks',
                   sa.Column('clearinghouse_provider', sa.String(length=30), nullable=True))

    # ── Add user_id to eligibility_checks ──
    op.add_column('eligibility_checks',
                   sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True))
    op.create_index('ix_eligibility_checks_user_id', 'eligibility_checks', ['user_id'])

    # ── Add user_id to prior_auth_checks ──
    op.add_column('prior_auth_checks',
                   sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True))
    op.create_index('ix_prior_auth_checks_user_id', 'prior_auth_checks', ['user_id'])


def downgrade() -> None:
    op.drop_index('ix_prior_auth_checks_user_id', table_name='prior_auth_checks')
    op.drop_column('prior_auth_checks', 'user_id')

    op.drop_index('ix_eligibility_checks_user_id', table_name='eligibility_checks')
    op.drop_column('eligibility_checks', 'user_id')
    op.drop_column('eligibility_checks', 'clearinghouse_provider')

    op.drop_index('ix_agent_runs_user_id', table_name='agent_runs')
    op.drop_index('ix_agent_runs_run_id', table_name='agent_runs')
    op.drop_table('agent_runs')

    op.drop_index('ix_appointments_user_id', table_name='appointments')
    op.drop_index('ix_appointments_appointment_id', table_name='appointments')
    op.drop_table('appointments')

    op.drop_index('ix_users_email', table_name='users')
    op.drop_table('users')
