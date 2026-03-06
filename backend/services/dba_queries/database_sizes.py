"""
Reemplazo de sp_GetDatabaseSizes usando DMVs estándar de SQL Server.
Obtiene tamaños de Data y Log por base de datos sin necesidad de stored procedures.
"""
import logging


def query_database_sizes(cursor):
    """
    Obtiene tamaños de Data y Log por base de datos usando sys.master_files
    (DMV estándar disponible en cualquier instancia SQL Server).
    
    Retorna una lista de diccionarios con las columnas:
    - DatabaseName: Nombre de la base de datos
    - DataSizeMB: Tamaño de archivos de datos en MB
    - LogSizeMB: Tamaño de archivos de log en MB
    - TotalSizeMB: Tamaño total en MB
    """
    query = """
        SELECT 
            DB_NAME(database_id) AS DatabaseName,
            CAST(SUM(CASE WHEN type_desc = 'ROWS' THEN size END) * 8.0 / 1024 AS DECIMAL(18,2)) AS DataSizeMB,
            CAST(SUM(CASE WHEN type_desc = 'LOG' THEN size END) * 8.0 / 1024 AS DECIMAL(18,2)) AS LogSizeMB,
            CAST(SUM(size) * 8.0 / 1024 AS DECIMAL(18,2)) AS TotalSizeMB
        FROM sys.master_files
        WHERE database_id > 4  -- Excluye bases de sistema (master, model, msdb, tempdb)
        GROUP BY database_id
        ORDER BY SUM(size) DESC
    """
    try:
        cursor.execute(query)
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        
        results = []
        for row in rows:
            item = {}
            for i, col in enumerate(columns):
                val = row[i]
                if isinstance(val, (float, int)):
                    val = round(float(val), 2)
                item[col] = str(val)
            results.append(item)
        
        return results
    except Exception as e:
        logging.error(f"Error al consultar tamaños de bases de datos: {e}")
        raise
