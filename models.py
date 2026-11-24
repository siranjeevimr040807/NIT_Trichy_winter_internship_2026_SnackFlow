
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True)
    password = db.Column(db.String(200))
    role = db.Column(db.String(20))


class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    state = db.Column(db.String(50))
    gstin = db.Column(db.String(20))


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    pack_size = db.Column(db.String(30))
    price_paise = db.Column(db.Integer)
    gst_rate = db.Column(db.Integer)
    hsn = db.Column(db.String(20))


class Material(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    unit = db.Column(db.String(20))
    stock = db.Column(db.Float, default=0)
    avg_rate = db.Column(db.Float, default=0)
    category = db.Column(db.String(30))


class BOMItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"))
    material_id = db.Column(db.Integer, db.ForeignKey("material.id"))
    quantity = db.Column(db.Float)


class StockMove(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_type = db.Column(db.String(20))
    item_id = db.Column(db.Integer)
    quantity = db.Column(db.Float)
    source = db.Column(db.String(50))
    source_id = db.Column(db.Integer)
    note = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Purchase(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    material_id = db.Column(db.Integer, db.ForeignKey("material.id"))
    quantity = db.Column(db.Float)
    rate = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customer.id"))
    salesman_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    quantity = db.Column(db.Integer)
    status = db.Column(db.String(20), default="Submitted")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Invoice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("order.id"))
    number = db.Column(db.String(30))
    taxable_paise = db.Column(db.Integer)
    cgst_paise = db.Column(db.Integer, default=0)
    sgst_paise = db.Column(db.Integer, default=0)
    igst_paise = db.Column(db.Integer, default=0)
    total_paise = db.Column(db.Integer)
    paid_paise = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ProductionRun(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"))
    batch_count = db.Column(db.Integer)
    expected_output = db.Column(db.Integer)
    actual_output = db.Column(db.Integer)
    damaged_pouches = db.Column(db.Integer)
    cartons_used = db.Column(db.Integer)
    labour = db.Column(db.Float)
    power = db.Column(db.Float)
    material_cost = db.Column(db.Float)
    cost_per_packet = db.Column(db.Float)
    yield_variance = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class RunUse(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    run_id = db.Column(db.Integer, db.ForeignKey("production_run.id"))
    material_id = db.Column(db.Integer, db.ForeignKey("material.id"))
    planned = db.Column(db.Float)
    actual = db.Column(db.Float)
    unit_cost = db.Column(db.Float)


class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey("invoice.id"))
    amount_paise = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
