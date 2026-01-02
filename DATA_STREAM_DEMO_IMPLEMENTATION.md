# Data Stream Demo Implementation Guide

A comprehensive guide to implementing real-time data streaming with interactive charts using WebSockets, HTMX, FastAPI, Chart.js, and Alpine.js. This approach provides bidirectional communication for data streaming control with rich data visualization.

## Overview

This implementation demonstrates real-time data streaming with interactive controls and live chart updates. Users can start/stop data streams, view real-time statistics, and see data visualized in charts. The demo features WebSocket-based data streaming, Chart.js integration, and comprehensive error handling.

### Key Benefits
- **Interactive Control**: Start/stop data streams on demand
- **Real-time Visualization**: Live charts that update with streaming data
- **Rich Statistics**: Real-time metrics and analytics
- **Bidirectional Communication**: Client can control server-side data generation
- **Performance Optimized**: Efficient chart updates and data management

### When to Use This Pattern
- **Use for**: Real-time dashboards, monitoring systems, live analytics, IoT data visualization
- **Ideal for**: Applications requiring user control over data streams with rich visualization

## Architecture

```
┌─────────────────┐    WebSocket     ┌──────────────────┐
│   Browser       │ ←──────────────→ │  FastAPI Server  │
│                 │   Commands       │                  │
│ HTMX + WS Ext   │ ←──────────────→ │  Data WebSocket  │
│ Chart.js        │   Data Stream    │  (/ws/data)      │
│ Alpine.js       │                  │                  │
│ (UI + Charts)   │                  │ Stream Manager   │
│                 │                  │ Data Generator   │
└─────────────────┘                  └──────────────────┘
```

## Implementation Steps

### 1. Backend Setup (FastAPI)

#### Install Dependencies
```bash
pip install fastapi uvicorn websockets
```

#### Data Stream Manager
```python
from fastapi import WebSocket, WebSocketDisconnect
import json
import asyncio
import random
import logging
from typing import List, Dict

class DataStreamManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.streaming_tasks: Dict[WebSocket, asyncio.Task] = {}

    async def connect(self, websocket: WebSocket):
        """Accept and store new WebSocket connection"""
        await websocket.accept()
        self.active_connections.append(websocket)
        logging.info(f"Data stream connection established. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection and cleanup streaming task"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        
        # Cancel streaming task if exists
        if websocket in self.streaming_tasks:
            self.streaming_tasks[websocket].cancel()
            del self.streaming_tasks[websocket]
            
        logging.info(f"Data stream connection closed. Total: {len(self.active_connections)}")

    async def start_streaming(self, websocket: WebSocket):
        """Start streaming data to specific WebSocket connection"""
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
                    
                    # Random interval between 0.5 and 2 seconds
                    await asyncio.sleep(random.uniform(0.5, 2.0))
                    
            except asyncio.CancelledError:
                logging.info("Data streaming task cancelled")
                pass
            except Exception as e:
                logging.error(f"Error in streaming task: {e}")
        
        # Create and store streaming task
        task = asyncio.create_task(stream_data())
        self.streaming_tasks[websocket] = task

    def stop_streaming(self, websocket: WebSocket):
        """Stop streaming data to specific WebSocket connection"""
        if websocket in self.streaming_tasks:
            self.streaming_tasks[websocket].cancel()
            del self.streaming_tasks[websocket]
            logging.info("Data streaming stopped for connection")

    def get_connection_count(self) -> int:
        """Get current number of active connections"""
        return len(self.active_connections)
    
    def get_streaming_count(self) -> int:
        """Get current number of active streaming connections"""
        return len(self.streaming_tasks)
```

#### FastAPI WebSocket Endpoint
```python
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import json
import logging

app = FastAPI()
data_manager = DataStreamManager()

@app.websocket("/ws/data")
async def data_websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for data streaming with command handling"""
    await data_manager.connect(websocket)
    try:
        while True:
            # Wait for command from client
            data = await websocket.receive_text()
            
            try:
                command = json.loads(data)
                action = command.get("action")
                
                if action == "start_stream":
                    await data_manager.start_streaming(websocket)
                    logging.info("Data streaming started for client")
                    
                elif action == "stop_stream":
                    data_manager.stop_streaming(websocket)
                    logging.info("Data streaming stopped for client")
                    
                else:
                    logging.warning(f"Unknown action received: {action}")
                    
            except json.JSONDecodeError as e:
                logging.error(f"JSON decode error in data endpoint: {e}")
                await websocket.send_text(json.dumps({
                    "error": "Invalid JSON format"
                }))
            
    except WebSocketDisconnect:
        data_manager.disconnect(websocket)
        logging.info("Data stream client disconnected normally")
    except Exception as e:
        logging.error(f"Data WebSocket error: {e}")
        data_manager.disconnect(websocket)

@app.get("/data-stream/stats")
async def data_stream_stats():
    """Get data streaming statistics"""
    return {
        "active_connections": data_manager.get_connection_count(),
        "streaming_connections": data_manager.get_streaming_count(),
        "status": "healthy"
    }
```

