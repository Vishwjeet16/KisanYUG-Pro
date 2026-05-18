# =========================================
# KISANYUG COMPLETE BACKEND
# FILE NAME : app.py
# =========================================

from flask import Flask, request, jsonify, session, render_template, redirect
from flask_cors import CORS
from pymongo import MongoClient
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import random

# =========================================
# FLASK APP
# =========================================

app = Flask(__name__)

app.secret_key = "KISANYUG_SECRET_KEY_2026"

# CORS
CORS(
    app,
    supports_credentials=True
)

# =========================================
# MONGODB CONNECTION
# =========================================

client = MongoClient("mongodb://localhost:27017/")

db = client["KisanYUG"]

users_collection = db["users"]

farmerpass_collection = db["farmer_pass"]

crops_collection = db["crops"]

support_collection = db["support_messages"]

orders_collection = db["orders"]

CHATBOT_ANSWERS = [
    {
        "keywords": ["sell", "upload", "crop", "farmer", "bech", "bechna", "fasal", "crop", "appload", "upload"],
        "answer_en": "To sell crops on kisanYUG, create a Farmer Pass first. After approval, open the Sell page, add crop details, upload a photo, and submit it.",
        "answer_hi": "kisanYUG par crop sell karne ke liye pehle Farmer Pass banao. Approval ke baad Sell page open karo, crop details aur photo upload karke submit karo.",
    },
    {
        "keywords": ["farmer pass", "pass", "kisan", "kisaan"],
        "answer_en": "A Farmer Pass verifies that you are a farmer. Log in, open Farmer Pass, fill in your farm and identity details, then submit the form.",
        "answer_hi": "Farmer Pass se verify hota hai ki aap kisan ho. Login karo, Farmer Pass page open karo, farm aur identity details fill karke submit karo.",
    },
    {
        "keywords": ["market", "buy", "product", "vegetable", "fruit", "kharid", "sabji", "phal"],
        "answer_en": "Open the kisanYUG Market page to browse fresh products. You can search, filter categories, add items to cart, and place an order.",
        "answer_hi": "Fresh products kharidne ke liye kisanYUG Market page open karo. Waha search, filter, cart me add aur order place kar sakte ho.",
    },
    {
        "keywords": ["cart", "order", "purchase", "checkout", "khareed", "kharid"],
        "answer_en": "Add products to your cart from the Market page. When you are ready, open the cart and click Purchase to complete the order.",
        "answer_hi": "Market page se product cart me add karo. Jab ready ho, cart open karke Purchase par click karo aur order complete karo.",
    },
    {
        "keywords": ["login", "account", "register", "signup", "sign up", "password"],
        "answer_en": "Use the Login page to access your account. If you are new, create an account with your name, email, phone number, and password.",
        "answer_hi": "Account access karne ke liye Login page use karo. Agar naye user ho to name, email, phone aur password se account create karo.",
    },
    {
        "keywords": ["contact", "support", "help", "problem", "madad", "dikkat", "samasya"],
        "answer_en": "For support, open the Contact Help page and submit the support form. You can also ask me questions about using kisanYUG.",
        "answer_hi": "Support ke liye Contact Help page open karo aur support form submit karo. kisanYUG ke baare me aap mujhse bhi pooch sakte ho.",
    },
    {
        "keywords": ["hello", "hi", "hey", "namaste", "hii"],
        "answer_en": "Hello! I am kisanYUG AI. I can help you with buying products, selling crops, Farmer Pass, orders, and account questions.",
        "answer_hi": "Namaste! Main kisanYUG AI hoon. Main buying, crop selling, Farmer Pass, orders aur account questions me help kar sakta hoon.",
    },
]

HINGLISH_WORDS = [
    "kaise", "kese", "kya", "kyu", "kyun", "mujhe", "mera", "meri", "mere",
    "bata", "bta", "chahiye", "karna", "karo", "h", "hai", "hu", "hoon",
    "nahi", "nahin", "kisan", "kisaan", "fasal", "bechna", "madad", "dikkat"
]


def wants_hinglish_reply(message):

    normalized_message = message.lower()

    if any("\u0900" <= character <= "\u097f" for character in message):

        return True

    return any(word in normalized_message.split() for word in HINGLISH_WORDS)

# =========================================
# HOME ROUTE
# =========================================

@app.route("/")
def home():

    return render_template(
        "index.html",
        has_farmer_pass=current_user_has_farmer_pass()
    )


def current_user_has_farmer_pass():

    if "user_id" not in session:

        return False

    farmer_pass = farmerpass_collection.find_one({
        "user_id": session["user_id"]
    })

    return bool(farmer_pass)


