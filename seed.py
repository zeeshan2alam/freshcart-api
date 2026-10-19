"""First-run data: the admin account, plus (optionally) demo products, an offer and sample orders."""
import random
import secrets
from datetime import timedelta

from sqlalchemy import func, select

import config
from database import SessionLocal
from models import Offer, Order, OrderItem, Product, User, utcnow
from security import hash_password

PRODUCTS = [
    ("Apple (Kashmiri)", "Fruits", "kg", 180, 40, "🍎"), ("Banana", "Fruits", "dozen", 60, 25, "🍌"),
    ("Tomato", "Vegetables", "kg", 30, 3, "🍅"), ("Potato", "Vegetables", "kg", 25, 80, "🥔"),
    ("Amul Milk", "Dairy", "litre", 56, 30, "🥛"), ("Paneer", "Dairy", "packet", 95, 0, "🧀"),
    ("Brown Bread", "Bakery", "packet", 45, 12, "🍞"), ("Basmati Rice", "Grains & Pulses", "kg", 120, 60, "🍚"),
    ("Orange Juice", "Beverages", "litre", 110, 18, "🧃"), ("Chocolate Cookies", "Snacks", "packet", 40, 4, "🍪"),
]


def run() -> None:
    with SessionLocal() as db:
        if not db.scalar(select(User).where(User.email == config.ADMIN_EMAIL)):
            db.add(User(name=config.ADMIN_NAME, email=config.ADMIN_EMAIL,
                        password_hash=hash_password(config.ADMIN_PASSWORD), role="admin"))
            db.commit()

        if not config.SEED_DEMO_DATA or db.scalar(select(func.count(Product.id))):
            return

        demo = User(name="Demo User", email="user@freshcart.com", password_hash=hash_password("user123"), role="customer")
        # sample orders belong to a separate account nobody can log in to, so the demo user's order list stays clean
        sampler = User(name="Sample Customer", email="sample@freshcart.com",
                       password_hash=hash_password(secrets.token_urlsafe(24)), role="customer")
        db.add_all([demo, sampler])
        db.add(Offer(text="MEGA FRESH SALE — Extra 10% OFF on everything", emoji="🎉", percent=10,
                     code="FRESH10", theme="red", active=True))
        catalog = [Product(name=n, category=c, unit=u, price=p, stock=s, emoji=e) for n, c, u, p, s, e in PRODUCTS]
        db.add_all(catalog)
        db.flush()

        # 30 days of sample orders so the analytics dashboard isn't empty (flagged is_sample)
        rnd, now, serial = random.Random(7), utcnow(), 0
        for days_ago in range(29, -1, -1):
            for _ in range(1 + rnd.randrange(3) + (1 if days_ago < 7 else 0)):
                picks = rnd.sample([p for p in catalog if p.name != "Paneer"], 1 + rnd.randrange(4))
                items = [OrderItem(product_id=p.id, name=p.name, unit=p.unit, price=p.price,
                                   qty=1 + rnd.randrange(4), emoji=p.emoji) for p in picks]
                subtotal = sum(i.price * i.qty for i in items)
                delivery = 0 if subtotal >= config.FREE_DELIVERY_ABOVE else config.DELIVERY_FEE
                method = rnd.choices(["upi", "card", "cod"], [5, 3, 2])[0]
                when = min(now - timedelta(days=days_ago) - timedelta(hours=rnd.randrange(0, 12)), now)
                serial += 1
                db.add(Order(code=f"FC{20000000 + serial:08d}", user_id=sampler.id, customer_name="Sample Customer", phone="9000000000",
                             address="Sample address", city="Mumbai", pincode="400001",
                             subtotal=subtotal, discount=0, coupon="", delivery=delivery,
                             total=subtotal + delivery, method=method,
                             status="Placed · Pay on delivery" if method == "cod" else "Paid",
                             is_sample=True, created_at=when, items=items))
        db.commit()
