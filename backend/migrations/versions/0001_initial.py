"""Initial local schema."""
from alembic import op
import sqlalchemy as sa
revision = '0001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('institutions', sa.Column('id', sa.String, primary_key=True), sa.Column('name', sa.String, nullable=False), sa.Column('year', sa.String, nullable=False), sa.Column('fields', sa.JSON, nullable=False), sa.Column('logo', sa.String), sa.Column('updated', sa.String, nullable=False))
    op.create_table('students', sa.Column('id', sa.String, primary_key=True), sa.Column('institution_id', sa.String, sa.ForeignKey('institutions.id'), nullable=False), sa.Column('data', sa.JSON, nullable=False), sa.Column('status', sa.String, nullable=False), sa.Column('photo_id', sa.String), sa.Column('revision', sa.Integer, nullable=False), sa.Column('updated', sa.String, nullable=False))
    op.create_table('captures', sa.Column('id', sa.String, primary_key=True), sa.Column('student_id', sa.String, sa.ForeignKey('students.id'), nullable=False), sa.Column('state', sa.String, nullable=False), sa.Column('original', sa.String), sa.Column('approved', sa.String), sa.Column('digest', sa.String), sa.Column('created', sa.String, nullable=False))
    op.create_table('templates', sa.Column('id', sa.String, primary_key=True), sa.Column('institution_id', sa.String, sa.ForeignKey('institutions.id'), nullable=False), sa.Column('name', sa.String, nullable=False), sa.Column('path', sa.String, nullable=False), sa.Column('mapping', sa.JSON, nullable=False), sa.Column('settings', sa.JSON, nullable=False))
    op.create_table('jobs', sa.Column('id', sa.String, primary_key=True), sa.Column('key', sa.String, unique=True, nullable=False), sa.Column('kind', sa.String, nullable=False), sa.Column('state', sa.String, nullable=False), sa.Column('payload', sa.JSON, nullable=False), sa.Column('result', sa.JSON, nullable=False), sa.Column('created', sa.String, nullable=False), sa.Column('updated', sa.String, nullable=False))
    op.create_table('audit', sa.Column('id', sa.String, primary_key=True), sa.Column('action', sa.String, nullable=False), sa.Column('entity_id', sa.String, nullable=False), sa.Column('created', sa.String, nullable=False))
    op.create_table('settings', sa.Column('key', sa.String, primary_key=True), sa.Column('value', sa.JSON, nullable=False))

def downgrade():
    for table in ('settings', 'audit', 'jobs', 'templates', 'captures', 'students', 'institutions'): op.drop_table(table)
