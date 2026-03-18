from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
import os
import json
import hashlib
import base64
import random
from datetime import datetime

app = FastAPI()

DATA_DIR = "data"
OBRAS_FILE = os.path.join(DATA_DIR, "obras.json")
TAGS_FILE = os.path.join(DATA_DIR, "tags.json")
USERS_FILE = os.path.join(DATA_DIR, "users.json")

ADMIN_USERNAME = "nugep"
ADMIN_PASSWORD = "nugep123"

ANIMAIS = ["Águia","Boto","Capivara","Doninha","Ema","Falcão","Gavião"]
ADJETIVOS = ["Azul","Bravo","Calmo","Dourado","Esperto","Feroz"]

def ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)

def load_json(path, default):
    ensure_data_dir()
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default

def save_json(path, data):
    ensure_data_dir()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def gen_uid():
    return base64.b64encode(os.urandom(10)).decode()

def animal():
    return random.choice(ANIMAIS) + " " + random.choice(ADJETIVOS)

def load_obras():
    default = [
        {"id":1,"titulo":"Guernica","artista":"Picasso","ano":"1937",
        "imagem":"https://upload.wikimedia.org/wikipedia/en/7/74/PicassoGuernica.jpg"},
        {"id":2,"titulo":"Noite Estrelada","artista":"Van Gogh","ano":"1889",
        "imagem":"https://upload.wikimedia.org/wikipedia/commons/thumb/e/ea/Van_Gogh_-_Starry_Night.jpg/800px-Van_Gogh_-_Starry_Night.jpg"}
    ]
    data = load_json(OBRAS_FILE, default)
    if not data:
        save_json(OBRAS_FILE, default)
        return default
    return data

# =========================
# HTML
# =========================

HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Folksonomia</title>
<style>
body{background:#001f3f;color:white;font-family:Arial;padding:30px}
.card{background:#0b223d;padding:20px;border-radius:12px;margin-bottom:20px}
input{padding:10px;width:100%;margin:10px 0}
button{padding:10px;width:100%;cursor:pointer}
img{width:100%;border-radius:10px}
</style>
</head>
<body>

<h1>Sistema Folksonomia</h1>

<div id="app"></div>

<script>
let user=null

async function start(){
  let saved=localStorage.getItem("user")
  if(saved){
    user=JSON.parse(saved)
    show()
  }else{
    let res=await fetch("/api/session",{method:"POST"})
    user=await res.json()
    localStorage.setItem("user",JSON.stringify(user))
    show()
  }
}

async function show(){
  let res=await fetch("/api/obras")
  let obras=await res.json()

  let html=""
  obras.forEach(o=>{
    html+=`
    <div class="card">
      <img src="${o.imagem}">
      <h3>${o.titulo}</h3>
      <input id="tag${o.id}" placeholder="tag">
      <button onclick="send(${o.id})">enviar</button>
    </div>`
  })

  document.getElementById("app").innerHTML=html
}

async function send(id){
  let tag=document.getElementById("tag"+id).value
  await fetch("/api/tag",{method:"POST",
  headers:{"Content-Type":"application/json"},
  body:JSON.stringify({user:user.user_id,obra:id,tag})})
  alert("ok")
}

start()
</script>

</body>
</html>
"""

# =========================
# ROTAS
# =========================

@app.get("/", response_class=HTMLResponse)
def home():
    return HTML

@app.post("/api/session")
def session():
    return {"user_id": gen_uid(), "animal": animal()}

@app.get("/api/obras")
def obras():
    return load_obras()

@app.post("/api/tag")
async def tag(request: Request):
    data = await request.json()
    tags = load_json(TAGS_FILE, [])
    tags.append(data)
    save_json(TAGS_FILE, tags)
    return {"ok": True}
