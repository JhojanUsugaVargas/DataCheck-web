"""
Monitor de TempDB: Archivos y Uso por Sesión.
"""
import logging

def query_tempdb_usage(cursor):
    """
    Obtiene el estado de archivos de TempDB y el uso actual por sesiones.
    """
    # 1. Archivos físicos
    files_query = """
        SELECT 
            name AS FileName,
            physical_name AS PhysicalPath,
            size * 8 / 1024 AS SizeMB,
            type_desc AS FileType
        FROM sys.master_files
        WHERE database_id = DB_ID('tempdb')
    """
    
    # 2. Uso por sesión
    sessions_query = """
        SELECT 
            s.session_id AS SessionID,
            s.login_name AS LoginName,
            s.status AS Status,
            (su.user_objects_alloc_page_count * 8.0 / 1024) AS UserObjectsMB,
            (su.internal_objects_alloc_page_count * 8.0 / 1024) AS InternalObjectsMB,
            CAST(r.text AS NVARCHAR(MAX)) AS LastQuery
        FROM sys.dm_db_session_space_usage AS su
        JOIN sys.dm_exec_sessions AS s ON s.session_id = su.session_id
        LEFT JOIN sys.dm_exec_requests req ON s.session_id = req.session_id
        OUTER APPLY sys.dm_exec_sql_text(req.sql_handle) AS r
        WHERE (su.user_objects_alloc_page_count > 0 OR su.internal_objects_alloc_page_count > 0)
        AND s.session_id > 50
        ORDER BY (su.user_objects_alloc_page_count + su.internal_objects_alloc_page_count) DESC
    """
    
    try:
        # Ejecutar archivos
        cursor.execute(files_query)
        files_rows = cursor.fetchall()
        files = []
        for r in files_rows:
            files.append({
                'name': str(r[0]),
                'path': str(r[1]),
                'size': str(r[2]),
                'type': str(r[3])
            })
            
        # Ejecutar sesiones
        cursor.execute(sessions_query)
        sessions_rows = cursor.fetchall()
        sessions = []
        for r in sessions_rows:
            sessions.append({
                'sid': str(r[0]),
                'login': str(r[1]),
                'status': str(r[2]),
                'user_mb': str(round(float(r[3]), 2)),
                'internal_mb': str(round(float(r[4]), 2)),
                'query': str(r[5]) if r[5] else 'N/A'
            })
            
        return {
            'files': files,
            'active_sessions': sessions
        }
    except Exception as e:
        logging.error(f"Error al consultar TempDB: {e}")
        raise
