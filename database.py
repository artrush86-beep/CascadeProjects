from sqlalchemy import Column, Integer, String, DateTime, Boolean, JSON, BigInteger, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from datetime import datetime
from config import settings

Base = declarative_base()


class Proxy(Base):
    __tablename__ = "proxies"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    ip = Column(String(45), nullable=False)
    port = Column(Integer, nullable=False)
    protocol = Column(String(10), nullable=False)  # http, https, socks4, socks5
    country_code = Column(String(2))
    anonymity = Column(String(20))  # elite, anonymous, transparent
    username = Column(String(100), nullable=True)  # для авторизации
    password = Column(String(100), nullable=True)  # для авторизации
    last_check = Column(DateTime)
    status = Column(String(20), default="pending")  # pending, active, dead
    fail_count = Column(Integer, default=0)
    speed_ms = Column(Integer)
    source = Column(String(50))  # proxyscrape, manual, webshare
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_proxies_status', 'status'),
        Index('idx_proxies_country', 'country_code'),
        Index('idx_proxies_protocol', 'protocol'),
    )


class Blacklist(Base):
    __tablename__ = "blacklist"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    ip = Column(String(45), nullable=False)
    port = Column(Integer, nullable=False)
    reason = Column(String(100))
    added_at = Column(DateTime, default=datetime.utcnow)
    source = Column(String(50))
    
    __table_args__ = (
        Index('idx_blacklist_ip', 'ip'),
    )


class ExchangeRule(Base):
    __tablename__ = "exchange_rules"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    exchange_name = Column(String(50), nullable=False)
    country_code = Column(String(2), nullable=False)
    restriction_type = Column(String(20))  # blocked, partial
    details = Column(String(500))
    
    __table_args__ = (
        Index('idx_exchange_name', 'exchange_name'),
    )


class User(Base):
    __tablename__ = "users"
    
    telegram_id = Column(BigInteger, primary_key=True)
    username = Column(String(100))
    settings = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)


class CheckHistory(Base):
    __tablename__ = "check_history"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    proxy_id = Column(Integer)
    check_time = Column(DateTime, default=datetime.utcnow)
    success = Column(Boolean)
    response_time_ms = Column(Integer)
    error_message = Column(String(500))


# Database engine
engine = create_async_engine(settings.DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session():
    async with async_session() as session:
        yield session
