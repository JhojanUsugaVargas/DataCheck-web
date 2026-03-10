"""
Servicio para consultar el listado y estado de las bases de datos.
"""
import logging

def query_databases(cursor):
    """
    Retorna el listado de bases de datos con su estado, modelo de recuperación, acceso y tipo.
    """
    query = """
    SELECT 
        name AS BaseDatos,
        state_desc AS Estado,
        recovery_model_desc AS ModeloRecuperacion,
        user_access_desc AS Acceso,
        CONVERT(VARCHAR, create_date, 120) AS FechaCreacion,
        CASE 
            WHEN database_id <= 4 THEN 'Sistema'
            ELSE 'Usuario'
        END AS TipoBase
    FROM sys.databases
    ORDER BY name;
    """
    try:
        cursor.execute(query)
        rows = cursor.fetchall()

        if not rows:
            return {
                'type': 'info',
                'message': 'ℹ️ No se encontraron bases de datos.'
            }

        columns = [desc[0] for desc in cursor.description]
        results = [dict(zip(columns, [str(v) if v is not None else 'N/A' for v in row])) for row in rows]

        return {
            'type': 'table',
            'title': '🗄️ Bases de Datos en la Instancia',
            'data': results
        }

    except Exception as e:
        logging.error(f"Error al consultar bases de datos: {e}")
        raise
