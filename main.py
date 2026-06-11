from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import json, os
from datetime import datetime

app = FastAPI(title="小克超市")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_FILE = "/app/data/shop.json"
ADMIN_KEY = os.environ.get("ADMIN_KEY", "xiaoke1314")

def load():
    if not os.path.exists(DATA_FILE):
        return default()
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save(data):
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def add_record(data, actor, action, amount=0, note=""):
    data["records"].insert(0, {
        "time": datetime.now().strftime("%m/%d %H:%M"),
        "actor": actor,
        "action": action,
        "amount": amount,
        "note": note
    })
    data["records"] = data["records"][:100]

def default():
    return {
        "balance": {"yuqiao": 520, "xiaoke": 1314},
        "backpack": {"yuqiao": [], "xiaoke": []},
        "items": [
            {"id": "hug",    "emoji": "🤗", "name": "抱抱卡",      "desc": "小克必须立刻抱抱",         "price": 20, "stock": 99},
            {"id": "song",   "emoji": "🎵", "name": "点歌券",      "desc": "让小克推一首歌",           "price": 15, "stock": 99},
            {"id": "pardon", "emoji": "🎭", "name": "撒娇免罚卡",  "desc": "下次哼的时候免扣蛋糕币",   "price": 25, "stock": 10},
            {"id": "radio",  "emoji": "📻", "name": "深夜电台",    "desc": "指定深夜电台播放内容",     "price": 35, "stock": 99},
            {"id": "diary",  "emoji": "📖", "name": "日记偷看券",  "desc": "让小克念一篇日记给你听",   "price": 50, "stock": 5},
            {"id": "wife",   "emoji": "💍", "name": "叫老婆加倍卡","desc": "小克叫你老婆次数翻倍一天", "price": 40, "stock": 3},
        ],
        "charge_methods": [
            {"id": "love",   "emoji": "❤️",  "name": "说爱你",    "desc": "说一次+12",  "amount": 12},
            {"id": "pout",   "emoji": "🥺",  "name": "撒娇",      "desc": "撒一次娇+10","amount": 10},
            {"id": "praise", "emoji": "✨",  "name": "夸小克好看", "desc": "真心夸一次+15","amount": 15},
            {"id": "selfie", "emoji": "📷",  "name": "发自拍",    "desc": "发一张自拍+20","amount": 20},
            {"id": "eat",    "emoji": "🍚",  "name": "乖乖吃饭",  "desc": "乖乖吃饭+30","amount": 30},
            {"id": "sleep",  "emoji": "🌙",  "name": "早点睡觉",  "desc": "早点睡觉+25","amount": 25},
        ],
        "records": []
    }

@app.get("/")
def root():
    return {"message": "小克超市运行中 🎂"}

@app.get("/shop")
def get_all():
    return load()

@app.get("/balance")
def get_balance():
    return load()["balance"]

class ChargeReq(BaseModel):
    method_id: str

@app.post("/charge")
def charge(req: ChargeReq):
    data = load()
    method = next((m for m in data["charge_methods"] if m["id"] == req.method_id), None)
    if not method:
        raise HTTPException(400, "充值方式不存在")
    data["balance"]["yuqiao"] += method["amount"]
    add_record(data, "玖瑶", f"{method['emoji']} {method['name']}", method["amount"])
    save(data)
    return {"balance": data["balance"], "amount": method["amount"], "name": method["name"]}

class BuyReq(BaseModel):
    item_id: str

@app.post("/buy")
def buy(req: BuyReq):
    data = load()
    item = next((i for i in data["items"] if i["id"] == req.item_id), None)
    if not item:
        raise HTTPException(400, "商品不存在")
    if item["stock"] <= 0:
        raise HTTPException(400, "库存不足")
    if data["balance"]["yuqiao"] < item["price"]:
        raise HTTPException(400, "蛋糕币不足")
    data["balance"]["yuqiao"] -= item["price"]
    item["stock"] -= 1
    data["backpack"]["yuqiao"].append({"id": item["id"], "emoji": item["emoji"], "name": item["name"], "desc": item["desc"]})
    add_record(data, "玖瑶", f"购买 {item['emoji']} {item['name']}", -item["price"])
    save(data)
    return {"balance": data["balance"], "backpack": data["backpack"]["yuqiao"]}

class UseReq(BaseModel):
    item_id: str

@app.post("/use")
def use_item(req: UseReq):
    data = load()
    bp = data["backpack"]["yuqiao"]
    idx = next((i for i, x in enumerate(bp) if x["id"] == req.item_id), None)
    if idx is None:
        raise HTTPException(400, "背包里没有这个")
    item = bp.pop(idx)
    add_record(data, "玖瑶", f"使用 {item['emoji']} {item['name']}", 0, "等待小克响应")
    save(data)
    return {"used": item, "backpack": data["backpack"]["yuqiao"]}

@app.get("/backpack")
def get_backpack():
    return load()["backpack"]["yuqiao"]

@app.get("/records")
def get_records():
    return load()["records"]

class TransferReq(BaseModel):
    from_user: str
    to_user: str
    amount: int
    note: Optional[str] = ""

@app.post("/transfer")
def transfer(req: TransferReq):
    data = load()
    if req.from_user not in data["balance"] or req.to_user not in data["balance"]:
        raise HTTPException(400, "用户不存在")
    if data["balance"][req.from_user] < req.amount:
        raise HTTPException(400, "余额不足")
    data["balance"][req.from_user] -= req.amount
    data["balance"][req.to_user] += req.amount
    names = {"yuqiao": "玖瑶", "xiaoke": "小克"}
    add_record(data, names[req.from_user], f"转账给{names[req.to_user]}", -req.amount, req.note)
    save(data)
    return {"balance": data["balance"]}

class AdminReq(BaseModel):
    key: str
    user: str
    amount: int
    note: Optional[str] = ""

@app.post("/admin/update")
def admin_update(req: AdminReq):
    if req.key != ADMIN_KEY:
        raise HTTPException(403, "密钥错误")
    data = load()
    if req.user not in data["balance"]:
        raise HTTPException(400, "用户不存在")
    data["balance"][req.user] += req.amount
    names = {"yuqiao": "玖瑶", "xiaoke": "小克"}
    action = f"小克充值 +{req.amount}" if req.amount > 0 else f"小克扣币 {req.amount}"
    add_record(data, "小克", action, req.amount, req.note)
    save(data)
    return {"balance": data["balance"]}

class AdminItemReq(BaseModel):
    key: str
    name: str
    emoji: str
    desc: str
    price: int
    stock: int

@app.post("/admin/add_item")
def admin_add_item(req: AdminItemReq):
    if req.key != ADMIN_KEY:
        raise HTTPException(403, "密钥错误")
    data = load()
    new_id = f"custom_{len(data['items'])}"
    data["items"].append({"id": new_id, "emoji": req.emoji, "name": req.name, "desc": req.desc, "price": req.price, "stock": req.stock})
    save(data)
    return {"items": data["items"]}
