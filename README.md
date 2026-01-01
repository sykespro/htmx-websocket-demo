# HTMX WebSocket Chat Demo

A simple real-time chat application using HTMX and FastAPI WebSockets.

## Features

- Real-time messaging using WebSockets
- HTMX for seamless frontend interactions
- Multiple user support
- Connection status indicator
- Clean, responsive UI

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

- Enter your name in the first input field
- Type messages and click Send
- Open multiple browser tabs to test real-time messaging
- Messages appear instantly for all connected users

## How it Works

- FastAPI handles WebSocket connections and message broadcasting
- HTMX WebSocket extension manages frontend WebSocket communication
- Messages are sent as JSON and broadcast to all connected clients
- The UI updates automatically when new messages arrive