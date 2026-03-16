"""
Top 5 consultas más costosas en CPU.
Usa sys.dm_exec_query_stats + sys.dm_exec_sql_text para identificar las queries
que más CPU consumen en la instancia SQL Server.
"""
import logging
import re


def query_top_cpu(cursor):
    """
    Obtiene las 5 consultas con mayor consumo de CPU acumulado.
    
    Retorna lista de diccionarios con:
    - query_text: texto truncado de la consulta (primeros 300 chars)
    - total_cpu_ms: CPU total en milisegundos
    - execution_count: cantidad de ejecuciones
    - avg_cpu_ms: CPU promedio por ejecución
    - total_elapsed_ms: tiempo total transcurrido en ms
    - last_execution: última fecha de ejecución
    - database: nombre de la base de datos
    """
    query = """
        SET NOCOUNT ON;

        SELECT TOP 5
            SUBSTRING(t.text, (qs.statement_start_offset/2) + 1,
                ((CASE qs.statement_end_offset
                    WHEN -1 THEN DATALENGTH(t.text)
                    ELSE qs.statement_end_offset
                END - qs.statement_start_offset)/2) + 1) AS QueryText,
            qs.total_worker_time / 1000 AS TotalCPU_ms,
            qs.execution_count AS ExecutionCount,
            (qs.total_worker_time / 1000) / NULLIF(qs.execution_count, 0) AS AvgCPU_ms,
            qs.total_elapsed_time / 1000 AS TotalElapsed_ms,
            qs.last_execution_time AS LastExecution,
            DB_NAME(t.dbid) AS DatabaseName
        FROM sys.dm_exec_query_stats qs
        CROSS APPLY sys.dm_exec_sql_text(qs.sql_handle) t
        WHERE qs.total_worker_time > 0
        ORDER BY qs.total_worker_time DESC;
    """
    
    try:
        cursor.execute(query)
        rows = cursor.fetchall()
        
        queries = []
        for row in rows:
            query_text = str(row[0]) if row[0] else 'N/A'
            # Limpiar y truncar
            query_text = re.sub(r'\s+', ' ', query_text).strip()
            if len(query_text) > 300:
                query_text = query_text[:300] + '...'
            
            queries.append({
                'query_text': query_text,
                'total_cpu_ms': int(row[1]) if row[1] is not None else 0,
                'execution_count': int(row[2]) if row[2] is not None else 0,
                'avg_cpu_ms': int(row[3]) if row[3] is not None else 0,
                'total_elapsed_ms': int(row[4]) if row[4] is not None else 0,
                'last_execution': str(row[5]) if row[5] else 'N/A',
                'database': str(row[6]) if row[6] else 'N/A'
            })
        
        # Calcular max_cpu para barras de progreso relativas
        max_cpu = max((q['total_cpu_ms'] for q in queries), default=1)
        for q in queries:
            q['cpu_percent'] = round(q['total_cpu_ms'] * 100.0 / max_cpu, 1) if max_cpu > 0 else 0
        
        return queries
    except Exception as e:
        logging.error(f"Error al consultar top CPU queries: {e}")
        raise
