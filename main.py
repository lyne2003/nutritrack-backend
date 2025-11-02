from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import Base, engine, SessionLocal
from schemas import UserCreate, UserLogin, UserResponse, DietaryRestrictionBase,UserServingSelection
from crud import create_user, get_user_by_email, verify_password, get_all_dietary_restrictions,save_user_serving
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import List  # ✅ add this line
from models import User, DietaryRestriction,Serving,UserServing
from fastapi.staticfiles import StaticFiles
from fastapi import Request
from database import get_db
from sqlalchemy import text  # ✅ add this import at the top if missing
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
from fastapi.security import HTTPBearer
from fastapi import Security

security = HTTPBearer(auto_error=False)

import os
print("📁 Current working directory:", os.getcwd())
print("📂 Static folder absolute path:", os.path.abspath("static"))

Base.metadata.create_all(bind=engine)

SECRET_KEY = "mysecretkey"  # change to something secure
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/signup", response_model=UserResponse)
def signup(user: UserCreate, db: Session = Depends(get_db)):
    existing_user = get_user_by_email(db, user.email)
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    new_user = create_user(db, user.full_name, user.email, user.password)
    return new_user

@app.post("/login")
def login(request: UserLogin, db: Session = Depends(get_db)):
    user = get_user_by_email(db, request.email)
    if not user or not verify_password(request.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    token_data = {
        "sub": user.email,
        "exp": datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    }
    access_token = jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)
    return {"access_token": access_token, "token_type": "bearer","onboarding_completed": user.onboarding_completed,"user_id": user.id  }

@app.put("/user/{user_id}/complete_onboarding")
def complete_onboarding(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.onboarding_completed = True
    db.commit()
    db.refresh(user)
    return {"message": "Onboarding completed successfully"}


@app.get("/dietary_restrictions", response_model=List[DietaryRestrictionBase])
def get_dietary_restrictions(request: Request, db: Session = Depends(get_db)):
    restrictions = get_all_dietary_restrictions(db)
    base_url = str(request.base_url).rstrip('/')
    for r in restrictions:
        if r.logo_path:
            r.logo_path = f"{base_url}/static/logos/{r.logo_path}"
    return restrictions


from schemas import UserDietarySelection
from crud import save_user_dietary_restrictions
from jose import jwt, JWTError

# ✅ Helper function to extract user ID from token
def get_current_user_id(token: str = Depends(lambda: None), db: Session = Depends(get_db)):
    if token is None:
        raise HTTPException(status_code=401, detail="Missing token")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        user = db.query(User).filter(User.email == email).first()
        if not user:
            raise HTTPException(status_code=401, detail="Invalid user")
        return user.id
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
        

from sqlalchemy import text

@app.post("/user/dietary_restrictions")
def set_user_dietary_restrictions(
    selection: UserDietarySelection,
    db: Session = Depends(get_db),
    credentials: dict = Security(security)
):
    if not credentials:
        raise HTTPException(status_code=401, detail="Missing token")

    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        user = db.query(User).filter(User.email == email).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        print(f"✅ User ID: {user.id}")
        print(f"✅ Dietary IDs: {selection.dietary_ids}")

        for dietary_id in selection.dietary_ids:
            db.execute(
                text("INSERT INTO user_dietary_restrictions (user_id, dietary_id) VALUES (:user_id, :dietary_id)"),
                {"user_id": user.id, "dietary_id": dietary_id},
            )

        db.commit()
        print("✅ Commit successful.")
        return {"message": "Dietary restrictions saved successfully"}

    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


from schemas import AllergyBase
from crud import get_all_allergies

@app.get("/allergies", response_model=List[AllergyBase])
def get_all_allergies_endpoint(request: Request, db: Session = Depends(get_db)):
    allergies = get_all_allergies(db)
    base_url = str(request.base_url).rstrip('/')
    for a in allergies:
        if a.logo_path:
            a.logo_path = f"{base_url}/static/logos/{a.logo_path}"
    return allergies

from schemas import UserAllergySelection
from crud import save_user_allergies

@app.post("/user/allergies")
def set_user_allergies(
    selection: UserAllergySelection,
    db: Session = Depends(get_db),
    credentials: dict = Security(security)
):
    if not credentials:
        raise HTTPException(status_code=401, detail="Missing token")

    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        user = db.query(User).filter(User.email == email).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        print(f"✅ User ID: {user.id}")
        print(f"✅ Allergies IDs: {selection.allergy_ids}")

        for allergy_id in selection.allergy_ids:
            db.execute(
                text("INSERT INTO user_allergies (user_id, allergy_id) VALUES (:user_id, :allergy_id)"),
                {"user_id": user.id, "allergy_id": allergy_id},
            )

        db.commit()
        print("✅ Commit successful.")
        return {"message": "Allergies saved successfully"}

    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

from schemas import ServingBase
from crud import get_all_servings

@app.get("/servings", response_model=List[ServingBase])
def get_all_servings_endpoint(request: Request, db: Session = Depends(get_db)):
    servings = get_all_servings(db)
    base_url = str(request.base_url).rstrip('/')
    for s in servings:
        if s.logo_path:
            s.logo_path = f"{base_url}/static/logos/{s.logo_path}"
    return servings

@app.post("/user/servings")
def set_user_servings(
    selection: UserServingSelection,
    db: Session = Depends(get_db),
    credentials: dict = Security(security)
):
    if not credentials:
        raise HTTPException(status_code=401, detail="Missing token")

    token = credentials.credentials
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    email = payload.get("sub")
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    family_count = selection.family_count
    serving = db.query(Serving).filter(Serving.id == selection.serving_id).first()
    if not serving:
        raise HTTPException(status_code=404, detail="Invalid serving_id")

    if family_count is None:
        if "just" in serving.name.lower():
            family_count = 1
        elif "couple" in serving.name.lower():
            family_count = 2
        elif "family" in serving.name.lower():
            raise HTTPException(status_code=400, detail="Family count required")

    save_user_serving(db, user.id, selection.serving_id, family_count)
    return {"message": "Serving preference saved successfully"}


# ===============================================
# 🧬 LAB RESULTS UPLOAD ENDPOINT
# ===============================================
from fastapi import UploadFile, File
from models import LabResult
import os

UPLOAD_DIR = "uploaded_lab_results"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.post("/upload_lab_result")
async def upload_lab_result(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    credentials: dict = Security(security)
):
    # ✅ Check token
    if not credentials:
        raise HTTPException(status_code=401, detail="Missing token")

    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        user = db.query(User).filter(User.email == email).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # ✅ Only allow PDF
        if not file.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail="Only PDF files are allowed")

        # ✅ Save file locally
        save_path = os.path.join(UPLOAD_DIR, f"user_{user.id}_{file.filename}")
        with open(save_path, "wb") as buffer:
            buffer.write(await file.read())

        # ✅ Save record in DB
        lab = LabResult(user_id=user.id, filename=file.filename)
        db.add(lab)
        db.commit()
        db.refresh(lab)

        return {"message": "Lab result uploaded successfully", "filename": file.filename}

    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error uploading file: {e}")

