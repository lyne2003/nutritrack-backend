from sqlalchemy.orm import Session
from models import User, DietaryRestriction,UserAllergies,Allergy  # ✅ ADD DietaryRestriction HERE
from passlib.context import CryptContext
from models import UserServing, Serving  # ✅ Add this line!
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()

def create_user(db: Session, full_name: str, email: str, password: str):
    hashed_password = pwd_context.hash(password)
    new_user = User(full_name=full_name, email=email, password=hashed_password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

def verify_password(plain, hashed):
    return pwd_context.verify(plain, hashed)

# ✅ New function
def get_all_dietary_restrictions(db: Session):
    return db.query(DietaryRestriction).all()

from models import UserDietaryRestriction

def save_user_dietary_restrictions(db: Session, user_id: int, dietary_ids: list[int]):
    # Delete old selections first
    db.query(UserDietaryRestriction).filter(UserDietaryRestriction.user_id == user_id).delete()

    # Insert new selections
    for d_id in dietary_ids:
        db.add(UserDietaryRestriction(user_id=user_id, dietary_id=d_id))

    db.commit()
    return {"message": "Dietary restrictions saved successfully."}


def get_all_allergies(db):
    return db.query(Allergy).all()

def save_user_allergies(db: Session, user_id: int, allergy_ids: list[int]):
    # Delete old selections first
    db.query(UserAllergies).filter(UserAllergies.user_id == user_id).delete()

    # Insert new selections
    for d_id in allergy_ids:
        db.add(UserAllergies(user_id=user_id, allergy_id=d_id))

    db.commit()
    return {"message": "Allergies saved successfully."}

def get_all_servings(db):
    from models import Serving
    return db.query(Serving).all()
def save_user_serving(db: Session, user_id: int, serving_id: int, family_count: int):
    new_entry = UserServing(
        user_id=user_id,
        serving_id=serving_id,
        family_count=family_count
    )
    db.add(new_entry)
    db.commit()
    db.refresh(new_entry)
    return new_entry
