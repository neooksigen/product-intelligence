from sqlalchemy import String, Integer, Text, Boolean, Uuid
from sqlalchemy.orm import Mapped, mapped_column
from app.database_sqlalchemy import Base 
import uuid

class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_name: Mapped[str] = mapped_column(Text)
    quantity: Mapped[str] = mapped_column(Text)
    measurement_scale: Mapped[str] = mapped_column(Text)
    price: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(Text) 
    rating: Mapped[str] = mapped_column(Text)
    review_count: Mapped[str] = mapped_column(Text)
    place: Mapped[str] = mapped_column(Text)
    method: Mapped[str] = mapped_column(Text)
    source_date: Mapped[str] = mapped_column(Text)
    timestamp_extract: Mapped[str] = mapped_column(Text)
    questions: Mapped[str] = mapped_column(Text)
    nonparsed_response: Mapped[str] = mapped_column(Text)
    owner_id: Mapped[uuid.UUID] = mapped_column(Uuid)

class SearchQueries(Base):
    __tablename__ = "search_queries" 

    id: Mapped[int] = mapped_column(primary_key=True)
    country: Mapped[str] = mapped_column(Text)
    search_query_text: Mapped[str] = mapped_column(Text)
    active_status: Mapped[bool] = mapped_column(Boolean)
    last_run_at: Mapped[str] = mapped_column(Text)

class ExtractUrls(Base):
    __tablename__ = "extract_urls" 

    id: Mapped[int] = mapped_column(primary_key=True)
    country: Mapped[str] = mapped_column(Text)
    url: Mapped[str] = mapped_column(Text)
    active_status: Mapped[bool] = mapped_column(Boolean)
    last_run_at: Mapped[str] = mapped_column(Text)    

class GsQueries(Base):
    __tablename__ = "gs_queries"

    id: Mapped[int] = mapped_column(primary_key=True)
    country: Mapped[str] = mapped_column(Text)
    gs_query: Mapped[str] = mapped_column(Text)
    active_status: Mapped[bool] = mapped_column(Boolean)
    last_run_at: Mapped[str] = mapped_column(Text)    