"""
Servicio para validar los backups de las bases de datos de usuario.
"""
import logging

def query_backup_status(cursor):
    """
    Retorna el estado de los últimos backups FULL, DIFF y LOG por base de datos.
    """
    query = """
    SELECT  
        d.name AS BaseDatos,
        CONVERT(VARCHAR, MAX(CASE WHEN b.type = 'D' THEN b.backup_finish_date END), 120) AS UltimoBackupFULL,
        CONVERT(VARCHAR, MAX(CASE WHEN b.type = 'I' THEN b.backup_finish_date END), 120) AS UltimoBackupDIFF,
        CONVERT(VARCHAR, MAX(CASE WHEN b.type = 'L' THEN b.backup_finish_date END), 120) AS UltimoBackupLOG
    FROM sys.databases d
    LEFT JOIN msdb.dbo.backupset b
        ON d.name = b.database_name
    WHERE d.database_id > 4
    GROUP BY d.name
    ORDER BY d.name;
    """
    try:
        cursor.execute(query)
        rows = cursor.fetchall()

        if not rows:
            return {
                'type': 'info',
                'message': 'ℹ️ No se encontraron bases de datos de usuario para validar backups.'
            }

        columns = [desc[0] for desc in cursor.description]
        results = [
            dict(zip(columns, [str(v) if v is not None else '⚠️ Sin backup' for v in row]))
            for row in rows
        ]

        return {
            'type': 'table',
            'title': '💾 Validación de Backups por Base de Datos',
            'data': results
        }

    except Exception as e:
        logging.error(f"Error al consultar backups: {e}")
        raise
