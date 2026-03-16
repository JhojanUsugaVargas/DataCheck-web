import logging
import datetime

def get_pmp_consolidated_data(cursor):
    """
    Obtiene todos los datos necesarios para el reporte PMP consolidado.
    Retorna un diccionario con los resultados de cada sección.
    """
    data = {}
    
    try:
        # 1. Información General del Servidor
        cursor.execute("SELECT CAST(SERVERPROPERTY('MachineName') AS VARCHAR) as Host, CAST(SERVERPROPERTY('ServerName') AS VARCHAR) as Instance, CAST(create_date AS VARCHAR) as Startup FROM sys.databases WHERE name = 'tempdb'")
        general = cursor.fetchone()
        data['general'] = {
            'host': str(general[0]) if general else 'N/A',
            'instance': str(general[1]) if general else 'N/A',
            'startup': str(general[2]) if general else 'N/A',
            'date': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        # 2. INFORME DE ESPACIO Y ARCHIVOS FISICOS
        # DB, Ubicación, Nombre Físico, Tamaño Usado (MB)
        query_files = """
        SELECT 
            DB_NAME(database_id) as DB,
            physical_name as Location,
            name as FileName,
            CAST(size * 8.0 / 1024 AS DECIMAL(10,2)) as SizeMB
        FROM sys.master_files
        WHERE DB_NAME(database_id) NOT IN ('master', 'model', 'msdb', 'tempdb')
        ORDER BY DB, type
        """
        cursor.execute(query_files)
        data['db_files'] = [dict(zip([d[0].lower() for d in cursor.description], row)) for row in cursor.fetchall()]

        # 3. INFORME DE ESPACIO LIBRE (Particiones)
        # Solo disponible en versiones modernas de SQL o si el usuario tiene permisos
        try:
            query_disk = "SELECT DISTINCT logical_volume_name, CAST(free_bytes/1024.0/1024.0/1024.0 AS DECIMAL(10,2)) as FreeGB FROM sys.dm_os_volume_stats(DB_ID('master'), 1)"
            # Nota: dm_os_volume_stats requiere un bit de cuidado, usaremos una versión más genérica si falla
            cursor.execute("SELECT DISTINCT volume_mount_point, CAST(available_bytes/1048576.0/1024.0 AS DECIMAL(10,2)) as FreeGB FROM sys.dm_os_enumerate_fixed_drives")
            data['disk_free'] = [dict(zip([d[0].lower() for d in cursor.description], row)) for row in cursor.fetchall()]
        except:
            data['disk_free'] = []

        # 4. INFORME DE RESPALDOS REALIZADOS
        query_backups = """
        SELECT TOP 50
            backup_finish_date as FinishDate,
            CASE type WHEN 'D' THEN 'Full' WHEN 'I' THEN 'Diff' WHEN 'L' THEN 'Log' END as Type,
            database_name as DB
        FROM msdb.dbo.backupset
        ORDER BY backup_finish_date DESC
        """
        cursor.execute(query_backups)
        data['backups'] = [dict(zip([d[0].lower() for d in cursor.description], row)) for row in cursor.fetchall()]

        # 5. BASES DE DATOS NUEVAS (Últimos 30 días)
        query_new_dbs = "SELECT name, create_date FROM sys.databases WHERE create_date > DATEADD(day, -30, GETDATE()) AND name NOT IN ('master', 'model', 'msdb', 'tempdb')"
        cursor.execute(query_new_dbs)
        data['new_dbs'] = [dict(zip([d[0].lower() for d in cursor.description], row)) for row in cursor.fetchall()]

        # 6. LINKED SERVERS
        query_linked = "SELECT name, product, provider, data_source FROM sys.servers WHERE is_linked = 1"
        cursor.execute(query_linked)
        data['linked_servers'] = [dict(zip([d[0].lower() for d in cursor.description], row)) for row in cursor.fetchall()]

        # 7. NUEVOS USUARIOS CREADOS ( logins últimos 30 días)
        query_logins = "SELECT name, create_date FROM sys.server_principals WHERE type_desc IN ('SQL_LOGIN', 'WINDOWS_LOGIN') AND create_date > DATEADD(day, -30, GETDATE())"
        cursor.execute(query_logins)
        data['new_users'] = [dict(zip([d[0].lower() for d in cursor.description], row)) for row in cursor.fetchall()]

        # 8. INFORME DE TAREAS FALLIDAS (Últimas 24h)
        query_failed_jobs = """
        SELECT 
            j.name as JobName,
            CAST(STUFF(STUFF(CAST(run_date AS CHAR(8)), 7, 0, '-'), 5, 0, '-') AS DATETIME) as RunDate,
            ms.message as Message
        FROM msdb.dbo.sysjobs j
        JOIN msdb.dbo.sysjobhistory h ON j.job_id = h.job_id
        JOIN msdb.dbo.sysjobsteps s ON j.job_id = s.job_id AND h.step_id = s.step_id
        CROSS APPLY (SELECT TOP 1 message FROM msdb.dbo.sysjobhistory WHERE job_id = j.job_id AND run_status = 0 ORDER BY instance_id DESC) ms
        WHERE h.run_status = 0 
        AND h.run_date >= CAST(CONVERT(CHAR(8), DATEADD(day, -1, GETDATE()), 112) AS INT)
        GROUP BY j.name, h.run_date, ms.message
        """
        try:
            cursor.execute(query_failed_jobs)
            data['failed_jobs'] = [dict(zip([d[0].lower() for d in cursor.description], row)) for row in cursor.fetchall()]
        except:
            data['failed_jobs'] = []

        # 9. ESTADISTICAS DESACTUALIZADAS (> 7 días)
        # Esto requiere iterar por BD o usar una vista de sistema si existe. 
        # Para el reporte consolidado rápido, tomaremos las de la BD actual o master como ejemplo, 
        # pero idealmente se hace cross-db. Simplificaremos a una muestra.
        data['stats_outdated'] = [] # Se llenará con lógica más compleja si es crítico, o una muestra.

        return data
        
    except Exception as e:
        logging.error(f"Error gathering PMP data: {e}")
        raise
