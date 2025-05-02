from enum import Enum
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
import uuid

db = SQLAlchemy()

class OrderStatus(Enum):
    PENDING = "wait"
    PAID = "paid"
    USED = "used"

class Order(db.Model):
    __tablename__ = 'orders'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    order_id = db.Column(db.String(32), unique=True, nullable=False, default=lambda: str(uuid.uuid4()).replace('-', ''))
    address = db.Column(db.String(66), nullable=False, default="", index=True)
    status = db.Column(db.Enum(OrderStatus), nullable=False, default=OrderStatus.PENDING)
    digest = db.Column(db.String(64), nullable=True, default="")
    blob_id = db.Column(db.String(64), nullable=True, default="")
    created_at = db.Column(db.Integer, default=lambda: int(datetime.now().timestamp()))
    updated_at = db.Column(db.Integer, default=lambda: int(datetime.now().timestamp()), onupdate=lambda: int(datetime.now().timestamp()))

    def __repr__(self):
        return f'<Order {self.order_id}>'