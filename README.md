# Library Management System - Backend API

Complete, high-performance backend API for the **Library Management System** built with **Python 3.11+**, **FastAPI**, **MongoDB Atlas (Async Motor / PyMongo)**, **Pydantic v2**, and **JWT Authentication**.

---

## 📁 Project Architecture

```
backend/
│
├── app/
│   ├── main.py                  # FastAPI entrypoint, CORS, lifespan startup/shutdown
│   ├── config.py                # Environment configuration using Pydantic Settings
│   ├── database.py              # Motor AsyncIOMotorClient connection & index creation
│   │
│   ├── models/                  # Domain Models
│   │   ├── admin.py
│   │   ├── book.py
│   │   ├── member.py
│   │   ├── subscription.py
│   │   └── order.py
│   │
│   ├── schemas/                 # Request / Response Schemas
│   │   ├── auth.py
│   │   ├── book.py
│   │   ├── member.py
│   │   ├── subscription.py
│   │   └── order.py
│   │
│   ├── routers/                 # API Routes
│   │   ├── auth.py              # Admin authentication & login
│   │   ├── books.py             # Admin book CRUD & CSV import
│   │   ├── members.py           # Admin member CRUD & history
│   │   ├── subscriptions.py     # Admin membership plan management (3 types)
│   │   ├── orders.py            # Lending orders, returns & email reminders
│   │   ├── reports.py           # Revenue collection reports & dashboard metrics
│   │   └── public_books.py      # Public catalog (published books only)
│   │
│   ├── services/                # Core Business Logic
│   │   ├── book_service.py      # Book lookup, ID generation (LIB-XXXXX), history
│   │   ├── member_service.py    # Member lookup, ID generation (MEM-XXXXX), history
│   │   ├── subscription_service.py # Membership plans (SUB-XXXXX)
│   │   ├── order_service.py     # Order creation (ORD-XXXXX), price snapshotting & returns
│   │   ├── email_service.py     # SMTP reminder sender abstraction
│   │   ├── report_service.py    # Daily/monthly collection & dashboard analytics
│   │   └── csv_import_service.py# UTF-8 CSV parser & validator (Tamil Unicode support)
│   │
│   ├── auth/                    # Security & Auth Dependencies
│   │   ├── security.py          # Password hashing (bcrypt) & JWT creation/decoding
│   │   └── dependencies.py      # OAuth2 HTTP Bearer dependency
│   │
│   └── utils/                   # Helpers
│       └── helpers.py           # Atomic sequential ID generator & date helpers
│
├── tests/                       # Automated Pytest Suite
│   ├── conftest.py              # Test database fixtures
│   ├── test_books.py            # Book CRUD, unique IDs, Tamil text & CSV import
│   ├── test_members.py          # Subscriptions & member linking
│   ├── test_orders.py           # Order creation, price snapshot immutability & returns
│   └── test_public.py           # Public API filtering isolation
│
├── seed.py                      # Standalone script to seed sample data (books, members, orders)
├── .env                         # Environment credentials (DO NOT COMMIT)
├── .env.example                 # Environment template
├── .gitignore                   # Git ignore settings
├── requirements.txt             # Python dependencies
└── README.md                    # Project documentation
```

---

## ⚡ Quick Setup Instructions

### 1. Prerequisites
- Python 3.11 or higher
- MongoDB Atlas cluster or local MongoDB instance (`mongodb://localhost:27017`)

### 2. Environment Setup
Clone or navigate to the backend directory:
```bash
cd backend
```

Create a virtual environment and activate it:
```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# Linux / MacOS
python3 -m venv .venv
source .venv/bin/activate
```

Install requirements:
```bash
pip install -r requirements.txt
```

### 3. Environment Variables Configuration
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