### 2. Frontend Setup (HTML + HTMX + Alpine.js + Chart.js)

#### HTML Structure
```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Data Stream - Real-time Analytics</title>
    <script src="https://unpkg.com/htmx.org@1.9.10"></script>
    <script src="https://unpkg.com/htmx.org/dist/ext/ws.js"></script>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://unpkg.com/alpinejs@3.x.x/dist/cdn.min.js" defer></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.5.1/dist/chart.umd.min.js"></script>
</head>
<body class="bg-gray-50 min-h-screen" x-data="dataStreamApp()">
    <!-- Your content here -->
</body>
</html>
```

#### Chart Integration (Global Scope)
```javascript
// Global chart variables - completely outside Alpine.js
let globalChart = null;
let globalChartLabels = [];
let globalChartTempData = [];
let globalChartHumidityData = [];

// Chart management functions
function initGlobalChart() {
    const canvas = document.getElementById('dataChart');
    if (!canvas) {
        return false;
    }
    
    try {
        // Destroy existing chart
        if (globalChart) {
            globalChart.destroy();
            globalChart = null;
        }
        
        // Reset data arrays
        globalChartLabels = [];
        globalChartTempData = [];
        globalChartHumidityData = [];
        
        const ctx = canvas.getContext('2d');
        
        globalChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: globalChartLabels,
                datasets: [{
                    label: 'Temperature (°C)',
                    data: globalChartTempData,
                    borderColor: '#3b82f6',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    fill: true,
                    tension: 0.4
                }, {
                    label: 'Humidity (%)',
                    data: globalChartHumidityData,
                    borderColor: '#10b981',
                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                    fill: false,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: 'index',
                    intersect: false,
                },
                scales: {
                    x: {
                        display: true,
                        grid: {
                            display: true
                        }
                    },
                    y: {
                        display: true,
                        grid: {
                            display: true
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: true,
                        position: 'top'
                    }
                },
                animation: {
                    duration: 0  // Disable animations for real-time updates
                }
            }
        });
        
        return true;
    } catch (error) {
        console.error('Error initializing chart:', error);
        return false;
    }
}

function updateGlobalChart(data, timestamp) {
    if (!globalChart) {
        return;
    }
    
    try {
        // Keep only last 20 data points for performance
        if (globalChartLabels.length >= 20) {
            globalChartLabels.shift();
            globalChartTempData.shift();
            globalChartHumidityData.shift();
        }
        
        // Add new data
        globalChartLabels.push(timestamp);
        globalChartTempData.push(data.temperature);
        globalChartHumidityData.push(data.humidity);
        
        // Update chart without animation
        globalChart.update('none');
    } catch (error) {
        console.error('Error updating chart:', error);
    }
}

function clearGlobalChart() {
    if (globalChart) {
        globalChartLabels.length = 0;
        globalChartTempData.length = 0;
        globalChartHumidityData.length = 0;
        globalChart.update('none');
    }
}
```

