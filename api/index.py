from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
import os
import json
import hashlib
import base64
import random
from datetime import datetime

app = FastAPI()

# =========================
# CONFIG
# =========================
DATA_DIR = "data"
OBRAS_FILE = os.path.join(DATA_DIR, "obras.json")
TAGS_FILE = os.path.join(DATA_DIR, "tags.json")
USERS_FILE = os.path.join(DATA_DIR, "users.json")
ADMIN_FILE = os.path.join(DATA_DIR, "admin.json")

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "nugep")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "nugep123")

ANIMAIS = [
    "Águia","Boto","Capivara","Doninha","Ema","Falcão","Gavião","Harpia","Irara","Jaguar",
    "Lontra","Mico","Onça","Paca","Quati","Raposa","Tamanduá","Urubu","Veado","Zorrilho",
    "Arara","Bugio","Caititu","Jaguatirica","Lobo","Mutum","Pirarucu","Tucano","Sucuri","Tatu"
]

ADJETIVOS = [
    "Azul","Bravo","Calmo","Dourado","Esperto","Feroz","Gracioso","Intenso","Jovial","Lento",
    "Mágico","Nobre","Ousado","Preciso","Rápido","Sábio","Tímido","Único","Valente","Zeloso",
    "Curioso","Furtivo","Altivo","Sereno","Vibrante","Audaz","Brilhante","Corajoso","Distinto","Elegante"
]

# =========================
# HELPERS
# =========================
def ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)

def load_json_file(filepath, default):
    ensure_data_dir()
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default
    return default

def save_json_file(filepath, data):
    ensure_data_dir()
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def generate_animal_name():
    return f"{random.choice(ANIMAIS)} {random.choice(ADJETIVOS)}"

def gen_uid():
    return base64.b64encode(os.urandom(12)).decode("ascii")

def check_admin():
    admins = load_json_file(ADMIN_FILE, [])
    if not admins:
        hashed = hashlib.sha256(ADMIN_PASSWORD.encode()).hexdigest()
        save_json_file(ADMIN_FILE, [
            {"id": 1, "username": ADMIN_USERNAME, "password": hashed}
        ])

def check_login(username, password):
    return (
        username == ADMIN_USERNAME and
        hashlib.sha256(password.encode()).hexdigest() ==
        hashlib.sha256(ADMIN_PASSWORD.encode()).hexdigest()
    )

def load_obras():
    default = [
        {
            "id": 1,
            "titulo": "Guernica",
            "artista": "Pablo Picasso",
            "ano": "1937",
            "imagem": "https://upload.wikimedia.org/wikipedia/en/7/74/PicassoGuernica.jpg"
        },
        {
            "id": 2,
            "titulo": "A Noite Estrelada",
            "artista": "Vincent van Gogh",
            "ano": "1889",
            "imagem": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/ea/Van_Gogh_-_Starry_Night_-_Google_Art_Project.jpg/1200px-Van_Gogh_-_Starry_Night_-_Google_Art_Project.jpg"
        },
        {
            "id": 3,
            "titulo": "Mona Lisa",
            "artista": "Leonardo da Vinci",
            "ano": "1503",
            "imagem": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/ec/Mona_Lisa%2C_by_Leonardo_da_Vinci%2C_from_C2RMF_retouched.jpg/800px-Mona_Lisa%2C_by_Leonardo_da_Vinci%2C_from_C2RMF_retouched.jpg"
        }
    ]
    obras = load_json_file(OBRAS_FILE, default)
    if not obras:
        save_json_file(OBRAS_FILE, default)
        return default
    return obras

def save_answers(uid, animal, answers):
    users = load_json_file(USERS_FILE, [])
    users.append({
        "user_id": uid,
        "animal_name": animal,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        **answers
    })
    save_json_file(USERS_FILE, users)

def save_tag(uid, obra_id, tag):
    tags = load_json_file(TAGS_FILE, [])
    tags.append({
        "id": len(tags) + 1,
        "user_id": uid,
        "obra_id": obra_id,
        "tag": tag.lower().strip(),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })
    save_json_file(TAGS_FILE, tags)

def all_tags():
    return load_json_file(TAGS_FILE, [])

def all_users():
    return load_json_file(USERS_FILE, [])

def ntag(tag):
    return tag.lower().strip()

def words(tag):
    return set(ntag(tag).split())

