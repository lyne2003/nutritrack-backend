from pydantic import BaseModel, EmailStr
from typing import Optional 
from typing import List

class UserCreate(BaseModel):
    full_name: str
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: int
    full_name: str
    email: str

    class Config:
        orm_mode = True
# ✅ New schema
class DietaryRestrictionBase(BaseModel):
    id: int
    name: str
    logo_path: Optional[str] = None

    class Config:
        orm_mode = True

class UserDietarySelection(BaseModel):
    dietary_ids: List[int]


class AllergyBase(BaseModel):
    id: int
    name: str
    logo_path: str | None = None

    class Config:
        orm_mode = True
class UserAllergySelection(BaseModel):
    allergy_ids: list[int]

class ServingBase(BaseModel):
    id: int
    name: str
    logo_path: str | None = None

    class Config:
        orm_mode = True
class UserServingSelection(BaseModel):
    serving_id: int
    family_count: Optional[int] = None

from pydantic import BaseModel
from typing import List

class SaveRecipeRequest(BaseModel):
    user_id: int
    recipe_name: str

    ingredients: List[str]
    steps: List[str]

    calories: float
    protein: float
    carbs: float
    fat: float

    servings: int