#### Alpine.js State Management
```javascript
function dataStreamApp() {
    return {
        socket: null,
        isConnected: false,
        isConnecting: false,
        isStreaming: false,
        dataPoints: [],
        chartInitialized: false,
        stats: {
            totalMessages: 0,
            avgValue: 0,
            maxValue: 0,
            messagesPerSecond: 0
        },
        startTime: null,
        
        get connectionStatus() {
            if (this.isConnecting) return 'Connecting...';
            return this.isConnected ? 'Connected' : 'Disconnected';
        },
        
        init() {
            // Initialize chart after a delay to ensure DOM is ready
            setTimeout(() => {
                const success = initGlobalChart();
                this.chartInitialized = success;
            }, 500);
            
            // Initialize WebSocket
            this.initWebSocket();
        },
        
        initWebSocket() {
            this.isConnecting = true;
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/ws/data`;
            
            this.socket = new WebSocket(wsUrl);
            
            this.socket.onopen = (event) => {
                console.log('Data WebSocket connected');
                this.isConnected = true;
                this.isConnecting = false;
            };
            
            this.socket.onclose = (event) => {
                console.log('Data WebSocket disconnected');
                this.isConnected = false;
                this.isConnecting = false;
                this.isStreaming = false;
                
                // Attempt to reconnect after 3 seconds
                setTimeout(() => this.initWebSocket(), 3000);
            };
            
            this.socket.onerror = (error) => {
                console.error('Data WebSocket error:', error);
                this.isConnecting = false;
            };
            
            this.socket.onmessage = (event) => {
                this.processDataPoint(event.data);
            };
        },
        
        toggleStream() {
            if (!this.socket || this.socket.readyState !== WebSocket.OPEN) return;
            
            this.isStreaming = !this.isStreaming;
            
            if (this.isStreaming) {
                this.startTime = Date.now();
                this.socket.send(JSON.stringify({ action: 'start_stream' }));
                console.log('Data streaming started');
            } else {
                this.socket.send(JSON.stringify({ action: 'stop_stream' }));
                console.log('Data streaming stopped');
            }
        },
        
        clearData() {
            this.dataPoints = [];
            this.stats = {
                totalMessages: 0,
                avgValue: 0,
                maxValue: 0,
                messagesPerSecond: 0
            };
            
            // Clear global chart
            clearGlobalChart();
            
            // Clear feed
            const dataFeed = document.getElementById('dataFeed');
            if (dataFeed) {
                const children = Array.from(dataFeed.children);
                children.forEach(child => {
                    if (child.classList.contains('data-item')) {
                        child.remove();
                    }
                });
            }
        },
        
        processDataPoint(rawData) {
            try {
                const data = JSON.parse(rawData);
                const timestamp = new Date().toLocaleTimeString();
                
                // Add to data points
                this.dataPoints.push(data);
                
                // Update chart
                this.updateChart(data, timestamp);
                
                // Update feed
                this.addToFeed(data, timestamp);
                
                // Update statistics
                this.updateStats(data);
                
            } catch (error) {
                console.error('Error processing data point:', error);
            }
        },
        
        updateChart(data, timestamp) {
            // Delegate to global function
            updateGlobalChart(data, timestamp);
        },
        
        addToFeed(data, timestamp) {
            const dataFeed = document.getElementById('dataFeed');
            
            const dataElement = document.createElement('div');
            dataElement.className = 'data-item animate-in slide-in-from-bottom-2 duration-300 mb-2 p-3 bg-white rounded-lg border border-gray-200';
            
            dataElement.innerHTML = `
                <div class="flex items-center justify-between">
                    <div class="flex items-center space-x-4">
                        <div class="w-2 h-2 bg-primary-500 rounded-full"></div>
                        <div class="text-sm">
                            <span class="font-medium text-gray-900">Sensor Data</span>
                            <span class="text-gray-500 ml-2">${timestamp}</span>
                        </div>
                    </div>
                    <div class="flex items-center space-x-4 text-sm">
                        <span class="text-blue-600">🌡️ ${data.temperature}°C</span>
                        <span class="text-green-600">💧 ${data.humidity}%</span>
                        <span class="text-purple-600">📊 ${data.pressure} hPa</span>
                    </div>
                </div>
            `;
            
            dataFeed.appendChild(dataElement);
            
            // Keep only last 50 items for performance
            const items = dataFeed.querySelectorAll('.data-item');
            if (items.length > 50) {
                items[0].remove();
            }
            
            dataFeed.scrollTop = dataFeed.scrollHeight;
        },
        
        updateStats(data) {
            this.stats.totalMessages++;
            
            // Calculate average temperature
            const temperatures = this.dataPoints.map(d => d.temperature);
            this.stats.avgValue = temperatures.reduce((a, b) => a + b, 0) / temperatures.length;
            
            // Find max temperature
            this.stats.maxValue = Math.max(...temperatures);
            
            // Calculate messages per second
            if (this.startTime) {
                const elapsed = (Date.now() - this.startTime) / 1000;
                this.stats.messagesPerSecond = this.stats.totalMessages / elapsed;
            }
        }
    }
}
```

### 3. Key Implementation Details

#### WebSocket Command Protocol
```json
// Start streaming command
{
    "action": "start_stream"
}

// Stop streaming command
{
    "action": "stop_stream"
}

