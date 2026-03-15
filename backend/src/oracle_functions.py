from datetime import datetime
import oracledb
import os
import logging
from dotenv import load_dotenv
import time
import ast

# Configuración de Logging (mejor que print)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# Variable global para el Pool
pool = None

def init_db_pool():
    """
    Inicializa el pool de conexiones con lógica de REINTENTO (Retry).
    """
    global pool
    
    # 1. Configuración inicial (Oracle Client y DSN)
    # Esto se hace fuera del bucle porque si falta el driver, reintentar no lo arreglará.
    try:
        oracledb.init_oracle_client()
    except Exception as err:
        logger.warning(f"Oracle Client ya iniciado o no necesario: {err}")

    dsn = f"{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_SERVICE_NAME')}"
    print(dsn)
    
    # Configuración de reintentos
    max_retries = 3
    retry_delay = 5 # Segundos de espera entre intentos

    # 2. Bucle de intentos de conexión
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Iniciando conexión a Oracle... (Intento {attempt} de {max_retries})")
            
            pool = oracledb.create_pool(
                user=os.getenv('DB_USER'),
                password=os.getenv('DB_PASSWORD'),
                dsn=dsn,
                min=3,
                max=10,
                increment=2
            )
            
            # Si llega aquí, es que funcionó
            logger.info("Connection Pool de Oracle creado exitosamente.")
            return # Salimos de la función inmediatamente

        except oracledb.DatabaseError as e:
            # Si falla, capturamos el error
            if attempt < max_retries:
                logger.warning(f"Fallo en intento {attempt}. Reintentando en {retry_delay} segundos... Error: {e}")
                time.sleep(retry_delay) # Esperar antes de reintentar
            else:
                # Si es el último intento, logueamos como error fatal
                logger.error(f"Error fatal: No se pudo conectar a la BD tras {max_retries} intentos. Razón: {e}")
                pool = None


def close_db_pool():
    """Cierra el pool al apagar la app"""
    global pool
    if pool:
        pool.close()
        logger.info("Connection Pool cerrado.")

def execute_sql(sql, var):
    """
    Ejecuta la consulta usando una conexión del pool.
    """
    global pool
    if pool is None:
        logger.error("El pool de conexiones no está inicializado.")
        return []

    connection = None
    try:
        # 1. Obtener conexión del pool (es muy rápido)
        connection = pool.acquire()
        
        # 2. Usar cursor
        with connection.cursor() as cursor:
            cursor.execute(sql,var)
            rows = cursor.fetchall()
            
            logger.info(f"Consulta ejecutada. Filas encontradas: {len(rows)}")
            return rows

    except oracledb.DatabaseError as exc:
        error, = exc.args
        logger.error(f"Error Oracle código: {error.code}. Mensaje: {error.message}")
        return [] # O raise exc
        
    except Exception as e:
        logger.error(f"Error general en searchSkuPriceStock: {e}")
        return []
        
    finally:
        if connection:
            pool.release(connection)


async def search_sku_prices_stock(codigos_medicamentos):
    """
    Función para buscar precios y stock por SKU

    Args:
       codigos_medicamentos (list): Lista
    
    return:
       list: Lista de diccionarios
    """
    
    # Extrae el año de la fecha actual para usarlo en la consulta
    current_year = datetime.now().year

    # Extraigo el mes actual para usarlo en la consulta en formato de dos dígitos por ejmplo: '02' para febrero
    current_month = datetime.now().month
    current_month_str = f"{current_month:02d}"  # Formatea el mes como dos dígitos

    init_db_pool()
    codigos_medicamentos=ast.literal_eval(codigos_medicamentos)
    bind_names = ",".join([f":{i+1}" for i in range(len(codigos_medicamentos))])
    print (bind_names)
  

    sql_test = f"SELECT artcod codigo_articulo, artnom nombre_articulo, arttarval precio_articulo, \
        salant+salent-salsal saldo FROM ivsal \
        INNER JOIN ivart ON salart=artcod \
        INNER JOIN ivarttar ON arttarcod=salart AND arttartar='FP' AND arttaread='01' AND arttartse='*' \
        WHERE salsed='01' AND salano={current_year} AND salmes={current_month_str} AND salser='3051' \
        AND artact='S' \
        AND salant+salent-salsal>0  \
        AND artcod IN ({bind_names})"
    
    print (sql_test)

    rows = execute_sql(sql_test, var=codigos_medicamentos) 
   
    resultados = []
    for row in rows:
        resultados.append({
            "sku": row[0],
            "descripcion": row[1],
            "precio": row[2],
            "saldo": row[3]
        })

    return resultados