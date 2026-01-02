from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
import json
import logging
import asyncio
import random
from typing import List, AsyncGenerator

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Pydantic model for sensor data
class SensorReading(BaseModel):
    temperature: float  # Celsius
    humidity: float     # Percentage
    pressure: float     # hPa
    timestamp: datetime
    
    def to_html(self) -> str:
        """Convert to HTML for SSE transmission"""
        return f'<div class="data-item animate-in slide-in-from-bottom-2 duration-300 mb-2 p-3 bg-white rounded-lg border border-gray-200"><div class="flex items-center justify-between"><div class="flex items-center space-x-4"><div class="w-2 h-2 bg-blue-500 rounded-full"></div><div class="text-sm"><span class="font-medium text-gray-900">SSE Data</span><span class="text-gray-500 ml-2">{self.timestamp.strftime("%H:%M:%S")}</span></div></div><div class="flex items-center space-x-4 text-sm"><span class="text-blue-600">🌡️ {self.temperature}°C</span><span class="text-green-600">💧 {self.humidity}%</span><span class="text-purple-600">📊 {self.pressure} hPa</span></div></div></div>'

app = FastAPI()

# Add CORS middleware for cross-origin support
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# SSE Connection Manager
class SSEConnectionManager:
    def __init__(self):
        self.active_connections = set()
    
    def add_connection(self, connection_id: str):
        """Add a connection to the active set"""
        self.active_connections.add(connection_id)
        logger.info(f"SSE connection added: {connection_id}")
    
    def remove_connection(self, connection_id: str):
        """Remove a connection from the active set"""
        self.active_connections.discard(connection_id)
        logger.info(f"SSE connection removed: {connection_id}")
    
    async def generate_data_stream(self) -> AsyncGenerator[str, None]:
        """Generate simulated sensor data stream"""
        try:
            while True:
                # Generate simulated sensor data
                sensor_data = SensorReading(
                    temperature=round(random.uniform(18.0, 28.0), 1),
                    humidity=round(random.uniform(30.0, 80.0), 1),
                    pressure=round(random.uniform(1000.0, 1020.0), 1),
                    timestamp=datetime.now()
                )
                
                # Format as SSE event
                html_data = sensor_data.to_html()
                sse_event = f"data: {html_data}\n\n"
                
                yield sse_event
                
                # Wait for random interval between 0.5 and 2 seconds
                await asyncio.sleep(random.uniform(0.5, 2.0))
                
        except asyncio.CancelledError:
            logger.info("SSE data stream cancelled")
        except Exception as e:
            logger.error(f"Error in SSE data stream: {e}")

sse_manager = SSEConnectionManager()

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

@app.get("/sse-demo", response_class=HTMLResponse)
async def get_sse_demo_page(request: Request):
    return templates.TemplateResponse("htmx_sse_demo.html", {"request": request})

@app.get("/sse-stream")
async def sse_stream():
    """SSE endpoint that streams sensor data"""
    import uuid
    connection_id = str(uuid.uuid4())
    
    async def event_stream():
        sse_manager.add_connection(connection_id)
        try:
            async for event in sse_manager.generate_data_stream():
                yield event
        except asyncio.CancelledError:
            logger.info(f"SSE stream cancelled for connection: {connection_id}")
        except Exception as e:
            logger.error(f"Error in SSE stream for connection {connection_id}: {e}")
        finally:
            sse_manager.remove_connection(connection_id)
    
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control",
        }
    )

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