from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from database import get_db
from deps import admin_only
from models import OrderItem, Product
from schemas import ProductIn, ProductOut

router = APIRouter(prefix="/products", tags=["products"])


@router.get("", response_model=list[ProductOut])
def list_products(
    q: str | None = Query(None, description="search in name"),
    category: str | None = None,
    db: Session = Depends(get_db),
):
    stmt = select(Product).order_by(Product.id.desc())
    if q:
        stmt = stmt.where(Product.name.ilike(f"%{q}%"))
    if category:
        stmt = stmt.where(Product.category == category)
    return db.scalars(stmt).all()


@router.get("/{product_id}", response_model=ProductOut)
def get_product(product_id: int, db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(404, "Product nahi mila.")
    return product


@router.post("", response_model=ProductOut, status_code=201, dependencies=[Depends(admin_only)])
def create_product(body: ProductIn, db: Session = Depends(get_db)):
    product = Product(**body.model_dump())
    db.add(product)
    db.commit()
    return product


@router.put("/{product_id}", response_model=ProductOut, dependencies=[Depends(admin_only)])
def update_product(product_id: int, body: ProductIn, db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(404, "Product nahi mila.")
    for key, value in body.model_dump().items():
        setattr(product, key, value)
    db.commit()
    return product


@router.delete("/{product_id}", status_code=204, dependencies=[Depends(admin_only)])
def delete_product(product_id: int, db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(404, "Product nahi mila.")
    # old orders keep their snapshot rows; just detach them from the deleted product
    db.execute(update(OrderItem).where(OrderItem.product_id == product_id).values(product_id=None))
    db.delete(product)
    db.commit()