# ===============================================
# 🧠 USER FINAL INFO RETRIEVAL ENDPOINTS
# ===============================================
from models import DietaryRestriction, Allergy, Serving, LabResult
from sqlalchemy import text

# 🔹 1. Get user's dietary restriction(s)
@app.get("/user/dietary_restrictions")
def get_user_dietary_restrictions(db: Session = Depends(get_db), credentials: dict = Security(security), request: Request = None):
    if not credentials:
        raise HTTPException(status_code=401, detail="Missing token")

    token = credentials.credentials
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    email = payload.get("sub")
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    base_url = str(request.base_url).rstrip('/')
    results = db.execute(text("""
        SELECT d.id, d.name, d.logo_path
        FROM user_dietary_restrictions udr
        JOIN dietary_restrictions d ON udr.dietary_id = d.id
        WHERE udr.user_id = :uid
    """), {"uid": user.id}).fetchall()

    return {
        "dietary_restrictions": [
            {
                "id": r[0],
                "name": r[1],
                "logo_path": f"{base_url}/static/logos/{r[2]}" if r[2] else None
            }
            for r in results
        ]
    }


# 🔹 2. Get user's allergy restriction(s)
@app.get("/user/allergies")
def get_user_allergies(
    db: Session = Depends(get_db),
    credentials: dict = Security(security),
    request: Request = None
):
    if not credentials:
        raise HTTPException(status_code=401, detail="Missing token")
    token = credentials.credentials

    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    email = payload.get("sub")
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    base_url = str(request.base_url).rstrip('/')
    results = db.execute(text("""
        SELECT a.id, a.name, a.logo_path
        FROM user_allergies ua
        JOIN allergies a ON ua.allergy_id = a.id
        WHERE ua.user_id = :uid
    """), {"uid": user.id}).fetchall()

    return {
        "allergies": [
            {
                "id": r[0],
                "name": r[1],
                "logo_path": f"{base_url}/static/logos/{r[2]}" if r[2] else None
            }
            for r in results
        ]
    }