// Data message format
{
    "temperature": 23.5,
    "humidity": 65.2,
    "pressure": 1013.2,
    "timestamp": 1640995200.123
}
```

#### Chart.js Integration Strategy
- **Global Scope**: Chart variables outside Alpine.js to avoid reactivity issues
- **Performance**: Disable animations for real-time updates
- **Data Management**: Keep only last 20 data points for smooth performance
- **Update Strategy**: Use `update('none')` for immediate chart updates

#### Performance Optimizations
1. **Chart Updates**: Disable animations and limit data points
2. **DOM Management**: Limit feed items to 50 for memory efficiency
3. **Data Processing**: Efficient statistics calculation
4. **Connection Management**: Proper cleanup of streaming tasks

### 4. Production Considerations

#### Resource Management
```python
class ResourceAwareStreamManager(DataStreamManager):
    def __init__(self, max_connections=100, max_streaming=50):
        super().__init__()
        self.max_connections = max_connections
        self.max_streaming = max_streaming
    
    async def connect(self, websocket: WebSocket):
        if len(self.active_connections) >= self.max_connections:
            await websocket.close(code=1008, reason="Connection limit reached")
            return False
        
        await super().connect(websocket)
        return True
    
    async def start_streaming(self, websocket: WebSocket):
        if len(self.streaming_tasks) >= self.max_streaming:
            await websocket.send_text(json.dumps({
                "error": "Streaming limit reached"
            }))
            return
        
        await super().start_streaming(websocket)
```

#### Monitoring and Metrics
```python
@app.get("/data-stream/metrics")
async def detailed_metrics():
    return {
        "connections": {
            "active": data_manager.get_connection_count(),
            "streaming": data_manager.get_streaming_count(),
            "max_connections": data_manager.max_connections,
            "max_streaming": data_manager.max_streaming
        },
        "performance": {
            "avg_message_rate": calculate_avg_message_rate(),
            "memory_usage": get_memory_usage(),
            "cpu_usage": get_cpu_usage()
        },
        "health": "healthy" if data_manager.get_connection_count() < data_manager.max_connections else "warning"
    }
```

### 5. Testing

#### Load Testing
```python
import asyncio
import websockets
import json
import time

async def test_client(uri, client_id):
    """Simulate a data streaming client"""
    try:
        async with websockets.connect(uri) as websocket:
            print(f"Client {client_id} connected")
            
            # Start streaming
            await websocket.send(json.dumps({"action": "start_stream"}))
            
            # Receive data for 30 seconds
            start_time = time.time()
            message_count = 0
            
            while time.time() - start_time < 30:
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    data = json.loads(message)
                    message_count += 1
                    
                    if message_count % 10 == 0:
                        print(f"Client {client_id}: Received {message_count} messages")
                        
                except asyncio.TimeoutError:
                    print(f"Client {client_id}: Timeout waiting for message")
                    break
            
            # Stop streaming
            await websocket.send(json.dumps({"action": "stop_stream"}))
            print(f"Client {client_id}: Total messages received: {message_count}")
            
    except Exception as e:
        print(f"Client {client_id} error: {e}")

async def run_load_test(num_clients=10):
    """Run load test with multiple clients"""
    uri = "ws://localhost:8000/ws/data"
    tasks = []
    
    for i in range(num_clients):
        task = asyncio.create_task(test_client(uri, i))
        tasks.append(task)
    
    await asyncio.gather(*tasks)

# Run the test
if __name__ == "__main__":
    asyncio.run(run_load_test(10))
```

### 6. Troubleshooting

#### Common Issues
1. **Chart not updating**: Check if Chart.js is loaded and canvas element exists
2. **Memory leaks**: Ensure proper cleanup of data arrays and DOM elements
3. **Performance degradation**: Limit data points and disable chart animations
4. **WebSocket connection issues**: Verify endpoint URL and connection handling

#### Debug Tools
```javascript
// Enable comprehensive logging
function enableDebugMode() {
    const originalLog = console.log;
    console.log = function(...args) {
        const timestamp = new Date().toISOString();
        originalLog(`[${timestamp}]`, ...args);
    };
    
    // Log WebSocket events
    const originalWebSocket = window.WebSocket;
    window.WebSocket = function(url, protocols) {
        console.log('WebSocket connecting to:', url);
        const ws = new originalWebSocket(url, protocols);
        
        ws.addEventListener('open', () => console.log('WebSocket opened'));
        ws.addEventListener('message', (event) => console.log('WebSocket message:', event.data));
        ws.addEventListener('close', () => console.log('WebSocket closed'));
        ws.addEventListener('error', (error) => console.error('WebSocket error:', error));
        
        return ws;
    };
    
    // Log chart updates
    const originalUpdate = updateGlobalChart;
    updateGlobalChart = function(data, timestamp) {
        console.log('Chart update:', { data, timestamp });
        return originalUpdate(data, timestamp);
    };
}
```

## Conclusion

This Data Stream implementation provides a comprehensive solution for real-time data visualization with interactive controls. The combination of WebSocket bidirectional communication, Chart.js visualization, and Alpine.js state management creates a powerful and responsive data streaming application.

Key advantages of this approach:
- **Interactive Control**: Users can start/stop data streams on demand
- **Rich Visualization**: Real-time charts with smooth updates
- **Performance Optimized**: Efficient data management and chart updates
- **Scalable Architecture**: Resource management and connection limits
- **Comprehensive Monitoring**: Statistics, metrics, and health checks

This implementation can be adapted for various use cases such as IoT dashboards, financial data streaming, system monitoring, or any application requiring real-time data visualization with user control.
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
                logging.error(f"Error in streaming task: {e}")
        
        task = asyncio.create_task(stream_data())
        self.streaming_tasks[websocket] = task

    def stop_streaming(self, websocket: WebSocket):
        if websocket in self.streaming_tasks:
            self.streaming_tasks[websocket].cancel()
            del self.streaming_tasks[websocket]

data_manager = DataStreamManager()
```

