"""
Consulta de tamaño de bases de datos (Data + Log) agrupada.
"""
import logging


def query_database_sizes(cursor):
    """
    Obtiene el tamaño total (Data + Log) de cada base de datos en MB.
    """
    query = """
        SET NOCOUNT ON;

        SELECT 
            DB_NAME(database_id) AS DatabaseName,
            CAST(SUM(CASE WHEN type = 0 THEN size END) * 8.0 / 1024 / 1024 AS DECIMAL(10,2)) AS DataSizeGB,
            CAST(SUM(CASE WHEN type = 1 THEN size END) * 8.0 / 1024 / 1024 AS DECIMAL(10,2)) AS LogSizeGB,
            CAST(SUM(size) * 8.0 / 1024 / 1024 AS DECIMAL(10,2)) AS TotalSizeGB
        FROM sys.master_files
        WHERE DB_NAME(database_id) IS NOT NULL
        AND DB_NAME(database_id) NOT IN ('master', 'model', 'msdb', 'tempdb')
        GROUP BY database_id
        ORDER BY TotalSizeGB DESC;
    """
    
    try:
        cursor.execute(query)
        rows = cursor.fetchall()
        
        result = []
        for row in rows:
            result.append({
                'database': str(row[0]),
                'data_size_gb': float(row[1]) if row[1] else 0,
                'log_size_gb': float(row[2]) if row[2] else 0,
                'size_gb': float(row[3]) if row[3] else 0
            })
        
        return result
    except Exception as e:
        logging.error(f"Error al consultar tamaños de BD: {e}")
        raise
