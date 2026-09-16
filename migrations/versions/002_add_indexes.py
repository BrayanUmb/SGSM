"""
Migraciones de Alembic - Versión 2: Agregar índices

Optimiza las consultas más frecuentes agregando índices en:
- usuarios: nombre_usuario, correo
- pacientes: numero_documento, id_usuario
- medicos: numero_licencia, id_usuario, id_especialidad
- citas: id_paciente, id_medico, estado, fecha
"""

from alembic import op
import sqlalchemy as sa


# Revisión
revision = '002_add_indexes'
down_revision = '001_initial_schema'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Agregar índices para optimizar consultas"""
    
    # Índices en tabla usuarios
    op.create_index('ix_usuarios_nombre_usuario', 'usuarios', ['nombre_usuario'])
    op.create_index('ix_usuarios_correo', 'usuarios', ['correo'])
    
    # Índices en tabla pacientes
    op.create_index('ix_pacientes_numero_documento', 'pacientes', ['numero_documento'])
    op.create_index('ix_pacientes_id_usuario', 'pacientes', ['id_usuario'])
    
    # Índices en tabla medicos
    op.create_index('ix_medicos_numero_licencia', 'medicos', ['numero_licencia'])
    op.create_index('ix_medicos_id_usuario', 'medicos', ['id_usuario'])
    op.create_index('ix_medicos_id_especialidad', 'medicos', ['id_especialidad'])
    op.create_index('ix_medicos_disponible', 'medicos', ['disponible'])
    
    # Índices en tabla citas
    op.create_index('ix_citas_id_paciente', 'citas', ['id_paciente'])
    op.create_index('ix_citas_id_medico', 'citas', ['id_medico'])
    op.create_index('ix_citas_estado', 'citas', ['estado'])
    op.create_index('ix_citas_fecha', 'citas', ['fecha'])
    
    # Índice compuesto para búsquedas frecuentes de citas por paciente y estado
    op.create_index('ix_citas_paciente_estado', 'citas', ['id_paciente', 'estado'])
    
    # Índice compuesto para búsquedas frecuentes de citas por médico y fecha
    op.create_index('ix_citas_medico_fecha', 'citas', ['id_medico', 'fecha'])


def downgrade() -> None:
    """Eliminar todos los índices"""
    op.drop_index('ix_citas_medico_fecha', table_name='citas')
    op.drop_index('ix_citas_paciente_estado', table_name='citas')
    op.drop_index('ix_citas_fecha', table_name='citas')
    op.drop_index('ix_citas_estado', table_name='citas')
    op.drop_index('ix_citas_id_medico', table_name='citas')
    op.drop_index('ix_citas_id_paciente', table_name='citas')
    op.drop_index('ix_medicos_disponible', table_name='medicos')
    op.drop_index('ix_medicos_id_especialidad', table_name='medicos')
    op.drop_index('ix_medicos_id_usuario', table_name='medicos')
    op.drop_index('ix_medicos_numero_licencia', table_name='medicos')
    op.drop_index('ix_pacientes_id_usuario', table_name='pacientes')
    op.drop_index('ix_pacientes_numero_documento', table_name='pacientes')
    op.drop_index('ix_usuarios_correo', table_name='usuarios')
    op.drop_index('ix_usuarios_nombre_usuario', table_name='usuarios')
