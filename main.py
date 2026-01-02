from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import json
import logging
import asyncio
import random
from typing import List

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Store active WebSocket connections
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        try:
            await websocket.send_text(message)
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")

    async def broadcast(self, message: str):
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"Error broadcasting to connection: {e}")
                disconnected.append(connection)
        
        # Remove disconnected connections
        for conn in disconnected:
            self.disconnect(conn)

# Data streaming manager
class DataStreamManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.streaming_tasks = {}

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        # Cancel streaming task if exists
        if websocket in self.streaming_tasks:
            self.streaming_tasks[websocket].cancel()
            del self.streaming_tasks[websocket]

    async def start_streaming(self, websocket: WebSocket):
        if websocket in self.streaming_tasks:
            return  # Already streaming
        
        async def stream_data():
            try:
                while True:
                    # Generate simulated sensor data
                    data = {
                        "temperature": round(random.uniform(18.0, 28.0), 1),
                        "humidity": round(random.uniform(30.0, 80.0), 1),
                        "pressure": round(random.uniform(1000.0, 1020.0), 1),
                        "timestamp": asyncio.get_event_loop().time()
                    }
                    
                    await websocket.send_text(json.dumps(data))
                    await asyncio.sleep(random.uniform(0.5, 2.0))  # Random interval
                    
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.error(f"Error in streaming task: {e}")
        
        task = asyncio.create_task(stream_data())
        self.streaming_tasks[websocket] = task

    def stop_streaming(self, websocket: WebSocket):
        if websocket in self.streaming_tasks:
            self.streaming_tasks[websocket].cancel()
            del self.streaming_tasks[websocket]

manager = ConnectionManager()
data_manager = DataStreamManager()

templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def get_chat_page(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/data-stream", response_class=HTMLResponse)
async def get_data_stream_page(request: Request):
    return templates.TemplateResponse("data_streaming_demo.html", {"request": request})

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            
            try:
                message_data = json.loads(data)
                # Send the raw message data as text for frontend to format
                response = f'{message_data["user"]}: {message_data["message"]}'
                await manager.broadcast(response)
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {e}")
                # Handle plain text messages
                response = f'Anonymous: {data}'
                await manager.broadcast(response)
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)

@app.websocket("/ws/data")
async def data_websocket_endpoint(websocket: WebSocket):
    await data_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            
            try:
                command = json.loads(data)
                if command.get("action") == "start_stream":
                    await data_manager.start_streaming(websocket)
                elif command.get("action") == "stop_stream":
                    data_manager.stop_streaming(websocket)
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error in data endpoint: {e}")
            
    except WebSocketDisconnect:
        data_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"Data WebSocket error: {e}")
        data_manager.disconnect(websocket)