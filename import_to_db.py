# =-=-=-=-==-=-=--=
# Sleep Data Import
# =-=-=-=-==-=-=--=
#
# This script processes sleep data from a ZIP file containing a CSV export,
# parses the sleep records, and imports them into a PostgreSQL database.
# It performs the following main functions:
#
# 1. Verifies and extracts the 'sleep-export.csv' file from a ZIP archive.
# 2. Sets up the PostgreSQL database and creates the necessary table if not exists.
# 3. Parses each sleep record from the CSV file, extracting relevant information.
# 4. Imports the parsed sleep records into the database, avoiding duplicates.
# 5. Provides a summary of the total records processed and new records added.
#
# The script handles various data points such as sleep duration, cycles,
# deep sleep, time awake, and location. It also manages timezone conversions
# to ensure accurate timestamp storage in the database.

import zipfile
import csv
import os
import io
import asyncpg
import asyncio
from datetime import datetime
from datetime import timezone as dt_timezone
from pytz import timezone
import patoolib
import os
import tempfile

def format_progress_bar(percentage, length=10):
    filled = int(percentage / 100 * length)
    return '█' * filled + '░' * (length - filled)

def format_sleep_record(record):
    start_timestamp = int(record['start_time'].timestamp())
    end_timestamp = int(record['end_time'].timestamp())
    duration = record['sleep_duration']
    
    if duration > 0:
        time_awake_percent = (record['time_awake'] / 60) / duration * 100 if record['time_awake'] is not None else 0
        deep_sleep_percent = record['deep_sleep'] * 100 if record['deep_sleep'] is not None else 0
    else:
        time_awake_percent = 0
        deep_sleep_percent = 0

    return {
        "name": f"Sleep Record: <t:{start_timestamp}:f>",
        "value": f"End Time: <t:{end_timestamp}:t>\n"
                 f"Duration: {duration:.2f} hours\n"
                 f"Time Awake: {time_awake_percent:.2f}%\n"
                 f"Deep Sleep: {deep_sleep_percent:.2f}%"
    }

def verify_zip(zip_data):
    try:
        # Create a temporary directory to extract files
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a temporary file to save the BytesIO content
            temp_zip = os.path.join(temp_dir, 'temp.zip')
            with open(temp_zip, 'wb') as f:
                if isinstance(zip_data, io.BytesIO):
                    f.write(zip_data.getvalue())
                elif isinstance(zip_data, str):
                    with open(zip_data, 'rb') as src:
                        f.write(src.read())
                else:
                    raise ValueError("Invalid input type for zip_data")

            # Extract the archive contents
            extract_dir = os.path.join(temp_dir, 'extracted')
            os.mkdir(extract_dir)
            patoolib.extract_archive(temp_zip, outdir=extract_dir)
            
            # Look for the sleep export CSV file
            for root, dirs, files in os.walk(extract_dir):
                for file in files:
                    if file.lower().endswith('.csv') and 'sleep' in file.lower():
                        source_path = os.path.join(root, file)
                        # Copy the file to the current directory and rename it
                        os.rename(source_path, 'sleep-export.csv')
                        print(f"Successfully extracted: {file}")
                        return True
            
            raise ValueError("No sleep-related CSV file found in the archive")
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


async def setup_database(host, user, password, dbname):
    # Connect to default database to create new database
    conn = await asyncpg.connect(
        host=host,
        user=user,
        password=password,
        database="postgres"
    )
    
    # Create database if it doesn't exist
    exists = await conn.fetchval(f"SELECT 1 FROM pg_catalog.pg_database WHERE datname = $1", dbname)
    if not exists:
        await conn.execute(f"CREATE DATABASE {dbname}")
        print(f"Database '{dbname}' created successfully.")
    
    await conn.close()

    # Connect to the new database
    conn = await asyncpg.connect(
        host=host,
        user=user,
        password=password,
        database=dbname
    )

    # Create table if it doesn't exist
    await conn.execute("""
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
    
    await conn.close()
    print(f"Table 'sleep_records' is set up in database '{dbname}'.")
async def import_to_database(records):
    conn = await asyncpg.connect(
        host="192.168.0.52",
        user="postgres",
        password="dev_password",
        database="sleep_data"
    )
    
    total_records = 0
    new_records = 0
    new_record_details = []
    
    for record in records:
        result = await conn.fetchrow("""
            INSERT INTO sleep_records 
            (start_time, end_time, sleep_duration, cycles, deep_sleep, time_awake, location_hash, comment)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            ON CONFLICT (start_time) DO NOTHING
            RETURNING start_time
        """, record['start_time'], record['end_time'], record['sleep_duration'],
              record['cycles'], record['deep_sleep'], record['time_awake'],
              record['location_hash'], record['comment'])
        
        total_records += 1
        if result is not None:
            new_records += 1
            new_record_details.append(format_sleep_record(record))
    
    await conn.close()
    
    print(f"Total sleep records processed: {total_records}")
    print(f"New sleep records added to the database: {new_records}")
    return total_records, new_records, new_record_details


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


async def process_zip_data(zip_data):
    zip_file = io.BytesIO(zip_data)
    if verify_zip(zip_file):
        records = process_sleep_data('sleep-export.csv')
        total_records, new_records, new_record_details = await import_to_database(records)
        os.remove('sleep-export.csv')
        print(f"Sleep data processed successfully. {total_records} records processed, {new_records} new records added.")
        return True, new_records, new_record_details
    else:
        print("Failed to process sleep data")
        return False, 0, []

async def main(zip_data=None):
    host = "192.168.0.52"
    user = "postgres"
    password = "dev_password"
    dbname = "sleep_data"

    await setup_database(host, user, password, dbname)

    if zip_data:
        success, new_records, new_record_details = await process_zip_data(zip_data)
        return success, new_records, new_record_details
    else:
        zip_file = 'sleep-export.zip'
        if verify_zip(zip_file):
            records = process_sleep_data('sleep-export.csv')
            total_records, new_records, new_record_details = await import_to_database(records)
            os.remove('sleep-export.csv')
            print(f"Sleep data processed successfully. {total_records} records processed, {new_records} new records added.")
            return True, new_records, new_record_details
        else:
            print("Failed to process sleep data")
            return False, 0, []

if __name__ == "__main__":
    asyncio.run(main())


