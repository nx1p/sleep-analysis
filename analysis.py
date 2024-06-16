from rich import print
import os
import zipfile
from dotenv import load_dotenv
import csv
from datetime import datetime

def parse_sleep_record(record):
    # Parse a single sleep record and return a dictionary or object
    # containing the relevant information
    pass

def analyze_sleep_data(sleep_records):
    # Perform analysis on the parsed sleep records
    # Calculate statistics, identify patterns, etc.
    pass

def generate_report(analysis_results):
    # Generate a report based on the analysis results
    # Format the report as desired (text, graphs, etc.)
    pass

def process_sleep_data(csv_file):
    sleep_records = []

    with open(csv_file, 'r') as file:
        csv_reader = csv.reader(file)
        next(csv_reader)  # Skip the header line

        for row in csv_reader:
            sleep_record = parse_sleep_record(row)
            sleep_records.append(sleep_record)

    analysis_results = analyze_sleep_data(sleep_records)
    report = generate_report(analysis_results)

    # Send the report to Discord if needed
    send_discord_message(report)

def send_discord_message(message):
    """
    Sends a message to a Discord webhook.
    Used to send report of the analysis to a Discord webhook.
    """
    webhook = os.getenv("DISCORD_WEBHOOK")

def extract_export_zip(zip_file):
    """
    Extracts the contents of the backup export zip file from Sleep As Android
    to a folder named 'sleep-export' in the current working directory.

    Args:
        zip_file (str): The path to the zip file.
    """
    export_folder = "sleep-export"

    # Create the export folder if it doesn't exist
    if not os.path.exists(export_folder):
        os.makedirs(export_folder)

    # Extract the contents of the zip file to the export folder
    with zipfile.ZipFile(zip_file, "r") as zip_ref:
        zip_ref.extractall(export_folder)

    print(f"[green]Successfully extracted the contents of {zip_file} to {export_folder}[/green]")


if __name__ == '__main__':
    load_dotenv()
    extract_export_zip("sleep-export.zip") # todo: script should exit here if extract fails for some reason lol
    process_sleep_data('sleep-export/sleep-export.csv')
