import aiohttp
import asyncio

async def test_upload():
    url = 'http://localhost:8080/upload'
    filename = 'sleep-export.zip'

    async with aiohttp.ClientSession() as session:
        with open(filename, 'rb') as f:
            data = f.read()

        headers = {'Content-Type': 'application/zip'}

        print(f"Uploading {filename} to {url}")
        async with session.post(url, data=data, headers=headers) as response:
            print(f"Status: {response.status}")
            print("Response:")
            print(await response.text())

if __name__ == "__main__":
    asyncio.run(test_upload())