### 3. WebSocket Endpoint

```python
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
                logging.error(f"JSON decode error in data endpoint: {e}")
            
    except WebSocketDisconnect:
        data_manager.disconnect(websocket)
    except Exception as e:
        logging.error(f"Data WebSocket error: {e}")
        data_manager.disconnect(websocket)
```

### 4. HTML Route

```python
@app.get("/data-stream", response_class=HTMLResponse)
async def get_data_stream_page(request: Request):
    return templates.TemplateResponse("data_streaming_demo.html", {"request": request})
```

## Frontend Implementation

### 1. Required Libraries

```html
<script src="https://unpkg.com/htmx.org@1.9.10"></script>
<script src="https://unpkg.com/htmx.org/dist/ext/ws.js"></script>
<script src="https://cdn.tailwindcss.com"></script>
<script src="https://unpkg.com/alpinejs@3.x.x/dist/cdn.min.js" defer></script>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.5.1/dist/chart.umd.min.js"></script>
```

### 2. Global Chart Management

```javascript
// Global chart variables - outside Alpine.js for better performance
let globalChart = null;
let globalChartLabels = [];
let globalChartTempData = [];
let globalChartHumidityData = [];

function initGlobalChart() {
    const canvas = document.getElementById('dataChart');
    if (!canvas) return false;
    
    try {
        // Destroy existing chart
        if (globalChart) {
            globalChart.destroy();
            globalChart = null;
        }
        
        // Reset data arrays
        globalChartLabels = [];
        globalChartTempData = [];
        globalChartHumidityData = [];
        
        const ctx = canvas.getContext('2d');
        
        globalChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: globalChartLabels,
                datasets: [{
                    label: 'Temperature (°C)',
                    data: globalChartTempData,
                    borderColor: '#3b82f6',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    fill: true,
                    tension: 0.4
                }, {
                    label: 'Humidity (%)',
                    data: globalChartHumidityData,
                    borderColor: '#10b981',
                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                    fill: false,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: 'index',
                    intersect: false,
                },
                scales: {
                    x: { display: true, grid: { display: true } },
                    y: { display: true, grid: { display: true } }
                },
                plugins: {
                    legend: { display: true, position: 'top' }
                },
                animation: { duration: 0 } // Disable animations for real-time
            }
        });
        
        return true;
    } catch (error) {
        console.error('Error initializing chart:', error);
        return false;
    }
}

function updateGlobalChart(data, timestamp) {
    if (!globalChart) return;
    
    try {
        // Keep only last 20 data points for performance
        if (globalChartLabels.length >= 20) {
            globalChartLabels.shift();
            globalChartTempData.shift();
            globalChartHumidityData.shift();
        }
        
        // Add new data
        globalChartLabels.push(timestamp);
        globalChartTempData.push(data.temperature);
        globalChartHumidityData.push(data.humidity);
        
        // Update chart without animation
        globalChart.update('none');
    } catch (error) {
        console.error('Error updating chart:', error);
    }
}

function clearGlobalChart() {
    if (globalChart) {
        globalChartLabels.length = 0;
        globalChartTempData.length = 0;
        globalChartHumidityData.length = 0;
        globalChart.update('none');
    }
}
```

### 3. Alpine.js Application State

