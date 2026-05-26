# =========================================
# KISANYUG COMPLETE BACKEND
# FILE NAME : app.py
# =========================================

from flask import Flask, request, jsonify, session, render_template, redirect
from flask_cors import CORS
from pymongo import MongoClient
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
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

mandi_listings_collection = db["mandi_listings"]

mandi_bids_collection = db["mandi_bids"]

mandi_buyers_collection = db["mandi_buyers"]

mandi_live_rooms_collection = db["mandi_live_rooms"]

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


def current_user_has_mandi_buyer_pass():

    if "user_id" not in session:

        return False

    buyer_pass = mandi_buyers_collection.find_one({
        "user_id": session["user_id"],
        "status": "active"
    })

    return bool(buyer_pass)


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
        "services",
        "mandi_sell",
        "mandi_buyer"
    }

    if page_name not in allowed_pages:

        return jsonify({
            "success": False,
            "message": "Page not found"
        }), 404

    if page_name == "kisanmarket":

        page_name = "kisanMarket"

    if page_name in ["sell", "kisanMarket", "mandi_sell"]:

        if "user_id" not in session:

            return redirect("/auth.html")

        if current_user_has_mandi_buyer_pass():

            return redirect("/mandi_buyer.html")

        if not current_user_has_farmer_pass():

            return redirect("/farmerpass.html")

    if page_name == "farmerpass":

        if current_user_has_mandi_buyer_pass():

            return redirect("/mandi_buyer.html")

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

        if not user.get("password"):

            return jsonify({
                "success": False,
                "message": "This account uses Google login. Please continue with Google."
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
        has_mandi_buyer_pass = current_user_has_mandi_buyer_pass()

        return jsonify({

            "loggedIn": True,
            "hasFarmerPass": has_farmer_pass,
            "hasMandiBuyerPass": has_mandi_buyer_pass,
            "role": "farmer" if has_farmer_pass else "mandi_buyer" if has_mandi_buyer_pass else "customer",

            "user": {

                "name": session.get("user_name"),
                "email": session.get("user_email"),
                "has_farmer_pass": has_farmer_pass,
                "has_mandi_buyer_pass": has_mandi_buyer_pass

            }

        })

    return jsonify({
        "loggedIn": False,
        "hasFarmerPass": False,
        "hasMandiBuyerPass": False,
        "role": "guest"
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

        if current_user_has_mandi_buyer_pass():

            return jsonify({
                "success": False,
                "error": "Is account par Mandi Buyer Pass active hai. Buyer account se Kisan/Farmer Pass nahi ban sakta."
            }), 403

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

        if current_user_has_mandi_buyer_pass():

            return jsonify({
                "success": False,
                "message": "Mandi Buyer account se crop upload nahi ho sakti. Crop sell karne ke liye alag Kisan/Farmer account use karein."
            }), 403

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


@app.route("/google-login", methods=["POST"])
def google_login():

    try:

        data = request.json or {}

        name = data.get("name")
        email = data.get("email")

        if not email:

            return jsonify({
                "success": False,
                "message": "Google account email not found"
            }), 400

        user = users_collection.find_one({
            "email": email
        })

        if not user:

            user_data = {

                "name": name or email.split("@")[0],
                "email": email,
                "phone": "",
                "password": "",
                "auth_provider": "google",
                "has_farmer_pass": False,
                "created_at": datetime.now()

            }

            result = users_collection.insert_one(user_data)

            user_data["_id"] = result.inserted_id

            user = user_data

        session["user_id"] = str(user["_id"])
        session["user_name"] = user.get("name") or name or email.split("@")[0]
        session["user_email"] = user["email"]

        return jsonify({

            "success": True,
            "message": "Google Login Successful",

            "user": {

                "name": session["user_name"],
                "email": session["user_email"],
                "phone": user.get("phone", "")

            }

        })

    except Exception as e:

        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


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
# MANDI SELLING AND LIVE BIDDING
# =========================================

def clean_crop_key(crop_name):

    return " ".join(str(crop_name or "").lower().strip().split())


def finalize_expired_mandi_listing(listing):

    if not listing or listing.get("status") != "open":

        return listing

    auction_ends_at = listing.get("auction_ends_at")

    if (
        auction_ends_at and
        datetime.now() >= auction_ends_at and
        listing.get("highest_bid") and
        listing.get("highest_buyer_token")
    ):

        mandi_listings_collection.update_one({
            "_id": listing["_id"]
        }, {
            "$set": {
                "status": "sold",
                "sold_at": datetime.now(),
                "sold_to": listing.get("highest_buyer"),
                "sold_to_token": listing.get("highest_buyer_token"),
                "sold_amount": listing.get("highest_bid")
            }
        })

        listing["status"] = "sold"
        listing["sold_at"] = datetime.now()
        listing["sold_to"] = listing.get("highest_buyer")
        listing["sold_to_token"] = listing.get("highest_buyer_token")
        listing["sold_amount"] = listing.get("highest_bid")

    return listing


def serialize_mandi_listing(listing, include_bids=False):

    listing = finalize_expired_mandi_listing(listing)
    highest_bid = listing.get("highest_bid")
    rejected_until = listing.get("rejected_until")
    auction_ends_at = listing.get("auction_ends_at")
    remaining_seconds = 0

    if listing.get("status") == "open" and auction_ends_at:

        remaining_seconds = max(
            0,
            int((auction_ends_at - datetime.now()).total_seconds())
        )

    data = {
        "_id": str(listing["_id"]),
        "user_id": listing.get("user_id"),
        "farmerPass": listing.get("farmerPass"),
        "farmerName": listing.get("farmerName"),
        "cropName": listing.get("cropName"),
        "cropKey": listing.get("cropKey"),
        "cropPhoto": listing.get("cropPhoto", ""),
        "quantity": listing.get("quantity"),
        "quality": listing.get("quality"),
        "expectedPrice": listing.get("expectedPrice"),
        "mandiArea": listing.get("mandiArea"),
        "mandiName": listing.get("mandiName"),
        "village": listing.get("village"),
        "address": listing.get("address"),
        "mapLat": listing.get("mapLat"),
        "mapLng": listing.get("mapLng"),
        "tokenNumber": listing.get("tokenNumber"),
        "tokenDate": listing.get("tokenDate"),
        "status": listing.get("status", "open"),
        "highestBid": highest_bid,
        "highestBuyer": listing.get("highest_buyer"),
        "highestBuyerToken": listing.get("highest_buyer_token"),
        "bidCount": listing.get("bid_count", 0),
        "auctionEndsAt": auction_ends_at.isoformat() if auction_ends_at else "",
        "auctionRemainingSeconds": remaining_seconds,
        "auctionStarted": bool(auction_ends_at),
        "soldTo": listing.get("sold_to"),
        "soldToToken": listing.get("sold_to_token"),
        "soldAmount": listing.get("sold_amount"),
        "serverNow": datetime.now().isoformat(),
        "created_at": listing.get("created_at").strftime("%d %b %Y, %I:%M %p")
        if listing.get("created_at") else "",
        "rejected_until": rejected_until.strftime("%d %b %Y")
        if rejected_until else ""
    }

    if include_bids:

        bids = []
        listing_bids = mandi_bids_collection.find({
            "listing_id": str(listing["_id"])
        }).sort("created_at", -1)

        for bid in listing_bids:

            bids.append({
                "_id": str(bid["_id"]),
                "buyerName": bid.get("buyerName"),
                "buyerToken": bid.get("buyerToken"),
                "buyerPhone": bid.get("buyerPhone"),
                "amount": bid.get("amount"),
                "message": bid.get("message"),
                "created_at": bid.get("created_at").strftime("%d %b %Y, %I:%M %p")
                if bid.get("created_at") else ""
            })

        data["bids"] = bids

    return data


def serialize_buyer_pass(buyer_pass):

    return {
        "_id": str(buyer_pass["_id"]),
        "buyerName": buyer_pass.get("buyerName"),
        "buyerPhone": buyer_pass.get("buyerPhone"),
        "mandiArea": buyer_pass.get("mandiArea"),
        "mandiName": buyer_pass.get("mandiName"),
        "licenseNumber": buyer_pass.get("licenseNumber"),
        "custom_id": buyer_pass.get("custom_id"),
        "status": buyer_pass.get("status", "active"),
        "created_at": buyer_pass.get("created_at").strftime("%d %b %Y, %I:%M %p")
        if buyer_pass.get("created_at") else ""
    }


def get_room_buyer_count(listing_id):

    bids = mandi_bids_collection.find({
        "listing_id": listing_id
    })

    buyer_tokens = set()

    for bid in bids:

        if bid.get("buyerToken"):

            buyer_tokens.add(bid.get("buyerToken"))

    room = mandi_live_rooms_collection.find_one({
        "listing_id": listing_id
    })

    if room:

        for buyer in room.get("buyers", []):

            if buyer.get("buyerToken"):

                buyer_tokens.add(buyer.get("buyerToken"))

    return len(buyer_tokens)


@app.route("/api/mandi-buyer-pass", methods=["POST"])
def create_mandi_buyer_pass():

    try:

        if "user_id" not in session:

            return jsonify({
                "success": False,
                "message": "Mandi Buyer Pass banane ke liye pehle buyer account se login karein."
            }), 401

        if "user_id" in session and current_user_has_farmer_pass():

            return jsonify({
                "success": False,
                "message": "Jis account par Kisan/Farmer Pass active hai, us account se Mandi Buyer Pass nahi ban sakta."
            }), 403

        data = request.json or {}
        buyer_name = data.get("buyerName")
        buyer_phone = data.get("buyerPhone")
        mandi_area = data.get("mandiArea")
        mandi_name = data.get("mandiName")
        license_number = data.get("licenseNumber")

        if not all([buyer_name, buyer_phone, mandi_area, mandi_name]):

            return jsonify({
                "success": False,
                "message": "Buyer name, phone, mandi area aur mandi name required hai."
            })

        existing_pass = mandi_buyers_collection.find_one({
            "user_id": session["user_id"],
            "status": "active"
        })

        if existing_pass:

            return jsonify({
                "success": True,
                "message": "Is phone par buyer pass already active hai.",
                "buyerPass": serialize_buyer_pass(existing_pass)
            })

        buyer_pass = {
            "user_id": session["user_id"],
            "user_email": session.get("user_email"),
            "buyerName": buyer_name,
            "buyerPhone": buyer_phone,
            "mandiArea": mandi_area,
            "mandiName": mandi_name,
            "licenseNumber": license_number or "",
            "custom_id": data.get("custom_id") or f"MBP-{random.randint(100000,999999)}",
            "status": "active",
            "created_at": datetime.now()
        }

        result = mandi_buyers_collection.insert_one(buyer_pass)
        buyer_pass["_id"] = result.inserted_id

        return jsonify({
            "success": True,
            "message": "Mandi Buyer Pass ban gaya. Ab aap live room join karke bid kar sakte hain.",
            "buyerPass": serialize_buyer_pass(buyer_pass)
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "message": str(e)
        })


@app.route("/api/mandi-buyer-pass/<pass_id>", methods=["GET"])
def get_mandi_buyer_pass(pass_id):

    buyer_pass = mandi_buyers_collection.find_one({
        "custom_id": pass_id,
        "status": "active"
    })

    if not buyer_pass:

        return jsonify({
            "success": False,
            "message": "Buyer Pass nahi mila."
        }), 404

    return jsonify({
        "success": True,
        "buyerPass": serialize_buyer_pass(buyer_pass)
    })


@app.route("/api/my-mandi-buyer-pass", methods=["GET"])
def get_my_mandi_buyer_pass():

    if "user_id" not in session:

        return jsonify({
            "success": False,
            "message": "Please login first"
        }), 401

    buyer_pass = mandi_buyers_collection.find_one({
        "user_id": session["user_id"],
        "status": "active"
    })

    if not buyer_pass:

        return jsonify({
            "success": False,
            "message": "No Mandi Buyer Pass found"
        })

    return jsonify({
        "success": True,
        "buyerPass": serialize_buyer_pass(buyer_pass)
    })


@app.route("/api/mandi-listings/<listing_id>/live-room", methods=["GET"])
def get_mandi_live_room(listing_id):

    try:

        listing = mandi_listings_collection.find_one({
            "_id": ObjectId(listing_id)
        })

        listing = finalize_expired_mandi_listing(listing)

        if not listing:

            return jsonify({
                "success": False,
                "message": "Listing not found"
            }), 404

        room = mandi_live_rooms_collection.find_one({
            "listing_id": listing_id
        }) or {}

        buyers = room.get("buyers", [])

        return jsonify({
            "success": True,
            "listing": serialize_mandi_listing(listing, include_bids=True),
            "room": {
                "listing_id": listing_id,
                "farmerLive": bool(room.get("farmerLive")),
                "buyers": buyers,
                "buyerCount": len(buyers),
                "minBuyers": 4,
                "maxBuyers": 8
            }
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "message": str(e)
        })


@app.route("/api/mandi-listings/<listing_id>/live-room/join", methods=["POST"])
def join_mandi_live_room(listing_id):

    try:

        data = request.json or {}
        role = data.get("role")

        listing = mandi_listings_collection.find_one({
            "_id": ObjectId(listing_id),
            "status": "open"
        })

        listing = finalize_expired_mandi_listing(listing)

        if not listing or listing.get("status") != "open":

            return jsonify({
                "success": False,
                "message": "Live room ab available nahi hai."
            })

        if role == "farmer":

            if "user_id" not in session or listing.get("user_id") != session["user_id"]:

                return jsonify({
                    "success": False,
                    "message": "Sirf crop owner farmer camera room start kar sakta hai."
                }), 401

            mandi_live_rooms_collection.update_one({
                "listing_id": listing_id
            }, {
                "$set": {
                    "listing_id": listing_id,
                    "farmerLive": True,
                    "farmerName": listing.get("farmerName"),
                    "updated_at": datetime.now()
                },
                "$setOnInsert": {
                    "buyers": [],
                    "created_at": datetime.now()
                }
            }, upsert=True)

            return jsonify({
                "success": True,
                "message": "Farmer live camera room active ho gaya."
            })

        if role == "buyer":

            if "user_id" not in session:

                return jsonify({
                    "success": False,
                    "message": "Live room join karne ke liye Mandi Buyer account se login karein."
                }), 401

            buyer_token = data.get("buyerToken")
            buyer_pass = mandi_buyers_collection.find_one({
                "custom_id": buyer_token,
                "user_id": session["user_id"],
                "status": "active"
            })

            if not buyer_pass:

                return jsonify({
                    "success": False,
                    "message": "Valid Mandi Buyer Pass required hai."
                })

            if buyer_pass.get("mandiArea") != listing.get("mandiArea"):

                return jsonify({
                    "success": False,
                    "message": "Buyer pass isi mandi area ka hona chahiye."
                })

            current_count = get_room_buyer_count(listing_id)
            already_joined = mandi_live_rooms_collection.find_one({
                "listing_id": listing_id,
                "buyers.buyerToken": buyer_token
            })

            if current_count >= 8 and not already_joined:

                return jsonify({
                    "success": False,
                    "message": "Is live room me 8 buyers already join ho chuke hain."
                })

            buyer_room_data = {
                "buyerName": buyer_pass.get("buyerName"),
                "buyerToken": buyer_pass.get("custom_id"),
                "mandiName": buyer_pass.get("mandiName"),
                "joined_at": datetime.now().strftime("%d %b %Y, %I:%M %p")
            }

            mandi_live_rooms_collection.update_one({
                "listing_id": listing_id
            }, {
                "$set": {
                    "listing_id": listing_id,
                    "updated_at": datetime.now()
                },
                "$addToSet": {
                    "buyers": buyer_room_data
                },
                "$setOnInsert": {
                    "farmerLive": False,
                    "created_at": datetime.now()
                }
            }, upsert=True)

            return jsonify({
                "success": True,
                "message": "Buyer live bidding room me join ho gaya."
            })

        return jsonify({
            "success": False,
            "message": "Role farmer ya buyer hona chahiye."
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "message": str(e)
        })


@app.route("/api/mandi-listings", methods=["POST"])
def create_mandi_listing():

    try:

        if "user_id" not in session:

            return jsonify({
                "success": False,
                "message": "Please login first"
            }), 401

        if current_user_has_mandi_buyer_pass():

            return jsonify({
                "success": False,
                "message": "Mandi Buyer account se crop sell nahi ho sakti. Crop sell karne ke liye alag Kisan/Farmer account use karein."
            }), 403

        data = request.json or {}
        farmer_pass_id = data.get("farmerPass")
        crop_name = data.get("cropName")
        mandi_area = data.get("mandiArea")
        crop_key = clean_crop_key(crop_name)

        required_fields = [
            farmer_pass_id,
            data.get("farmerName"),
            crop_name,
            data.get("quantity"),
            data.get("expectedPrice"),
            mandi_area,
            data.get("mandiName")
        ]

        if not all(required_fields):

            return jsonify({
                "success": False,
                "message": "All required fields fill karein"
            })

        farmer = farmerpass_collection.find_one({
            "custom_id": farmer_pass_id,
            "user_id": session["user_id"]
        })

        if not farmer:

            return jsonify({
                "success": False,
                "message": "Invalid Farmer Pass"
            })

        now = datetime.now()

        active_crop = mandi_listings_collection.find_one({
            "user_id": session["user_id"],
            "cropKey": crop_key,
            "status": {
                "$in": ["open", "accepted"]
            }
        })

        if active_crop:

            return jsonify({
                "success": False,
                "message": "Ye crop already ek mandi/area me active hai. Same crop dusre area me upload nahi ho sakti."
            })

        rejected_crop = mandi_listings_collection.find_one({
            "user_id": session["user_id"],
            "cropKey": crop_key,
            "status": "rejected",
            "rejected_until": {
                "$gt": now
            }
        })

        if rejected_crop:

            return jsonify({
                "success": False,
                "message": "Offer reject hone ke baad is crop ka token 8 din ke liye hold par hai.",
                "rejected_until": rejected_crop["rejected_until"].strftime("%d %b %Y")
            })

        token_date = now.strftime("%Y-%m-%d")
        used_tokens = mandi_listings_collection.count_documents({
            "mandiArea": mandi_area,
            "tokenDate": token_date
        })

        if used_tokens >= 50:

            return jsonify({
                "success": False,
                "message": "Is area ki aaj ki 50 token limit complete ho gayi hai."
            })

        token_number = used_tokens + 1
        listing = {
            "user_id": session["user_id"],
            "farmerPass": farmer_pass_id,
            "farmerName": data.get("farmerName"),
            "cropName": crop_name,
            "cropKey": crop_key,
            "cropPhoto": data.get("cropPhoto", ""),
            "quantity": data.get("quantity"),
            "quality": data.get("quality", ""),
            "expectedPrice": data.get("expectedPrice"),
            "mandiArea": mandi_area,
            "mandiName": data.get("mandiName"),
            "village": data.get("village", ""),
            "address": data.get("address", ""),
            "mapLat": data.get("mapLat", ""),
            "mapLng": data.get("mapLng", ""),
            "tokenNumber": token_number,
            "tokenDate": token_date,
            "status": "open",
            "highest_bid": 0,
            "highest_buyer": "",
            "highest_buyer_token": "",
            "auction_ends_at": None,
            "bid_count": 0,
            "created_at": now
        }

        result = mandi_listings_collection.insert_one(listing)
        listing["_id"] = result.inserted_id

        return jsonify({
            "success": True,
            "message": f"Crop mandi bidding ke liye live ho gayi. Token #{token_number}",
            "listing": serialize_mandi_listing(listing)
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "message": str(e)
        })


@app.route("/api/mandi-listings", methods=["GET"])
def get_mandi_listings():

    listings = []
    query = {
        "status": "open"
    }

    mandi_area = request.args.get("area")

    if mandi_area:

        query["mandiArea"] = mandi_area

    for listing in mandi_listings_collection.find(query).sort([
        ("tokenDate", -1),
        ("mandiArea", 1),
        ("tokenNumber", 1)
    ]):

        listing = finalize_expired_mandi_listing(listing)

        if listing.get("status") == "open":

            listings.append(serialize_mandi_listing(listing))

    return jsonify({
        "success": True,
        "listings": listings
    })


@app.route("/api/my-mandi-listings", methods=["GET"])
def get_my_mandi_listings():

    if "user_id" not in session:

        return jsonify({
            "success": False,
            "message": "Please login first",
            "listings": []
        }), 401

    listings = []

    for listing in mandi_listings_collection.find({
        "user_id": session["user_id"]
    }).sort("created_at", -1):

        listings.append(serialize_mandi_listing(listing, include_bids=True))

    return jsonify({
        "success": True,
        "listings": listings
    })


@app.route("/api/mandi-listings/<listing_id>/bid", methods=["POST"])
def create_mandi_bid(listing_id):

    try:

        if "user_id" not in session:

            return jsonify({
                "success": False,
                "message": "Bid karne ke liye Mandi Buyer account se login karein."
            }), 401

        if current_user_has_farmer_pass():

            return jsonify({
                "success": False,
                "message": "Kisan/Farmer account se bidding nahi ho sakti. Mandi Buyer ke liye alag account use karein."
            }), 403

        data = request.json or {}
        buyer_name = data.get("buyerName")
        buyer_token = data.get("buyerToken")
        buyer_phone = data.get("buyerPhone")
        amount = float(data.get("amount") or 0)

        if not all([buyer_name, buyer_token, buyer_phone]) or amount <= 0:

            return jsonify({
                "success": False,
                "message": "Buyer name, mandi token, phone aur bid amount required hai."
            })

        listing = mandi_listings_collection.find_one({
            "_id": ObjectId(listing_id),
            "status": "open"
        })

        listing = finalize_expired_mandi_listing(listing)

        if not listing or listing.get("status") != "open":

            return jsonify({
                "success": False,
                "message": "Auction complete ho chuki hai ya listing live nahi hai."
            })

        buyer_pass = mandi_buyers_collection.find_one({
            "custom_id": buyer_token,
            "user_id": session["user_id"],
            "status": "active"
        })

        if not buyer_pass:

            return jsonify({
                "success": False,
                "message": "Valid Mandi Buyer Pass required hai."
            })

        if buyer_pass.get("buyerPhone") != buyer_phone:

            return jsonify({
                "success": False,
                "message": "Buyer Pass phone number match nahi ho raha."
            })

        if buyer_pass.get("mandiArea") != listing.get("mandiArea"):

            return jsonify({
                "success": False,
                "message": "Buyer Pass isi mandi area ka hona chahiye."
            })

        room_joined = mandi_live_rooms_collection.find_one({
            "listing_id": listing_id,
            "buyers.buyerToken": buyer_token
        })

        if not room_joined:

            return jsonify({
                "success": False,
                "message": "Bid sirf live room join karne ke baad hi submit hogi."
            })

        already_bidded = mandi_bids_collection.find_one({
            "listing_id": listing_id,
            "buyerToken": buyer_token
        })

        if get_room_buyer_count(listing_id) >= 8 and not already_bidded:

            return jsonify({
                "success": False,
                "message": "Is crop ke live room me 8 buyers already active hain."
            })

        current_highest = float(listing.get("highest_bid") or 0)

        if amount <= current_highest:

            return jsonify({
                "success": False,
                "message": "Bid current highest bid se zyada honi chahiye."
            })

        bid = {
            "listing_id": listing_id,
            "buyerName": buyer_pass.get("buyerName") or buyer_name,
            "buyerToken": buyer_token,
            "buyerPhone": buyer_pass.get("buyerPhone") or buyer_phone,
            "amount": amount,
            "message": data.get("message", ""),
            "created_at": datetime.now()
        }

        auction_ends_at = datetime.now() + timedelta(seconds=10)

        mandi_bids_collection.insert_one(bid)
        mandi_listings_collection.update_one({
            "_id": ObjectId(listing_id)
        }, {
            "$set": {
                "highest_bid": amount,
                "highest_buyer": buyer_pass.get("buyerName") or buyer_name,
                "highest_buyer_token": buyer_token,
                "auction_ends_at": auction_ends_at,
                "auction_started_at": listing.get("auction_started_at") or datetime.now()
            },
            "$inc": {
                "bid_count": 1
            }
        })

        return jsonify({
            "success": True,
            "message": "Live bid submit ho gayi. 10 second auction timer reset ho gaya.",
            "auctionEndsAt": auction_ends_at.isoformat(),
            "auctionRemainingSeconds": 10
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "message": str(e)
        })


@app.route("/api/mandi-listings/<listing_id>/decision", methods=["POST"])
def decide_mandi_offer(listing_id):

    try:

        if "user_id" not in session:

            return jsonify({
                "success": False,
                "message": "Please login first"
            }), 401

        data = request.json or {}
        decision = data.get("decision")

        listing = mandi_listings_collection.find_one({
            "_id": ObjectId(listing_id),
            "user_id": session["user_id"]
        })

        if not listing:

            return jsonify({
                "success": False,
                "message": "Listing not found"
            })

        if listing.get("status") != "open":

            return jsonify({
                "success": False,
                "message": "Is listing par decision already ho chuka hai."
            })

        if decision == "accept":

            if not listing.get("highest_bid"):

                return jsonify({
                    "success": False,
                    "message": "Accept karne ke liye pehle buyer bid chahiye."
                })

            mandi_listings_collection.update_one({
                "_id": ObjectId(listing_id)
            }, {
                "$set": {
                    "status": "accepted",
                    "accepted_at": datetime.now()
                }
            })

            return jsonify({
                "success": True,
                "message": "Offer accept ho gaya. Ab crop selected mandi/buyer ke paas le kar jani hogi."
            })

        if decision == "reject":

            rejected_until = datetime.now() + timedelta(days=8)

            mandi_listings_collection.update_one({
                "_id": ObjectId(listing_id)
            }, {
                "$set": {
                    "status": "rejected",
                    "rejected_at": datetime.now(),
                    "rejected_until": rejected_until
                }
            })

            return jsonify({
                "success": True,
                "message": "Offer reject ho gaya. Crop buyer/mandi page se remove ho gayi aur token 8 din ke liye hold par hai."
            })

        return jsonify({
            "success": False,
            "message": "Decision accept ya reject hona chahiye."
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
