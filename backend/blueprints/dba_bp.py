from flask import Blueprint, jsonify, session, request
import logging
from utils.config import get_db_connection
from utils.decorators import login_required, role_required
from services.dba_queries.disk_space import query_disk_space, query_disk_space_summary
from services.dba_queries.database_sizes import query_database_sizes
from services.dba_queries.instance_monitor import query_instance_monitor
from services.dba_queries.tempdb_monitor import query_tempdb_usage
from services.dba_queries.job_monitor import query_job_monitor
from services.dba_queries.alwayson_monitor import query_alwayson_status
from services.dba_queries.databases_monitor import query_databases
from services.dba_queries.backup_monitor import query_backup_status
from services.dba_queries.resource_history import query_resource_history
from services.dba_queries.transactions_monitor import query_transactions
from services.dba_queries.services_status import query_services_status
from services.dba_queries.top_cpu_queries import query_top_cpu
import re

dba_bp = Blueprint('dba', __name__)

def get_active_conn():
    """Retorna una conexión a la instancia seleccionada en sesión, o a la DB principal si no hay selección."""
    from utils.config import get_db_connection
    current_conn_str = session.get('current_conn_str')
    if current_conn_str:
        return get_db_connection(dynamic_conn_str=current_conn_str)
    return get_db_connection()

@dba_bp.route('/api/status')
@login_required
def action_status():
    """Verifica el estado de SQL Server y retorna nombre e información de uptime."""
    conn = get_active_conn()
    if not conn:
        return jsonify({'type': 'error', 'message': '❌ El servicio de SQL Server **no está disponible**.'})

    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                @@SERVERNAME AS Servidor,
                sqlserver_start_time AS FechaInicioSQLServer,
                DATEDIFF(HOUR, sqlserver_start_time, GETDATE()) AS HorasActivo,
                DATEDIFF(DAY, sqlserver_start_time, GETDATE()) AS DiasActivo
            FROM sys.dm_os_sys_info
        """)
        row = cursor.fetchone()
        conn.close()

        if not row:
            return jsonify({'type': 'error', 'message': '❌ No se pudo obtener el estado del servidor.'})

        servidor = str(row[0])
        fecha_inicio = str(row[1]) if row[1] else 'N/A'
        horas_activo = int(row[2]) if row[2] is not None else 0
        dias_activo = int(row[3]) if row[3] is not None else 0

        return jsonify({
            'type': 'server_uptime',
            'title': '📊 Estado SQL Server',
            'data': {
                'servidor': servidor,
                'fecha_inicio': fecha_inicio,
                'horas_activo': horas_activo,
                'dias_activo': dias_activo,
            }
        })
    except Exception as e:
        if conn: conn.close()
        return jsonify({'type': 'error', 'message': f'❌ Error al consultar servidor: {str(e)}'})

@dba_bp.route('/api/bloqueos')
@login_required
@role_required('DBA')
def action_bloqueos():
    """Consulta bloqueos recientes."""
    conn = get_active_conn()
    if not conn:
        return jsonify({'type': 'error', 'message': '❌ Error al conectar a la base de datos.'})

    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT TOP 5 
                login_name, session_id, LEFT(text, 100) AS query_preview,
                total_elapsed_time / 1000 AS segundos_ejecucion, Fecha
            FROM Deadlocks_Tab
            ORDER BY Fecha DESC
        """)
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return jsonify({'type': 'success', 'message': '✅ No se encontraron bloqueos recientes.'})

        bloqueos = []
        for row in rows:
            bloqueos.append({
                'usuario': str(row[0]),
                'sesion': str(row[1]),
                'query': str(row[2]),
                'segundos': str(row[3]),
                'fecha': str(row[4])
            })
        return jsonify({'type': 'table', 'title': '🔒 Últimos bloqueos detectados', 'data': bloqueos})
    except Exception as e:
        if conn: conn.close()
        return jsonify({'type': 'error', 'message': f'❌ Error al consultar bloqueos: {str(e)}'})