@app.route("/<page_name>.html")
def html_page(page_name):

    allowed_pages = {
        "index",
        "market",
        "sell",
        "orders",
        "kisanMarket",
        "kisanmarket",
        "farmerpass",
        "auth",
        "CreateAccount",
        "forgotpassword",
        "contact_help",
        "services"
    }

    if page_name not in allowed_pages:

        return jsonify({
            "success": False,
            "message": "Page not found"
        }), 404

    if page_name == "kisanmarket":

        page_name = "kisanMarket"

    if page_name in ["sell", "kisanMarket"]:

        if "user_id" not in session:

            return redirect("/auth.html")

        if not current_user_has_farmer_pass():

            return redirect("/farmerpass.html")

    return render_template(
        f"{page_name}.html",
        has_farmer_pass=current_user_has_farmer_pass()
    )


# =========================================
# REGISTER API
# =========================================

@app.route("/register", methods=["POST"])
def register():

    try:

        data = request.json

        name = data.get("name")
        email = data.get("email")
        phone = data.get("phone")
        password = data.get("password")

        # CHECK EMPTY
        if not all([name, email, phone, password]):

            return jsonify({
                "success": False,
                "message": "All fields required"
            })

        # EMAIL EXISTS
        existing_user = users_collection.find_one({
            "email": email
        })

        if existing_user:

            return jsonify({
                "success": False,
                "message": "Email already exists"
            })

        # HASH PASSWORD
        hashed_password = generate_password_hash(password)

        user_data = {

            "name": name,
            "email": email,
            "phone": phone,
            "password": hashed_password,

            "has_farmer_pass": False,

            "created_at": datetime.now()

        }

        users_collection.insert_one(user_data)

        return jsonify({
            "success": True,
            "message": "Account Created Successfully"
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "message": str(e)
        })


# =========================================
# LOGIN API
# =========================================

@app.route("/login", methods=["POST"])
def login():

    try:

        data = request.json

        email = data.get("email")
        password = data.get("password")

        user = users_collection.find_one({
            "email": email
        })

        # USER CHECK
        if not user:

            return jsonify({
                "success": False,
                "message": "User not found"
            })

        # PASSWORD CHECK
        if not check_password_hash(
            user["password"],
            password
        ):

            return jsonify({
                "success": False,
                "message": "Wrong password"
            })

        # SESSION
        session["user_id"] = str(user["_id"])
        session["user_name"] = user["name"]
        session["user_email"] = user["email"]

        return jsonify({

            "success": True,
            "message": "Login Successful",

            "user": {

                "name": user["name"],
                "email": user["email"],
                "phone": user["phone"]

            }

        })

    except Exception as e:

        return jsonify({
            "success": False,
            "message": str(e)
        })


# =========================================
# CHECK LOGIN
# =========================================

@app.route("/check-login", methods=["GET"])
def check_login():

    if "user_id" in session:

        has_farmer_pass = current_user_has_farmer_pass()

        return jsonify({

            "loggedIn": True,
            "hasFarmerPass": has_farmer_pass,

            "user": {

                "name": session.get("user_name"),
                "email": session.get("user_email"),
                "has_farmer_pass": has_farmer_pass

            }

        })

    return jsonify({
        "loggedIn": False,
        "hasFarmerPass": False
    })


# =========================================
# LOGOUT
# =========================================

@app.route("/logout", methods=["POST"])
def logout():

    session.clear()

    return jsonify({
        "success": True,
        "message": "Logout Successful"
    })


# =========================================
# FARMER PASS CREATE
# =========================================

@app.route("/api/farmerpass", methods=["POST"])
def create_farmer_pass():

    try:

        # LOGIN CHECK
        if "user_id" not in session:

            return jsonify({
                "success": False,
                "error": "Please login first"
            })

        # REQUEST DATA
        data = request.json

        # =========================================
        # CHECK EXISTING PASS
        # =========================================

        existing_pass = farmerpass_collection.find_one({
            "user_id": session["user_id"]
        })

        if existing_pass:

            return jsonify({
                "success": False,
                "error": "Farmer Pass already created"
            })

        # =========================================
        # CREATE PASS DATA
        # =========================================

        farmer_pass = {

            "user_id": session["user_id"],

            "name": data.get("name"),
            "village": data.get("village"),
            "crop": data.get("crop"),
            "season": data.get("season"),
            "area": data.get("area"),
            "valid_till": data.get("valid_till"),

            "custom_id":
            data.get("custom_id") or
            f"AGP-{random.randint(100000,999999)}",

            "qr_text": data.get("qr_text"),

            "created_at": datetime.now()

        }

        # SAVE PASS
        farmerpass_collection.insert_one(
            farmer_pass
        )

        # =========================================
        # UPDATE USER STATUS
        # =========================================

        users_collection.update_one(

            {
                "_id": ObjectId(session["user_id"])
            },

            {
                "$set": {
                    "has_farmer_pass": True
                }
            }

        )

        # SUCCESS RESPONSE
        return jsonify({

            "success": True,
            "message": "Farmer Pass Created Successfully",

            "pass_id":
            farmer_pass["custom_id"]

        })

    except Exception as e:

        return jsonify({
            "success": False,
            "error": str(e)
        })


