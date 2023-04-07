import os
import requests
import uvicorn
import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.requests import Request
from fastapi.responses import Response, StreamingResponse

app = FastAPI()

origins = [
    "http://localhost",
    "http://localhost:8080",
    "https://chat.openai.com"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

access_token = os.getenv('ACCESS_TOKEN', '')
puid = os.getenv('PUID', '')
http_proxy = os.getenv('http_proxy', '')

if access_token == '' and puid == '':
    print('Error: ACCESS_TOKEN and PUID are not set')
    exit()

session = requests.session()

if http_proxy != '':
    session.proxies = {'https': http_proxy}
    print('Proxy set:' + http_proxy)


async def refresh_puid():
    global puid
    while True:
        try:
            url = 'https://chat.openai.com/backend-api/models'
            headers = {
                'Host': 'chat.openai.com',
                'Origin': 'https://chat.openai.com/chat',
                'Referer': 'https://chat.openai.com/chat',
                'Sec-Ch-Ua': 'Chromium";v="110", "Not A(Brand";v="24", "Brave";v="110',
                'Sec-Ch-Ua-Platform': 'Linux',
                'Content-Type': 'application/json',
                'Accept': 'text/event-stream',
                'Authorization': 'Bearer ' + access_token,
            }
            cookies = {'_puid': puid}
            response = session.get(url, headers=headers, cookies=cookies)
            response.raise_for_status()
            print('Got response: ' + str(response.status_code))
            if response.status_code != 200:
                print('Error: ' + response.text)
                break
            cookies = response.cookies
            puid_cookie = cookies.get('_puid')
            if puid_cookie:
                puid = puid_cookie.value
                print('puid: ' + puid)
            else:
                print('Error: Failed to refresh puid cookie')
        except Exception as e:
            print('Error: Failed to refresh puid cookie: ' + str(e))
        await asyncio.sleep(6 * 60 * 60)  # sleep for 6 hours


if access_token != '':
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    loop.create_task(refresh_puid())


@app.get('/')
def home():
    return {'data': 'Hello World!'}


@app.get('/ping')
def ping():
    return {'message': 'pong'}


@app.get("/api/{path:path}")
@app.post("/api/{path:path}")
@app.put("/api/{path:path}")
@app.delete("/api/{path:path}")
async def proxy(request: Request, path: str):
    try:
        url = 'https://chat.openai.com/backend-api/' + path
        headers = {
            'Host': 'chat.openai.com',
            'Origin': 'https://chat.openai.com/chat',
            'Connection': 'keep-alive',
            'Content-Type': 'application/json',
            'Keep-Alive': 'timeout=360',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36',
            'Authorization': request.headers.get('authorization', ''),
        }
        cookies = {}
        puid_header = request.headers.get('puid', '')
        if puid_header == '':
            cookies['_puid'] = puid
        else:
            cookies['_puid'] = puid_header
        response = session.request(request.method, url, headers=headers, cookies=cookies, json=request.json())
        response.raise_for_status()
        return StreamingResponse(iter(response.content), status_code=response.status_code, headers=response.headers)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == '__main__':
    uvicorn.run("main:app", host='127.0.0.1', port=8000)
