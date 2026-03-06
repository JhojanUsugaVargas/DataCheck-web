"""
Reemplazo de sp_DiskSpace usando DMVs estándar de SQL Server.
Obtiene información de espacio en disco sin necesidad de stored procedures.
"""
import logging


def query_disk_space(cursor):
    """
    Obtiene información de espacio en disco usando sys.dm_os_volume_stats
    y sys.master_files (DMVs estándar disponibles en cualquier instancia SQL Server).
    
    Retorna una lista de diccionarios con las columnas:
    - Drive: Letra de la unidad
    - TotalGB: Tamaño total en GB
    - FreeGB: Espacio libre en GB
    - UsedGB: Espacio usado en GB
    - FreePct: Porcentaje libre
    """
    query = """
        SELECT DISTINCT
            vs.volume_mount_point AS Drive,
            CAST(vs.total_bytes / 1073741824.0 AS DECIMAL(18,2)) AS TotalGB,
            CAST(vs.available_bytes / 1073741824.0 AS DECIMAL(18,2)) AS FreeGB,
            CAST((vs.total_bytes - vs.available_bytes) / 1073741824.0 AS DECIMAL(18,2)) AS UsedGB,
            CAST(vs.available_bytes * 100.0 / vs.total_bytes AS DECIMAL(5,2)) AS FreePct
        FROM sys.master_files AS mf
        CROSS APPLY sys.dm_os_volume_stats(mf.database_id, mf.file_id) AS vs
        ORDER BY vs.volume_mount_point
    """
    try:
        cursor.execute(query)
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        
        results = []
        for row in rows:
            disco = {}
            for i, col in enumerate(columns):
                val = row[i]
                if isinstance(val, (float, int)):
                    val = round(float(val), 2)
                disco[col] = str(val)
            results.append(disco)
        
        return results
    except Exception as e:
        logging.error(f"Error al consultar espacio en disco: {e}")
        raise


def query_disk_space_summary(cursor):
    """
    Versión simplificada para uso en el resumen de performance.
    Retorna líneas formateadas para mostrar en el dashboard.
    """
    query = """
        SELECT DISTINCT
            vs.volume_mount_point AS Drive,
            CAST(vs.total_bytes / 1073741824.0 AS DECIMAL(18,2)) AS TotalGB,
            CAST(vs.available_bytes / 1073741824.0 AS DECIMAL(18,2)) AS FreeGB
        FROM sys.master_files AS mf
        CROSS APPLY sys.dm_os_volume_stats(mf.database_id, mf.file_id) AS vs
        ORDER BY vs.volume_mount_point
    """
    try:
        cursor.execute(query)
        rows = cursor.fetchall()
        return rows
    except Exception as e:
        logging.error(f"Error al consultar resumen de discos: {e}")
        return None