@dba_bp.route('/api/cpu')
@login_required
def action_cpu():
    """Monitor rápido de instancia: CPU, Memoria SQL, Sesiones y Requests."""
    conn = get_active_conn()
    if not conn:
        return jsonify({'type': 'error', 'message': '❌ Error al conectar a la base de datos para métricas.'})

    try:
        cursor = conn.cursor()
        data = query_instance_monitor(cursor)
        conn.close()

        if not data:
            return jsonify({'type': 'error', 'message': '❌ No se pudieron obtener métricas de la instancia.'})

        return jsonify({
            'type': 'instance_monitor',
            'title': '⚙️ Monitor de Salud de Instancia',
            'data': data
        })
    except Exception as e:
        if conn: conn.close()
        logging.error(f"Error en monitor de instancia: {e}")
        return jsonify({'type': 'error', 'message': f'❌ No se pudieron obtener métricas: {str(e)}'})

@dba_bp.route('/api/whoisactive')
@login_required
@role_required('DBA')
def action_whoisactive():
    """Ejecuta sp_whoisactive para ver sesiones activas con detalle completo."""
    conn = get_active_conn()
    if not conn:
        return jsonify({'type': 'error', 'message': '❌ Error al conectar a la base de datos.'})

    try:
        cursor = conn.cursor()
        cursor.execute("EXEC sp_whoisactive @get_outer_command = 2, @get_task_info = 2")
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        conn.close()

        if not rows:
            return jsonify({'type': 'success', 'message': '📌 No hay sesiones activas significativas en este momento.'})

        sesiones = []
        for row in rows:
            raw_data = {col.lower(): row[i] for i, col in enumerate(columns)}
            sql_raw = raw_data.get('sql_text') or raw_data.get('[sql_text]')
            if sql_raw and hasattr(sql_raw, '__str__'):
                sql_str = str(sql_raw)
                if '<?query' in sql_str:
                    match = re.search(r'--\s*(.*)', sql_str, re.DOTALL)
                    if match: sql_str = match.group(1)
                sql_final = sql_str[:500] + ('...' if len(sql_str) > 500 else '')
            else:
                sql_final = "N/A"

            duration = raw_data.get('dd hh:mm:ss.ms') or raw_data.get('[dd hh:mm:ss.ms]') or "0s"
            
            sesiones.append({
                'sesion_id': str(raw_data.get('session_id', 'N/A')),
                'usuario': str(raw_data.get('login_name', 'N/A')),
                'db': str(raw_data.get('database_name', 'N/A')),
                'duracion': str(duration),
                'bloquea_spid': str(raw_data.get('blocking_session_id', '') or ''),
                'wait': str(raw_data.get('wait_info', 'Runnable')),
                'query': str(sql_final)
            })
        
        return jsonify({
            'type': 'table', 
            'title': '👤 Sesiones Activas Detalladas', 
            'data': sesiones,
            'columns': ['sesion_id', 'usuario', 'db', 'duracion', 'bloquea_spid', 'wait', 'query']
        })
    except Exception as e:
        if conn: conn.close()
        logging.error(f"Error en sp_whoisactive: {e}")
        return jsonify({'type': 'error', 'message': f'❌ Error al ejecutar sp_whoisactive: {str(e)}'})

@dba_bp.route('/api/discos')
@login_required
def action_discos():
    """Información de espacio en disco."""
    conn = get_active_conn()
    if not conn:
        return jsonify({'type': 'error', 'message': '❌ Error al conectar a la base de datos.'})

    try:
        cursor = conn.cursor()
        discos = query_disk_space(cursor)
        conn.close()

        if not discos:
            return jsonify({'type': 'success', 'message': 'No se encontró información de espacio en disco.'})

        return jsonify({'type': 'disk_monitor', 'title': '💾 Espacio en Discos', 'data': discos})
    except Exception as e:
        if conn: conn.close()
        return jsonify({'type': 'error', 'message': f'❌ Error: {str(e)}'})

