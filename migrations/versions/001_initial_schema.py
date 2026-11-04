"""
Migraciones de Alembic - Versión 1: Schema inicial

Crea las tablas principales del sistema SGSM:
- usuarios
- especialidades
- pacientes
- medicos
- consultorios
- citas
"""

from alembic import op
import sqlalchemy as sa


# Revisión
revision = '001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Crear todas las tablas"""
    
    # Crear tabla usuarios
    op.create_table(
        'usuarios',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('nombre_usuario', sa.String(50), nullable=False),
        sa.Column('contrasena', sa.String(255), nullable=False),
        sa.Column('correo', sa.String(100), nullable=False),
        sa.Column('rol', sa.Enum('paciente', 'medico', 'admin', 'recepcionista', name='rolenum'), nullable=False),
        sa.Column('activo', sa.Boolean(), default=True),
        sa.Column('fecha_creacion', sa.DateTime(), nullable=False),
        sa.Column('fecha_actualizacion', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('nombre_usuario'),
        sa.UniqueConstraint('correo')
    )
    
    # Crear tabla especialidades
    op.create_table(
        'especialidades',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('nombre', sa.String(100), nullable=False),
        sa.Column('descripcion', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('nombre')
    )
    
    # Crear tabla pacientes
    op.create_table(
        'pacientes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('id_usuario', sa.Integer(), nullable=False),
        sa.Column('numero_documento', sa.String(20), nullable=False),
        sa.Column('tipo_documento', sa.String(10), default='CC'),
        sa.Column('eps', sa.String(100), nullable=False),
        sa.Column('telefono', sa.String(20), nullable=True),
        sa.Column('fecha_nacimiento', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['id_usuario'], ['usuarios.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('numero_documento')
    )
    
    # Crear tabla medicos
    op.create_table(
        'medicos',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('id_usuario', sa.Integer(), nullable=False),
        sa.Column('id_especialidad', sa.Integer(), nullable=False),
        sa.Column('numero_licencia', sa.String(50), nullable=False),
        sa.Column('colegio_profesional', sa.String(100), nullable=True),
        sa.Column('disponible', sa.Boolean(), default=True),
        sa.ForeignKeyConstraint(['id_usuario'], ['usuarios.id'], ),
        sa.ForeignKeyConstraint(['id_especialidad'], ['especialidades.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('numero_licencia')
    )
    
    # Crear tabla consultorios
    op.create_table(
        'consultorios',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('numero', sa.String(20), nullable=False),
        sa.Column('piso', sa.Integer(), nullable=False),
        sa.Column('capacidad', sa.Integer(), default=1),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('numero')
    )
    
    # Crear tabla citas
    op.create_table(
        'citas',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('id_paciente', sa.Integer(), nullable=False),
        sa.Column('id_medico', sa.Integer(), nullable=False),
        sa.Column('id_consultorio', sa.Integer(), nullable=False),
        sa.Column('fecha', sa.DateTime(), nullable=False),
        sa.Column('hora', sa.String(5), nullable=False),
        sa.Column('estado', sa.Enum('pendiente', 'confirmada', 'en_consulta', 'completada', 'cancelada', name='estadocitaenum'), default='pendiente'),
        sa.Column('motivo_consulta', sa.Text(), nullable=True),
        sa.Column('notas', sa.Text(), nullable=True),
        sa.Column('fecha_creacion', sa.DateTime(), nullable=False),
        sa.Column('fecha_actualizacion', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['id_paciente'], ['pacientes.id'], ),
        sa.ForeignKeyConstraint(['id_medico'], ['medicos.id'], ),
        sa.ForeignKeyConstraint(['id_consultorio'], ['consultorios.id'], ),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    """Eliminar todas las tablas"""
    op.drop_table('citas')
    op.drop_table('consultorios')
    op.drop_table('medicos')
    op.drop_table('pacientes')
    op.drop_table('especialidades')
    op.drop_table('usuarios')
