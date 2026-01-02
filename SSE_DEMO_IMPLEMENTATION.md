# SSE Demo Implementation Guide

A comprehensive guide to implementing real-time data streaming using Server-Sent Events (SSE) with HTMX, FastAPI, and Alpine.js. This approach provides unidirectional server-to-client communication with automatic reconnection and minimal JavaScript.

## Overview

Server-Sent Events (SSE) is a web standard that allows a server to push data to a client over a single HTTP connection. Unlike WebSockets, SSE is unidirectional (server-to-client only) and uses standard HTTP, making it simpler to implement and more firewall-friendly.

### Key Benefits
- **Simpler Protocol**: Uses standard HTTP with `text/event-stream` content type
- **Automatic Reconnection**: Browsers automatically reconnect on connection loss
- **Firewall Friendly**: Works through most proxies and firewalls
- **Built-in Event Types**: Supports custom event types and data formatting
- **Lower Overhead**: No custom message framing required

### When to Use SSE vs WebSockets
- **Use SSE for**: Live feeds, notifications, real-time dashboards, log streaming
- **Use WebSockets for**: Chat applications, gaming, bidirectional communication

## Architecture

```
┌─────────────┐    HTTP GET     ┌──────────────────┐
│   Browser   │ ──────────────> │  FastAPI Server  │
│             │                 │                  │
│ HTMX + SSE  │ <────────────── │  SSE Endpoint    │
│ Extension   │  Event Stream   │  (/sse-stream)   │
│             │                 │                  │
│ Alpine.js   │                 │ Connection Mgr   │
│ (UI State)  │                 │ Data Generator   │
└─────────────┘                 └──────────────────┘
```

## Implementation Steps

### 1. Backend Setup (FastAPI)

#### Install Dependencies
```bash
pip install fastapi uvicorn pydantic
```

#### Data Model
```python
from pydantic import BaseModel
from datetime import datetime

class SensorReading(BaseModel):
    temperature: float  # Celsius
    humidity: float     # Percentage
    pressure: float     # hPa
    timestamp: datetime
    
    def to_html(self) -> str:
        """Convert to HTML for SSE transmission"""
        return f'''
        <div class="data-item animate-in slide-in-from-bottom-2 duration-300 mb-2 p-3 bg-white rounded-lg border border-gray-200">
            <div class="flex items-center justify-between">
                <div class="flex items-center space-x-4">
                    <div class="w-2 h-2 bg-blue-500 rounded-full"></div>
                    <div class="text-sm">
                        <span class="font-medium text-gray-900">SSE Data</span>
                        <span class="text-gray-500 ml-2">{self.timestamp.strftime('%H:%M:%S')}</span>
                    </div>
                </div>
                <div class="flex items-center space-x-4 text-sm">
                    <span class="text-blue-600">🌡️ {self.temperature}°C</span>
                    <span class="text-green-600">💧 {self.humidity}%</span>
                    <span class="text-purple-600">📊 {self.pressure} hPa</span>
                </div>
            </div>
        </div>
        '''
```

#### Connection Manager
```python
import asyncio
import uuid
import logging
from typing import AsyncGenerator, Dict, Set
from datetime import datetime

class SSEConnectionManager:
    def __init__(self):
        self.active_connections: Set[str] = set()
        self.connection_health: Dict[str, Dict] = {}
    
    def add_connection(self, connection_id: str):
        """Add a connection to the active set"""
        self.active_connections.add(connection_id)
        self.connection_health[connection_id] = {
            'start_time': datetime.now(),
            'last_ping': datetime.now(),
            'error_count': 0
        }
        logging.info(f"SSE connection added: {connection_id}")
    
    def remove_connection(self, connection_id: str):
        """Remove a connection from the active set"""
        self.active_connections.discard(connection_id)
        self.connection_health.pop(connection_id, None)
        logging.info(f"SSE connection removed: {connection_id}")
    
    async def generate_data_stream(self, connection_id: str = None) -> AsyncGenerator[str, None]:
        """Generate simulated sensor data stream with error handling"""
        consecutive_errors = 0
        max_consecutive_errors = 3
        
        try:
            while True:
                try:
                    # Generate simulated sensor data
                    sensor_data = SensorReading(
                        temperature=round(random.uniform(18.0, 28.0), 1),
                        humidity=round(random.uniform(30.0, 80.0), 1),
                        pressure=round(random.uniform(1000.0, 1020.0), 1),
                        timestamp=datetime.now()
                    )
                    
                    # Format as SSE event
                    html_data = sensor_data.to_html()
                    sse_event = f"event: message\ndata: {html_data}\n\n"
                    
                    consecutive_errors = 0  # Reset error counter on success
                    yield sse_event
                    
                    # Wait for random interval between 0.5 and 2 seconds
                    await asyncio.sleep(random.uniform(0.5, 2.0))
                    
                except Exception as data_error:
                    consecutive_errors += 1
                    logging.error(f"Error generating sensor data: {data_error}")
                    
                    if consecutive_errors >= max_consecutive_errors:
                        # Send error event to client
                        error_event = f"event: error\ndata: Data generation failed after {max_consecutive_errors} attempts\n\n"
                        yield error_event
                        break
                    
                    # Wait before retrying
                    await asyncio.sleep(1.0)
                
        except asyncio.CancelledError:
            logging.info("SSE data stream cancelled")
            raise
        except Exception as e:
            logging.error(f"Critical error in SSE data stream: {e}")
            # Send final error event
            error_event = f"event: error\ndata: Critical stream error: {str(e)}\n\n"
            yield error_event
```

