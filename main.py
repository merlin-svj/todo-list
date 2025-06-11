from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import json
import hashlib

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change this to specific domains in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

templates = Jinja2Templates(directory="templates")

def get_users():
    try:
        with open('user.json') as f:
            return json.load(f)
    except:
        return {}

def set_user(username, password):
    users = get_users()
    users[username] = hashlib.sha256(password.encode()).hexdigest()
    with open('user.json', 'w') as f:
        json.dump(users, f)

def verify_user(username, password):
    users = get_users()
    hashed = hashlib.sha256(password.encode()).hexdigest()
    return username in users and users[username] == hashed

def is_logged_in(request: Request):
    return request.cookies.get("logged_in") == "yes" and request.cookies.get("username") is not None

def get_current_username(request: Request):
    if is_logged_in(request):
        return request.cookies.get("username")
    return None

def get_todo_file(username):
    return f"todos_{username}.json"

@app.get("/register")
def register_page(request: Request):
    if is_logged_in(request):
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse("register.html", {"request": request})

@app.post("/register")
async def register(request: Request):
    if is_logged_in(request):
        return RedirectResponse("/", status_code=303)
    form = await request.form()
    username = form["username"]
    password = form["password"]
    users = get_users()
    if username in users:
        return templates.TemplateResponse("register.html", {"request": request, "error": "Username already exists"})
    set_user(username, password)
    response = RedirectResponse("/login", status_code=303)
    return response

@app.get("/login")
def login_page(request: Request):
    if is_logged_in(request):
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse("login.html", {"request": request, "error": ""})

@app.post("/login")
async def login(request: Request):
    if is_logged_in(request):
        return RedirectResponse("/", status_code=303)
    form = await request.form()
    username = form["username"]
    password = form["password"]
    if verify_user(username, password):
        response = RedirectResponse("/", status_code=303)
        response.set_cookie("logged_in", "yes")
        response.set_cookie("username", username)
        return response
    else:
        return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid credentials"})

@app.get("/logout")
def logout(request: Request):
    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie("logged_in")
    response.delete_cookie("username")
    return response

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    if not is_logged_in(request):
        return RedirectResponse("/login", status_code=303)
    username = get_current_username(request)
    todo_file = get_todo_file(username)
    try:
        with open(todo_file) as f:
            data = json.load(f)
    except:
        data = {}
    # Sort tasks by priority (convert to int for correct sorting)
    sorted_items = sorted(
        data.items(),
        key=lambda item: int(item[1].get("priority", 9999))
    )
    sorted_data = {k: v for k, v in sorted_items}
    return templates.TemplateResponse("todolist.html", {"request": request, "tododict": sorted_data})

@app.get("/delete/{id}")
async def delete_todo(request: Request, id: str):
    if not is_logged_in(request):
        return RedirectResponse("/login", status_code=303)
    username = get_current_username(request)
    todo_file = get_todo_file(username)
    try:
        with open(todo_file) as f:
            data = json.load(f)
    except:
        data = {}
    if id in data:
        del data[id]
        with open(todo_file, 'w') as f:
            json.dump(data, f)
    return RedirectResponse("/", 303)

@app.post("/add")
async def add_todo(request: Request):
    if not is_logged_in(request):
        return RedirectResponse("/login", status_code=303)
    username = get_current_username(request)
    todo_file = get_todo_file(username)
    try:
        with open(todo_file) as f:
            data = json.load(f)
    except:
        data = {}
    formdata = await request.form()
    newdata = {}
    i = 1
    for id in data:
        newdata[str(i)] = data[id]
        i += 1
    newdata[str(i)] = {
        "name": formdata["newtodo"],
        "priority": formdata["priority"]
    }
    with open(todo_file, 'w') as f:
        json.dump(newdata, f)
    return RedirectResponse("/", 303)