@dba_bp.route('/api/datalog')
@login_required
def action_datalog():
    """Consulta tamaños de Data y Log."""
    conn = get_active_conn()
    if not conn:
        return jsonify({'type': 'error', 'message': '❌ Error al conectar a la base de datos.'})

    try:
        cursor = conn.cursor()
        datos = query_database_sizes(cursor)
        conn.close()

        if not datos:
            return jsonify({'type': 'success', 'message': 'No se encontró información.'})

        return jsonify({'type': 'datalog_monitor', 'title': '🕵️‍♂️ Validación de Data y Log', 'data': datos})
    except Exception as e:
        if conn: conn.close()
        return jsonify({'type': 'error', 'message': f'❌ Error: {str(e)}'})

@dba_bp.route('/api/tempdb')
@login_required
@role_required('DBA')
def action_tempdb():
    """Muestra estado de TempDB."""
    conn = get_active_conn()
    if not conn:
        return jsonify({'type': 'error', 'message': '❌ Error al conectar a la base de datos.'})

    try:
        cursor = conn.cursor()
        data = query_tempdb_usage(cursor)
        conn.close()

        if not data:
            return jsonify({'type': 'success', 'message': 'No se encontró información de TempDB.'})

        return jsonify({
            'type': 'tempdb_monitor',
            'title': '🧹 Monitor de TempDB',
            'data': data
        })
    except Exception as e:
        if conn: conn.close()
        return jsonify({'type': 'error', 'message': f'❌ Error: {str(e)}'})

@dba_bp.route('/api/jobs')
@login_required
def action_jobs():
    """Consulta el historial de Jobs."""
    conn = get_active_conn()
    if not conn:
        return jsonify({'type': 'error', 'message': '❌ Error al conectar a la base de datos.'})

    try:
        cursor = conn.cursor()
        data = query_job_monitor(cursor)
        conn.close()

        if not data:
            return jsonify({'type': 'success', 'message': '✅ No se encontraron ejecuciones de jobs en las últimas 24 horas.'})

        return jsonify({
            'type': 'table',
            'title': '📋 Validación de Jobs (Últimas 24h)',
            'data': data
        })
    except Exception as e:
        if conn: conn.close()
        return jsonify({'type': 'error', 'message': f'❌ Error al consultar jobs: {str(e)}'})

@dba_bp.route('/api/alwayson')
@login_required
def action_alwayson():
    """Consulta el estado de Always On Availability Groups."""
    conn = get_active_conn()
    if not conn:
        return jsonify({'type': 'error', 'message': '❌ Error al conectar a la base de datos.'})

    try:
        cursor = conn.cursor()
        data = query_alwayson_status(cursor)
        conn.close()

        # query_alwayson_status ya devuelve el diccionario formateado
        return jsonify(data)
    except Exception as e:
        if conn: conn.close()
        return jsonify({'type': 'error', 'message': f'❌ Error al consultar Always On: {str(e)}'})

@dba_bp.route('/api/databases')
@login_required
def action_databases():
    """Lista todas las bases de datos de la instancia."""
    conn = get_active_conn()
    if not conn:
        return jsonify({'type': 'error', 'message': '❌ Error al conectar a la base de datos.'})

    try:
        cursor = conn.cursor()
        data = query_databases(cursor)
        conn.close()
        return jsonify(data)
    except Exception as e:
        if conn: conn.close()
        return jsonify({'type': 'error', 'message': f'❌ Error al consultar bases de datos: {str(e)}'})

@dba_bp.route('/api/backups')
@login_required
def action_backups():
    """Valida el estado de backups de las bases de datos de usuario."""
    conn = get_active_conn()
    if not conn:
        return jsonify({'type': 'error', 'message': '❌ Error al conectar a la base de datos.'})

    try:
        cursor = conn.cursor()
        data = query_backup_status(cursor)
        conn.close()
        return jsonify(data)
    except Exception as e:
        if conn: conn.close()
        return jsonify({'type': 'error', 'message': f'❌ Error al validar backups: {str(e)}'})

