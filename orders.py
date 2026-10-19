import secrets

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

import config
from database import get_db
from deps import admin_only, current_user
from models import Offer, Order, OrderItem, Product, User
from schemas import OrderIn, OrderOut

router = APIRouter(prefix="/orders", tags=["orders"])


def _new_code(db: Session) -> str:
    while True:
        code = f"FC{secrets.randbelow(10**8):08d}"
        if not db.scalar(select(Order.id).where(Order.code == code)):
            return code


@router.post("", response_model=OrderOut, status_code=201)
def place_order(body: OrderIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Prices, discount, delivery fee and stock are all decided here, never trusted from the client.

    Payment is simulated: only the chosen method is stored, never card / UPI details.
    """
    if user.role == "admin":
        raise HTTPException(403, "Admin order place nahi kar sakta.")

    wanted: dict[int, int] = {}
    for item in body.items:
        wanted[item.product_id] = wanted.get(item.product_id, 0) + item.qty

    products = {p.id: p for p in db.scalars(select(Product).where(Product.id.in_(wanted)))}
    for pid, qty in wanted.items():
        product = products.get(pid)
        if not product:
            raise HTTPException(404, f"Product #{pid} nahi mila.")
        if product.stock < qty:
            raise HTTPException(409, f'"{product.name}" ka sirf {product.stock} stock bacha hai.')

    subtotal = round(sum(products[pid].price * qty for pid, qty in wanted.items()), 2)

    coupon, discount = "", 0
    if body.coupon:
        code = body.coupon.strip().upper()
        offer = db.scalar(select(Offer).where(Offer.code == code, Offer.active.is_(True), Offer.percent > 0))
        if not offer:
            raise HTTPException(400, "Coupon valid nahi hai.")
        coupon, discount = code, int(subtotal * offer.percent / 100 + 0.5)

    delivery = 0 if subtotal >= config.FREE_DELIVERY_ABOVE else config.DELIVERY_FEE
    order = Order(
        code=_new_code(db), user_id=user.id, customer_name=body.customer_name, phone=body.phone,
        address=body.address, city=body.city, pincode=body.pincode,
        subtotal=subtotal, discount=discount, coupon=coupon, delivery=delivery,
        total=subtotal - discount + delivery, method=body.method,
        status="Placed · Pay on delivery" if body.method == "cod" else "Paid",
        items=[
            OrderItem(product_id=pid, name=products[pid].name, unit=products[pid].unit,
                      price=products[pid].price, qty=qty, emoji=products[pid].emoji)
            for pid, qty in wanted.items()
        ],
    )
    for pid, qty in wanted.items():
        products[pid].stock -= qty
    db.add(order)
    db.commit()
    return order


@router.get("", response_model=list[OrderOut])
def list_orders(user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Customers see their own orders, admins see everyone's."""
    stmt = select(Order).order_by(Order.created_at.desc(), Order.id.desc())
    if user.role != "admin":
        stmt = stmt.where(Order.user_id == user.id)
    return db.scalars(stmt).all()


@router.delete("/sample", status_code=204, dependencies=[Depends(admin_only)])
def delete_sample_orders(db: Session = Depends(get_db)):
    ids = db.scalars(select(Order.id).where(Order.is_sample.is_(True))).all()
    if ids:
        db.execute(delete(OrderItem).where(OrderItem.order_id.in_(ids)))
        db.execute(delete(Order).where(Order.id.in_(ids)))
        db.commit()
