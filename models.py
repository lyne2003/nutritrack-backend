# from sqlalchemy import Column, Integer, String, DateTime, func, ForeignKey, Boolean
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    func,
    ForeignKey,
    Boolean
)
from datetime import datetime
from sqlalchemy import Float  # 👈 ADD THIS IMPORT
from database import Base


# user model
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(100))
    email = Column(String(100), unique=True, index=True)
    password = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    onboarding_completed = Column(Boolean, default=False)  # ✅ New field
    reset_otp = Column(String(10), nullable=True)
    reset_otp_expiry = Column(DateTime, nullable=True)
    onboarding_step = Column(Integer, default=1)

# diets model
class DietaryRestriction(Base):
    __tablename__ = "dietary_restrictions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    logo_path = Column(String(255))

# diet - user join table
class UserDietaryRestriction(Base):
    __tablename__ = "user_dietary_restrictions"

    user_id = Column(Integer, primary_key=True)
    dietary_id = Column(Integer, primary_key=True)

# allergy model
class Allergy(Base):
    __tablename__ = "Allergies"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    logo_path = Column(String(255))

# allergy - user join table
class UserAllergies(Base):
    __tablename__ = "user_allergies"

    user_id = Column(Integer, primary_key=True)
    allergy_id = Column(Integer, primary_key=True)

# serving model
class Serving(Base):
    __tablename__ = "Servings"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    logo_path = Column(String(255))

class UserServing(Base):
    __tablename__ = "user_servings"
    user_id = Column(Integer, primary_key=True)
    serving_id = Column(Integer, primary_key=True)
    family_count = Column(Integer)

class LabResult(Base):
    __tablename__ = "lab_results"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    filename = Column(String(255), nullable=False)
    uploaded_at = Column(DateTime, server_default=func.now())
    # 🔥 ADD THESE FIELDS
    glucose = Column(Float, nullable=True)
    ldl = Column(Float, nullable=True)
    hdl = Column(Float, nullable=True)
    triglycerides = Column(Float, nullable=True)
    creatinine = Column(Float, nullable=True)

class SavedRecipe(Base):
    __tablename__ = "saved_recipes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))

    recipe_name = Column(String(255))

    ingredients = Column(Text)
    steps = Column(Text)

    calories = Column(Float)
    protein = Column(Float)
    carbs = Column(Float)
    fat = Column(Float)

    servings = Column(Integer)

    created_at = Column(DateTime, default=datetime.utcnow)
