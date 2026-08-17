import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import r2
from app.config import settings
from app.database import connect_to_mongo, close_mongo_connection, get_admins_collection
from app.auth.security import hash_password
from app.utils.helpers import current_utc_datetime

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("library_main")

async def ensure_default_admin():
    try:
        admins_col = get_admins_collection()
        admin_email = settings.ADMIN_EMAIL.lower().strip()
        existing = await admins_col.find_one({"email": admin_email})
        if not existing:
            hashed_pwd = hash_password(settings.ADMIN_INITIAL_PASSWORD)
            admin_doc = {
                "email": admin_email,
                "name": "Library Admin",
                "hashed_password": hashed_pwd,
                "created_at": current_utc_datetime(),
                "updated_at": current_utc_datetime()
            }
            await admins_col.insert_one(admin_doc)
            logger.info(f"Default admin created successfully ({admin_email})")
    except Exception as e:
        logger.warning(f"Could not check/create default admin on startup: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Initializing Library Management System Backend...")
    try:
        await connect_to_mongo()
        await ensure_default_admin()
    except Exception as e:
        logger.error(f"Startup MongoDB initialization warning: {e}")
    yield
    # Shutdown
    logger.info("Shutting down Library Management System Backend...")
    await close_mongo_connection()

app = FastAPI(
    title="Library Management System API",
    description="Complete Backend API for Library Management System with Python, FastAPI & MongoDB Atlas.",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for uploads
import os
from fastapi.staticfiles import StaticFiles
static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Import Routers
from app.routers import (
    auth,
    books,
    public_books,
    members,
    subscriptions,
    orders,
    reports
)

app.include_router(auth.router)
app.include_router(books.router)
app.include_router(public_books.router)
app.include_router(members.router)
app.include_router(subscriptions.router)
app.include_router(orders.router)
app.include_router(reports.router)
app.include_router(r2.router)

@app.get("/", tags=["Health Check"])
async def root():
    return {
        "status": "online",
        "service": "Library Management System API",
        "version": "1.0.0",
        "docs_url": "/docs"
    }
