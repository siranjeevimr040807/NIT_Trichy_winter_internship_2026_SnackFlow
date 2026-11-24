
from flask import Flask, render_template, request, redirect, url_for, flash, send_file, Response
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from functools import wraps
from datetime import datetime
from io import BytesIO
import csv

from config import Config
from models import (
    db, User, Customer, Product, Material, BOMItem, StockMove,
    Purchase, Order, Invoice, ProductionRun, RunUse, Payment
)

from reportlab.pdfgen import canvas

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# -------------------- COMMON HELPERS --------------------

def role_required(*roles):
    def decorator(function):
        @wraps(function)
        @login_required
        def wrapper(*args, **kwargs):
            if current_user.role not in roles:
                flash("You do not have permission to access this page.")
                return redirect(url_for("dashboard"))
            return function(*args, **kwargs)
        return wrapper
    return decorator


def add_stock_move(item_type, item_id, quantity, source, source_id=None, note=""):
    move = StockMove(
        item_type=item_type,
        item_id=item_id,
        quantity=quantity,
        source=source,
        source_id=source_id,
        note=note,
        created_at=datetime.utcnow()
    )
    db.session.add(move)


# -------------------- LOGIN --------------------

@app.route("/", methods=["GET", "POST"])
@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        user = User.query.filter_by(username=username).first()

        if user and user.password == password:
            login_user(user)
            return redirect(url_for("dashboard"))

        flash("Invalid username or password.")

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


# -------------------- DASHBOARD --------------------

@app.route("/dashboard")
@login_required
def dashboard():
    orders = Order.query.order_by(Order.created_at.desc()).limit(5).all()
    products = Product.query.all()
    materials = Material.query.all()
    invoices = Invoice.query.all()

    total_sales = sum(i.total_paise for i in invoices)
    outstanding = sum(i.total_paise - i.paid_paise for i in invoices)

    return render_template(
        "dashboard.html",
        orders=orders,
        products=products,
        materials=materials,
        total_sales=total_sales,
        outstanding=outstanding
    )


# -------------------- SALES ORDERS --------------------

@app.route("/orders", methods=["GET", "POST"])
@role_required("salesman", "admin", "owner", "auditor")
def orders():
    if request.method == "POST":
        customer = db.session.get(Customer, int(request.form["customer_id"]))
        product = db.session.get(Product, int(request.form["product_id"]))
        quantity = int(request.form["quantity"])

        if not customer or not product or quantity <= 0:
            flash("Please enter valid order details.")
            return redirect(url_for("orders"))

        order = Order(
            customer_id=customer.id,
            salesman_id=current_user.id,
            quantity=quantity,
            status="Submitted",
            created_at=datetime.utcnow()
        )
        db.session.add(order)
        db.session.commit()
        flash("Order submitted successfully.")
        return redirect(url_for("orders"))

    all_orders = Order.query.order_by(Order.created_at.desc()).all()

    return render_template(
        "orders.html",
        orders=all_orders,
        customers=Customer.query.all(),
        products=Product.query.all()
    )


# -------------------- ADMIN APPROVAL --------------------

@app.route("/approve/<int:order_id>", methods=["POST"])
@role_required("admin", "owner")
def approve_order(order_id):
    order = db.session.get(Order, order_id)

    if not order or order.status != "Submitted":
        flash("Order cannot be approved.")
        return redirect(url_for("orders"))

    customer = db.session.get(Customer, order.customer_id)
    product = Product.query.first()

    if not product:
        flash("No product is available.")
        return redirect(url_for("orders"))

    # For this demo, the first product is used for each order.
    # The order model can be extended with product_id for multiple products.

    taxable = product.price_paise * order.quantity
    gst = int(taxable * product.gst_rate / 100)

    invoice = Invoice(
        order_id=order.id,
        number=f"INV-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        taxable_paise=taxable,
        cgst_paise=gst // 2 if customer.state == "Tamil Nadu" else 0,
        sgst_paise=gst - gst // 2 if customer.state == "Tamil Nadu" else 0,
        igst_paise=0 if customer.state == "Tamil Nadu" else gst,
        total_paise=taxable + gst,
        paid_paise=0,
        created_at=datetime.utcnow()
    )

    order.status = "Approved"
    db.session.add(invoice)
    db.session.commit()

    flash("Order approved and invoice generated.")
    return redirect(url_for("orders"))


# -------------------- DISPATCH --------------------