@dba_bp.route('/api/resource_chart')
@login_required
def action_resource_chart():
    """Obtiene datos históricos de CPU y Memoria para gráfico de líneas."""
    conn = get_active_conn()
    if not conn:
        return jsonify({'type': 'error', 'message': '❌ Error al conectar a la base de datos.'})

    try:
        cursor = conn.cursor()
        data = query_resource_history(cursor)
        conn.close()
        return jsonify({
            'type': 'resource_chart',
            'title': '📈 Consumo de Recursos (CPU & Memoria)',
            'data': data
        })
    except Exception as e:
        if conn: conn.close()
        return jsonify({'type': 'error', 'message': f'❌ Error al consultar recursos: {str(e)}'})

@dba_bp.route('/api/transactions')
@login_required
def action_transactions():
    """Monitor de transacciones por base de datos."""
    conn = get_active_conn()
    if not conn:
        return jsonify({'type': 'error', 'message': '❌ Error al conectar a la base de datos.'})

    try:
        cursor = conn.cursor()
        data = query_transactions(cursor)
        conn.close()

        if not data:
            return jsonify({'type': 'success', 'message': '✅ No se encontraron transacciones activas.'})

        return jsonify({
            'type': 'transactions_monitor',
            'title': '🔄 Transacciones por Base de Datos',
            'data': data
        })
    except Exception as e:
        if conn: conn.close()
        return jsonify({'type': 'error', 'message': f'❌ Error al consultar transacciones: {str(e)}'})

@dba_bp.route('/api/services_status')
@login_required
def action_services_status():
    """Estado de servicios SQL Server y Agent."""
    conn = get_active_conn()
    if not conn:
        return jsonify({'type': 'error', 'message': '❌ Error al conectar a la base de datos.'})

    try:
        cursor = conn.cursor()
        data = query_services_status(cursor)
        conn.close()

        if not data:
            return jsonify({'type': 'success', 'message': '⚠️ No se pudo obtener información de servicios.'})

        return jsonify({
            'type': 'services_status',
            'title': '🟢 Estado de Servicios SQL',
            'data': data
        })
    except Exception as e:
        if conn: conn.close()
        return jsonify({'type': 'error', 'message': f'❌ Error al consultar servicios: {str(e)}'})

@dba_bp.route('/api/top_cpu_queries')
@login_required
def action_top_cpu_queries():
    """Top 5 queries más costosas en CPU."""
    conn = get_active_conn()
    if not conn:
        return jsonify({'type': 'error', 'message': '❌ Error al conectar a la base de datos.'})

    try:
        cursor = conn.cursor()
        data = query_top_cpu(cursor)
        conn.close()

        if not data:
            return jsonify({'type': 'success', 'message': '✅ No se encontraron queries con alto consumo de CPU.'})

        return jsonify({
            'type': 'top_cpu_queries',
            'title': '🔥 Top 5 Queries por CPU',
            'data': data
        })
    except Exception as e:
        if conn: conn.close()
        return jsonify({'type': 'error', 'message': f'❌ Error al consultar top CPU queries: {str(e)}'})
@dba_bp.route('/api/tempdb/shrink')
@login_required
@role_required('DBA')
def action_tempdb_shrink():
    conn = get_active_conn()
    if not conn:
        return jsonify({'type': 'error', 'message': '🚫 Error al conectar a la base de datos.'})

    try:
        cursor = conn.cursor()
        cursor.execute("DBCC FREEPROCCACHE; DBCC DROPCLEANBUFFERS; DBCC FREESYSTEMCACHE ('ALL');")
        cursor.execute("USE [tempdb]; CHECKPOINT; DBCC SHRINKDATABASE(tempdb, 10);")
        conn.close()
        return jsonify({'type': 'success', 'message': '✅ Se ha solicitado la compactación de TempDB.'})
    except Exception as e:
        if conn: conn.close()
        return jsonify({'type': 'error', 'message': f'🚫 Error al compactar: {str(e)}'})

