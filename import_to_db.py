import zipfile
import csv
import os
import psycopg2
from datetime import datetime
from datetime import timezone as dt_timezone
from pytz import timezone


def verify_zip(zip_file):
    try:
        with zipfile.ZipFile(zip_file, 'r') as zip_ref:
            file_list = zip_ref.namelist()
            if 'sleep-export.csv' not in file_list:
                raise ValueError("sleep-export.csv not found in the zip file")
            zip_ref.extract('sleep-export.csv')
        return True
    except zipfile.BadZipFile:
        print("Error: Invalid zip file")
        return False
    except Exception as e:
        print(f"Error: {str(e)}")
        return False



def parse_sleep_record(row):
    id_timestamp = int(row['Id']) / 1000  # Convert milliseconds to seconds
    start_time = datetime.fromtimestamp(id_timestamp, dt_timezone.utc)
    
    tz = timezone(row['Tz'])
    end_time_str = row['To']
    end_time = datetime.strptime(end_time_str, '%d. %m. %Y %H:%M')
    end_time = tz.localize(end_time)

    hours = float(row['Hours'])
    len_adjust = float(row['LenAdjust'])
    if len_adjust != -1.0:
        sleep_duration = hours + (len_adjust / 60)
    else:
        sleep_duration = hours
    
    cycles = int(row['Cycles']) if row['Cycles'] != '-1' else None
    deep_sleep = float(row['DeepSleep']) if row['DeepSleep'] not in ['-1.0', '-2.0'] else None
    time_awake = abs(int(len_adjust)) if len_adjust != -1.0 else None
    
    return {
        'start_time': start_time,
        'end_time': end_time,
        'sleep_duration': sleep_duration,
        'cycles': cycles,
        'deep_sleep': deep_sleep,
        'time_awake': time_awake,
        'location_hash': row['Geo'],
        'comment': row['Comment']
    }


def import_to_database(records):
    conn = psycopg2.connect(
        dbname="sleep_data",
        user="postgres",
        password="dev_password",
        host="192.168.0.52"
    )
    cur = conn.cursor()
    
    total_records = 0
    new_records = 0
    
    for record in records:
        cur.execute("""
            INSERT INTO sleep_records 
            (start_time, end_time, sleep_duration, cycles, deep_sleep, time_awake, location_hash, comment)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (start_time) DO NOTHING
            RETURNING start_time
        """, (
            record['start_time'],
            record['end_time'],
            record['sleep_duration'],
            record['cycles'],
            record['deep_sleep'],
            record['time_awake'],
            record['location_hash'],
            record['comment']
        ))
        
        total_records += 1
        if cur.fetchone() is not None:
            new_records += 1
    
    conn.commit()
    cur.close()
    conn.close()
    
    print(f"Total sleep records processed: {total_records}")
    print(f"New sleep records added to the database: {new_records}")

    return total_records, new_records


def setup_database(host, user, password, dbname):
    new_db_created = False
    new_table_created = False

    # Connect to default database to create new database
    conn = psycopg2.connect(
        host=host,
        user=user,
        password=password,
        dbname="postgres"
    )
    conn.autocommit = True
    cur = conn.cursor()

    # Create database if it doesn't exist
    cur.execute(f"SELECT 1 FROM pg_catalog.pg_database WHERE datname = '{dbname}'")
    if cur.fetchone() is None:
        cur.execute(f"CREATE DATABASE {dbname}")
        new_db_created = True
    
    cur.close()
    conn.close()

    # Connect to the new database
    conn = psycopg2.connect(
        host=host,
        user=user,
        password=password,
        dbname=dbname
    )
    cur = conn.cursor()

    # Check if table exists
    cur.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = 'sleep_records'
        )
    """)
    table_exists = cur.fetchone()[0]

    if not table_exists:
        # Create table if it doesn't exist
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sleep_records (
                start_time TIMESTAMP WITH TIME ZONE PRIMARY KEY,
                end_time TIMESTAMP WITH TIME ZONE,
                sleep_duration FLOAT,
                cycles INTEGER,
                deep_sleep FLOAT,
                time_awake INTEGER,
                location_hash TEXT,
                comment TEXT
            )
        """)
        new_table_created = True

    conn.commit()
    cur.close()
    conn.close()

    if new_db_created and new_table_created:
        print(f"Database '{dbname}' and table 'sleep_records' set up successfully.")
    elif new_db_created:
        print(f"Database '{dbname}' created successfully. Table 'sleep_records' already existed.")
    elif new_table_created:
        print(f"Table 'sleep_records' created successfully in existing database '{dbname}'.")
    else:
        print(f"Database '{dbname}' and table 'sleep_records' are already set up.")



def process_sleep_data(csv_file):
    records = []
    with open(csv_file, 'r') as file:
        csv_reader = csv.reader(file)

        while True:
            try:
                header = next(csv_reader)
                values = next(csv_reader)
                row = dict(zip(header, values))
                record = parse_sleep_record(row)
                records.append(record)
            except StopIteration:
                break

    return records


def main():
    host = "192.168.0.52"
    user = "postgres"
    password = "dev_password"
    dbname = "sleep_data"

    setup_database(host, user, password, dbname)

    zip_file = 'sleep-export.zip'
    if verify_zip(zip_file):
        records = process_sleep_data('sleep-export.csv')
        total_records, new_records = import_to_database(records)
        os.remove('sleep-export.csv')
        print(f"Sleep data processed successfully. {total_records} records processed, {new_records} new records added.")
    else:
        print("Failed to process sleep data")


if __name__ == "__main__":
    main()
