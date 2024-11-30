# Compilation Service

A high-performance, scalable REST API service for compiling LaTeX documents to PDF.

## Features

- Fast LaTeX compilation with parallel processing
- Redis caching for improved performance
- Rate limiting and request throttling
- Automatic PDF file cleanup
- Comprehensive logging and monitoring
- Docker support for easy deployment
- Clean architecture with separation of concerns

## Requirements

- Python 3.11+
- Redis
- TeXLive distribution
- Docker (optional)

## Installation

### Local Development

1. Clone the repository:
```bash
git clone https://github.com/yourusername/latex-service.git
cd latex-service
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Copy .env.example to .env and adjust settings:
```bash
cp .env.example .env
```

5. Start Redis:
```bash
docker-compose up redis -d
```

6. Run the application:
```bash
uvicorn app.main:app --reload
```

### Docker Deployment

1. Build and start all services:
```bash
docker-compose up --build
```

## API Documentation

Once the service is running, access the API documentation at:
- Swagger UI: http://localhost:8000/api/docs
- ReDoc: http://localhost:8000/api/redoc

## Usage Example

```python
import requests

url = "http://localhost:8000/api/v1/compile"
latex_content = r"""
\documentclass{article}
\begin{document}
Hello, World!
\end{document}
"""

response = requests.post(url, json={"content": latex_content})
print(response.json())
```

## Project Structure

```
latex_service/
├── README.md
├── requirements.txt
├── docker-compose.yml
├── Dockerfile
├── .env
└── app/
    ├── main.py
    ├── config.py
    ├── core/
    ├── api/
    ├── models/
    ├── services/
    └── utils/
```

## Configuration

The service can be configured using environment variables or .env file. See `.env.example` for available options.

## Monitoring

The service exposes Prometheus metrics at `/metrics` endpoint and includes:
- Request latency
- Error rates
- Compilation success/failure rates
- Worker pool status

## Testing

Run the test suite:
```bash
pytest
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
```
