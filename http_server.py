import aiohttp
from aiohttp import web
import asyncio
import importlib.util

print("Starting HTTP POST Upload Server")

# Import the main function from import_to_db.py
spec = importlib.util.spec_from_file_location("import_to_db", "import_to_db.py")
import_to_db = importlib.util.module_from_spec(spec)
spec.loader.exec_module(import_to_db)
print("Successfully imported import_to_db.py")

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
    success = await process_sleep_data(zip_data)
    
    if success:
        print("Processing completed successfully")
        return web.Response(text="ZIP file uploaded and processed successfully.")
    else:
        print("Processing failed")
        return web.Response(text="ZIP file uploaded, but processing failed.", status=500)

async def process_sleep_data(zip_data):
    print("Calling import_to_db.main function")
    success = await import_to_db.main(zip_data)
    print(f"import_to_db.main function returned: {success}")
    return success

app = web.Application(client_max_size=1024**3)  # Set to 1GB
app.router.add_post('/upload', handle_upload)

if __name__ == '__main__':
    print("Starting web server on http://0.0.0.0:8080")
    web.run_app(app, host='0.0.0.0', port=8080)
