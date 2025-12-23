from pydantic import BaseModel, Field
from typing import List, Optional, Literal

Category = Literal[
    "MEALS", "LODGING", "AIRFARE", "RAIL", "TAXI", "PUBLIC_TRANSIT",
    "MILEAGE", "CLIENT_ENTERTAINMENT", "OFFICE", "TRAINING", "OTHER"
]
MealType = Optional[Literal["BREAKFAST", "LUNCH", "DINNER", "OTHER"]]

class Receipt(BaseModel):
    provided: bool = False
    receipt_id: Optional[str] = None
    file_name: Optional[str] = None
    mime_type: Optional[str] = None

class PreApproval(BaseModel):
    provided: bool = False
    reference: Optional[str] = None

class Attendee(BaseModel):
    name: str
    type: Literal["EMPLOYEE", "EXTERNAL"]
    company: Optional[str] = None

class Mileage(BaseModel):
    km: Optional[float] = None
    start_location: Optional[str] = None
    end_location: Optional[str] = None

class Employee(BaseModel):
    employee_id: str
    name: str
    email: str
    department: str
    manager_id: str
    country: str
    grade: Optional[str] = None
    cost_center: Optional[str] = None
    project_code: Optional[str] = None

class Trip(BaseModel):
    trip_id: Optional[str] = None
    business_purpose: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    destination_city: Optional[str] = None
    destination_country: Optional[str] = None

class Line(BaseModel):
    line_id: str
    date: str
    category: Category
    amount: float = Field(ge=0)
    currency: str = Field(min_length=3, max_length=3)
    vendor: str
    description: str

    meal_type: MealType = None
    attendees: Optional[List[Attendee]] = None
    mileage: Optional[Mileage] = None
    receipt: Optional[Receipt] = None
    preapproval: Optional[PreApproval] = None

class Claim(BaseModel):
    claim_id: str
    submission_date: str
    currency: str = Field(min_length=3, max_length=3)
    employee: Employee
    trip: Optional[Trip] = None
    lines: List[Line]
