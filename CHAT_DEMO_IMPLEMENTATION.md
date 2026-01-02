# Chat Demo Implementation Guide

A complete guide to implementing real-time chat functionality using HTMX WebSockets, FastAPI, and Alpine.js.

## Overview

This implementation demonstrates bidirectional real-time communication using WebSockets. Users can join chat rooms, send messages, and see messages from other users instantly. The demo features automatic reconnection, message grouping, and a clean, responsive UI.

## Architecture

```
┌─────────────────┐    WebSocket     ┌─────────────────┐
│   Browser       │ ←──────────────→ │   FastAPI       │
│   (HTMX + JS)   │                  │   Server        │
└─────────────────┘                  └─────────────────┘
        │                                      │
        ├─ HTMX WebSocket Extension            ├─ ConnectionManager
        ├─ Alpine.js State Management         ├─ Message Broadcasting
        └─ Custom Message Parsing             └─ Connection Tracking
```

## Backend Implementation (FastAPI)

### 1. Dependencies

```python
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import List
import json
import logging
```

### 2. Connection Manager

```python
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
            logging.error(f"Error sending personal message: {e}")

    async def broadcast(self, message: str):
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logging.error(f"Error broadcasting to connection: {e}")
                disconnected.append(connection)
        
        # Remove disconnected connections
        for conn in disconnected:
            self.disconnect(conn)

manager = ConnectionManager()
```

### 3. WebSocket Endpoint

```python
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
                logging.error(f"JSON decode error: {e}")
                # Handle plain text messages
                response = f'Anonymous: {data}'
                await manager.broadcast(response)
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logging.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)
```

### 4. HTML Route

```python
@app.get("/", response_class=HTMLResponse)
async def get_chat_page(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})
```

## Frontend Implementation

### 1. Required Libraries

```html
<script src="https://unpkg.com/htmx.org@1.9.10"></script>
<script src="https://unpkg.com/htmx.org/dist/ext/ws.js"></script>
<script src="https://cdn.tailwindcss.com"></script>
<script src="https://unpkg.com/alpinejs@3.x.x/dist/cdn.min.js" defer></script>
```

### 2. Alpine.js Application State

```javascript
function chatApp() {
    return {
        socket: null,
        isConnected: false,
        isConnecting: false,
        username: '',
        tempUsername: '',
        currentMessage: '',
        messages: [],
        
        get connectionStatus() {
            if (this.isConnecting) return 'Connecting...';
            return this.isConnected ? 'Connected' : 'Disconnected';
        },
        
        init() {
            this.initWebSocket();
        },
        
        // ... other methods
    }
}
```

### 3. WebSocket Connection Management

```javascript
initWebSocket() {
    this.isConnecting = true;
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;
    
    this.socket = new WebSocket(wsUrl);
    
    this.socket.onopen = (event) => {
        this.isConnected = true;
        this.isConnecting = false;
    };
    
    this.socket.onclose = (event) => {
        this.isConnected = false;
        this.isConnecting = false;
        
        // Attempt to reconnect after 3 seconds
        setTimeout(() => this.initWebSocket(), 3000);
    };
    
    this.socket.onerror = (error) => {
        console.error('WebSocket error:', error);
        this.isConnecting = false;
    };
    
    this.socket.onmessage = (event) => {
        this.addMessageToUI(event.data);
    };
}
```

### 4. Message Handling

```javascript
sendMessage() {
    const message = this.currentMessage.trim();
    
    if (message && this.socket && this.socket.readyState === WebSocket.OPEN && this.username) {
        const data = JSON.stringify({
            user: this.username,
            message: message
        });
        this.socket.send(data);
        this.currentMessage = '';
    }
}

addMessageToUI(textContent) {
    const messagesDiv = document.getElementById('messages');
    
    // Parse the plain text message
    const { username, message } = this.parseMessage(textContent);
    const timestamp = new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
    
    // Check if this is from the same user as the last message
    const lastMessage = messagesDiv.lastElementChild;
    const isConsecutive = lastMessage && 
        lastMessage.dataset.username === username && 
        this.isRecentMessage(lastMessage.dataset.timestamp);
    
    // Create message element with appropriate styling
    const messageElement = document.createElement('div');
    messageElement.className = 'message-item animate-in slide-in-from-bottom-2 duration-300';
    messageElement.dataset.username = username;
    messageElement.dataset.timestamp = Date.now();
    
    // Different layouts for consecutive vs new messages
    if (isConsecutive) {
        // Compact message without avatar and name
        messageElement.innerHTML = `
            <div class="flex hover:bg-gray-50 group transition-colors py-0.5 px-2 -mx-2 rounded ml-11">
                <div class="flex-1 min-w-0">
                    <div class="text-sm text-gray-900 leading-relaxed">${message}</div>
                </div>
                <div class="opacity-0 group-hover:opacity-100 text-xs text-gray-400 ml-2 transition-opacity">
                    ${timestamp}
                </div>
            </div>
        `;
    } else {
        // Full message with avatar and name
        messageElement.innerHTML = `
            <div class="flex hover:bg-gray-50 group transition-colors py-2 px-2 -mx-2 rounded ${messagesDiv.children.length > 0 ? 'mt-3' : ''}">
                <div class="flex-shrink-0 mr-3">
                    <div class="w-8 h-8 bg-gradient-to-br from-primary-400 to-primary-600 rounded-lg flex items-center justify-center">
                        <span class="text-xs font-medium text-white">${username.charAt(0).toUpperCase()}</span>
                    </div>
                </div>
                <div class="flex-1 min-w-0">
                    <div class="flex items-baseline space-x-2 mb-1">
                        <span class="text-sm font-semibold text-gray-900">${username}</span>
                        <span class="text-xs text-gray-500">${timestamp}</span>
                    </div>
                    <div class="text-sm text-gray-900 leading-relaxed">${message}</div>
                </div>
            </div>
        `;
    }
    
    messagesDiv.appendChild(messageElement);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
    
    this.messages.push(textContent);
}
```

