# Forest Rights Act (FRA) Decision Support System & WebGIS Platform

## Overview

This is a comprehensive AI-powered Decision Support System (DSS) and WebGIS platform designed to digitize, manage, and visualize Forest Rights Act (FRA) implementation across multiple Indian states including Madhya Pradesh, Tripura, Odisha, and Telangana.

## Key Features

### 🤖 AI-Powered Document Processing
- **Named Entity Recognition (NER)** for extracting structured data from legacy documents
- **OCR capabilities** for digitizing scanned FRA documentation
- **Document classification** and automated data validation

### 🛰️ Satellite Imagery Analysis
- **Computer Vision models** for high-resolution satellite imagery processing
- **Land-use classification** using supervised ML models (Random Forest, CNN)
- **Asset mapping** and change detection over time

### 🗺️ Interactive WebGIS Platform
- **Multi-layer mapping** with forest cover, agricultural land, water bodies, and infrastructure
- **Real-time visualization** of FRA claims and community assets
- **Spatial analysis** tools for decision-making support

### 📊 Decision Support System
- **Cross-referencing** FRA holders with Central Sector Schemes (CSS)
- **Intelligent recommendations** for targeted development interventions
- **Performance analytics** and reporting dashboards

### 👥 Multi-Role Access Control
- **Administrators**: Full system control and configuration
- **Government Officials**: Comprehensive data access and analysis
- **Field Workers**: Data entry and tracking capabilities
- **Tribal Communities**: Basic information retrieval and status checking

## Technical Architecture

### Backend Components
- **FastAPI** for high-performance REST APIs
- **PostgreSQL** with PostGIS for spatial data storage
- **SQLAlchemy** for database ORM
- **TensorFlow/PyTorch** for AI/ML models

### Frontend Components
- **React** with TypeScript for responsive web interface
- **Leaflet/Folium** for interactive mapping
- **Material-UI** for consistent user experience
- **Chart.js** for data visualization

### AI/ML Pipeline
- **spaCy & Transformers** for NLP and NER
- **OpenCV** for computer vision tasks
- **scikit-learn** for traditional ML algorithms
- **Custom CNN models** for satellite imagery analysis

## Installation & Setup

### Prerequisites
- Python 3.9+
- PostgreSQL 13+ with PostGIS extension
- Node.js 16+
- Docker (optional)

### Quick Start

1. **Clone and setup environment**:
```bash
git clone <repository-url>
cd fra-dss-platform
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. **Database setup**:
```bash
# Create PostgreSQL database with PostGIS
createdb fra_database
psql fra_database -c "CREATE EXTENSION postgis;"

# Run migrations
alembic upgrade head
```

3. **Install frontend dependencies**:
```bash
cd frontend
npm install
```

4. **Start the application**:
```bash
# Backend
uvicorn app.main:app --reload --port 8000

# Frontend (in another terminal)
cd frontend
npm start
```

## Project Structure

```
fra-dss-platform/
├── app/                          # Backend application
│   ├── ai_models/               # AI/ML model implementations
│   ├── api/                     # API endpoints
│   ├── core/                    # Core configuration and utilities
│   ├── database/                # Database models and connections
│   ├── services/                # Business logic services
│   └── main.py                  # FastAPI application entry point
├── frontend/                    # React frontend application
├── data/                        # Sample data and datasets
├── tests/                       # Test suites
├── docs/                        # Documentation
├── docker/                      # Docker configuration
└── scripts/                     # Utility scripts
```

## Data Sources & Integration

### Supported Data Types
- **Legacy Documents**: PDF, DOC, scanned images
- **Satellite Imagery**: Landsat, Sentinel, high-resolution commercial imagery
- **Government Databases**: FRA claims, scheme beneficiaries, village boundaries
- **Geospatial Data**: Forest cover maps, land use classifications, infrastructure layers

### API Integrations
- Government scheme databases
- Satellite imagery providers
- Census and demographic data
- Weather and climate data

## Security & Privacy

- **Role-based access control** (RBAC)
- **Data encryption** at rest and in transit
- **Audit logging** for all system operations
- **GDPR compliance** for personal data handling
- **Secure API authentication** using JWT tokens

## Performance Metrics

- **Document Digitization**: 95%+ accuracy target
- **Real-time Updates**: Sub-second response times
- **Scalability**: Support for 100,000+ concurrent users
- **Data Coverage**: Complete coverage of target states
- **Uptime**: 99.9% availability SLA

## Contributing

Please read our contributing guidelines and code of conduct before submitting pull requests.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For technical support and questions, please contact the development team or create an issue in the project repository.