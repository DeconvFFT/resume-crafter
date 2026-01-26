"""Add automation tables for job search campaigns and networking

Revision ID: 5c0d4ee95f92
Revises: 4b9c3dd94e81
Create Date: 2026-01-25 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '5c0d4ee95f92'
down_revision: Union[str, None] = '4b9c3dd94e81'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create automation tables for job search, applications, and networking."""

    # Create search_campaigns table
    op.create_table(
        'search_campaigns',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='draft'),
        sa.Column('target_roles', sa.ARRAY(sa.String), nullable=False),
        sa.Column('target_locations', sa.ARRAY(sa.String), nullable=False),
        sa.Column('target_companies', sa.ARRAY(sa.String), nullable=True),
        sa.Column('keywords', sa.ARRAY(sa.String), nullable=False),
        sa.Column('excluded_keywords', sa.ARRAY(sa.String), nullable=True),
        sa.Column('min_salary', sa.Integer, nullable=True),
        sa.Column('max_salary', sa.Integer, nullable=True),
        sa.Column('remote_preference', sa.String(50), nullable=True),
        sa.Column('experience_level', sa.String(50), nullable=True),
        sa.Column('last_run_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('next_run_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('settings', postgresql.JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_search_campaigns_user_id', 'search_campaigns', ['user_id'])

    # Create discovered_jobs table
    op.create_table(
        'discovered_jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('campaign_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('search_campaigns.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('external_id', sa.String(255), nullable=False),
        sa.Column('source', sa.String(50), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('company', sa.String(255), nullable=False),
        sa.Column('location', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=False),
        sa.Column('requirements', sa.Text, nullable=True),
        sa.Column('salary_min', sa.Integer, nullable=True),
        sa.Column('salary_max', sa.Integer, nullable=True),
        sa.Column('salary_currency', sa.String(10), nullable=True),
        sa.Column('url', sa.String(1024), nullable=False),
        sa.Column('posted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('match_score', sa.Float, nullable=True),
        sa.Column('match_reasoning', sa.Text, nullable=True),
        sa.Column('is_qualified', sa.Boolean, nullable=True),
        sa.Column('raw_data', postgresql.JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_discovered_jobs_campaign_id', 'discovered_jobs', ['campaign_id'])
    op.create_index('ix_discovered_jobs_user_id', 'discovered_jobs', ['user_id'])
    op.create_index('ix_discovered_jobs_user_source_external', 'discovered_jobs', ['user_id', 'source', 'external_id'])
    op.create_index('ix_discovered_jobs_campaign_score', 'discovered_jobs', ['campaign_id', 'match_score'])

    # Create job_applications table
    op.create_table(
        'job_applications',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('discovered_job_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('discovered_jobs.id', ondelete='SET NULL'), nullable=True),
        sa.Column('campaign_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('search_campaigns.id', ondelete='SET NULL'), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='discovered'),
        sa.Column('status_history', postgresql.JSONB, nullable=True),
        sa.Column('job_title', sa.String(255), nullable=False),
        sa.Column('company', sa.String(255), nullable=False),
        sa.Column('job_url', sa.String(1024), nullable=True),
        sa.Column('resume_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('documents.id', ondelete='SET NULL'), nullable=True),
        sa.Column('cover_letter', sa.Text, nullable=True),
        sa.Column('applied_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('response_received_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('interview_scheduled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('rejection_reason', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_job_applications_user_id', 'job_applications', ['user_id'])
    op.create_index('ix_job_applications_user_status', 'job_applications', ['user_id', 'status'])
    op.create_index('ix_job_applications_user_company', 'job_applications', ['user_id', 'company'])

    # Create company_profiles table
    op.create_table(
        'company_profiles',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('website', sa.String(512), nullable=True),
        sa.Column('linkedin_url', sa.String(512), nullable=True),
        sa.Column('careers_url', sa.String(512), nullable=True),
        sa.Column('industry', sa.String(255), nullable=True),
        sa.Column('size', sa.String(100), nullable=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('tech_stack', sa.ARRAY(sa.String), nullable=True),
        sa.Column('culture_notes', sa.Text, nullable=True),
        sa.Column('interview_process', sa.Text, nullable=True),
        sa.Column('glassdoor_rating', sa.Float, nullable=True),
        sa.Column('research_data', postgresql.JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_company_profiles_user_id', 'company_profiles', ['user_id'])
    op.create_index('ix_company_profiles_user_name', 'company_profiles', ['user_id', 'name'])

    # Create company_contacts table
    op.create_table(
        'company_contacts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('company_profile_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('company_profiles.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('linkedin_url', sa.String(512), nullable=False),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('relevance_score', sa.Float, nullable=True),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_company_contacts_user_id', 'company_contacts', ['user_id'])
    op.create_index('ix_company_contacts_company_profile_id', 'company_contacts', ['company_profile_id'])

    # Create networking_outreach table
    op.create_table(
        'networking_outreach',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('contact_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('company_contacts.id', ondelete='CASCADE'), nullable=False),
        sa.Column('application_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('job_applications.id', ondelete='SET NULL'), nullable=True),
        sa.Column('channel', sa.String(50), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('subject', sa.String(255), nullable=True),
        sa.Column('message', sa.Text, nullable=False),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('response_received_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('follow_up_count', sa.Integer, nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_networking_outreach_user_id', 'networking_outreach', ['user_id'])
    op.create_index('ix_networking_outreach_contact_id', 'networking_outreach', ['contact_id'])
    op.create_index('ix_networking_outreach_user_status', 'networking_outreach', ['user_id', 'status'])
    op.create_index('ix_networking_outreach_contact', 'networking_outreach', ['contact_id'])

    # Create automation_logs table
    op.create_table(
        'automation_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('action_type', sa.String(100), nullable=False),
        sa.Column('entity_type', sa.String(100), nullable=False),
        sa.Column('entity_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('details', postgresql.JSONB, nullable=True),
        sa.Column('duration_ms', sa.Integer, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_automation_logs_user_id', 'automation_logs', ['user_id'])
    op.create_index('ix_automation_logs_user_action', 'automation_logs', ['user_id', 'action_type'])
    op.create_index('ix_automation_logs_user_created', 'automation_logs', ['user_id', 'created_at'])


def downgrade() -> None:
    """Drop automation tables in reverse order to handle foreign key dependencies."""
    op.drop_table('automation_logs')
    op.drop_table('networking_outreach')
    op.drop_table('company_contacts')
    op.drop_table('company_profiles')
    op.drop_table('job_applications')
    op.drop_table('discovered_jobs')
    op.drop_table('search_campaigns')
