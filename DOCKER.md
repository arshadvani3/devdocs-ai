# Docker Deployment Guide

Complete Docker containerization for DevDocs AI with production and development configurations.

## Quick Start

### Production Deployment

```bash
# Start all services
docker-compose up -d

# Pull Ollama model (first time only)
docker exec -it devdocs-ollama ollama pull llama3.2:3b

# View logs
docker-compose logs -f

# Access the application
# Frontend: http://localhost
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

### Development Mode

```bash
# Start with hot-reload
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

# Frontend will be available at http://localhost:5173
```

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  Docker Network                          │
│                                                           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────┐│
│  │ Frontend │  │ Backend  │  │  Ollama  │  │  Redis  ││
│  │ (Nginx)  │─→│ FastAPI  │─→│   LLM    │  │  Cache  ││
│  │  :80     │  │  :8000   │  │  :11434  │  │  :6379  ││
│  └──────────┘  └──────────┘  └──────────┘  └─────────┘│
│       │             │              │             │      │
│       └─────────────┴──────────────┴─────────────┘      │
└─────────────────────────────────────────────────────────┘
         │             │              │             │
    ┌────────┐   ┌─────────┐   ┌──────────┐  ┌──────────┐
    │ Static │   │ ChromaDB│   │  Ollama  │  │  Redis   │
    │ Assets │   │  Data   │   │  Models  │  │   Data   │
    └────────┘   └─────────┘   └──────────┘  └──────────┘
```

## Services

### 1. Frontend (Nginx + React)
- **Image**: Multi-stage build (Node.js → Nginx)
- **Port**: 80
- **Features**:
  - Production-optimized React build
  - Gzip compression
  - Static asset caching
  - API proxy to backend
  - WebSocket support
  - Security headers

### 2. Backend (FastAPI)
- **Image**: Python 3.11 slim
- **Port**: 8000
- **Features**:
  - Non-root user execution
  - Health checks
  - Persistent ChromaDB volume
  - Auto-reload in dev mode

### 3. Ollama (LLM)
- **Image**: Official Ollama
- **Port**: 11434
- **Features**:
  - Model persistence
  - 8GB memory limit
  - Health monitoring
  - GPU support (optional)

### 4. Redis (Cache)
- **Image**: Redis 7 Alpine
- **Port**: 6379
- **Features**:
  - AOF persistence
  - Health checks
  - Data volume

## Commands

### Service Management

```bash
# Start all services
docker-compose up -d

# Start specific service
docker-compose up -d backend

# Stop all services
docker-compose down

# Stop and remove volumes (CAUTION: deletes data)
docker-compose down -v

# Restart service
docker-compose restart backend

# View service status
docker-compose ps

# View resource usage
docker stats
```

### Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend

# Last 100 lines
docker-compose logs --tail=100 backend

# Since timestamp
docker-compose logs --since 2024-01-01T10:00:00
```

### Exec into Containers

```bash
# Backend shell
docker exec -it devdocs-backend sh

# Check backend health
docker exec devdocs-backend curl http://localhost:8000/api/v1/health

# Ollama shell
docker exec -it devdocs-ollama sh

# List Ollama models
docker exec devdocs-ollama ollama list

# Redis CLI
docker exec -it devdocs-redis redis-cli
```

### Building Images

```bash
# Build all images
docker-compose build

# Build with no cache
docker-compose build --no-cache

# Build specific service
docker-compose build backend

# Pull latest base images
docker-compose pull
```

## Environment Variables

### Backend (.env)

```bash
# LLM Configuration
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_MODEL=llama3.2:3b
OLLAMA_TIMEOUT=300

# Cache Configuration
REDIS_URL=redis://redis:6379/0
ENABLE_CACHING=true
CACHE_TTL_EMBEDDINGS=86400
CACHE_TTL_RESPONSES=3600

# Database
CHROMA_PERSIST_DIRECTORY=/app/chroma_db

# Performance
MAX_CHUNK_SIZE=500
RETRIEVAL_TOP_K=5
MAX_CONTEXT_CHARS=2000