@dba_bp.route('/api/performance')
@login_required
@role_required('DBA')
def action_performance():
    """Verifica performance general del servidor remoto de SQL."""
    conn = get_active_conn()
    if not conn:
        return jsonify({'type': 'error', 'message': '❌ No se pudo conectar al servidor para verificar performance.'})

    try:
        cursor = conn.cursor()
        
        # 1. Nombre del Servidor y Estado
        cursor.execute("SELECT @@SERVERNAME")
        server_name = cursor.fetchone()[0]

        # 2. CPU Remote (SQL)
        cpu_query = """
            SELECT TOP 1 [SQLProcessUtilization] FROM (
                SELECT record.value('(./Record/SchedulerMonitorEvent/SystemHealth/ProcessUtilization)[1]', 'int') AS [SQLProcessUtilization],
                record.value('(./Record/@id)[1]', 'int') AS record_id
                FROM (SELECT CAST(record AS xml) AS [record] FROM sys.dm_os_ring_buffers 
                WHERE ring_buffer_type = N'RING_BUFFER_SCHEDULER_MONITOR' AND record LIKE '%<SchedulerMonitorEvent>%') AS x
            ) AS y ORDER BY record_id DESC
        """
        cursor.execute(cpu_query)
        cpu_row = cursor.fetchone()
        cpu_val = cpu_row[0] if cpu_row else "N/A"

        # 3. Memoria Remote (OS)
        mem_query = """
            SELECT 
                total_physical_memory_kb / 1048576.0 AS TotalGB, 
                available_physical_memory_kb / 1048576.0 AS AvailGB 
            FROM sys.dm_os_sys_memory
        """
        cursor.execute(mem_query)
        mem_row = cursor.fetchone()
        if mem_row:
            total_gb = round(float(mem_row[0]), 1)
            avail_gb = round(float(mem_row[1]), 1)
            used_gb = round(total_gb - avail_gb, 1)
            mem_pct = round((used_gb * 100.0 / total_gb), 1) if total_gb > 0 else 0
            mem_info = f"{mem_pct}% usada ({used_gb} / {total_gb} GB)"
        else:
            mem_info = "N/A"

        # 4. Discos (usando DMVs estándar)
        disk_summary = ""
        try:
            d_rows = query_disk_space_summary(cursor)
            if d_rows:
                disk_summary = "\n".join([f"  • {row[0]}: {row[2]} GB libres / {row[1]} GB total" for row in d_rows])
        except Exception:
            disk_summary = "  • Información de discos no disponible."

        conn.close()

        message = (
            f"**📈 Performance de la Instancia: {server_name}**\n\n"
            f"**Estado:** ✅ En línea\n"
            f"**CPU (SQL/Sist.):** {cpu_val}%\n"
            f"**Memoria:** {mem_info}\n"
            f"**Discos Remotos:**\n{disk_summary}"
        )
        return jsonify({'type': 'success', 'message': message})
    except Exception as e:
        if conn: conn.close()
        return jsonify({'type': 'error', 'message': f'❌ Error al obtener performance: {str(e)}'})

@dba_bp.route('/api/cancelar', methods=['POST'])
@login_required
@role_required('DBA')
def action_cancelar():
    """Cancela una consulta SQL por SPID."""
    data = request.get_json() or {}
    spid_str = data.get('spid') or data.get('message')
    if not spid_str:
        return jsonify({'type': 'prompt', 'message': '⚠️ Por favor, ingresa el SPID de la consulta a cancelar:', 'input_action': 'cancelar'})

    try:
        spid = int(spid_str)
    except ValueError:
        return jsonify({'type': 'error', 'message': '⚠️ El SPID debe ser un número entero válido.'})

    conn = get_active_conn()
    if not conn:
        return jsonify({'type': 'error', 'message': '❌ Error al conectar a la base de datos.'})

    try:
        cursor = conn.cursor()
        cursor.execute(f"KILL {spid}")
        conn.close()
        return jsonify({'type': 'success', 'message': f'✅ Consulta con SPID {spid} cancelada correctamente.'})
    except Exception as e:
        if conn: conn.close()
        return jsonify({'type': 'error', 'message': f'❌ Error al cancelar SPID {spid}: {str(e)}'})
