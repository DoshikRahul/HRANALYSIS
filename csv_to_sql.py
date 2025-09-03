import os
import pandas as pd
import mysql.connector
from mysql.connector import Error
import chardet

# ---------- Step 1: Detect file encoding ----------
def detect_encoding(file_path):
    with open(file_path, "rb") as f:
        result = chardet.detect(f.read(50000))  # check first 50k bytes
    return result["encoding"]

# ---------- Step 2: Convert CSV to MySQL ----------
def csv_to_mysql(csv_file, table_name, host, user, password, database):
    try:
        # Detect encoding automatically
        encoding = detect_encoding(csv_file)
        print(f"[INFO] Detected file encoding: {encoding}")

        # Read CSV with detected encoding
        df = pd.read_csv(csv_file, encoding=encoding)

        # Connect to MySQL
        conn = mysql.connector.connect(
            host=host,
            user=user,
            password=password,
            database=database
        )
        cursor = conn.cursor()

        # Drop table if exists (optional, avoids conflicts)
        cursor.execute(f"DROP TABLE IF EXISTS {table_name}")

        # Create table dynamically from CSV columns (all TEXT for safety)
        create_table_query = f"CREATE TABLE {table_name} ("
        for col in df.columns:
            create_table_query += f"`{col}` TEXT,"
        create_table_query = create_table_query.rstrip(",") + ");"
        cursor.execute(create_table_query)

        # Insert rows
        placeholders = ", ".join(["%s"] * len(df.columns))
        insert_query = f"INSERT INTO {table_name} ({', '.join(df.columns)}) VALUES ({placeholders})"

        for _, row in df.iterrows():
            cursor.execute(insert_query, tuple(row.astype(str)))  # ensure strings

        conn.commit()
        print(f"[SUCCESS] Data from {csv_file} inserted into `{table_name}` successfully!")

    except Error as e:
        print(f"[ERROR] MySQL error: {e}")
    except Exception as e:
        print(f"[ERROR] General error: {e}")
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()
            print("[INFO] MySQL connection closed.")

# ---------- Step 3: Run the script ----------
if __name__ == "__main__":
    csv_file = r"D:\ForteAI\successfully_working\hr_sentiment_analysis_local_csv_based\data\sentiment_reports.csv"   # ✅ raw string path
    table_name = "sentiment_reports"     # table name in MySQL

    # MySQL credentials
    host = "localhost"
    user = "root"
    password = "rootroot"
    database = "fortai_employees"

    csv_to_mysql(csv_file, table_name, host, user, password, database)
    print("[INFO] CSV to MySQL process completed.")