def ngrams(text, n=3):
    t = ntag(text)
    return {t} if len(t) < n else {t[i:i+n] for i in range(len(t)-n+1)}

def sim(t1, t2):
    a, b = ntag(t1), ntag(t2)
    if a == b:
        return 1.0
    if a in b or b in a:
        return 0.55 + 0.45 * (min(len(a), len(b)) / max(len(a), len(b)))
    w1, w2 = words(t1), words(t2)
    if w1 and w2:
        j = len(w1 & w2) / len(w1 | w2)
        if j >= 0.5:
            return j
    if len(a) >= 3 and len(b) >= 3:
        ng1, ng2 = ngrams(a), ngrams(b)
        nj = len(ng1 & ng2) / len(ng1 | ng2) if (ng1 | ng2) else 0
        if nj > 0:
            wj = len(w1 & w2) / len(w1 | w2) if (w1 | w2) else 0
            return 0.6 * nj + 0.4 * wj
    return 0.0

def tag_connections(tags_list, threshold=0.35):
    uniq = list(set(ntag(t) for t in tags_list))
    conns = []
    for i in range(len(uniq)):
        for j in range(i + 1, len(uniq)):
            s = sim(uniq[i], uniq[j])
            if s >= threshold:
                w1, w2 = words(uniq[i]), words(uniq[j])
                shared = w1 & w2
                if uniq[i] in uniq[j] or uniq[j] in uniq[i]:
                    tipo = "Contenção"
                elif shared:
                    tipo = f"Palavra comum: {', '.join(shared)}"
                else:
                    tipo = "Similaridade fonética"
                conns.append({
                    "tag_a": uniq[i],
                    "tag_b": uniq[j],
                    "similaridade": round(s, 3),
                    "tipo": tipo
                })
    conns.sort(key=lambda x: x["similaridade"], reverse=True)
    return conns

# =========================
# STARTUP
# =========================
@app.on_event("startup")
def startup():
    check_admin()
    load_obras()