# =========================================
# GET FARMER PASS
# =========================================

@app.route("/api/get-pass/<pass_id>", methods=["GET"])
def get_pass(pass_id):

    farmer = farmerpass_collection.find_one({
        "custom_id": pass_id
    })

    if not farmer:

        return jsonify({
            "success": False,
            "message": "Pass not found"
        })

    farmer["_id"] = str(farmer["_id"])

    return jsonify({
        "success": True,
        "data": farmer
    })


# =========================================
# GET CURRENT USER FARMER PASS
# =========================================

@app.route("/api/my-pass", methods=["GET"])
def my_pass():

    try:

        # LOGIN CHECK
        if "user_id" not in session:

            return jsonify({
                "success": False,
                "message": "Please login first"
            })

        # FIND PASS
        farmer_pass = farmerpass_collection.find_one({
            "user_id": session["user_id"]
        })

        if not farmer_pass:

            return jsonify({
                "success": False,
                "message": "No farmer pass found"
            })

        # OBJECT ID STRING
        farmer_pass["_id"] = str(
            farmer_pass["_id"]
        )

        return jsonify({

            "success": True,
            "pass": farmer_pass

        })

    except Exception as e:

        return jsonify({

            "success": False,
            "message": str(e)

        })

# =========================================
# UPLOAD CROP
# =========================================

@app.route("/api/upload-crop", methods=["POST"])
def upload_crop():

    try:

        # LOGIN REQUIRED
        if "user_id" not in session:

            return jsonify({
                "success": False,
                "message": "Please login first"
            })

        data = request.json

        farmer_pass_id = data.get("farmerPass")

        # CHECK FARMER PASS
        farmer = farmerpass_collection.find_one({
            "custom_id": farmer_pass_id,
            "user_id": session["user_id"]
        })

        if not farmer:

            return jsonify({
                "success": False,
                "message": "Invalid Farmer Pass"
            })

        crop_data = {

            "user_id": session["user_id"],

            "farmerPass": farmer_pass_id,

            "farmerName": data.get("farmerName"),

            "cropName": data.get("cropName"),

            "cropQty": data.get("cropQty"),

            "cropPrice": data.get("cropPrice"),

            "cropVillage": data.get("cropVillage"),

            "cropImage": data.get("cropImage"),

            "created_at": datetime.now()

        }

        crops_collection.insert_one(crop_data)

        return jsonify({

            "success": True,
            "message": "Crop Uploaded Successfully"

        })

    except Exception as e:

        return jsonify({

            "success": False,
            "message": str(e)

        })



# =========================================
# SUPPORT CONTACT API
# =========================================

@app.route("/api/support", methods=["POST"])
def support_message():

    try:

        data = request.json

        full_name = data.get("full_name")
        email = data.get("email")
        inquiry_type = data.get("inquiry_type")
        message = data.get("message")

        # VALIDATION
        if not all([
            full_name,
            email,
            inquiry_type,
            message
        ]):

            return jsonify({

                "success": False,
                "message": "All fields are required"

            })

        # SAVE DATA
        support_data = {

            "full_name": full_name,
            "email": email,
            "inquiry_type": inquiry_type,
            "message": message,
            "created_at": datetime.now()

        }

        support_collection.insert_one(
            support_data
        )

        return jsonify({

            "success": True,
            "message": "Support message sent successfully"

        })

    except Exception as e:

        return jsonify({

            "success": False,
            "message": str(e)

        })


# =========================================
# CHATBOT API
# =========================================