### 5. HTML Structure

```html
<body class="bg-gray-50 min-h-screen" x-data="chatApp()">
    <!-- Header with connection status -->
    <header class="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
            <div class="flex items-center justify-between h-16">
                <div class="flex items-center space-x-3">
                    <div class="w-8 h-8 bg-primary-500 rounded-lg flex items-center justify-center">
                        <!-- Chat icon -->
                    </div>
                    <h1 class="text-xl font-semibold text-gray-900">Chat</h1>
                </div>
                
                <!-- Connection Status -->
                <div class="flex items-center space-x-2">
                    <div class="flex items-center space-x-2" 
                         :class="isConnected ? 'text-green-600' : 'text-red-600'">
                        <div class="w-2 h-2 rounded-full" 
                             :class="isConnected ? 'bg-green-500' : 'bg-red-500'"
                             x-show="!isConnecting"
                             x-transition></div>
                        <div class="w-2 h-2 rounded-full bg-yellow-500 animate-pulse" 
                             x-show="isConnecting"
                             x-transition></div>
                        <span class="text-sm font-medium" x-text="connectionStatus"></span>
                    </div>
                </div>
            </div>
        </div>
    </header>

    <!-- Main Chat Container -->
    <main class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div class="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
            
            <!-- Messages Area -->
            <div class="h-96 overflow-y-auto p-3 bg-gray-50" id="messages">
                <!-- Messages will be inserted here -->
            </div>

            <!-- Input Area -->
            <div class="border-t border-gray-200 bg-white p-4">
                <!-- User Name Input -->
                <div class="mb-3" x-show="!username" x-transition>
                    <label class="block text-sm font-medium text-gray-700 mb-2">What's your name?</label>
                    <div class="flex space-x-3">
                        <input type="text" 
                               x-model="tempUsername"
                               @keydown.enter="setUsername()"
                               placeholder="Enter your name"
                               class="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-colors">
                        <button @click="setUsername()" 
                                :disabled="!tempUsername.trim()"
                                class="px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors">
                            Continue
                        </button>
                    </div>
                </div>

                <!-- Message Input -->
                <div x-show="username" x-transition>
                    <div class="flex items-start space-x-3">
                        <textarea x-model="currentMessage"
                                @keydown.enter.prevent="sendMessage()"
                                @input="autoResize($event)"
                                placeholder="Type your message..."
                                rows="1"
                                class="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent resize-none transition-colors h-12"></textarea>
                        <button @click="sendMessage()" 
                                :disabled="!currentMessage.trim() || !isConnected"
                                class="w-12 h-12 bg-primary-500 text-white rounded-lg hover:bg-primary-600 disabled:opacity-50 disabled:cursor-not-allowed transition-all transform hover:scale-105 active:scale-95 flex items-center justify-center flex-shrink-0">
                            <!-- Send icon -->
                        </button>
                    </div>
                </div>
            </div>
        </div>
    </main>
</body>
```

## Key Features

### 1. Automatic Reconnection
- Reconnects every 3 seconds on connection loss
- Visual feedback during reconnection attempts
- Maintains chat history during reconnections

### 2. Message Grouping
- Consecutive messages from the same user are grouped
- Timestamps appear on hover for grouped messages
- Clean, Discord-like message layout

### 3. Responsive Design
- Works on desktop and mobile devices
- Adaptive textarea that grows with content
- Touch-friendly interface elements

### 4. Real-time Connection Status
- Visual indicators for connection state
- Color-coded status (green=connected, red=disconnected, yellow=connecting)
- Connection status text updates

## Customization Options

### 1. Message Formatting
```javascript
// Custom message parsing
parseMessage(messageContent) {
    const match = messageContent.match(/^([^:]+):\s*(.+)$/);
    if (match) {
        return { username: match[1].trim(), message: match[2].trim() };
    }
    return { username: 'Anonymous', message: messageContent.trim() };
}
```

### 2. Connection Settings
```javascript
// Adjust reconnection timing
setTimeout(() => this.initWebSocket(), 3000); // 3 second delay

// Custom WebSocket URL
const wsUrl = `${protocol}//${window.location.host}/ws`;
```

### 3. UI Theming
```javascript
// Tailwind configuration
tailwind.config = {
    theme: {
        extend: {
            colors: {
                primary: {
                    50: '#eff6ff',
                    500: '#3b82f6',
                    600: '#2563eb',
                    700: '#1d4ed8'
                }
            }
        }
    }
}
```

## Deployment Considerations

### 1. WebSocket Proxy Configuration (Nginx)
```nginx
location /ws {
    proxy_pass http://backend;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

### 2. CORS Configuration
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 3. Error Handling
- Implement proper logging for WebSocket errors
- Add rate limiting for message sending
- Handle malformed JSON gracefully
- Monitor connection counts and resource usage

## Testing

### 1. Multi-tab Testing
- Open multiple browser tabs to test real-time messaging
- Verify message broadcasting works correctly
- Test connection recovery after network issues

### 2. Network Conditions
- Test with slow/unstable connections
- Verify reconnection logic works properly
- Check message delivery guarantees

### 3. Load Testing
- Test with multiple concurrent connections
- Monitor memory usage and connection cleanup
- Verify broadcast performance with many users

This implementation provides a solid foundation for real-time chat applications with WebSockets, featuring automatic reconnection, clean UI, and robust error handling.