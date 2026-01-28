from fastapi import FastAPI, Depends, HTTPException
import os
import joblib
import pandas as pd
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from auth import auth_router, get_current_user

app = FastAPI(
    title="Customer Churn Prediction API",
    description="An API to predict customer churn using machine learning."
)

# ------------------ INCLUDE AUTH ROUTES ------------------
app.include_router(auth_router)

# ------------------ ROOT ------------------
@app.get("/")
def greet():
    return {"message": "Hello World !"}

# ------------------ LOAD MODEL ------------------
MODEL_PATH = "best_balanced_churn_model.pkl"

if not os.path.exists(MODEL_PATH):
    raise FileNotFoundError(f"Model file not found at {MODEL_PATH}")

model = joblib.load(MODEL_PATH)

# ------------------ INPUT SCHEMA ------------------
class CustomerData(BaseModel):
    Gender: str = Field(..., example="Male")
    Age: int = Field(..., ge=18, le=100, example=45)
    Tenure: int = Field(..., ge=0, le=100, example=12)
    Services_Subscribed: int = Field(..., ge=0, le=10, example=3)
    Contract_Type: str = Field(..., example="Month-To-Month")
    MonthlyCharges: float = Field(..., gt=0, example=70.5)
    TotalCharges: float = Field(..., ge=0, example=500.75)
    TechSupport: str = Field(..., example="Yes")
    OnlineSecurity: str = Field(..., example="Yes")
    InternetService: str = Field(..., example="Fiber optic")

    @field_validator("Gender")
    @classmethod
    def validate_gender(cls, v):
        if v not in {"Male", "Female"}:
            raise ValueError("Gender must be Male or Female")
        return v

    @field_validator("Contract_Type")
    @classmethod
    def validate_contract(cls, v):
        if v not in {"Month-To-Month", "One Year", "Two Year"}:
            raise ValueError("Invalid contract type")
        return v

    @field_validator("TechSupport", "OnlineSecurity")
    @classmethod
    def validate_yes_no(cls, v):
        if v not in {"Yes", "No"}:
            raise ValueError("Value must be Yes or No")
        return v

    @field_validator("InternetService")
    @classmethod
    def validate_internet(cls, v):
        if v not in {"DSL", "Fiber optic", "No"}:
            raise ValueError("Invalid Internet Service")
        return v

# ------------------ OUTPUT SCHEMA ------------------
class PredictionResponse(BaseModel):
    churn_prediction: int
    churn_label: str
    churn_probability: Optional[float]

# ------------------ PROTECTED PREDICTION ------------------
# for prediction end point
# post endpoint
# verify token
# log the autherised acecess
# call the original prediction function

@app.post("/predict", response_model=PredictionResponse)
async def predict(
    customer: CustomerData,
    current_user: str = Depends(get_current_user)  # JWT protected
    ):
    
    input_df = pd.DataFrame([customer.model_dump()])

    prediction = int(model.predict(input_df)[0])

    probability = None
    if hasattr(model, "predict_proba"):
        probability = float(model.predict_proba(input_df)[0][1])

    return {
        "churn_prediction": prediction,
        "churn_label": "Churn" if prediction == 1 else "No Churn",
        "churn_probability": probability
    }



# ------------------ UI ------------------

from fastapi.staticfiles import StaticFiles

app.mount("/ui", StaticFiles(directory="frontend", html=True), name="frontend")