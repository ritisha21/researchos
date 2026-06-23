"""initial schema — papers and roadmaps tables

Revision ID: 0001_initial
Revises:
Create Date: 2026-01-01 00:00:00

This is the baseline migration. It mirrors exactly what main.py's
create_all() previously generated, so applying it against a fresh
database produces an identical schema to before.

After this migration exists, main.py should stop calling create_all()
and instead the operator should run:
    alembic upgrade head
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "papers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(length=1024), nullable=False),
        sa.Column("authors", postgresql.ARRAY(sa.String()), nullable=False, server_default="{}"),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("abstract", sa.Text(), nullable=True),
        sa.Column("doi", sa.String(length=256), nullable=True),
        sa.Column("arxiv_id", sa.String(length=64), nullable=True),
        sa.Column("semantic_scholar_id", sa.String(length=64), nullable=True),
        sa.Column("citation_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("url", sa.String(length=2048), nullable=True),
        sa.Column("source", sa.String(length=32), nullable=False, server_default="manual"),
        sa.Column("has_pdf", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("pdf_path", sa.String(length=512), nullable=True),
        sa.Column("is_indexed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("key_contributions", sa.Text(), nullable=True),
        sa.Column("limitations", sa.Text(), nullable=True),
        sa.Column("future_work", sa.Text(), nullable=True),
        sa.Column("beginner_explanation", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("doi", name="uq_papers_doi"),
        sa.UniqueConstraint("arxiv_id", name="uq_papers_arxiv_id"),
        sa.UniqueConstraint("semantic_scholar_id", name="uq_papers_semantic_scholar_id"),
    )
    op.create_index("ix_papers_id", "papers", ["id"])
    op.create_index("ix_papers_title", "papers", ["title"])

    op.create_table(
        "roadmaps",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("topic", sa.String(length=512), nullable=False),
        sa.Column("topic_display", sa.String(length=512), nullable=False),
        sa.Column("prerequisites", postgresql.JSON(), nullable=False, server_default="[]"),
        sa.Column("learning_path", postgresql.JSON(), nullable=False, server_default="[]"),
        sa.Column("foundational_papers", postgresql.JSON(), nullable=False, server_default="[]"),
        sa.Column("intermediate_papers", postgresql.JSON(), nullable=False, server_default="[]"),
        sa.Column("advanced_papers", postgresql.JSON(), nullable=False, server_default="[]"),
        sa.Column("research_frontiers", postgresql.JSON(), nullable=False, server_default="[]"),
        sa.Column("research_gaps", postgresql.JSON(), nullable=False, server_default="[]"),
        sa.Column("recommended_reading_order", postgresql.JSON(), nullable=False, server_default="[]"),
        sa.Column("generated_by_model", sa.String(length=128), nullable=False, server_default=""),
        sa.Column("raw_llm_response", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("topic", name="uq_roadmaps_topic"),
    )
    op.create_index("ix_roadmaps_topic", "roadmaps", ["topic"])


def downgrade() -> None:
    op.drop_index("ix_roadmaps_topic", table_name="roadmaps")
    op.drop_table("roadmaps")
    op.drop_index("ix_papers_title", table_name="papers")
    op.drop_index("ix_papers_id", table_name="papers")
    op.drop_table("papers")