# =========================
# HTML ÚNICO
# =========================
INDEX_HTML = """
<!DOCTYPE html>
<html lang="pt-br">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Sistema Folksonomia Digital</title>
  <style>
    *{box-sizing:border-box;margin:0;padding:0;font-family:Arial,sans-serif}
    body{
      background:linear-gradient(-45deg,#000,#001f3f,#000,#0b2c56);
      background-size:400% 400%;
      animation:bg 15s ease infinite;
      color:#fff;
      min-height:100vh;
    }
    @keyframes bg{
      0%{background-position:0% 50%}
      50%{background-position:100% 50%}
      100%{background-position:0% 50%}
    }
    .container{max-width:1250px;margin:0 auto;padding:24px}
    .title{
      text-align:center;
      font-size:2.6rem;
      font-weight:800;
      margin-bottom:10px;
    }
    .subtitle{
      text-align:center;
      opacity:.9;
      margin-bottom:24px;
    }
    .card{
      background:rgba(255,255,255,.12);
      border:1px solid rgba(255,255,255,.2);
      border-radius:20px;
      padding:20px;
      backdrop-filter:blur(16px);
      margin-bottom:20px;
      box-shadow:0 12px 30px rgba(0,0,0,.18);
    }
    .grid{
      display:grid;
      grid-template-columns:repeat(auto-fit,minmax(280px,1fr));
      gap:20px;
    }
    .obra img{
      width:100%;
      height:240px;
      object-fit:cover;
      border-radius:14px;
      margin-bottom:12px;
    }
    .obra h3{margin-bottom:6px}
    .obra p{opacity:.8;margin-bottom:10px}
    input, textarea, select{
      width:100%;
      padding:12px;
      border-radius:12px;
      border:1px solid rgba(255,255,255,.18);
      background:rgba(255,255,255,.12);
      color:#fff;
      margin-top:8px;
      margin-bottom:12px;
      outline:none;
    }
    textarea{min-height:120px;resize:vertical}
    button{
      width:100%;
      padding:12px;
      border:none;
      border-radius:12px;
      background:#8ed8ff;
      color:#001f3f;
      font-weight:700;
      cursor:pointer;
      transition:.2s ease;
    }
    button:hover{transform:translateY(-1px);filter:brightness(1.05)}
    .row{
      display:grid;
      grid-template-columns:1fr 1fr;
      gap:16px;
    }
    .small{
      font-size:.9rem;
      opacity:.8;
    }
    .tag-list{
      display:flex;
      flex-wrap:wrap;
      gap:8px;
      margin-top:10px;
    }
    .tag{
      display:inline-block;
      padding:6px 12px;
      border-radius:999px;
      background:rgba(255,255,255,.16);
      border:1px solid rgba(255,255,255,.22);
      font-size:.85rem;
    }
    .topbar{
      display:flex;
      justify-content:space-between;
      align-items:center;
      gap:14px;
      margin-bottom:20px;
      flex-wrap:wrap;
    }
    .pill{
      display:inline-block;
      padding:8px 14px;
      border-radius:999px;
      background:rgba(142,216,255,.15);
      border:1px solid rgba(142,216,255,.35);
      color:#8ed8ff;
      font-weight:700;
    }
    .hidden{display:none}
    .admin-grid{
      display:grid;
      grid-template-columns:repeat(auto-fit,minmax(180px,1fr));
      gap:12px;
      margin-bottom:20px;
    }
    .kpi{
      padding:16px;
      border-radius:16px;
      background:rgba(255,255,255,.09);
      border:1px solid rgba(255,255,255,.15);
      text-align:center;
    }
    .kpi .v{
      font-size:2rem;
      font-weight:800;
      margin-top:6px;
      color:#8ed8ff;
    }
    .divider{
      height:1px;
      background:rgba(255,255,255,.15);
      margin:16px 0;
    }
    .notice{
      margin-top:12px;
      font-size:.92rem;
      opacity:.88;
    }
    @media(max-width:700px){
      .row{grid-template-columns:1fr}
      .title{font-size:2rem}
    }
  </style>
</head>
<body>
  <div class="container">
    <div class="topbar">
      <div style="width:100%">
        <div class="title">Sistema Folksonomia Digital</div>
        <div class="subtitle">Versão única para Vercel / Glitch</div>
      </div>
      <div id="animalPill" class="pill hidden"></div>
    </div>

    <div id="introBox" class="card">
      <h2 style="margin-bottom:14px">Questionário de acesso</h2>
      <div class="row">
        <div>
          <label>1. Qual é o seu nível de familiaridade com museus?</label>
          <select id="q1">
            <option>Nunca visito museus</option>
            <option>Visito raramente</option>
            <option>Visito ocasionalmente</option>
            <option>Visito frequentemente</option>
          </select>

          <label>2. Você já ouviu falar sobre documentação museológica?</label>
          <select id="q2">
            <option>Nunca ouvi falar</option>
            <option>Já ouvi, mas não sei o que é</option>
            <option>Tenho uma ideia básica</option>
            <option>Conheço bem o tema</option>
          </select>
        </div>

        <div>
          <label>3. O que você entende por tags ou etiquetas digitais aplicadas a acervo?</label>
          <textarea id="q3" placeholder="Descreva sua compreensão..."></textarea>
        </div>
      </div>
      <button onclick="enviarQuestionario()">Acessar Plataforma</button>
      <div class="notice">Depois do questionário, você poderá adicionar tags às obras e acessar o painel administrativo.</div>
    </div>

    <div id="galeriaBox" class="hidden">
      <div class="card">
        <h2 style="margin-bottom:10px">Galeria de Obras</h2>
        <p class="small">Explore as obras e contribua com suas tags.</p>
      </div>

      <div id="obrasGrid" class="grid"></div>

      <div class="card" style="margin-top:20px">
        <h2 style="margin-bottom:12px">Área Administrativa</h2>
        <div class="row">
          <div>
            <label>Usuário</label>
            <input id="adminUser" placeholder="Digite o usuário" />
          </div>
          <div>
            <label>Senha</label>
            <input id="adminPass" type="password" placeholder="Digite a senha" />
          </div>
        </div>
        <button onclick="loginAdmin()">Entrar</button>
      </div>

      <div id="adminBox" class="card hidden">
        <h2 style="margin-bottom:12px">Dashboard Administrativo</h2>

        <div class="admin-grid">
          <div class="kpi"><div>Total de Tags</div><div class="v" id="kpiTags">0</div></div>
          <div class="kpi"><div>Tags Únicas</div><div class="v" id="kpiUniques">0</div></div>
          <div class="kpi"><div>Participantes</div><div class="v" id="kpiUsers">0</div></div>
          <div class="kpi"><div>Obras</div><div class="v" id="kpiObras">0</div></div>
        </div>

        <div class="divider"></div>

        <h3 style="margin-bottom:10px">Top Tags</h3>
        <div id="topTags"></div>

        <div class="divider"></div>

        <h3 style="margin-bottom:10px">Conexões entre tags</h3>
        <button onclick="carregarConexoes()">Calcular conexões</button>
        <div id="connections" style="margin-top:14px"></div>
      </div>
    </div>
  </div>

  <script>
    let sessionData = null;
    let obras = [];
    let tagsGlobais = [];
    let questionnaireDone = false;

    async function initSession(){
      const savedSession = localStorage.getItem("folk_session");
      const savedCompleted = localStorage.getItem("folk_completed");

      if(savedSession){
        sessionData = JSON.parse(savedSession);
      } else {
        const res = await fetch("/api/session/new", { method: "POST" });
        sessionData = await res.json();
        localStorage.setItem("folk_session", JSON.stringify(sessionData));
      }

      questionnaireDone = savedCompleted === "true";
      showAnimal();

      if(questionnaireDone){
        document.getElementById("introBox").classList.add("hidden");
        document.getElementById("galeriaBox").classList.remove("hidden");
        await loadObras();
      }
    }

    function showAnimal(){
      const el = document.getElementById("animalPill");
      el.classList.remove("hidden");
      el.innerText = "🐾 " + sessionData.animal_name;
    }

    async function enviarQuestionario(){
      const q1 = document.getElementById("q1").value;
      const q2 = document.getElementById("q2").value;
      const q3 = document.getElementById("q3").value.trim();

      if(!q3){
        alert("Preencha a resposta aberta.");
        return;
      }

      const res = await fetch("/api/answers", {
        method: "POST",
        headers: {"Content-Type":"application/json"},
        body: JSON.stringify({
          user_id: sessionData.user_id,
          animal_name: sessionData.animal_name,
          q1, q2, q3
        })
      });

      if(!res.ok){
        alert("Erro ao salvar questionário.");
        return;
      }

      localStorage.setItem("folk_completed", "true");
      document.getElementById("introBox").classList.add("hidden");
      document.getElementById("galeriaBox").classList.remove("hidden");
      await loadObras();
      alert("Questionário enviado com sucesso.");
    }

    async function loadObras(){
      const res = await fetch("/api/obras");
      obras = await res.json();

      const tagsRes = await fetch("/api/tags");
      tagsGlobais = await tagsRes.json();

      const grid = document.getElementById("obrasGrid");
      grid.innerHTML = "";

      obras.forEach((obra) => {
        const userTags = tagsGlobais.filter(
          t => t.user_id === sessionData.user_id && Number(t.obra_id) === Number(obra.id)
        );

        const grouped = {};
        userTags.forEach(t => {
          grouped[t.tag] = (grouped[t.tag] || 0) + 1;
        });

        const tagsHtml = Object.entries(grouped).map(([tag, count]) =>
          `<span class="tag">${tag} (${count})</span>`
        ).join("");

        const card = document.createElement("div");
        card.className = "card obra";
        card.innerHTML = `
          <img src="${obra.imagem}" alt="${obra.titulo}" />
          <h3>#${obra.id} — ${obra.titulo}</h3>
          <p>${obra.artista} — ${obra.ano}</p>
          <input id="tag-${obra.id}" placeholder="Digite uma tag" />
          <button onclick="enviarTag(${obra.id})">Adicionar Tag</button>
          <div class="tag-list">${tagsHtml || "<span class='small'>Sem tags suas ainda.</span>"}</div>
        `;
        grid.appendChild(card);
      });
    }

    async function enviarTag(obraId){
      const input = document.getElementById(`tag-${obraId}`);
      const tag = input.value.trim();

      if(!tag){
        alert("Digite uma tag.");
        return;
      }

      const res = await fetch("/api/tags", {
        method: "POST",
        headers: {"Content-Type":"application/json"},
        body: JSON.stringify({
          user_id: sessionData.user_id,
          obra_id: obraId,
          tag
        })
      });

      if(!res.ok){
        alert("Erro ao enviar tag.");
        return;
      }

      input.value = "";
      await loadObras();
    }

    async function loginAdmin(){
      const username = document.getElementById("adminUser").value.trim();
      const password = document.getElementById("adminPass").value.trim();

      const res = await fetch("/api/admin/login", {
        method: "POST",
        headers: {"Content-Type":"application/json"},
        body: JSON.stringify({ username, password })
      });

      if(!res.ok){
        alert("Login inválido.");
        return;
      }

      document.getElementById("adminBox").classList.remove("hidden");
      await loadAdmin();
    }

    async function loadAdmin(){
      const [tagsRes, usersRes, obrasRes] = await Promise.all([
        fetch("/api/tags"),
        fetch("/api/users"),
        fetch("/api/obras")
      ]);

      const tags = await tagsRes.json();
      const users = await usersRes.json();
      const obras = await obrasRes.json();

      document.getElementById("kpiTags").innerText = tags.length;
      document.getElementById("kpiUniques").innerText = new Set(tags.map(t => t.tag)).size;
      document.getElementById("kpiUsers").innerText = new Set(users.map(u => u.user_id)).size;
      document.getElementById("kpiObras").innerText = obras.length;

      const counts = {};
      tags.forEach(t => counts[t.tag] = (counts[t.tag] || 0) + 1);

      const top = Object.entries(counts)
        .sort((a,b) => b[1] - a[1])
        .slice(0, 10);

      document.getElementById("topTags").innerHTML = top.length
        ? top.map(([tag, count]) => `<div class="tag" style="margin:4px 6px 4px 0">${tag} (${count})</div>`).join("")
        : "<div class='small'>Sem dados.</div>";
    }

    async function carregarConexoes(){
      const tagsRes = await fetch("/api/tags");
      const tags = await tagsRes.json();
      const lista = tags.map(t => t.tag);

      const res = await fetch("/api/connections", {
        method: "POST",
        headers: {"Content-Type":"application/json"},
        body: JSON.stringify({
          tags: lista,
          threshold: 0.35
        })
      });

      const conns = await res.json();
      const box = document.getElementById("connections");

      if(!conns.length){
        box.innerHTML = "<div class='small'>Nenhuma conexão encontrada.</div>";
        return;
      }

      box.innerHTML = conns.slice(0, 20).map(c => `
        <div style="padding:10px;border-radius:12px;background:rgba(255,255,255,.08);margin-bottom:8px">
          <strong>${c.tag_a}</strong> ↔ <strong>${c.tag_b}</strong><br/>
          <span class="small">Similaridade: ${c.similaridade} | ${c.tipo}</span>
        </div>
      `).join("");
    }

    initSession();
  </script>
</body>
</html>
"""

