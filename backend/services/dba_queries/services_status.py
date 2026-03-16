"""
Monitor de estado de servicios SQL Server (Engine y Agent).
Usa sys.dm_server_services para obtener estado, tipo de inicio y cuenta de servicio.
"""
import logging


def query_services_status(cursor):
    """
    Obtiene el estado de los servicios de SQL Server.
    
    Retorna lista de diccionarios con:
    - service_name: nombre del servicio
    - service_type: tipo (Engine, Agent, Full-Text, etc.)
    - status: estado actual (Running, Stopped, etc.)
    - status_desc: descripción del estado
    - startup_type: tipo de inicio (Automatic, Manual, Disabled)
    - service_account: cuenta de servicio
    - process_id: PID del proceso
    - last_startup: última fecha de inicio
    """
    query = """
        SET NOCOUNT ON;

        DECLARE @has_service_type INT = 0;
        IF EXISTS (SELECT * FROM sys.all_columns WHERE object_id = OBJECT_ID('sys.dm_server_services') AND name = 'service_type')
            SET @has_service_type = 1;

        DECLARE @sql NVARCHAR(MAX);
        IF @has_service_type = 1
        BEGIN
            SET @sql = '
                SELECT 
                    servicename AS ServiceName,
                    CASE 
                        WHEN service_type = 1 THEN ''SQL Server Engine''
                        WHEN service_type = 2 THEN ''SQL Server Agent''
                        WHEN service_type = 3 THEN ''Full-Text Search''
                        WHEN service_type = 4 THEN ''Integration Services''
                        WHEN service_type = 5 THEN ''Reporting Services''
                        WHEN service_type = 6 THEN ''Analysis Services''
                        ELSE ''Otro ('' + CAST(service_type AS VARCHAR) + '')''
                    END AS ServiceType,
                    status AS StatusCode,
                    status_desc AS StatusDesc,
                    startup_type_desc AS StartupType,
                    service_account AS ServiceAccount,
                    process_id AS ProcessId,
                    CAST(last_startup_time AS VARCHAR(30)) AS LastStartup
                FROM sys.dm_server_services';
        END
        ELSE
        BEGIN
            SET @sql = '
                SELECT 
                    servicename AS ServiceName,
                    ''SQL Server Service'' AS ServiceType,
                    status AS StatusCode,
                    status_desc AS StatusDesc,
                    startup_type_desc AS StartupType,
                    service_account AS ServiceAccount,
                    process_id AS ProcessId,
                    CAST(last_startup_time AS VARCHAR(30)) AS LastStartup
                FROM sys.dm_server_services';
        END

        EXEC sp_executesql @sql;
    """
    
    try:
        cursor.execute(query)
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        
        services = []
        for row in rows:
            service = {}
            for i, col in enumerate(columns):
                val = row[i]
                if val is None:
                    val = 'N/A'
                service[col.lower()] = str(val)
            
            # Determinar ícono de estado
            status_desc = service.get('statusdesc', '').lower()
            if 'running' in status_desc:
                service['status_icon'] = '🟢'
                service['status_class'] = 'running'
            elif 'stopped' in status_desc:
                service['status_icon'] = '🔴'
                service['status_class'] = 'stopped'
            elif 'paused' in status_desc:
                service['status_icon'] = '🟡'
                service['status_class'] = 'paused'
            else:
                service['status_icon'] = '⚪'
                service['status_class'] = 'unknown'
            
            services.append(service)
        
        return services
    except Exception as e:
        logging.error(f"Error al consultar estado de servicios: {e}")
        raise
