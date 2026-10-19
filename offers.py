from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_db
from deps import admin_only
from models import Offer
from schemas import CouponIn, CouponOut, OfferIn, OfferOut, OfferPatch

router = APIRouter(tags=["offers"])


@router.get("/offers", response_model=list[OfferOut])
def active_offers(db: Session = Depends(get_db)):
    """Public: what the sale marquee shows."""
    return db.scalars(select(Offer).where(Offer.active.is_(True)).order_by(Offer.id.desc())).all()


@router.get("/offers/all", response_model=list[OfferOut], dependencies=[Depends(admin_only)])
def all_offers(db: Session = Depends(get_db)):
    return db.scalars(select(Offer).order_by(Offer.id.desc())).all()


@router.post("/offers", response_model=OfferOut, status_code=201, dependencies=[Depends(admin_only)])
def create_offer(body: OfferIn, db: Session = Depends(get_db)):
    if body.code and db.scalar(select(Offer).where(Offer.code == body.code)):
        raise HTTPException(409, "Ye coupon code pehle se hai.")
    offer = Offer(**body.model_dump(), active=True)
    db.add(offer)
    db.commit()
    return offer


@router.patch("/offers/{offer_id}", response_model=OfferOut, dependencies=[Depends(admin_only)])
def set_offer_active(offer_id: int, body: OfferPatch, db: Session = Depends(get_db)):
    offer = db.get(Offer, offer_id)
    if not offer:
        raise HTTPException(404, "Offer nahi mila.")
    offer.active = body.active
    db.commit()
    return offer


@router.delete("/offers/{offer_id}", status_code=204, dependencies=[Depends(admin_only)])
def delete_offer(offer_id: int, db: Session = Depends(get_db)):
    offer = db.get(Offer, offer_id)
    if not offer:
        raise HTTPException(404, "Offer nahi mila.")
    db.delete(offer)
    db.commit()


@router.post("/coupons/validate", response_model=CouponOut)
def validate_coupon(body: CouponIn, db: Session = Depends(get_db)):
    code = body.code.strip().upper()
    offer = db.scalar(select(Offer).where(Offer.code == code, Offer.active.is_(True), Offer.percent > 0))
    return CouponOut(valid=bool(offer), code=code, percent=offer.percent if offer else 0)
