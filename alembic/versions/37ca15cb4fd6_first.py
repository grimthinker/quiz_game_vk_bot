"""First

Revision ID: 37ca15cb4fd6
Revises: 
Create Date: 2022-09-10 22:41:15.185030

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '37ca15cb4fd6'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('admins',
    sa.Column('id', sa.BigInteger(), nullable=False),
    sa.Column('email', sa.String(length=60), nullable=False),
    sa.Column('password', sa.Text(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('chats',
    sa.Column('id', sa.BigInteger(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('players',
    sa.Column('id', sa.BigInteger(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('themes',
    sa.Column('id', sa.BigInteger(), nullable=False),
    sa.Column('title', sa.String(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('title')
    )
    op.create_table('game_sessions',
    sa.Column('id', sa.BigInteger(), nullable=False),
    sa.Column('chat_id', sa.BigInteger(), nullable=False),
    sa.Column('creator', sa.BigInteger(), nullable=False),
    sa.ForeignKeyConstraint(['chat_id'], ['chats.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['creator'], ['players.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('questions',
    sa.Column('id', sa.BigInteger(), nullable=False),
    sa.Column('theme_id', sa.BigInteger(), nullable=False),
    sa.Column('title', sa.String(), nullable=False),
    sa.Column('points', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['theme_id'], ['themes.id'], onupdate='CASCADE', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('title')
    )
    op.create_table('answers',
    sa.Column('id', sa.BigInteger(), nullable=False),
    sa.Column('question_id', sa.BigInteger(), nullable=False),
    sa.Column('title', sa.String(), nullable=False),
    sa.Column('is_correct', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['question_id'], ['questions.id'], onupdate='CASCADE', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('players_sessions',
    sa.Column('players', sa.BigInteger(), nullable=True),
    sa.Column('game_sessions', sa.BigInteger(), nullable=True),
    sa.ForeignKeyConstraint(['game_sessions'], ['game_sessions.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['players'], ['players.id'], ondelete='CASCADE')
    )
    op.create_table('session_state',
    sa.Column('session_id', sa.BigInteger(), nullable=False),
    sa.Column('state_name', sa.Integer(), nullable=False),
    sa.Column('current_question', sa.BigInteger(), nullable=True),
    sa.Column('current_answerer', sa.BigInteger(), nullable=True),
    sa.ForeignKeyConstraint(['current_answerer'], ['players.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['current_question'], ['questions.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['session_id'], ['game_sessions.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('session_id')
    )
    op.create_table('sessions_questions',
    sa.Column('session_state_id', sa.BigInteger(), nullable=False),
    sa.Column('question_id', sa.BigInteger(), nullable=False),
    sa.Column('is_answered', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['question_id'], ['questions.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['session_state_id'], ['session_state.session_id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('session_state_id', 'question_id')
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('sessions_questions')
    op.drop_table('session_state')
    op.drop_table('players_sessions')
    op.drop_table('answers')
    op.drop_table('questions')
    op.drop_table('game_sessions')
    op.drop_table('themes')
    op.drop_table('players')
    op.drop_table('chats')
    op.drop_table('admins')
    # ### end Alembic commands ###
