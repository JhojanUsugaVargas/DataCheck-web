"""
Historial de consumo de recursos (CPU y Memoria) de la instancia SQL Server.
Usa sys.dm_os_ring_buffers para obtener datos históricos (~30 min).
Retorna arrays para renderizar gráficos de líneas con Chart.js.
"""
import logging
from datetime import datetime


def query_resource_history(cursor):
    """
    Obtiene datos históricos de CPU y Memoria desde los ring buffers de SQL Server.
    
    Retorna un diccionario con:
    - timestamps: lista de timestamps (strings HH:MM:SS)
    - sql_cpu: lista de porcentajes de CPU de SQL Server
    - other_cpu: lista de porcentajes de CPU de otros procesos
    - memory_percent: porcentaje actual de memoria en uso
    - memory_used_mb: MB de memoria en uso por SQL
    - memory_total_mb: MB totales del servidor
    """
    query = """
        SET NOCOUNT ON;

        -- Obtener historial de CPU desde ring buffers (últimos ~30 minutos)
        SELECT TOP 30
            record.value('(./Record/@id)[1]', 'int') AS record_id,
            DATEADD(ms, -1 * (ts_now - [timestamp]), GETDATE()) AS EventTime,
            record.value('(./Record/SchedulerMonitorEvent/SystemHealth/ProcessUtilization)[1]', 'int') AS SQL_CPU,
            record.value('(./Record/SchedulerMonitorEvent/SystemHealth/SystemIdle)[1]', 'int') AS System_Idle,
            100 - record.value('(./Record/SchedulerMonitorEvent/SystemHealth/ProcessUtilization)[1]', 'int')
                - record.value('(./Record/SchedulerMonitorEvent/SystemHealth/SystemIdle)[1]', 'int') AS Other_CPU
        FROM (
            SELECT 
                CONVERT(XML, record) AS record,
                [timestamp],
                (SELECT cpu_ticks / (cpu_ticks / ms_ticks) FROM sys.dm_os_sys_info) AS ts_now
            FROM sys.dm_os_ring_buffers
            WHERE ring_buffer_type = 'RING_BUFFER_SCHEDULER_MONITOR'
            AND record LIKE '%<SystemHealth>%'
        ) x
        ORDER BY record_id ASC;
    """
    
    mem_query = """
        SELECT 
            (pm.physical_memory_in_use_kb / 1024) AS SQL_Memory_Used_MB,
            (osm.total_physical_memory_kb / 1024) AS Total_Memory_MB,
            (osm.available_physical_memory_kb / 1024) AS Available_Memory_MB,
            CAST((osm.total_physical_memory_kb - osm.available_physical_memory_kb) * 100.0 / osm.total_physical_memory_kb AS DECIMAL(5,1)) AS Memory_Percent
        FROM sys.dm_os_process_memory pm
        CROSS JOIN sys.dm_os_sys_memory osm;
    """
    
    try:
        cursor.execute(query)
        rows = cursor.fetchall()
        
        timestamps = []
        sql_cpu = []
        other_cpu = []
        
        for row in rows:
            event_time = row[1]
            if event_time:
                if isinstance(event_time, datetime):
                    timestamps.append(event_time.strftime('%H:%M'))
                else:
                    timestamps.append(str(event_time)[-8:-3])  # HH:MM
            else:
                timestamps.append('')
            
            sql_cpu.append(int(row[2]) if row[2] is not None else 0)
            other_cpu.append(int(row[4]) if row[4] is not None else 0)
        
        # Memoria
        cursor.execute(mem_query)
        mem_row = cursor.fetchone()
        
        memory_used_mb = int(mem_row[0]) if mem_row and mem_row[0] else 0
        memory_total_mb = int(mem_row[1]) if mem_row and mem_row[1] else 0
        memory_available_mb = int(mem_row[2]) if mem_row and mem_row[2] else 0
        memory_percent = round(float(mem_row[3]), 1) if mem_row and mem_row[3] else 0
        
        return {
            'timestamps': timestamps,
            'sql_cpu': sql_cpu,
            'other_cpu': other_cpu,
            'memory_percent': memory_percent,
            'memory_used_mb': memory_used_mb,
            'memory_total_mb': memory_total_mb,
            'memory_available_mb': memory_available_mb
        }
    except Exception as e:
        logging.error(f"Error al consultar historial de recursos: {e}")
        raise