#### FastAPI Routes
```python
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Add CORS middleware for cross-origin support
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

sse_manager = SSEConnectionManager()

@app.get("/sse-stream")
async def sse_stream():
    """SSE endpoint that streams sensor data with enhanced error handling"""
    connection_id = str(uuid.uuid4())
    
    async def event_stream():
        sse_manager.add_connection(connection_id)
        try:
            # Send initial connection confirmation
            yield "event: connected\ndata: Connection established\n\n"
            
            async for event in sse_manager.generate_data_stream(connection_id):
                yield event
        except asyncio.CancelledError:
            logging.info(f"SSE stream cancelled for connection: {connection_id}")
            # Send close event before terminating
            try:
                yield "event: close\ndata: Connection closed\n\n"
            except:
                pass  # Client may have already disconnected
        except Exception as e:
            logging.error(f"Error in SSE stream for connection {connection_id}: {e}")
            # Send error event to client
            try:
                yield f"event: error\ndata: Server error occurred: {str(e)}\n\n"
            except:
                pass  # Client may have already disconnected
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
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )

@app.get("/sse-health")
async def sse_health():
    """Health check endpoint for SSE connections"""
    return {
        "active_connections": len(sse_manager.active_connections),
        "connection_details": {
            conn_id: {
                "uptime_seconds": (datetime.now() - health['start_time']).total_seconds(),
                "last_ping_seconds_ago": (datetime.now() - health['last_ping']).total_seconds(),
                "error_count": health['error_count']
            }
            for conn_id, health in sse_manager.connection_health.items()
        }
    }
```

### 2. Frontend Setup (HTML + HTMX + Alpine.js)

#### HTML Structure
```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SSE Demo - Real-time Server-Sent Events</title>
    <script src="https://unpkg.com/htmx.org@1.9.10"></script>
    <script src="https://unpkg.com/htmx.org/dist/ext/sse.js"></script>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://unpkg.com/alpinejs@3.x.x/dist/cdn.min.js" defer></script>
</head>
<body class="bg-gray-50 min-h-screen" x-data="sseApp()">
    <!-- Your content here -->
</body>
</html>
```

#### HTMX SSE Integration
```html
<!-- Hidden SSE connector that controls the connection -->
<div x-show="connectionStatus === 'connected' || connectionStatus === 'connecting'"
     hx-ext="sse"
     sse-connect="/sse-stream"
     sse-swap="message"
     hx-target="#sse-feed"
     hx-swap="beforeend"
     style="position: absolute; visibility: hidden; height: 0; overflow: hidden;">
</div>

<!-- SSE Feed Container - Content is preserved here -->
<div class="h-96 overflow-y-auto p-4 bg-gray-50" 
     id="sse-feed"
     x-show="connectionStatus !== 'disconnected'">
    <!-- Data will be inserted here by HTMX SSE -->
</div>
```