@app.route("/api/chatbot", methods=["POST"])
def chatbot():

    try:

        data = request.json or {}
        user_message = (data.get("message") or "").strip()

        if not user_message:

            return jsonify({
                "success": False,
                "message": "Please type a message."
            }), 400

        normalized_message = user_message.lower()
        reply_language = "answer_hi" if wants_hinglish_reply(user_message) else "answer_en"

        for item in CHATBOT_ANSWERS:

            if any(keyword in normalized_message for keyword in item["keywords"]):

                return jsonify({
                    "success": True,
                    "reply": item[reply_language]
                })

        fallback_reply = (
            "Main kisanYUG marketplace, Farmer Pass, crop selling, orders, login aur support me help kar sakta hoon. Aap apna question simple words me poochiye."
            if reply_language == "answer_hi"
            else "I can help with the kisanYUG marketplace, Farmer Pass, selling crops, orders, login, and support. Please ask your question in simple English."
        )

        return jsonify({
            "success": True,
            "reply": fallback_reply
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


# =========================================
# CROP SERIALIZER
# =========================================

def build_crop_response(query):
    crops = []

    all_crops = crops_collection.find(query).sort(
        "created_at",
        -1
    )

    for crop in all_crops:

        crops.append({

            "_id": str(crop["_id"]),

            "farmerPass":
            crop.get("farmerPass"),

            "farmerName":
            crop.get("farmerName"),

            "cropName":
            crop.get("cropName"),

            "cropQty":
            crop.get("cropQty"),

            "cropPrice":
            crop.get("cropPrice"),

            "cropVillage":
            crop.get("cropVillage"),

            "cropImage":
            crop.get("cropImage")

        })

    return jsonify({

        "success": True,
        "crops": crops

    })


# =========================================
# GET ALL CROPS FOR PUBLIC MARKET
# =========================================

@app.route("/api/crops", methods=["GET"])
def get_crops():

    return build_crop_response({})


# =========================================
# GET CURRENT USER CROPS FOR KISANMARKET
# =========================================

@app.route("/api/my-crops", methods=["GET"])
def get_my_crops():

    if "user_id" not in session:

        return jsonify({
            "success": False,
            "message": "Please login first",
            "crops": []
        }), 401

    return build_crop_response({
        "user_id": session["user_id"]
    })


# =========================================
# CREATE PURCHASE ORDER
# =========================================

@app.route("/api/purchase", methods=["POST"])
def create_purchase():

    try:

        if "user_id" not in session:

            return jsonify({
                "success": False,
                "message": "Please login first"
            })

        data = request.json
        items = data.get("items", [])
        total = data.get("total", 0)

        if not items:

            return jsonify({
                "success": False,
                "message": "Cart is empty"
            })

        order = {

            "user_id": session["user_id"],
            "user_name": session.get("user_name"),
            "user_email": session.get("user_email"),
            "items": items,
            "total": total,
            "status": "placed",
            "created_at": datetime.now()

        }

        result = orders_collection.insert_one(order)

        return jsonify({

            "success": True,
            "message": "Purchase successful",
            "order_id": str(result.inserted_id)

        })

    except Exception as e:

        return jsonify({
            "success": False,
            "message": str(e)
        })


# =========================================
# GET CURRENT USER ORDERS
# =========================================

@app.route("/api/my-orders", methods=["GET"])
def my_orders():

    try:

        if "user_id" not in session:

            return jsonify({
                "success": False,
                "message": "Please login first",
                "orders": []
            })

        orders = []
        user_orders = orders_collection.find({
            "user_id": session["user_id"]
        }).sort("created_at", -1)

        for order in user_orders:

            orders.append({
                "_id": str(order["_id"]),
                "items": order.get("items", []),
                "total": order.get("total", 0),
                "status": order.get("status", "placed"),
                "created_at": order.get("created_at").strftime("%d %b %Y, %I:%M %p")
                if order.get("created_at") else ""
            })

        return jsonify({
            "success": True,
            "orders": orders
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "message": str(e),
            "orders": []
        })


# =========================================
# DELETE CROP
# =========================================

@app.route("/api/delete-crop/<crop_id>", methods=["DELETE"])
def delete_crop(crop_id):

    try:

        if "user_id" not in session:

            return jsonify({
                "success": False,
                "message": "Please login first"
            })

        crop = crops_collection.find_one({
            "_id": ObjectId(crop_id)
        })

        if not crop:

            return jsonify({
                "success": False,
                "message": "Crop not found"
            })

        # ONLY OWNER DELETE
        if crop["user_id"] != session["user_id"]:

            return jsonify({
                "success": False,
                "message": "Unauthorized"
            })

        crops_collection.delete_one({
            "_id": ObjectId(crop_id)
        })

        return jsonify({
            "success": True,
            "message": "Crop Deleted"
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "message": str(e)
        })


# =========================================
# USER PROFILE
# =========================================

@app.route("/api/profile", methods=["GET"])
def profile():

    if "user_id" not in session:

        return jsonify({
            "success": False,
            "message": "Please login"
        })

    user = users_collection.find_one({
        "_id": ObjectId(session["user_id"])
    })

    return jsonify({

        "success": True,

        "user": {

            "name": user["name"],
            "email": user["email"],
            "phone": user["phone"]

        }

    })


# =========================================
# START SERVER
# =========================================

if __name__ == "__main__":

    app.run(
        debug=True,
        port=5000
    )
