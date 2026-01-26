"""Initial schema - create all tables

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-01-25 22:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID


# revision identifiers, used by Alembic.
revision: str = '0001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', UUID(as_uuid=True), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255), nullable=True),
        sa.Column('phone', sa.String(50), nullable=True),
        sa.Column('location', sa.String(255), nullable=True),
        sa.Column('websites', sa.ARRAY(sa.String()), nullable=True),
        sa.Column('linkedin_url', sa.String(512), nullable=True),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)

    # Create documents table
    op.create_table(
        'documents',
        sa.Column('id', UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), nullable=False),
        sa.Column('filename', sa.String(255), nullable=False),
        sa.Column('file_path', sa.String(512), nullable=True),
        sa.Column('file_size_bytes', sa.Integer(), nullable=True),
        sa.Column('mime_type', sa.String(100), nullable=True),
        sa.Column('source_type', sa.String(50), nullable=False),
        sa.Column('source_url', sa.String(1024), nullable=True),
        sa.Column('raw_text', sa.Text(), nullable=True),
        sa.Column('document_class', sa.String(50), nullable=True),
        sa.Column('classification_confidence', sa.Float(), nullable=True),
        sa.Column('classification_reasoning', sa.Text(), nullable=True),
        sa.Column('verified_by_user', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('processing_status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('processing_error', sa.Text(), nullable=True),
        sa.Column('processing_logs', JSONB(), nullable=True),
        sa.Column('checkpoint_state', JSONB(), nullable=True),
        sa.Column('checkpoint_step', sa.String(50), nullable=True),
        sa.Column('checkpoint_timestamp', sa.DateTime(), nullable=True),
        sa.Column('processing_attempt', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE')
    )
    op.create_index('ix_documents_user_id', 'documents', ['user_id'])
    op.create_index('ix_documents_user_class', 'documents', ['user_id', 'document_class'])

    # Create experiences table
    op.create_table(
        'experiences',
        sa.Column('id', UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), nullable=False),
        sa.Column('source_document_id', UUID(as_uuid=True), nullable=True),
        sa.Column('company', sa.String(255), nullable=False),
        sa.Column('role', sa.String(255), nullable=False),
        sa.Column('location', sa.String(255), nullable=True),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.Column('is_current', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['source_document_id'], ['documents.id'], ondelete='SET NULL')
    )
    op.create_index('ix_experiences_user_id', 'experiences', ['user_id'])

    # Create experience_bullets table
    op.create_table(
        'experience_bullets',
        sa.Column('id', UUID(as_uuid=True), nullable=False),
        sa.Column('experience_id', UUID(as_uuid=True), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('order_index', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('skills', sa.ARRAY(sa.String()), nullable=True),
        sa.Column('metrics', sa.Text(), nullable=True),
        sa.Column('action_verbs', sa.ARRAY(sa.String()), nullable=True),
        sa.Column('embedding_id', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['experience_id'], ['experiences.id'], ondelete='CASCADE')
    )
    op.create_index('ix_experience_bullets_experience_id', 'experience_bullets', ['experience_id'])

    # Create projects table
    op.create_table(
        'projects',
        sa.Column('id', UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), nullable=False),
        sa.Column('source_document_id', UUID(as_uuid=True), nullable=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('technologies', sa.ARRAY(sa.String()), nullable=True),
        sa.Column('start_date', sa.Date(), nullable=True),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['source_document_id'], ['documents.id'], ondelete='SET NULL')
    )
    op.create_index('ix_projects_user_id', 'projects', ['user_id'])

    # Create project_bullets table
    op.create_table(
        'project_bullets',
        sa.Column('id', UUID(as_uuid=True), nullable=False),
        sa.Column('project_id', UUID(as_uuid=True), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('order_index', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('skills', sa.ARRAY(sa.String()), nullable=True),
        sa.Column('metrics', sa.Text(), nullable=True),
        sa.Column('embedding_id', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE')
    )
    op.create_index('ix_project_bullets_project_id', 'project_bullets', ['project_id'])

    # Create project_links table
    op.create_table(
        'project_links',
        sa.Column('id', UUID(as_uuid=True), nullable=False),
        sa.Column('project_id', UUID(as_uuid=True), nullable=False),
        sa.Column('url', sa.String(1024), nullable=False),
        sa.Column('link_type', sa.String(50), nullable=False),
        sa.Column('title', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE')
    )
    op.create_index('ix_project_links_project_id', 'project_links', ['project_id'])

    # Create skills table
    op.create_table(
        'skills',
        sa.Column('id', UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('category', sa.String(50), nullable=False, server_default='other'),
        sa.Column('proficiency', sa.String(50), nullable=True),
        sa.Column('years_of_experience', sa.Integer(), nullable=True),
        sa.Column('is_highlighted', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('display_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('embedding_id', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE')
    )
    op.create_index('ix_skills_user_id', 'skills', ['user_id'])
    op.create_index('ix_skills_user_category', 'skills', ['user_id', 'category'])

    # Create publications table
    op.create_table(
        'publications',
        sa.Column('id', UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), nullable=False),
        sa.Column('source_document_id', UUID(as_uuid=True), nullable=True),
        sa.Column('title', sa.String(512), nullable=False),
        sa.Column('authors', sa.Text(), nullable=False),
        sa.Column('publication_type', sa.String(50), nullable=False, server_default='other'),
        sa.Column('venue', sa.String(255), nullable=True),
        sa.Column('publisher', sa.String(255), nullable=True),
        sa.Column('publication_date', sa.Date(), nullable=True),
        sa.Column('doi', sa.String(255), nullable=True),
        sa.Column('arxiv_id', sa.String(100), nullable=True),
        sa.Column('url', sa.String(1024), nullable=True),
        sa.Column('abstract', sa.Text(), nullable=True),
        sa.Column('citation_count', sa.Integer(), nullable=True),
        sa.Column('is_first_author', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('author_position', sa.Integer(), nullable=True),
        sa.Column('display_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('embedding_id', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['source_document_id'], ['documents.id'], ondelete='SET NULL')
    )
    op.create_index('ix_publications_user_id', 'publications', ['user_id'])
    op.create_index('ix_publications_user_type', 'publications', ['user_id', 'publication_type'])

    # Create supporting_documents table
    op.create_table(
        'supporting_documents',
        sa.Column('id', UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), nullable=False),
        sa.Column('source_document_id', UUID(as_uuid=True), nullable=True),
        sa.Column('experience_id', UUID(as_uuid=True), nullable=True),
        sa.Column('project_id', UUID(as_uuid=True), nullable=True),
        sa.Column('doc_type', sa.String(50), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('authors', sa.Text(), nullable=True),
        sa.Column('publication', sa.String(255), nullable=True),
        sa.Column('doi_url', sa.String(512), nullable=True),
        sa.Column('issuer', sa.String(255), nullable=True),
        sa.Column('issue_date', sa.Date(), nullable=True),
        sa.Column('expiry_date', sa.Date(), nullable=True),
        sa.Column('credential_id', sa.String(255), nullable=True),
        sa.Column('credential_url', sa.String(512), nullable=True),
        sa.Column('recommender_name', sa.String(255), nullable=True),
        sa.Column('recommender_title', sa.String(255), nullable=True),
        sa.Column('recommender_relationship', sa.String(255), nullable=True),
        sa.Column('portfolio_url', sa.String(512), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['source_document_id'], ['documents.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['experience_id'], ['experiences.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.CheckConstraint(
            "(experience_id IS NOT NULL AND project_id IS NULL) OR "
            "(experience_id IS NULL AND project_id IS NOT NULL)",
            name="ck_supporting_docs_parent"
        )
    )
    op.create_index('ix_supporting_documents_user_id', 'supporting_documents', ['user_id'])

    # Create job_descriptions table
    op.create_table(
        'job_descriptions',
        sa.Column('id', UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), nullable=False),
        sa.Column('source_url', sa.String(1024), nullable=True),
        sa.Column('raw_text', sa.Text(), nullable=False),
        sa.Column('company', sa.String(255), nullable=True),
        sa.Column('role', sa.String(255), nullable=True),
        sa.Column('location', sa.String(255), nullable=True),
        sa.Column('salary_range', sa.String(100), nullable=True),
        sa.Column('experience_level', sa.String(50), nullable=True),
        sa.Column('processing_status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('processing_error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE')
    )
    op.create_index('ix_job_descriptions_user_id', 'job_descriptions', ['user_id'])

    # Create job_requirements table
    op.create_table(
        'job_requirements',
        sa.Column('id', UUID(as_uuid=True), nullable=False),
        sa.Column('job_id', UUID(as_uuid=True), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('requirement_type', sa.String(50), nullable=False),
        sa.Column('importance_score', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('keywords', sa.ARRAY(sa.String()), nullable=True),
        sa.Column('embedding_id', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['job_id'], ['job_descriptions.id'], ondelete='CASCADE'),
        sa.CheckConstraint("importance_score >= 1 AND importance_score <= 5", name="ck_importance_range")
    )
    op.create_index('ix_job_requirements_job_id', 'job_requirements', ['job_id'])

    # Create resume_matches table
    op.create_table(
        'resume_matches',
        sa.Column('id', UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), nullable=False),
        sa.Column('job_id', UUID(as_uuid=True), nullable=False),
        sa.Column('overall_match_score', sa.Float(), nullable=False),
        sa.Column('skill_coverage', sa.Float(), nullable=False),
        sa.Column('experience_relevance', sa.Float(), nullable=False),
        sa.Column('processing_status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['job_id'], ['job_descriptions.id'], ondelete='CASCADE')
    )
    op.create_index('ix_resume_matches_user_id', 'resume_matches', ['user_id'])
    op.create_index('ix_resume_matches_job_id', 'resume_matches', ['job_id'])
    op.create_index('ix_resume_matches_user_job', 'resume_matches', ['user_id', 'job_id'])

    # Create resume_match_items table
    op.create_table(
        'resume_match_items',
        sa.Column('id', UUID(as_uuid=True), nullable=False),
        sa.Column('match_id', UUID(as_uuid=True), nullable=False),
        sa.Column('requirement_id', UUID(as_uuid=True), nullable=False),
        sa.Column('experience_bullet_id', UUID(as_uuid=True), nullable=True),
        sa.Column('project_bullet_id', UUID(as_uuid=True), nullable=True),
        sa.Column('relevance_score', sa.Float(), nullable=False),
        sa.Column('match_explanation', sa.Text(), nullable=True),
        sa.Column('included_in_resume', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['match_id'], ['resume_matches.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['requirement_id'], ['job_requirements.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['experience_bullet_id'], ['experience_bullets.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['project_bullet_id'], ['project_bullets.id'], ondelete='SET NULL')
    )
    op.create_index('ix_resume_match_items_match_id', 'resume_match_items', ['match_id'])

    # Create background_tasks table
    op.create_table(
        'background_tasks',
        sa.Column('id', UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), nullable=False),
        sa.Column('task_type', sa.String(100), nullable=False),
        sa.Column('entity_id', UUID(as_uuid=True), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('progress', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('result', JSONB(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE')
    )
    op.create_index('ix_background_tasks_user_status', 'background_tasks', ['user_id', 'status'])

    # Create search_campaigns table
    op.create_table(
        'search_campaigns',
        sa.Column('id', UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='draft'),
        sa.Column('target_roles', sa.ARRAY(sa.String()), nullable=False),
        sa.Column('target_locations', sa.ARRAY(sa.String()), nullable=False),
        sa.Column('target_companies', sa.ARRAY(sa.String()), nullable=True),
        sa.Column('keywords', sa.ARRAY(sa.String()), nullable=False),
        sa.Column('excluded_keywords', sa.ARRAY(sa.String()), nullable=True),
        sa.Column('min_salary', sa.Integer(), nullable=True),
        sa.Column('max_salary', sa.Integer(), nullable=True),
        sa.Column('remote_preference', sa.String(50), nullable=True),
        sa.Column('experience_level', sa.String(50), nullable=True),
        sa.Column('last_run_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('next_run_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('settings', JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE')
    )
    op.create_index('ix_search_campaigns_user_id', 'search_campaigns', ['user_id'])

    # Create discovered_jobs table
    op.create_table(
        'discovered_jobs',
        sa.Column('id', UUID(as_uuid=True), nullable=False),
        sa.Column('campaign_id', UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), nullable=False),
        sa.Column('external_id', sa.String(255), nullable=False),
        sa.Column('source', sa.String(50), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('company', sa.String(255), nullable=False),
        sa.Column('location', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('requirements', sa.Text(), nullable=True),
        sa.Column('salary_min', sa.Integer(), nullable=True),
        sa.Column('salary_max', sa.Integer(), nullable=True),
        sa.Column('salary_currency', sa.String(10), nullable=True),
        sa.Column('url', sa.String(1024), nullable=False),
        sa.Column('posted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('match_score', sa.Float(), nullable=True),
        sa.Column('match_reasoning', sa.Text(), nullable=True),
        sa.Column('is_qualified', sa.Boolean(), nullable=True),
        sa.Column('raw_data', JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['campaign_id'], ['search_campaigns.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE')
    )
    op.create_index('ix_discovered_jobs_campaign_id', 'discovered_jobs', ['campaign_id'])
    op.create_index('ix_discovered_jobs_user_id', 'discovered_jobs', ['user_id'])
    op.create_index('ix_discovered_jobs_user_source_external', 'discovered_jobs', ['user_id', 'source', 'external_id'])
    op.create_index('ix_discovered_jobs_campaign_score', 'discovered_jobs', ['campaign_id', 'match_score'])

    # Create job_applications table
    op.create_table(
        'job_applications',
        sa.Column('id', UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), nullable=False),
        sa.Column('discovered_job_id', UUID(as_uuid=True), nullable=True),
        sa.Column('campaign_id', UUID(as_uuid=True), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='discovered'),
        sa.Column('status_history', JSONB(), nullable=True),
        sa.Column('job_title', sa.String(255), nullable=False),
        sa.Column('company', sa.String(255), nullable=False),
        sa.Column('job_url', sa.String(1024), nullable=True),
        sa.Column('resume_id', UUID(as_uuid=True), nullable=True),
        sa.Column('cover_letter', sa.Text(), nullable=True),
        sa.Column('applied_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('response_received_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('interview_scheduled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('rejection_reason', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['discovered_job_id'], ['discovered_jobs.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['campaign_id'], ['search_campaigns.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['resume_id'], ['documents.id'], ondelete='SET NULL')
    )
    op.create_index('ix_job_applications_user_id', 'job_applications', ['user_id'])
    op.create_index('ix_job_applications_user_status', 'job_applications', ['user_id', 'status'])
    op.create_index('ix_job_applications_user_company', 'job_applications', ['user_id', 'company'])

    # Create company_profiles table
    op.create_table(
        'company_profiles',
        sa.Column('id', UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('website', sa.String(512), nullable=True),
        sa.Column('linkedin_url', sa.String(512), nullable=True),
        sa.Column('careers_url', sa.String(512), nullable=True),
        sa.Column('industry', sa.String(255), nullable=True),
        sa.Column('size', sa.String(100), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('tech_stack', sa.ARRAY(sa.String()), nullable=True),
        sa.Column('culture_notes', sa.Text(), nullable=True),
        sa.Column('interview_process', sa.Text(), nullable=True),
        sa.Column('glassdoor_rating', sa.Float(), nullable=True),
        sa.Column('research_data', JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE')
    )
    op.create_index('ix_company_profiles_user_id', 'company_profiles', ['user_id'])
    op.create_index('ix_company_profiles_user_name', 'company_profiles', ['user_id', 'name'])

    # Create company_contacts table
    op.create_table(
        'company_contacts',
        sa.Column('id', UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), nullable=False),
        sa.Column('company_profile_id', UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('linkedin_url', sa.String(512), nullable=False),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('relevance_score', sa.Float(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['company_profile_id'], ['company_profiles.id'], ondelete='CASCADE')
    )
    op.create_index('ix_company_contacts_user_id', 'company_contacts', ['user_id'])
    op.create_index('ix_company_contacts_company_profile_id', 'company_contacts', ['company_profile_id'])

    # Create networking_outreach table
    op.create_table(
        'networking_outreach',
        sa.Column('id', UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), nullable=False),
        sa.Column('contact_id', UUID(as_uuid=True), nullable=False),
        sa.Column('application_id', UUID(as_uuid=True), nullable=True),
        sa.Column('channel', sa.String(50), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('subject', sa.String(255), nullable=True),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('response_received_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('follow_up_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['contact_id'], ['company_contacts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['application_id'], ['job_applications.id'], ondelete='SET NULL')
    )
    op.create_index('ix_networking_outreach_user_id', 'networking_outreach', ['user_id'])
    op.create_index('ix_networking_outreach_user_status', 'networking_outreach', ['user_id', 'status'])
    op.create_index('ix_networking_outreach_contact', 'networking_outreach', ['contact_id'])

    # Create automation_logs table
    op.create_table(
        'automation_logs',
        sa.Column('id', UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), nullable=False),
        sa.Column('action_type', sa.String(100), nullable=False),
        sa.Column('entity_type', sa.String(100), nullable=False),
        sa.Column('entity_id', UUID(as_uuid=True), nullable=True),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('details', JSONB(), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE')
    )
    op.create_index('ix_automation_logs_user_action', 'automation_logs', ['user_id', 'action_type'])
    op.create_index('ix_automation_logs_user_created', 'automation_logs', ['user_id', 'created_at'])


def downgrade() -> None:
    op.drop_table('automation_logs')
    op.drop_table('networking_outreach')
    op.drop_table('company_contacts')
    op.drop_table('company_profiles')
    op.drop_table('job_applications')
    op.drop_table('discovered_jobs')
    op.drop_table('search_campaigns')
    op.drop_table('background_tasks')
    op.drop_table('resume_match_items')
    op.drop_table('resume_matches')
    op.drop_table('job_requirements')
    op.drop_table('job_descriptions')
    op.drop_table('supporting_documents')
    op.drop_table('publications')
    op.drop_table('skills')
    op.drop_table('project_links')
    op.drop_table('project_bullets')
    op.drop_table('projects')
    op.drop_table('experience_bullets')
    op.drop_table('experiences')
    op.drop_table('documents')
    op.drop_table('users')