#### Alpine.js State Management
```javascript
function sseApp() {
    return {
        connectionStatus: 'disconnected', // 'disconnected', 'connecting', 'connected', 'error'
        connectionStartTime: null,
        currentTime: Date.now(),
        errorMessage: '',
        networkStatus: 'online',
        reconnectAttempts: 0,
        maxReconnectAttempts: 5,
        reconnectDelay: 1000,
        stats: {
            totalEvents: 0,
            eventsPerMinute: 0,
            lastEventTime: '--:--'
        },
        
        get connectionStatusText() {
            switch (this.connectionStatus) {
                case 'connecting': return 'Connecting...';
                case 'connected': return 'Connected';
                case 'error': return 'Error';
                default: return 'Disconnected';
            }
        },
        
        get connectionTime() {
            if (!this.connectionStartTime || this.connectionStatus !== 'connected') {
                return '00:00';
            }
            
            const elapsed = Math.floor((this.currentTime - this.connectionStartTime) / 1000);
            const minutes = Math.floor(elapsed / 60);
            const seconds = elapsed % 60;
            return `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
        },
        
        init() {
            this.setupSSEListeners();
            this.setupNetworkMonitoring();
            
            // Update connection time every second
            setInterval(() => {
                this.currentTime = Date.now();
            }, 1000);
        },
        
        setupSSEListeners() {
            // Listen for HTMX SSE connection events
            document.body.addEventListener('htmx:sseOpen', (event) => {
                console.log('SSE connection opened via HTMX');
                this.connectionStatus = 'connected';
                this.errorMessage = '';
                this.reconnectAttempts = 0;
                this.reconnectDelay = 1000;
                if (!this.connectionStartTime) {
                    this.connectionStartTime = Date.now();
                }
            });
            
            document.body.addEventListener('htmx:sseError', (event) => {
                console.log('SSE connection error via HTMX:', event.detail);
                this.handleConnectionError('Failed to establish SSE connection. Please check your network connection and try again.');
            });
            
            document.body.addEventListener('htmx:sseClose', (event) => {
                console.log('SSE connection closed via HTMX');
                if (this.connectionStatus === 'connected') {
                    this.handleConnectionError('Connection was unexpectedly closed. The server may be unavailable.');
                } else {
                    this.connectionStatus = 'disconnected';
                    this.connectionStartTime = null;
                }
            });
            
            document.body.addEventListener('htmx:sseMessage', (event) => {
                console.log('SSE message received:', event.detail);
                
                const eventType = event.detail.type || 'message';
                
                switch (eventType) {
                    case 'connected':
                        this.connectionStatus = 'connected';
                        this.errorMessage = '';
                        break;
                        
                    case 'error':
                        this.handleConnectionError(`Server error: ${event.detail.data}`);
                        break;
                        
                    case 'close':
                        this.connectionStatus = 'disconnected';
                        this.connectionStartTime = null;
                        break;
                        
                    case 'message':
                    default:
                        this.updateStats();
                        if (this.connectionStatus === 'error') {
                            this.connectionStatus = 'connected';
                            this.errorMessage = '';
                        }
                        break;
                }
            });
            
            // Listen for DOM updates after SSE messages are swapped
            document.body.addEventListener('htmx:afterSwap', (event) => {
                if (event.target.id === 'sse-feed') {
                    this.limitFeedItems();
                    this.scrollToBottom();
                }
            });
        },
        
        setupNetworkMonitoring() {
            window.addEventListener('online', () => {
                this.networkStatus = 'online';
                if (this.connectionStatus === 'error' && this.errorMessage.includes('Network')) {
                    setTimeout(() => this.reconnect(), 1000);
                }
            });
            
            window.addEventListener('offline', () => {
                this.networkStatus = 'offline';
                if (this.connectionStatus === 'connected') {
                    this.handleConnectionError('Network connection lost. Will reconnect when network is restored.');
                }
            });
            
            this.networkStatus = navigator.onLine ? 'online' : 'offline';
        },
        
        handleConnectionError(message) {
            this.connectionStatus = 'error';
            this.errorMessage = message;
            this.connectionStartTime = null;
            
            // Auto-retry logic for certain errors
            if (this.reconnectAttempts < this.maxReconnectAttempts && 
                this.networkStatus === 'online' && 
                !message.includes('Server error')) {
                
                this.reconnectAttempts++;
                const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
                
                setTimeout(() => {
                    if (this.connectionStatus === 'error') {
                        this.reconnect();
                    }
                }, delay);
            }
        },
        
        startConnection() {
            this.connectionStatus = 'connecting';
            this.connectionStartTime = Date.now();
        },
        
        stopConnection() {
            this.connectionStatus = 'disconnected';
            this.connectionStartTime = null;
        },
        
        clearFeed() {
            const feedElement = document.getElementById('sse-feed');
            if (feedElement) {
                feedElement.innerHTML = '';
            }
            
            this.stats = {
                totalEvents: 0,
                eventsPerMinute: 0,
                lastEventTime: '--:--'
            };
        },
        
        updateStats() {
            this.stats.totalEvents++;
            this.stats.lastEventTime = new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
            
            if (this.connectionStartTime) {
                const elapsedMinutes = (Date.now() - this.connectionStartTime) / (1000 * 60);
                this.stats.eventsPerMinute = this.stats.totalEvents / elapsedMinutes;
            }
        },
        
        limitFeedItems() {
            const feedElement = document.getElementById('sse-feed');
            if (feedElement) {
                const items = feedElement.querySelectorAll('.data-item');
                const maxItems = 50;
                
                if (items.length > maxItems) {
                    const itemsToRemove = items.length - maxItems;
                    for (let i = 0; i < itemsToRemove; i++) {
                        items[i].remove();
                    }
                }
            }
        },
        
        scrollToBottom() {
            const feedElement = document.getElementById('sse-feed');
            if (feedElement) {
                feedElement.scrollTo({
                    top: feedElement.scrollHeight,
                    behavior: 'smooth'
                });
            }
        },
        
        reconnect() {
            this.errorMessage = '';
            this.startConnection();
        },
        
        dismissError() {
            this.connectionStatus = 'disconnected';
            this.errorMessage = '';
            this.reconnectAttempts = 0;
        }
    }
}
```

### 3. Key Implementation Details

#### SSE Event Format
SSE events must follow this format:
```
event: message
data: <your-data-here>

