import os
from dotenv import load_dotenv
import aiohttp
from aiohttp import web
import asyncio
import importlib.util

print("Starting HTTP POST Upload Server")

load_dotenv()
DISCORD_WEBHOOK = os.getenv('DISCORD_WEBHOOK')

# Import the main function from import_to_db.py
spec = importlib.util.spec_from_file_location("import_to_db", "import_to_db.py")
import_to_db = importlib.util.module_from_spec(spec)
spec.loader.exec_module(import_to_db)
print("Successfully imported import_to_db.py")

if not DISCORD_WEBHOOK or not isinstance(DISCORD_WEBHOOK, str):
    print("Error: DISCORD_WEBHOOK is not set or is not a string")
    DISCORD_WEBHOOK = None

async def send_discord_notification(message, new_record_details=None):
    if DISCORD_WEBHOOK:
        async with aiohttp.ClientSession() as session:
            embed = {
                "title": "Sleep Data Update",
                "description": message,
                "color": 0x00ff00,
                "fields": []
            }
            
            if new_record_details:
                embed["fields"] = new_record_details
            
            webhook_data = {"embeds": [embed]}
            async with session.post(DISCORD_WEBHOOK, json=webhook_data) as response:
                if response.status == 204:
                    print("Discord notification sent successfully")
                else:
                    print(f"Failed to send Discord notification. Status: {response.status}")
    else:
        print("Discord notification not sent: DISCORD_WEBHOOK is not set")

async def handle_upload(request):
    print("Received upload request")
    
    content_type = request.headers.get('Content-Type', '')
    if content_type != 'application/zip':
        print("Error: Invalid content type")
        return web.Response(text="Invalid content type. Please upload a ZIP file.", status=400)
    
    zip_data = await request.read()
    print(f"Received ZIP data: {len(zip_data)} bytes")
    
    # Process the uploaded file
    print("Processing sleep data")
    success, new_records, new_record_details = await process_sleep_data(zip_data)
    
    if success:
        print("Processing completed successfully")
        if new_records > 0:
            await send_discord_notification(f"New sleep data processed! {new_records} new records added.", new_record_details)
        else:
            await send_discord_notification("Sleep tracking likely cancelled. No new sleep data found.")
        return web.Response(text="ZIP file uploaded and processed successfully.")
    else:
        print("Processing failed")
        await send_discord_notification("Failed to process sleep data. Please check the logs.")
        return web.Response(text="ZIP file uploaded, but processing failed.", status=500)

async def process_sleep_data(zip_data):
    print("Calling import_to_db.main function")
    success, new_records, new_record_details = await import_to_db.main(zip_data)
    print(f"import_to_db.main function returned: success={success}, new_records={new_records}")
    return success, new_records, new_record_details

app = web.Application(client_max_size=1024**3)  # Set to 1GB
app.router.add_post('/upload', handle_upload)

if __name__ == '__main__':
    print("Starting web server on http://0.0.0.0:8080")
    web.run_app(app, host='0.0.0.0', port=8080)
