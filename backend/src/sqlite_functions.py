import sqlite3
import pathlib
import pandas as pd
import ast

# Constantes
DATA_PATH=pathlib.Path(__file__).parent.parent / "data/"
DB_NAME="inventory.db"
INVENTORY_FILE="articulos_drogueria.csv"


def connect_to_db():
    """Connect to the SQLite
    database and return a connection object."""
    conn=sqlite3.connect(DATA_PATH / DB_NAME)
    return conn

def create_table(conn):
    """Create a table if it
    does not exist."""
    cursor=conn.cursor()
    cursor.execute('''
                   CREATE VIRTUAL TABLE products USING fts5  (
                   codigo_medicamento,
                   nombre_medicamento,
                   grupo_medicamento,
                   tokenize='trigram'
                   )
        ''')
    conn.commit()

def load_inventory(conn):
    """Load the inventory data
    from a CSV file into the database."""
    df=pd.read_csv(DATA_PATH / INVENTORY_FILE)
    
    # Insertar los datos por lotes de 500
    batch_size = 500
    for i in range(0, len(df), batch_size):
        batch_df = df[i:i + batch_size]
        batch_df.to_sql('products', conn, if_exists='append', index=False)
        print(f"Inserted {len(batch_df)} rows.")

    # Cerrar la conexión
    conn.close()

def search_items(q: str):
    """Search for items in the database."""
    conn=connect_to_db()
    cursor=conn.cursor()
    if len(q) < 5: return # Tu regla de negocio
    
    # Búsqueda rápida con ranking
    query = """
        SELECT codigo_medicamento, nombre_medicamento, grupo_medicamento
        FROM products 
        WHERE products MATCH? 
        ORDER BY rank 
        LIMIT 10
    """
    # El truco: añadir * para autocompletado
    cursor.execute(query, (f"{q}*",)) 
    return cursor.fetchall()

def search_rates(codigos_medicamentos):
    """Search for items rates"""
    conn = connect_to_db()
    cursor = conn.cursor()

    codigos_medicamentos=ast.literal_eval(codigos_medicamentos)
    bind_names = ",".join([f":{i+1}" for i in range(len(codigos_medicamentos))])
    print (bind_names)

    query = f"SELECT p.codigo_medicamento, p.nombre_medicamento, r.valor, r.saldo \
        FROM rates r, products p \
        WHERE r.codigo_medicamento=p.codigo_medicamento AND p.codigo_medicamento IN ({bind_names})"
  
    cursor.execute(query, codigos_medicamentos)
    rows = cursor.fetchall()

    results = []
    for row in rows:
        results.append({
            "sku": row[0],
            "descripcion": row[1],
            "precio": row[2],
            "saldo": row[3]
        })
    return results






    