```javascript
function dataStreamApp() {
    return {
        socket: null,
        isConnected: false,
        isConnecting: false,
        isStreaming: false,
        dataPoints: [],
        chartInitialized: false,
        stats: {
            totalMessages: 0,
            avgValue: 0,
            maxValue: 0,
            messagesPerSecond: 0
        },
        startTime: null,
        
        get connectionStatus() {
            if (this.isConnecting) return 'Connecting...';
            return this.isConnected ? 'Connected' : 'Disconnected';
        },
        
        init() {
            // Initialize chart after a delay
            setTimeout(() => {
                const success = initGlobalChart();
                this.chartInitialized = success;
            }, 500);
            
            // Initialize WebSocket
            this.initWebSocket();
        },
        
        // ... other methods
    }
}
```

### 4. WebSocket Connection Management

```javascript
initWebSocket() {
    this.isConnecting = true;
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/data`;
    
    this.socket = new WebSocket(wsUrl);
    
    this.socket.onopen = (event) => {
        this.isConnected = true;
        this.isConnecting = false;
    };
    
    this.socket.onclose = (event) => {
        this.isConnected = false;
        this.isConnecting = false;
        this.isStreaming = false;
        
        // Attempt to reconnect after 3 seconds
        setTimeout(() => this.initWebSocket(), 3000);
    };
    
    this.socket.onerror = (error) => {
        this.isConnecting = false;
    };
    
    this.socket.onmessage = (event) => {
        this.processDataPoint(event.data);
    };
}
```

### 5. Streaming Control

```javascript
toggleStream() {
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) return;
    
    this.isStreaming = !this.isStreaming;
    
    if (this.isStreaming) {
        this.startTime = Date.now();
        this.socket.send(JSON.stringify({ action: 'start_stream' }));
    } else {
        this.socket.send(JSON.stringify({ action: 'stop_stream' }));
    }
}

clearData() {
    this.dataPoints = [];
    this.stats = {
        totalMessages: 0,
        avgValue: 0,
        maxValue: 0,
        messagesPerSecond: 0
    };
    
    // Clear global chart
    clearGlobalChart();
    
    // Clear feed
    const dataFeed = document.getElementById('dataFeed');
    if (dataFeed) {
        const children = Array.from(dataFeed.children);
        children.forEach(child => {
            if (child.classList.contains('data-item')) {
                child.remove();
            }
        });
    }
}
```

### 6. Data Processing and Visualization

```javascript
processDataPoint(rawData) {
    try {
        const data = JSON.parse(rawData);
        const timestamp = new Date().toLocaleTimeString();
        
        // Add to data points
        this.dataPoints.push(data);
        
        // Update chart
        this.updateChart(data, timestamp);
        
        // Update feed
        this.addToFeed(data, timestamp);
        
        // Update statistics
        this.updateStats(data);
        
    } catch (error) {
        console.error('Error processing data point:', error);
    }
}

updateChart(data, timestamp) {
    // Delegate to global function
    updateGlobalChart(data, timestamp);
}

addToFeed(data, timestamp) {
    const dataFeed = document.getElementById('dataFeed');
    
    const dataElement = document.createElement('div');
    dataElement.className = 'data-item animate-in slide-in-from-bottom-2 duration-300 mb-2 p-3 bg-white rounded-lg border border-gray-200';
    
    dataElement.innerHTML = `
        <div class="flex items-center justify-between">
            <div class="flex items-center space-x-4">
                <div class="w-2 h-2 bg-primary-500 rounded-full"></div>
                <div class="text-sm">
                    <span class="font-medium text-gray-900">Sensor Data</span>
                    <span class="text-gray-500 ml-2">${timestamp}</span>
                </div>
            </div>
            <div class="flex items-center space-x-4 text-sm">
                <span class="text-blue-600">🌡️ ${data.temperature}°C</span>
                <span class="text-green-600">💧 ${data.humidity}%</span>
                <span class="text-purple-600">📊 ${data.pressure} hPa</span>
            </div>
        </div>
    `;
    
    dataFeed.appendChild(dataElement);
    
    // Keep only last 50 items for performance
    const items = dataFeed.querySelectorAll('.data-item');
    if (items.length > 50) {
        items[0].remove();
    }
    
    dataFeed.scrollTop = dataFeed.scrollHeight;
}