# Logging
LOG_LEVEL=INFO
DEBUG=false
```

### Frontend (.env)

```bash
VITE_API_BASE_URL=http://localhost:8000/api/v1
VITE_WS_URL=ws://localhost:8000/api/v1/stream
```

## Production Optimizations

### Security
- ✅ Non-root user in all containers
- ✅ Read-only application code mounts
- ✅ Security headers in Nginx
- ✅ Network isolation
- ✅ Minimal base images (Alpine/Slim)

### Performance
- ✅ Multi-stage builds (smaller images)
- ✅ Layer caching optimization
- ✅ Gzip compression
- ✅ Static asset caching
- ✅ Health checks with retries
- ✅ Resource limits (Ollama: 8GB)

### Reliability
- ✅ Automatic restarts (`unless-stopped`)
- ✅ Health checks for all services
- ✅ Dependency ordering (`depends_on`)
- ✅ Volume persistence
- ✅ Graceful shutdown

## Volumes

```bash
# List volumes
docker volume ls

# Inspect volume
docker volume inspect devdocs-ai_chroma_data

# Backup ChromaDB
docker run --rm -v devdocs-ai_chroma_data:/data -v $(pwd):/backup \
  alpine tar czf /backup/chroma_backup.tar.gz -C /data .

# Restore ChromaDB
docker run --rm -v devdocs-ai_chroma_data:/data -v $(pwd):/backup \
  alpine tar xzf /backup/chroma_backup.tar.gz -C /data

# Remove unused volumes
docker volume prune
```

## Networking

```bash
# Inspect network
docker network inspect devdocs-ai_devdocs-network

# Test connectivity
docker exec devdocs-backend ping -c 3 redis
docker exec devdocs-backend curl http://ollama:11434/api/tags
```

## Troubleshooting

### Ollama Model Not Found

```bash
# Pull the model
docker exec -it devdocs-ollama ollama pull llama3.2:3b

# Verify installation
docker exec devdocs-ollama ollama list

# Check logs
docker-compose logs ollama
```

### Backend Can't Connect to Services

```bash
# Check service health
docker-compose ps

# Test Redis connection
docker exec devdocs-backend sh -c "curl -f redis:6379 || echo 'Redis unreachable'"

# Test Ollama connection
docker exec devdocs-backend curl http://ollama:11434/api/tags

# Restart services in order
docker-compose restart redis ollama backend frontend
```

### Permission Errors

```bash
# Fix volume permissions
docker-compose down
docker volume rm devdocs-ai_chroma_data
docker-compose up -d
```

### Out of Memory

```bash
# Increase Ollama memory limit in docker-compose.yml
services:
  ollama:
    deploy:
      resources:
        limits:
          memory: 12G  # Increase if needed
```

### Build Failures

```bash
# Clear build cache
docker builder prune

# Rebuild from scratch
docker-compose build --no-cache
```

## GPU Support (Optional)

For GPU-accelerated LLM inference:

```yaml
# Add to ollama service in docker-compose.yml
services:
  ollama:
    runtime: nvidia
    environment:
      - NVIDIA_VISIBLE_DEVICES=all
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

Requires: NVIDIA Docker runtime installed

## Monitoring

### Health Checks

```bash
# Check all services
curl http://localhost:8000/api/v1/health

# Expected response:
{
  "status": "healthy",
  "services": {
    "ollama": true,
    "chromadb": true,
    "embeddings": true,
    "cache": true
  }
}
```

### Metrics

```bash
# Prometheus metrics
curl http://localhost:8000/api/v1/metrics

# Collection statistics
curl http://localhost:8000/api/v1/stats
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Build and Push Docker Images

on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Build images
        run: docker-compose build

      - name: Run tests
        run: |
          docker-compose up -d
          docker exec devdocs-backend pytest
          docker-compose down
```

## Best Practices

1. **Always use specific image tags** (not `latest`)
2. **Set resource limits** for memory-intensive services
3. **Enable health checks** for all services
4. **Use volumes** for persistent data
5. **Implement graceful shutdown** in applications
6. **Monitor resource usage** with `docker stats`
7. **Regular backups** of ChromaDB and Redis data
8. **Keep images updated** for security patches

## Production Checklist

- [ ] Environment variables configured
- [ ] Ollama model pulled (llama3.2:3b)
- [ ] Health checks passing
- [ ] Volumes persisted
- [ ] Resource limits set
- [ ] Logs configured
- [ ] Backups scheduled
- [ ] Monitoring enabled
- [ ] SSL/TLS configured (if public)
- [ ] Firewall rules updated

---

## License

MIT
