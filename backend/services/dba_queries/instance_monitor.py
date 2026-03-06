"""
Monitor rápido de instancia SQL Server.
CPU - Memoria - Sesiones - Queries activas.
Usa únicamente DMVs estándar, funciona en cualquier instancia SQL Server.
"""
import logging


def query_instance_monitor(cursor):
    """
    Ejecuta un monitor completo de la instancia SQL Server usando DMVs estándar.
    
    Retorna un diccionario con:
    - CPU: sql_cpu_percent, cpu_idle, cpu_other
    - Memoria: sql_mem_used_mb, sql_max_mem_mb, sql_mem_free_mb, sql_mem_usage_percent
    - Actividad: sessions_running, sessions_user, requests_active
    - Fecha del snapshot
    """
    query = """
        SET NOCOUNT ON;

        DECLARE @SQL_CPU INT
        DECLARE @SystemIdle INT
        DECLARE @MaxMemoryMB INT

        -- CPU de SQL Server
        SELECT TOP 1
            @SQL_CPU = record.value('(./Record/SchedulerMonitorEvent/SystemHealth/ProcessUtilization)[1]', 'int'),
            @SystemIdle = record.value('(./Record/SchedulerMonitorEvent/SystemHealth/SystemIdle)[1]', 'int')
        FROM (
            SELECT CONVERT(XML, record) AS record
            FROM sys.dm_os_ring_buffers
            WHERE ring_buffer_type = 'RING_BUFFER_SCHEDULER_MONITOR'
            AND record LIKE '%<SystemHealth>%'
        ) x
        ORDER BY record.value('(./Record/@id)[1]', 'int') DESC;

        -- Memoria máxima configurada
        SELECT @MaxMemoryMB = CONVERT(INT, value_in_use)
        FROM sys.configurations
        WHERE name = 'max server memory (MB)';

        SELECT
            GETDATE() AS Fecha,

            -- CPU
            @SQL_CPU AS SQL_CPU_Porcentaje,
            @SystemIdle AS CPU_Libre_Servidor,
            (100 - @SQL_CPU - @SystemIdle) AS CPU_Otros_Procesos,

            -- Memoria
            pm.physical_memory_in_use_kb / 1024 AS SQL_Memory_Usada_MB,
            @MaxMemoryMB AS SQL_Max_Memory_MB,
            @MaxMemoryMB - (pm.physical_memory_in_use_kb / 1024) AS SQL_Memory_Libre_MB,
            ((pm.physical_memory_in_use_kb / 1024.0) / @MaxMemoryMB) * 100 AS SQL_Memory_Usage_Percent,

            -- Actividad
            (SELECT COUNT(*) FROM sys.dm_exec_sessions WHERE status = 'running') AS Sesiones_Ejecutando,
            (SELECT COUNT(*) FROM sys.dm_exec_sessions WHERE is_user_process = 1) AS Sesiones_Usuario,

            -- Requests activas
            (SELECT COUNT(*) FROM sys.dm_exec_requests) AS Requests_Activas

        FROM sys.dm_os_process_memory pm;
    """
    try:
        cursor.execute(query)
        row = cursor.fetchone()
        
        if not row:
            return None

        return {
            'fecha': str(row[0]),
            'sql_cpu_percent': int(row[1]) if row[1] is not None else 0,
            'cpu_idle': int(row[2]) if row[2] is not None else 0,
            'cpu_other': int(row[3]) if row[3] is not None else 0,
            'sql_mem_used_mb': int(row[4]) if row[4] is not None else 0,
            'sql_max_mem_mb': int(row[5]) if row[5] is not None else 0,
            'sql_mem_free_mb': int(row[6]) if row[6] is not None else 0,
            'sql_mem_usage_percent': round(float(row[7]), 1) if row[7] is not None else 0,
            'sessions_running': int(row[8]) if row[8] is not None else 0,
            'sessions_user': int(row[9]) if row[9] is not None else 0,
            'requests_active': int(row[10]) if row[10] is not None else 0,
        }
    except Exception as e:
        logging.error(f"Error en monitor de instancia: {e}")
        raise