updateStats(data) {
    this.stats.totalMessages++;
    
    // Calculate average temperature
    const temperatures = this.dataPoints.map(d => d.temperature);
    this.stats.avgValue = temperatures.reduce((a, b) => a + b, 0) / temperatures.length;
    
    // Find max temperature
    this.stats.maxValue = Math.max(...temperatures);
    
    // Calculate messages per second
    if (this.startTime) {
        const elapsed = (Date.now() - this.startTime) / 1000;
        this.stats.messagesPerSecond = this.stats.totalMessages / elapsed;
    }
}
```

### 7. HTML Structure

```html
<body class="bg-gray-50 min-h-screen" x-data="dataStreamApp()">
    <!-- Header with controls -->
    <header class="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div class="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
            <div class="flex items-center justify-between h-16">
                <div class="flex items-center space-x-3">
                    <div class="w-8 h-8 bg-primary-500 rounded-lg flex items-center justify-center">
                        <!-- Data stream icon -->
                    </div>
                    <h1 class="text-xl font-semibold text-gray-900">Data Stream</h1>
                </div>
                
                <!-- Connection Status and Controls -->
                <div class="flex items-center space-x-4">
                    <div class="flex items-center space-x-2" 
                         :class="isConnected ? 'text-green-600' : 'text-red-600'">
                        <div class="w-2 h-2 rounded-full" 
                             :class="isConnected ? 'bg-green-500' : 'bg-red-500'"
                             x-show="!isConnecting"
                             x-transition></div>
                        <span class="text-sm font-medium" x-text="connectionStatus"></span>
                    </div>
                    
                    <!-- Controls -->
                    <div class="flex items-center space-x-2">
                        <button @click="toggleStream()" 
                                :disabled="!isConnected"
                                class="px-3 py-1 text-sm rounded-lg transition-colors"
                                :class="isStreaming ? 'bg-red-100 text-red-700 hover:bg-red-200' : 'bg-green-100 text-green-700 hover:bg-green-200'"
                                x-text="isStreaming ? 'Stop' : 'Start'">
                        </button>
                        <button @click="clearData()" 
                                class="px-3 py-1 text-sm bg-gray-100 text-gray-700 hover:bg-gray-200 rounded-lg transition-colors">
                            Clear
                        </button>
                    </div>
                </div>
            </div>
        </div>
    </header>

    <!-- Main Content -->
    <main class="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <!-- Stats Cards -->
        <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
            <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
                <div class="flex items-center justify-between">
                    <div>
                        <p class="text-sm font-medium text-gray-600">Total Messages</p>
                        <p class="text-2xl font-bold text-gray-900" x-text="stats.totalMessages"></p>
                    </div>
                    <div class="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center">
                        <!-- Icon -->
                    </div>
                </div>
            </div>
            
            <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
                <div class="flex items-center justify-between">
                    <div>
                        <p class="text-sm font-medium text-gray-600">Avg Value</p>
                        <p class="text-2xl font-bold text-gray-900" x-text="stats.avgValue.toFixed(1)"></p>
                    </div>
                    <div class="w-8 h-8 bg-green-100 rounded-lg flex items-center justify-center">
                        <!-- Icon -->
                    </div>
                </div>
            </div>
            
            <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
                <div class="flex items-center justify-between">
                    <div>
                        <p class="text-sm font-medium text-gray-600">Max Value</p>
                        <p class="text-2xl font-bold text-gray-900" x-text="stats.maxValue"></p>
                    </div>
                    <div class="w-8 h-8 bg-purple-100 rounded-lg flex items-center justify-center">
                        <!-- Icon -->
                    </div>
                </div>
            </div>
            
            <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
                <div class="flex items-center justify-between">
                    <div>
                        <p class="text-sm font-medium text-gray-600">Messages/sec</p>
                        <p class="text-2xl font-bold text-gray-900" x-text="stats.messagesPerSecond.toFixed(1)"></p>
                    </div>
                    <div class="w-8 h-8 bg-orange-100 rounded-lg flex items-center justify-center">
                        <!-- Icon -->
                    </div>
                </div>
            </div>
        </div>

        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <!-- Chart -->
            <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                <div class="flex items-center justify-between mb-4">
                    <h2 class="text-lg font-semibold text-gray-900">Real-time Data</h2>
                    <div class="flex items-center space-x-2 text-sm text-gray-500">
                        <div class="w-2 h-2 bg-primary-500 rounded-full" x-show="isStreaming" x-transition></div>
                        <span x-text="isStreaming ? 'Live' : 'Paused'"></span>
                    </div>
                </div>
                <div class="h-64 relative bg-white border rounded-lg">
                    <canvas id="dataChart" width="400" height="200" style="display: block; width: 100%; height: 100%;"></canvas>
                    <div x-show="!chartInitialized" class="absolute inset-0 flex items-center justify-center bg-gray-50 rounded">
                        <div class="text-center">
                            <div class="w-8 h-8 bg-gray-200 rounded-full animate-pulse mx-auto mb-2"></div>
                            <p class="text-sm text-gray-500">Initializing chart...</p>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Live Data Feed -->
            <div class="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
                <div class="p-4 border-b border-gray-200">
                    <h2 class="text-lg font-semibold text-gray-900">Live Data Feed</h2>
                </div>
                <div class="h-80 overflow-y-auto p-4 bg-gray-50" id="dataFeed">
                    <!-- Data items will be inserted here -->
                </div>
            </div>
        </div>
    </main>
