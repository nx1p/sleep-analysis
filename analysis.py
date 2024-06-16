# big todos:
# - sleep data analysis on sleep quality not just quantity
# - make code more robust (error handling, checking values, etc)
# - optimisations? probably?
# - clean up code (this kinda comes under optimisations tho lol :p)
# smol todos:
# - add a stat for least amount that was slept in one night during a time period and when? that would be nice

from rich import print
import os
import zipfile
from dotenv import load_dotenv
import csv
from datetime import datetime
from pytz import timezone
from datetime import datetime, timedelta
import requests

def send_discord_message(message):
    """
    Sends a message to a Discord webhook.
    Used to send report of the analysis to a Discord webhook.
    """
    webhook = os.getenv("DISCORD_WEBHOOK")
    
    if webhook is None:
        print("DISCORD_WEBHOOK environment variable not set. Skipping sending message to Discord.")
        return

    data = {
        "content": message
    }

    try:
        response = requests.post(webhook, json=data)
        response.raise_for_status()
        print("Message sent to Discord successfully!")
    except requests.exceptions.RequestException as e:
        print(f"Error sending message to Discord: {e}")

# Parse a single sleep record and return a dictionary or object
# containing the relevant information
def parse_sleep_record(record):
    sleep_data = {}

    # Extract the timezone
    tz_str = record[1]  # 'Tz' field
    tz = timezone(tz_str)

    # Extract the start time
    start_time_str = record[2]  # 'From' field
    start_time = datetime.strptime(start_time_str, '%d. %m. %Y %H:%M')
    sleep_data['start_time'] = tz.localize(start_time)

    # Extract the end time
    end_time_str = record[3]  # 'To' field
    end_time = datetime.strptime(end_time_str, '%d. %m. %Y %H:%M')
    sleep_data['end_time'] = tz.localize(end_time)

    # Extract the LenAdjust value (minutes spent awake during sleep record (as a negative))
    len_adjust_str = record[13]  # 'LenAdjust' field
    if len_adjust_str == '-1.0':
        sleep_data['len_adjust'] = None  # Manually added record, data not available
    else:
        sleep_data['len_adjust'] = int(float(len_adjust_str))

    return sleep_data

# Calculate the sleep to awake ratio given sleep records data and a time period
def calculate_sleep_awake_ratio(sleep_records, time_period):
    end_time = datetime.now(timezone('UTC'))
    start_time = end_time - timedelta(days=time_period)

    total_sleep_duration = timedelta()

    for record in sleep_records:
        if record['start_time'] >= start_time:
            sleep_duration = record['end_time'] - record['start_time']
            if record['len_adjust'] is not None:
                sleep_duration += timedelta(minutes=record['len_adjust'])
            total_sleep_duration += sleep_duration

    total_duration = timedelta(days=time_period)
    total_awake_duration = total_duration - total_sleep_duration

    sleep_ratio = (total_sleep_duration / total_duration) * 100
    awake_ratio = (total_awake_duration / total_duration) * 100

    return sleep_ratio, awake_ratio, total_sleep_duration

def analyze_sleep_data(sleep_records):
    time_periods = [1, 3, 7]  # 24 hours, 3 days, 7 days
    analysis_results = {}

    for period in time_periods:
        sleep_ratio, awake_ratio = calculate_sleep_awake_ratio(sleep_records, period)
        analysis_results[period] = {
            'sleep_ratio': sleep_ratio,
            'awake_ratio': awake_ratio
        }

    return analysis_results

# Perform analysis on the parsed sleep records
# Calculate statistics, identify patterns, etc.
def analyze_sleep_data(sleep_records):
    time_periods = [1, 3, 7]  # 24 hours, 3 days, 7 days
    analysis_results = {}

    for period in time_periods:
        sleep_ratio, awake_ratio, total_sleep_duration = calculate_sleep_awake_ratio(sleep_records, period)
        analysis_results[period] = {
            'sleep_ratio': sleep_ratio,
            'awake_ratio': awake_ratio,
            'total_sleep_duration': total_sleep_duration
        }

    return analysis_results


# Generate a report based on the analysis results
# Format the report as desired (text, graphs, etc.)
def generate_report(analysis_results):
    report = "=-=-=-=-=  Sleep Quantity Stats  =-=-=-=-=\n"

    for period, results in analysis_results.items():
        sleep_ratio = results['sleep_ratio']
        awake_ratio = results['awake_ratio']
        total_sleep_duration = results['total_sleep_duration']

        if period == 1:
            period_label = "24h"
        elif period == 3:
            period_label = "3d"
        elif period == 7:
            period_label = "7d"
        else:
            raise ValueError(f"Unsupported time period: {period}")

        report += f"--=--=--=    {period_label}    =--=--=--\n"
        report += f"asleep percent: {sleep_ratio:.2f}%\n"
        report += f"awake percent: {awake_ratio:.2f}%\n"

        if period == 1:
            sleep_hours = total_sleep_duration.total_seconds() / 3600
            report += f"sleep quantity: {sleep_hours:.0f}h\n"
        else:
            avg_sleep_duration = total_sleep_duration / period
            avg_sleep_hours = avg_sleep_duration.total_seconds() / 3600
            avg_awake_hours = 24 - avg_sleep_hours
            report += f"avg 24h asleep: {avg_sleep_hours:.1f}h \n"
            report += f"avg 24h awake: {avg_awake_hours:.1f}h\n"

    report += "--=--=--=--=--=--=--=--=--\n"
    report += "=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-="

    return report





def process_sleep_data(csv_file):
    sleep_records = []

    with open(csv_file, 'r') as file:
        csv_reader = csv.reader(file)

        while True:
            try:
                header = next(csv_reader)
                values = next(csv_reader)
                sleep_record = parse_sleep_record(values)
                sleep_records.append(sleep_record)
            except StopIteration:
                break

    analysis_results = analyze_sleep_data(sleep_records)
    report = generate_report(analysis_results)

    # Send the report to Discord
    send_discord_message(report)


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