@app.route("/dispatch/<int:order_id>", methods=["POST"])
@role_required("admin", "owner")
def dispatch_order(order_id):
    order = db.session.get(Order, order_id)

    if not order or order.status != "Approved":
        flash("Only approved orders can be dispatched.")
        return redirect(url_for("orders"))

    product = Product.query.first()
    if not product:
        flash("Product not found.")
        return redirect(url_for("orders"))

    # Check finished goods balance from the stock ledger.
    moves = StockMove.query.filter_by(
        item_type="FG",
        item_id=product.id
    ).all()

    available = sum(move.quantity for move in moves)

    if available < order.quantity:
        flash(f"Insufficient stock. Available: {available}")
        return redirect(url_for("orders"))

    add_stock_move(
        "FG", product.id, -order.quantity,
        "Dispatch", order.id, "Customer dispatch"
    )

    order.status = "Dispatched"
    db.session.commit()

    flash("Order dispatched and finished goods stock updated.")
    return redirect(url_for("orders"))


# -------------------- PURCHASE --------------------

@app.route("/purchase", methods=["GET", "POST"])
@role_required("production", "admin", "owner")
def purchase():
    if request.method == "POST":
        material_id = int(request.form["material_id"])
        quantity = float(request.form["quantity"])
        rate = float(request.form["rate"])

        material = db.session.get(Material, material_id)

        if not material or quantity <= 0 or rate < 0:
            flash("Enter valid purchase details.")
            return redirect(url_for("purchase"))

        old_value = material.stock * material.avg_rate
        new_value = quantity * rate
        new_stock = material.stock + quantity

        material.avg_rate = (
            (old_value + new_value) / new_stock if new_stock else 0
        )
        material.stock = new_stock

        purchase_entry = Purchase(
            material_id=material.id,
            quantity=quantity,
            rate=rate,
            created_at=datetime.utcnow()
        )

        db.session.add(purchase_entry)
        add_stock_move(
            "RAW", material.id, quantity,
            "Purchase", note="Material purchase"
        )
        db.session.commit()

        flash("Purchase recorded and stock updated.")
        return redirect(url_for("purchase"))

    return render_template(
        "purchase.html",
        materials=Material.query.all(),
        purchases=Purchase.query.order_by(Purchase.created_at.desc()).all()
    )


# -------------------- PRODUCTION --------------------

@app.route("/production", methods=["GET", "POST"])
@role_required("production", "admin", "owner")
def production():
    products = Product.query.all()
    materials = Material.query.all()

    if request.method == "POST":
        product_id = int(request.form["product_id"])
        output = int(request.form["output"])
        labour = float(request.form["labour"])
        power = float(request.form["power"])

        product = db.session.get(Product, product_id)
        bom_items = BOMItem.query.filter_by(product_id=product_id).all()

        if not product or output <= 0:
            flash("Enter valid production details.")
            return redirect(url_for("production"))

        planned_output = sum(item.quantity for item in bom_items)
        total_material_cost = 0
        run = ProductionRun(
            product_id=product_id,
            batch_count=1,
            expected_output=planned_output,
            actual_output=output,
            damaged_pouches=float(request.form.get("damaged", 0)),
            cartons_used=float(request.form.get("cartons", 0)),
            labour=labour,
            power=power,
            material_cost=0,
            cost_per_packet=0,
            yield_variance=0,
            created_at=datetime.utcnow()
        )
        db.session.add(run)
        db.session.flush()

        for item in bom_items:
            material = db.session.get(Material, item.material_id)
            actual = float(request.form.get(f"material_{material.id}", item.quantity))

            if material.stock < actual:
                db.session.rollback()
                flash(f"Insufficient {material.name} stock.")
                return redirect(url_for("production"))

            cost = actual * material.avg_rate
            total_material_cost += cost

            material.stock -= actual

            db.session.add(RunUse(
                run_id=run.id,
                material_id=material.id,
                planned=item.quantity,
                actual=actual,
                unit_cost=material.avg_rate
            ))

            add_stock_move(
                "RAW", material.id, -actual,
                "Production", run.id, "Material consumed"
            )

        total_cost = total_material_cost + labour + power
        run.material_cost = total_material_cost
        run.cost_per_packet = total_cost / output
        run.yield_variance = (
            ((output - planned_output) / planned_output) * 100
            if planned_output else 0
        )

        add_stock_move(
            "FG", product.id, output,
            "Production", run.id, "Finished goods produced"
        )

        db.session.commit()
        flash("Production recorded and stock updated.")
        return redirect(url_for("production"))

    runs = ProductionRun.query.order_by(
        ProductionRun.created_at.desc()
    ).all()

    return render_template(
        "production.html",
        products=products,
        materials=materials,
        runs=runs
    )


# -------------------- PAYMENTS --------------------

