
from app import app, db
from models import *

with app.app_context():

    db.drop_all()
    db.create_all()

    users = [
        User(username="admin", password="demo123", role="admin"),
        User(username="salesman_a", password="demo123", role="salesman"),
        User(username="salesman_b", password="demo123", role="salesman"),
        User(username="production", password="demo123", role="production"),
        User(username="auditor", password="demo123", role="auditor"),
        User(username="owner", password="demo123", role="owner")
    ]

    db.session.add_all(users)

    customers = [
        Customer(name="Retailer A", state="Tamil Nadu",
                 gstin="33AAAAA0000A1Z5"),

        Customer(name="Distributor B", state="Karnataka",
                 gstin="29BBBBB0000B1Z5")
    ]

    product = Product(
        name="Murukku",
        pack_size="200 g",
        price_paise=5000,
        gst_rate=5,
        hsn="210690"
    )

    db.session.add_all(customers + [product])
    db.session.flush()

    materials = [
        Material(name="Flour", unit="kg", stock=100,
                 avg_rate=42, category="raw"),

        Material(name="Cooking oil", unit="litre", stock=30,
                 avg_rate=140, category="raw"),

        Material(name="Salt and spice mix", unit="kg", stock=5,
                 avg_rate=200, category="raw"),

        Material(name="200 g pouch", unit="piece", stock=500,
                 avg_rate=2.5, category="packaging"),

        Material(name="Carton", unit="piece", stock=30,
                 avg_rate=15, category="packaging")
    ]

    db.session.add_all(materials)
    db.session.flush()

    bom = [
        BOMItem(product_id=product.id,
                material_id=materials[0].id, quantity=40),

        BOMItem(product_id=product.id,
                material_id=materials[1].id, quantity=10),

        BOMItem(product_id=product.id,
                material_id=materials[2].id, quantity=1.2),

        BOMItem(product_id=product.id,
                material_id=materials[3].id, quantity=200),

        BOMItem(product_id=product.id,
                material_id=materials[4].id, quantity=10)
    ]

    db.session.add_all(bom)

    for item in materials:
        db.session.add(
            StockMove(
                item_type="material",
                item_id=item.id,
                quantity=item.stock,
                source="opening",
                source_id=0,
                note="Opening stock"
            )
        )

    db.session.add(
        StockMove(
            item_type="product",
            item_id=product.id,
            quantity=50,
            source="opening",
            source_id=0,
            note="Opening finished goods"
        )
    )

    db.session.commit()

    print("Benchmark data loaded successfully!")
    print("Demo password: demo123")