# 🔹 3. Get user's serving preference
@app.get("/user/servings")
def get_user_serving(
    db: Session = Depends(get_db),
    credentials: dict = Security(security),
    request: Request = None
):
    if not credentials:
        raise HTTPException(status_code=401, detail="Missing token")
    token = credentials.credentials

    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    email = payload.get("sub")
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    base_url = str(request.base_url).rstrip('/')
    result = db.execute(text("""
        SELECT s.id, s.name, s.logo_path, us.family_count
        FROM user_servings us
        JOIN servings s ON us.serving_id = s.id
        WHERE us.user_id = :uid
    """), {"uid": user.id}).fetchone()

    if not result:
        return {"servings": []}

    sid, name, logo, family_count = result

    # 🧠 Label adjustment for family count
    if "family" in name.lower() and family_count:
        name = f"Family of {family_count}"

    return {
        "servings": [{
            "id": sid,
            "name": name,
            "logo_path": f"{base_url}/static/logos/{logo}" if logo else None
        }]
    }



# 🔹 4. Get user's latest uploaded lab result
@app.get("/user/lab_result")
def get_user_lab_result(db: Session = Depends(get_db), credentials: dict = Security(security)):
    if not credentials:
        raise HTTPException(status_code=401, detail="Missing token")
    token = credentials.credentials

    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    email = payload.get("sub")
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    result = (
        db.query(LabResult)
        .filter(LabResult.user_id == user.id)
        .order_by(LabResult.uploaded_at.desc())
        .first()
    )

    if not result:
        return {"lab_result": None}

    return {"lab_result": result.filename}

from sqlalchemy import text

@app.get("/user_info/{user_id}")
def get_user_info(user_id: int, db: Session = Depends(get_db)):
    from sqlalchemy import text

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    base_url = "http://10.0.2.2:8000"

    # ✅ Fetch Dietary Restrictions (with ID)
    diet_query = text("""
        SELECT d.id, d.name, d.logo_path
        FROM user_dietary_restrictions udr
        JOIN dietary_restrictions d ON udr.dietary_id = d.id
        WHERE udr.user_id = :user_id
    """)
    diets = [
        {
            "id": row[0],
            "name": row[1],
            "logo": f"{base_url}/static/logos/{row[2]}" if row[2] else None
        }
        for row in db.execute(diet_query, {"user_id": user_id}).fetchall()
    ]

    # ✅ Fetch Allergies (with ID)
    allergy_query = text("""
        SELECT a.id, a.name, a.logo_path
        FROM user_allergies ua
        JOIN allergies a ON ua.allergy_id = a.id
        WHERE ua.user_id = :user_id
    """)
    allergies = [
        {
            "id": row[0],
            "name": row[1],
            "logo": f"{base_url}/static/logos/{row[2]}" if row[2] else None
        }
        for row in db.execute(allergy_query, {"user_id": user_id}).fetchall()
    ]

    # ✅ Fetch latest lab result (optional)
    lab_result = db.execute(
        text("""
            SELECT filename
            FROM lab_results
            WHERE user_id = :user_id
            ORDER BY uploaded_at DESC
            LIMIT 1
        """),
        {"user_id": user_id},
    ).fetchone()

    lab_result_filename = lab_result[0] if lab_result else None

    # ✅ Final response
    return {
        "user_id": user_id,
        "dietary_restrictions": diets,
        "allergies": allergies,
        "lab_result_filename": lab_result_filename,
    }


from sqlalchemy import text

# ===============================================
# 🗑️ DELETE a specific dietary restriction for a user
# ===============================================
@app.delete("/user/dietary_restrictions/{dietary_id}")
def delete_user_dietary_restriction(
    dietary_id: int,
    db: Session = Depends(get_db),
    credentials: dict = Security(security)
):
    if not credentials:
        raise HTTPException(status_code=401, detail="Missing token")

    token = credentials.credentials
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    email = payload.get("sub")
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        result = db.execute(
            text("DELETE FROM user_dietary_restrictions WHERE user_id = :uid AND dietary_id = :did"),
            {"uid": user.id, "did": dietary_id}
        )
        db.commit()

        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Dietary restriction not found for this user")

        return {"message": "Dietary restriction deleted successfully"}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting dietary restriction: {e}")


# ===============================================
# 🗑️ DELETE a specific allergy for a user
# ===============================================
@app.delete("/user/allergies/{allergy_id}")
def delete_user_allergy(
    allergy_id: int,
    db: Session = Depends(get_db),
    credentials: dict = Security(security)
):
    if not credentials:
        raise HTTPException(status_code=401, detail="Missing token")

    token = credentials.credentials
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    email = payload.get("sub")
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        result = db.execute(
            text("DELETE FROM user_allergies WHERE user_id = :uid AND allergy_id = :aid"),
            {"uid": user.id, "aid": allergy_id}
        )
        db.commit()

        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Allergy not found for this user")

        return {"message": "Allergy deleted successfully"}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting allergy: {e}")