@app.route("/payments", methods=["GET", "POST"])
@role_required("admin", "owner")
def payments():
    if request.method == "POST":
        invoice_id = int(request.form["invoice_id"])
        amount = int(float(request.form["amount"]) * 100)

        invoice = db.session.get(Invoice, invoice_id)

        if not invoice or amount <= 0:
            flash("Invalid payment.")
            return redirect(url_for("payments"))

        if invoice.paid_paise + amount > invoice.total_paise:
            flash("Payment exceeds the outstanding amount.")
            return redirect(url_for("payments"))

        invoice.paid_paise += amount
        db.session.add(Payment(
            invoice_id=invoice.id,
            amount_paise=amount,
            created_at=datetime.utcnow()
        ))
        db.session.commit()

        flash("Payment recorded.")
        return redirect(url_for("payments"))

    return render_template(
        "payments.html",
        invoices=Invoice.query.all(),
        payments=Payment.query.order_by(Payment.created_at.desc()).all()
    )


# -------------------- INVENTORY --------------------

@app.route("/inventory")
@role_required("admin", "production", "owner", "auditor")
def inventory():
    return render_template(
        "inventory.html",
        materials=Material.query.all(),
        products=Product.query.all(),
        moves=StockMove.query.order_by(
            StockMove.created_at.desc()
        ).limit(100).all()
    )


# -------------------- REPORTS AND CSV --------------------

@app.route("/reports")
@role_required("admin", "owner", "auditor")
def reports():
    invoices = Invoice.query.all()
    runs = ProductionRun.query.all()

    sales_total = sum(i.total_paise for i in invoices)
    outstanding = sum(i.total_paise - i.paid_paise for i in invoices)

    return render_template(
        "reports.html",
        invoices=invoices,
        runs=runs,
        sales_total=sales_total,
        outstanding=outstanding
    )


@app.route("/export/sales")
@role_required("admin", "owner", "auditor")
def export_sales():
    output = BytesIO()
    text_output = output

    rows = Invoice.query.all()
    lines = ["Invoice,Order ID,Taxable,CGST,SGST,IGST,Total,Paid,Outstanding"]

    for invoice in rows:
        lines.append(
            f"{invoice.number},{invoice.order_id},"
            f"{invoice.taxable_paise / 100:.2f},"
            f"{invoice.cgst_paise / 100:.2f},"
            f"{invoice.sgst_paise / 100:.2f},"
            f"{invoice.igst_paise / 100:.2f},"
            f"{invoice.total_paise / 100:.2f},"
            f"{invoice.paid_paise / 100:.2f},"
            f"{(invoice.total_paise - invoice.paid_paise) / 100:.2f}"
        )

    return Response(
        "\n".join(lines),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=sales.csv"}
    )


@app.route("/export/stock")
@role_required("admin", "owner", "auditor")
def export_stock():
    lines = ["Material,Unit,Stock,Average Rate"]

    for material in Material.query.all():
        lines.append(
            f"{material.name},{material.unit},"
            f"{material.stock},{material.avg_rate}"
        )

    return Response(
        "\n".join(lines),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=stock.csv"}
    )


# -------------------- GST INVOICE PDF --------------------

@app.route("/invoice/<int:invoice_id>/pdf")
@login_required
def invoice_pdf(invoice_id):
    invoice = db.session.get(Invoice, invoice_id)

    if not invoice:
        flash("Invoice not found.")
        return redirect(url_for("orders"))

    order = db.session.get(Order, invoice.order_id)
    customer = db.session.get(Customer, order.customer_id)

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer)
    pdf.setTitle(invoice.number)

    pdf.drawString(50, 800, "GST TAX INVOICE")
    pdf.drawString(50, 770, f"Invoice Number: {invoice.number}")
    pdf.drawString(50, 745, f"Customer: {customer.name}")
    pdf.drawString(50, 720, f"GSTIN: {customer.gstin or '-'}")
    pdf.drawString(50, 695, f"State: {customer.state}")
    pdf.drawString(50, 650, f"Order Quantity: {order.quantity}")
    pdf.drawString(50, 620, f"Taxable Value: Rs. {invoice.taxable_paise / 100:.2f}")
    pdf.drawString(50, 595, f"CGST: Rs. {invoice.cgst_paise / 100:.2f}")
    pdf.drawString(50, 570, f"SGST: Rs. {invoice.sgst_paise / 100:.2f}")
    pdf.drawString(50, 545, f"IGST: Rs. {invoice.igst_paise / 100:.2f}")
    pdf.drawString(50, 510, f"Total: Rs. {invoice.total_paise / 100:.2f}")

    pdf.save()
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"{invoice.number}.pdf",
        mimetype="application/pdf"
    )


if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    app.run(debug=True)
