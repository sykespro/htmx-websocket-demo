# HTMX WebSocket Demo

A collection of real-time applications using HTMX and FastAPI WebSockets.

## Features

### Chat Demo (`/`)
- Real-time messaging using WebSockets
- HTMX for seamless frontend interactions
- Multiple user support
- Connection status indicator
- Clean, responsive UI

### Data Streaming Demo (`/data-stream`)
- Real-time sensor data simulation
- Live charts and statistics
- WebSocket-based data streaming
- Interactive controls (start/stop/clear)
- Real-time analytics dashboard

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

Or install uvicorn with WebSocket support directly:
```bash
pip install 'uvicorn[standard]' fastapi jinja2 python-multipart
```

2. Run the server:
```bash
uvicorn main:app --reload
```

3. Open your browser to `http://localhost:8000`

## Usage

### Chat Demo
- Enter your name in the first input field
- Type messages and click Send
- Open multiple browser tabs to test real-time messaging
- Messages appear instantly for all connected users

### Data Streaming Demo
- Navigate to `/data-stream`
- Click "Start" to begin receiving simulated sensor data
- Watch real-time charts and statistics update automatically
- Use "Stop" to pause streaming and "Clear" to reset data
- Open multiple tabs to see synchronized data streams

## How it Works

- FastAPI handles WebSocket connections and message broadcasting
- HTMX WebSocket extension manages frontend WebSocket communication
- Messages are sent as JSON and broadcast to all connected clients
- The UI updates automatically when new messages arrive
- Data streaming uses separate WebSocket endpoint with asyncio tasks for continuous data generation