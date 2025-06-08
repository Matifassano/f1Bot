import pyodbc
import os
from dotenv import load_dotenv

load_dotenv()

def get_db_connection():
    try:
        conn = pyodbc.connect(
            driver='{ODBC Driver 17 for SQL Server}',
            server=os.getenv('DB_SERVER'),
            database=os.getenv('DB_NAME'),
            uid=os.getenv('DB_USERNAME'),
            pwd=os.getenv('DB_PASSWORD')
        )
        cursor = conn.cursor()
        return conn, cursor
    except pyodbc.Error as e:
        print(f"Error connecting to database: {str(e)}")
        raise

try:
    conn, cursor = get_db_connection()

    # 1. Events table
    create_events_table = """
    IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'EventF1')
    BEGIN
        CREATE TABLE EventF1 (
        id INT IDENTITY(1,1) PRIMARY KEY,
        season INT NOT NULL,
        gp NVARCHAR(100) NOT NULL,
        driver NVARCHAR(100) NOT NULL,
        UNIQUE (season, gp, driver)
        );
    END
    """

    # 2. Graphs table
    create_graphs_table = """
    IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'Graph')
    BEGIN
        CREATE TABLE Graph (
        id INT IDENTITY(1,1) PRIMARY KEY,
        event_id INT NOT NULL FOREIGN KEY REFERENCES EventF1(id),
        name NVARCHAR(100) NOT NULL,
        graph_path NVARCHAR(255) NOT NULL,
        description NVARCHAR(MAX)
        );
    END
    """

    # 3. Resumes table
    create_resumes_table = """
    IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'Resume')
    BEGIN
        CREATE TABLE Resume (
        id INT IDENTITY(1,1) PRIMARY KEY,
        event_id INT NOT NULL FOREIGN KEY REFERENCES EventF1(id),
        type NVARCHAR(100) NOT NULL,
        content NVARCHAR(MAX) NOT NULL,
        );
    END
    """

    cursor.execute(create_events_table)
    cursor.execute(create_graphs_table)
    cursor.execute(create_resumes_table)
    conn.commit()

except pyodbc.Error as e:
    print(f"Database error: {str(e)}")
    if conn:
        conn.rollback()
    raise

finally:
    if cursor:
        cursor.close()
    if conn:
        conn.close()