```
- Each field ends with `\n`
- Events are separated by an empty line (`\n\n`)
- `event:` field is optional (defaults to "message")
- `data:` field contains the actual data

#### HTMX SSE Attributes
- `hx-ext="sse"`: Enables SSE extension
- `sse-connect="/sse-stream"`: Establishes EventSource connection
- `sse-swap="message"`: Swaps incoming SSE messages into element
- `hx-target="#sse-feed"`: Target element for content insertion
- `hx-swap="beforeend"`: Append new content to end of target

#### Error Handling Strategies
1. **Connection Errors**: Automatic reconnection with exponential backoff
2. **Network Failures**: Monitor online/offline status
3. **Server Errors**: Display user-friendly error messages
4. **Data Validation**: Validate incoming data before processing

#### Performance Optimizations
1. **Feed Limiting**: Keep only last 50 items to prevent memory issues
2. **Efficient DOM Updates**: Use `beforeend` swap for better performance
3. **Connection Pooling**: Track and manage multiple connections
4. **Resource Cleanup**: Properly clean up connections on disconnect

### 4. Production Considerations

#### Security
```python
# Use specific origins in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["Cache-Control"],
)
```

#### Scaling
- Use Redis for connection state management across multiple servers
- Implement connection limits per client
- Add rate limiting to prevent abuse
- Monitor connection health and cleanup inactive connections

#### Monitoring
```python
@app.get("/sse-metrics")
async def sse_metrics():
    return {
        "active_connections": len(sse_manager.active_connections),
        "total_events_sent": sse_manager.total_events_sent,
        "average_connection_duration": sse_manager.avg_connection_duration,
        "error_rate": sse_manager.error_rate
    }
```

#### Deployment
- Use a reverse proxy (nginx) with proper SSE configuration
- Set appropriate timeouts for long-lived connections
- Configure load balancer for sticky sessions if needed
- Monitor server resources (memory, CPU, open file descriptors)

### 5. Testing

#### Unit Tests
```python
import pytest
from fastapi.testclient import TestClient

def test_sse_endpoint():
    client = TestClient(app)
    with client.stream("GET", "/sse-stream") as response:
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream"
        
        # Read first few events
        events = []
        for line in response.iter_lines():
            if line.startswith("data:"):
                events.append(line)
                if len(events) >= 3:
                    break
        
        assert len(events) >= 3
```

#### Integration Tests
```javascript
// Test HTMX SSE integration
describe('SSE Integration', () => {
    it('should connect and receive events', async () => {
        const mockEventSource = new MockEventSource('/sse-stream');
        
        // Simulate connection
        mockEventSource.onopen();
        expect(connectionStatus).toBe('connected');
        
        // Simulate message
        mockEventSource.onmessage({
            data: '<div class="data-item">Test data</div>'
        });
        
        expect(document.querySelector('.data-item')).toBeTruthy();
    });
});
```

### 6. Troubleshooting

#### Common Issues
1. **Connection not establishing**: Check CORS headers and network connectivity
2. **Events not appearing**: Verify SSE event format and HTMX target element
3. **Memory leaks**: Implement proper connection cleanup and feed limiting
4. **Reconnection failures**: Check error handling and retry logic

#### Debug Tools
```javascript
// Enable HTMX logging
htmx.logAll();

// Monitor SSE events
document.body.addEventListener('htmx:sseMessage', (event) => {
    console.log('SSE Event:', event.detail);
});
```

## Conclusion

This SSE implementation provides a robust, scalable solution for real-time data streaming with minimal complexity. The combination of FastAPI's async capabilities, HTMX's declarative approach, and Alpine.js's reactive state management creates a powerful yet maintainable real-time application.

The key advantages of this approach are:
- **Simplicity**: No complex WebSocket protocols or custom message handling
- **Reliability**: Built-in browser reconnection and error handling
- **Performance**: Efficient DOM updates and resource management
- **Maintainability**: Clear separation of concerns and minimal JavaScript

This implementation can be easily adapted for various use cases such as live dashboards, notification systems, log streaming, or any scenario requiring unidirectional real-time data flow.