# =========================
# ROTAS
# =========================
@app.get("/", response_class=HTMLResponse)
def home():
    return HTMLResponse(INDEX_HTML)

@app.post("/api/session/new")
def create_session():
    return {
        "user_id": gen_uid(),
        "animal_name": generate_animal_name()
    }

@app.get("/api/obras")
def get_obras():
    return load_obras()

@app.get("/api/tags")
def get_tags():
    return all_tags()

@app.get("/api/users")
def get_users():
    return all_users()

@app.post("/api/answers")
async def post_answers(request: Request):
    payload = await request.json()
    required = ["user_id", "animal_name", "q1", "q2", "q3"]
    for key in required:
        if key not in payload:
            raise HTTPException(status_code=400, detail=f"Campo ausente: {key}")

    save_answers(payload["user_id"], payload["animal_name"], {
        "q1": payload["q1"],
        "q2": payload["q2"],
        "q3": payload["q3"]
    })
    return {"ok": True}

@app.post("/api/tags")
async def post_tag(request: Request):
    payload = await request.json()
    required = ["user_id", "obra_id", "tag"]
    for key in required:
        if key not in payload:
            raise HTTPException(status_code=400, detail=f"Campo ausente: {key}")

    save_tag(payload["user_id"], int(payload["obra_id"]), payload["tag"])
    return {"ok": True}

@app.post("/api/admin/login")
async def admin_login(request: Request):
    payload = await request.json()
    username = payload.get("username", "")
    password = payload.get("password", "")

    if not check_login(username, password):
        raise HTTPException(status_code=401, detail="Credenciais inválidas")

    return {"ok": True}

@app.post("/api/connections")
async def post_connections(request: Request):
    payload = await request.json()
    tags = payload.get("tags", [])
    threshold = float(payload.get("threshold", 0.35))
    return tag_connections(tags, threshold)
