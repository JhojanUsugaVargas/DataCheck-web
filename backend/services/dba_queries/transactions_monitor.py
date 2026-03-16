"""
Monitor de transacciones por base de datos.
Usa sys.dm_os_performance_counters para obtener métricas de transacciones.
"""
import logging


def query_transactions(cursor):
    """
    Obtiene métricas de transacciones por base de datos desde los performance counters.
    
    Retorna lista de diccionarios con:
    - database: nombre de la BD
    - transactions_sec: transacciones por segundo
    - active_transactions: transacciones activas
    - log_flushes_sec: flushes de log por segundo
    - log_bytes_flushed_sec: bytes de log flushed por segundo
    """
    query = """
        SET NOCOUNT ON;

        SELECT 
            DB_NAME(dtst.database_id) AS DatabaseName,
            COUNT(*) AS ActiveTransactions,
            MAX(dtat.transaction_begin_time) AS LastTransactionTime
        FROM sys.dm_tran_session_transactions dtst
        INNER JOIN sys.dm_tran_active_transactions dtat ON dtst.transaction_id = dtat.transaction_id
        WHERE DB_NAME(dtst.database_id) IS NOT NULL
        AND DB_NAME(dtst.database_id) NOT IN ('tempdb')
        GROUP BY dtst.database_id
        ORDER BY COUNT(*) DESC;
    """
    
    counter_query = """
        SELECT
            RTRIM(instance_name) AS DatabaseName,
            RTRIM(counter_name) AS CounterName,
            cntr_value AS CounterValue
        FROM sys.dm_os_performance_counters
        WHERE object_name LIKE '%Databases%'
        AND counter_name IN ('Transactions/sec', 'Log Flushes/sec', 'Log Bytes Flushed/sec')
        AND instance_name NOT IN ('_Total', '')
        AND instance_name NOT LIKE 'mssqlsystemresource%'
        ORDER BY instance_name, counter_name;
    """
    
    try:
        # Transacciones activas
        cursor.execute(query)
        active_rows = cursor.fetchall()
        
        active_map = {}
        for row in active_rows:
            db_name = str(row[0])
            active_map[db_name] = {
                'active_transactions': int(row[1]),
                'last_transaction': str(row[2]) if row[2] else 'N/A'
            }
        
        # Counters de performance
        cursor.execute(counter_query)
        counter_rows = cursor.fetchall()
        
        db_counters = {}
        for row in counter_rows:
            db_name = str(row[0])
            counter_name = str(row[1]).strip()
            counter_value = int(row[2]) if row[2] is not None else 0
            
            if db_name not in db_counters:
                db_counters[db_name] = {
                    'database': db_name,
                    'transactions_sec': 0,
                    'log_flushes_sec': 0,
                    'log_bytes_flushed_sec': 0,
                    'active_transactions': 0,
                    'last_transaction': 'N/A'
                }
            
            if 'Transactions/sec' in counter_name:
                db_counters[db_name]['transactions_sec'] = counter_value
            elif 'Log Flushes/sec' in counter_name:
                db_counters[db_name]['log_flushes_sec'] = counter_value
            elif 'Log Bytes Flushed/sec' in counter_name:
                db_counters[db_name]['log_bytes_flushed_sec'] = counter_value
        
        # Merge con transacciones activas
        for db_name, info in active_map.items():
            if db_name in db_counters:
                db_counters[db_name]['active_transactions'] = info['active_transactions']
                db_counters[db_name]['last_transaction'] = info['last_transaction']
            else:
                db_counters[db_name] = {
                    'database': db_name,
                    'transactions_sec': 0,
                    'log_flushes_sec': 0,
                    'log_bytes_flushed_sec': 0,
                    'active_transactions': info['active_transactions'],
                    'last_transaction': info['last_transaction']
                }
        
        # Convertir a lista ordenada por transacciones/sec descendente
        result = sorted(db_counters.values(), key=lambda x: x['transactions_sec'], reverse=True)
        
        # Filtrar bases del sistema
        system_dbs = ['master', 'model', 'msdb', 'tempdb', 'mssqlsystemresource']
        result = [r for r in result if r['database'].lower() not in system_dbs]
        
        return result
    except Exception as e:
        logging.error(f"Error al consultar transacciones: {e}")
        raise