</body>
```

## Key Features

### 1. Controlled Streaming
- Start/stop streaming on demand
- Maintains connection while pausing data flow
- Clean state management for streaming status

### 2. Real-time Chart Integration
- Chart.js with live data updates
- Performance optimized (no animations, limited data points)
- Multiple data series (temperature, humidity)
- Responsive chart sizing

### 3. Live Statistics
- Real-time calculation of averages, maximums
- Messages per second tracking
- Connection time monitoring
- Automatic stat updates

### 4. Performance Optimization
- Limited data retention (20 chart points, 50 feed items)
- Global chart management outside Alpine.js
- Efficient DOM updates
- Memory leak prevention

## Customization Options

### 1. Data Generation
```python
# Custom sensor data generation
data = {
    "temperature": round(random.uniform(18.0, 28.0), 1),
    "humidity": round(random.uniform(30.0, 80.0), 1),
    "pressure": round(random.uniform(1000.0, 1020.0), 1),
    "timestamp": asyncio.get_event_loop().time(),
    # Add custom fields
    "custom_field": random.randint(0, 100)
}
```

### 2. Chart Configuration
```javascript
// Customize chart appearance
globalChart = new Chart(ctx, {
    type: 'line', // or 'bar', 'scatter', etc.
    data: {
        datasets: [{
            label: 'Temperature (°C)',
            borderColor: '#3b82f6',
            backgroundColor: 'rgba(59, 130, 246, 0.1)',
            fill: true,
            tension: 0.4,
            pointRadius: 2, // Customize point size
            pointHoverRadius: 4
        }]
    },
    options: {
        // Custom options
        scales: {
            y: {
                beginAtZero: false,
                min: 15,
                max: 35
            }
        }
    }
});
```

### 3. Statistics Calculation
```javascript
// Add custom statistics
updateStats(data) {
    this.stats.totalMessages++;
    
    // Custom calculations
    const values = this.dataPoints.map(d => d.temperature);
    this.stats.avgValue = values.reduce((a, b) => a + b, 0) / values.length;
    this.stats.maxValue = Math.max(...values);
    this.stats.minValue = Math.min(...values);
    this.stats.standardDeviation = this.calculateStdDev(values);
    
    // Rate calculations
    if (this.startTime) {
        const elapsed = (Date.now() - this.startTime) / 1000;
        this.stats.messagesPerSecond = this.stats.totalMessages / elapsed;
    }
}
```

## Deployment Considerations

### 1. WebSocket Configuration
```python
# Production WebSocket settings
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        ws_ping_interval=20,
        ws_ping_timeout=20,
        ws_max_size=16777216
    )
```

### 2. Resource Management
- Implement connection limits
- Add memory usage monitoring
- Clean up streaming tasks properly
- Handle client disconnections gracefully

### 3. Data Persistence
```python
# Optional: Save streaming data
import sqlite3
from datetime import datetime

class DataLogger:
    def __init__(self, db_path="stream_data.db"):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS sensor_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                temperature REAL,
                humidity REAL,
                pressure REAL
            )
        ''')
        conn.commit()
        conn.close()
    
    def log_data(self, data):
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT INTO sensor_data (temperature, humidity, pressure) VALUES (?, ?, ?)",
            (data["temperature"], data["humidity"], data["pressure"])
        )
        conn.commit()
        conn.close()
```

## Testing

### 1. Performance Testing
- Test with high-frequency data streams
- Monitor memory usage over time
- Verify chart performance with many data points
- Test connection recovery under load

### 2. UI Testing
- Test responsive design on different screen sizes
- Verify chart resizing works correctly
- Test start/stop/clear functionality
- Validate statistics calculations

### 3. Network Testing
- Test with unstable network connections
- Verify reconnection logic
- Test data integrity during reconnections
- Monitor WebSocket connection health

This implementation provides a robust foundation for real-time data streaming applications with live visualization, featuring controlled streaming, real-time charts, and comprehensive statistics tracking.