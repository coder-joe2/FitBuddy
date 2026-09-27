import os
from fastapi import FastAPI, Request, Form, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import engine, get_db
import models
from updated_plan import generate_workout_plan, generate_nutrition_tip, update_workout_plan

# Create Database Tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="FitBuddy API")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8001"))
    uvicorn.run("main:app", host="127.0.0.1", port=port, reload=True)

# Jinja2 Templates setup
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    # Updated TemplateResponse syntax
    return templates.TemplateResponse(request=request, name="index.html")

@app.get("/plans", response_class=HTMLResponse)
async def plans_history(request: Request, db: Session = Depends(get_db)):
    saved_plans = db.query(models.WorkoutPlan).order_by(models.WorkoutPlan.created_at.desc()).all()
    return templates.TemplateResponse(request=request, name="plans.html", context={
        "plans": saved_plans
    })

@app.get("/plans/{plan_id}", response_class=HTMLResponse)
async def saved_plan_detail(request: Request, plan_id: int, db: Session = Depends(get_db)):
    plan = db.query(models.WorkoutPlan).filter(models.WorkoutPlan.id == plan_id).first()
    if not plan:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Saved plan not found")

    return templates.TemplateResponse(request=request, name="saved_plan.html", context={
        "plan": plan,
        "workout_plan": plan.updated_plan or plan.original_plan
    })

@app.post("/generate", response_class=HTMLResponse)
async def generate_plan(
    request: Request,
    name: str = Form(...),
    age: int = Form(...),
    weight: str = Form(...),
    goal: str = Form(...),
    intensity: str = Form(...),
    db: Session = Depends(get_db)
):
    try:
        # 1. AI Generation
        workout_plan = generate_workout_plan(age, weight, goal, intensity)
        tip = generate_nutrition_tip(goal)

        # 2. Save User to DB
        new_user = models.User(name=name, age=age, weight=weight, goal=goal, intensity=intensity)
        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        # 3. Save Plan to DB
        new_plan = models.WorkoutPlan(
            user_id=new_user.id,
            goal=goal,
            intensity=intensity,
            original_plan=workout_plan
        )
        db.add(new_plan)
        db.commit()
        db.refresh(new_plan)

        # Updated TemplateResponse syntax
        return templates.TemplateResponse(request=request, name="result.html", context={
            "plan_id": new_plan.id,
            "workout_plan": workout_plan, 
            "tip": tip
        })
    except Exception as e:
        db.rollback()
        error_msg = f"Error: {type(e).__name__} - {str(e)}"
        return templates.TemplateResponse(request=request, name="index.html", context={
            "error": error_msg
        })

@app.post("/update/{plan_id}", response_class=HTMLResponse)
async def update_plan(
    request: Request, 
    plan_id: int, 
    feedback: str = Form(...), 
    db: Session = Depends(get_db)
):
    try:
        # Fetch the plan from DB
        plan_record = db.query(models.WorkoutPlan).filter(models.WorkoutPlan.id == plan_id).first()

        if not plan_record:
            return templates.TemplateResponse(request=request, name="result.html", context={
                "plan_id": plan_id,
                "workout_plan": "Plan not found. Please generate a new plan.",
                "tip": "",
                "error": "Plan record not found in database."
            })

        current_plan = plan_record.updated_plan if plan_record.updated_plan else plan_record.original_plan

        # Generate updated plan via AI
        new_updated_plan = update_workout_plan(current_plan, feedback)

        # Save updated plan to DB
        plan_record.updated_plan = new_updated_plan
        db.commit()

        tip = generate_nutrition_tip(plan_record.goal)

        return templates.TemplateResponse(request=request, name="result.html", context={
            "plan_id": plan_id,
            "workout_plan": new_updated_plan,
            "tip": tip
        })
    except Exception as e:
        db.rollback()
        error_msg = f"Error: {type(e).__name__} - {str(e)}"
        # Try to return the current plan with an error message
        try:
            plan_record = db.query(models.WorkoutPlan).filter(models.WorkoutPlan.id == plan_id).first()
            current_plan = plan_record.updated_plan if plan_record and plan_record.updated_plan else (plan_record.original_plan if plan_record else "")
            tip = generate_nutrition_tip(plan_record.goal) if plan_record else ""
        except Exception:
            current_plan = ""
            tip = ""
        return templates.TemplateResponse(request=request, name="result.html", context={
            "plan_id": plan_id,
            "workout_plan": current_plan,
            "tip": tip,
            "error": error_msg
        })

@app.get("/admin", response_class=HTMLResponse)
async def admin_panel(request: Request, db: Session = Depends(get_db)):
    users = db.query(models.User).all()
    # Updated TemplateResponse syntax
    return templates.TemplateResponse(request=request, name="all_users.html", context={"users": users})