# RSS Hub - Complete RSS to Telegram Platform

A modern, full-featured RSS feed aggregator that automatically posts new entries to Telegram channels. Includes a beautiful web dashboard, REST API, and robust background processing.

## 🚀 Features

### Core Functionality
- **Automatic RSS Monitoring** - Scheduled checking of multiple RSS feeds
- **Telegram Integration** - Auto-post new entries to channels/groups
- **Web Dashboard** - Modern Vue.js interface for management
- **REST API** - Full-featured API for automation and integration

### Security
- **SSRF Protection** - Validates URLs and blocks internal IP addresses
- **XSS Prevention** - HTML sanitization with allowlist approach
- **Secure Configuration** - Environment-based secrets management
- **Non-root Docker** - Runs as unprivileged user

### Performance
- **Async Processing** - Non-blocking RSS parsing and API calls
- **Connection Pooling** - Efficient SQLite database connections
- **Concurrent Feed Checking** - Parallel processing of multiple feeds
- **Smart Caching** - SHA-256 hashing to prevent duplicates

### Reliability
- **Retry Logic** - Exponential backoff for failed requests
- **Graceful Shutdown** - Proper cleanup on termination
- **Health Checks** - Built-in monitoring endpoints
- **Error Logging** - Comprehensive logging system

## 📁 Project Structure

```
rss-hub/
├── backend/
│   ├── app/
│   │   ├── api/          # REST API routes
│   │   ├── core/         # Configuration & settings
│   │   ├── db/           # Database layer
│   │   ├── services/     # Business logic
│   │   ├── tasks/        # Background jobs
│   │   ├── main.py       # Application entry point
│   │   └── server.py     # FastAPI server
│   ├── tests/            # Test suite
│   └── requirements.txt  # Python dependencies
├── frontend/
│   └── index.html        # Vue.js dashboard (single file)
├── docker/
│   └── Dockerfile        # Production Docker image
├── docker-compose.yml    # Container orchestration
├── .env.example          # Environment template
└── README.md             # This file
```

## 🛠️ Quick Start

### Prerequisites
- Docker & Docker Compose (recommended)
- OR Python 3.11+

### Option 1: Docker (Recommended)

1. **Clone and configure:**
```bash
git clone <repository>
cd rss-hub
cp .env.example .env
```

2. **Edit `.env` with your settings:**
```env
BOT_TOKEN=your_telegram_bot_token
ADMIN_IDS=123456789,987654321
CHANNEL_ID=-1001234567890
```

3. **Start the service:**
```bash
docker-compose up -d --build
```

4. **Access the dashboard:**
- Web UI: http://localhost:8000
- API Docs: http://localhost:8000/docs

### Option 2: Local Development

1. **Install dependencies:**
```bash
cd rss-hub/backend
pip install -r requirements.txt
```

2. **Set environment variables:**
```bash
export BOT_TOKEN="your_token"
export ADMIN_IDS="123456789"
export CHANNEL_ID="-1001234567890"
```

3. **Run the application:**
```bash
python -m uvicorn backend.app.server:app --reload
```

## 📱 Telegram Bot Commands

| Command | Description |
|---------|-------------|
| `/start` | Welcome message and quick help |
| `/help` | Detailed command reference |
| `/feeds` | List all configured RSS feeds |
| `/add <url> [title]` | Add new RSS feed |
| `/remove <id>` | Remove feed by ID |
| `/stats` | View statistics |

## 🔌 API Endpoints

### Feeds Management
- `GET /api/feeds` - List all feeds
- `GET /api/feeds/{id}` - Get specific feed
- `POST /api/feeds` - Add new feed
- `DELETE /api/feeds/{id}` - Remove feed
- `POST /api/feeds/{id}/check` - Trigger immediate check

### Statistics & Monitoring
- `GET /api/stats` - Get statistics
- `GET /health` - Health check endpoint
- `GET /api/scheduler/status` - Scheduler status
- `POST /api/scheduler/start` - Start scheduler
- `POST /api/scheduler/stop` - Stop scheduler

## ⚙️ Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `BOT_TOKEN` | Telegram bot token (required) | - |
| `ADMIN_IDS` | Comma-separated admin user IDs (required) | - |
| `CHANNEL_ID` | Target channel/group ID | - |
| `CHECK_INTERVAL` | Feed check interval (seconds) | 300 |
| `DATABASE_PATH` | SQLite database location | data/rss_hub.db |
| `WEB_HOST` | Web server host | 0.0.0.0 |
| `WEB_PORT` | Web server port | 8000 |
| `LOG_LEVEL` | Logging level | INFO |
| `RSS_TIMEOUT` | RSS fetch timeout (seconds) | 10 |

## 🎨 Web Dashboard Features

- **Real-time Statistics** - Live feed and post counts
- **Feed Management** - Add, remove, and monitor feeds
- **Activity Chart** - Visual representation of posting activity
- **System Status** - Health monitoring indicators
- **Manual Triggers** - On-demand feed checking
- **Responsive Design** - Works on desktop and mobile

## 🔒 Security Features

1. **SSRF Protection**: All URLs are validated to prevent access to internal networks
2. **Input Sanitization**: HTML content is cleaned using allowlist approach
3. **Token Validation**: Bot tokens are validated on startup
4. **Admin Verification**: All bot commands verify user permissions
5. **SQL Injection Prevention**: Parameterized queries throughout

## 🧪 Testing

```bash
# Run tests
pytest backend/tests/

# Run with coverage
pytest --cov=backend/app backend/tests/
```

## 📊 Monitoring

### Health Check
```bash
curl http://localhost:8000/health
```

Response:
```json
{
  "status": "healthy",
  "database": "ok",
  "scheduler": "running"
}
```

### Logs
```bash
# Docker logs
docker-compose logs -f rss-hub

# Log files
tail -f logs/app.log
```

## 🚀 Advanced Usage

### Multiple Instances
Run multiple instances with different configurations for load balancing:

```yaml
# docker-compose.override.yml
services:
  rss-hub-1:
    extends: rss-hub
    environment:
      - DATABASE_PATH=/app/data/rss_hub_1.db
  
  rss-hub-2:
    extends: rss-hub
    environment:
      - DATABASE_PATH=/app/data/rss_hub_2.db
```

### Custom Scheduling
Modify check intervals per feed via API or database.

### Webhook Mode
Configure Telegram bot for webhook instead of polling (for production deployments).

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📝 License

MIT License - See LICENSE file for details.

## 🆘 Support

- Open an issue for bugs and feature requests
- Check existing issues before creating new ones
- Include logs and configuration when reporting issues

---

Built with ❤️ using FastAPI, Vue.js, and Python