Ensure your `.env` contains:
```env
MONGODB_URI=mongodb+srv://librarymanagement689_db_user:LibDev_2026!ChangeMe@cluster0.mongodb.net/library_management?retryWrites=true&w=majority
MONGODB_DATABASE=library_management

JWT_SECRET=lib_management_jwt_secret_key_2026_dev_98234710293847
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

ADMIN_EMAIL=admin@library.com
ADMIN_INITIAL_PASSWORD=Admin123!Secure

SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=admin@library.com
SMTP_PASSWORD=dev_smtp_password
EMAIL_FROM=noreply@library.com

REMINDER_DAYS_BEFORE_DUE=2
CORS_ORIGINS=http://localhost:4200,http://localhost:3000,http://127.0.0.1:4200
```

---

## 🔑 Default Admin & Seed Data Generation

To populate default admin account (`admin@library.com` / `Admin123!Secure`), 20 sample books (10 Tamil + 10 English), 5 members, 3 subscription plans, and 5 lending orders:

```bash
python seed.py
```

*Note: On normal app startup, `main.py` will also automatically create the default admin account if none exists.*

---

## 🚀 Running the Server

Start the development server with Uvicorn:
```bash
uvicorn app.main:app --reload --port 8000
```

Access Swagger Interactive API Documentation:
- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## 🧪 Running Automated Tests

Execute all pytest tests:
```bash
pytest -v
```

This tests:
1. **Admin Login & Auth**
2. **Book CRUD & Unique ID Generation (`LIB-00001`)**
3. **Tamil Unicode Support & CSV Import**
4. **Member & Configurable Subscription Management**
5. **Order Creation & Price Snapshot Immutability** (Verifies master book price edits do NOT change past order totals)
6. **Book Returns & Stock Availability Updates**
7. **Public Website Catalog Filtering** (`publish_on_website = true` only)

---

## 📌 Main API Endpoints Summary

### Authentication
- `POST /api/auth/login`: Admin login (returns JWT Bearer token)
- `GET /api/auth/me`: Get current admin info

### Public Website
- `GET /api/books`: Search & paginate published books only (`publish_on_website = true`)
- `GET /api/books/{book_id}`: Fetch single published book

### Admin Book Management
- `POST /api/admin/books`: Create a new book (auto generates `LIB-XXXXX`)
- `GET /api/admin/books`: Search, filter (category, language, status, publication), and paginate books
- `GET /api/admin/books/{book_id}`: Fetch book details
- `PUT /api/admin/books/{book_id}`: Update book details
- `DELETE /api/admin/books/{book_id}`: Delete book
- `POST /api/admin/books/import`: Bulk import books via UTF-8 CSV
- `GET /api/admin/books/{book_id}/history`: Book borrowing history & earnings report

### Admin Subscriptions (3 Configurable Types)
- `POST /api/admin/subscriptions`: Create subscription type
- `GET /api/admin/subscriptions`: List subscription types
- `PUT /api/admin/subscriptions/{subscription_id}`: Update subscription type
- `DELETE /api/admin/subscriptions/{subscription_id}`: Delete subscription type

### Admin Member Management
- `POST /api/admin/members`: Create member (auto generates `MEM-XXXXX`)
- `GET /api/admin/members`: Search and paginate members
- `GET /api/admin/members/{member_id}`: Get member details
- `PUT /api/admin/members/{member_id}`: Update member
- `DELETE /api/admin/members/{member_id}`: Delete member
- `GET /api/admin/members/{member_id}/orders`: Member borrowing history

### Admin Lending Orders & Returns
- `POST /api/admin/orders`: Create lending order (fetches price from DB, snapshots price, calculates subtotal, updates stock)
- `GET /api/admin/orders`: Search and list orders
- `GET /api/admin/orders/{order_id}`: Get order details
- `POST /api/admin/orders/{order_id}/return`: Return specific or all books in order
- `POST /api/admin/orders/send-reminders`: Trigger due-date reminder emails

### Admin Reports & Dashboard
- `GET /api/admin/dashboard`: Metrics summary (total books, available, borrowed, published, active orders, overdue, daily/monthly revenue)
- `GET /api/admin/reports/daily`: Daily collection report
- `GET /api/admin/reports/monthly`: Monthly collection report
- `GET /api/admin/reports/book/{book_id}`: Single book revenue report
