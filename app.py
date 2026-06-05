import os
import time
from pathlib import Path
from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

from db import (
    init_db,
    add_clothing_item,
    get_clothing_items,
    delete_clothing_item,
    save_favorite_outfit,
    get_favorite_outfits,
    delete_favorite_outfit,
)

from services import (
    get_weather,
    get_today_calendar_events,
    generate_outfit_recommendation,
)

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

UPLOAD_FOLDER = BASE_DIR / "static" / "uploads"
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

app = Flask(
    __name__,
    template_folder=str(BASE_DIR / "templates"),
    static_folder=str(BASE_DIR / "static")
)

app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-key")
CORS(app)

init_db()


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def save_uploaded_image(file):
    if not file or file.filename == "":
        return ""

    if not allowed_file(file.filename):
        raise ValueError("Only PNG, JPG, JPEG and WEBP images are allowed.")

    filename = secure_filename(file.filename)
    unique_name = f"{int(time.time())}_{filename}"
    file_path = UPLOAD_FOLDER / unique_name

    file.save(file_path)

    return f"/static/uploads/{unique_name}"


@app.route("/", methods=["GET"])
def home():
    return render_template("index.html")


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "message": "Morning Wear Assistant is running"
    })


@app.route("/api/weather", methods=["GET"])
def weather():
    try:
        city = request.args.get("city", os.getenv("DEFAULT_CITY", "Vechta"))
        country = request.args.get("country", os.getenv("DEFAULT_COUNTRY", "DE"))

        weather_data = get_weather(city, country)

        return jsonify({"success": True, "weather": weather_data})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/calendar/today", methods=["GET"])
def calendar_today():
    try:
        events = get_today_calendar_events()
        return jsonify({"success": True, "events": events})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/closet", methods=["GET"])
def closet_list():
    try:
        items = get_clothing_items()
        return jsonify({"success": True, "items": items})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/closet", methods=["POST"])
def closet_add():
    try:
        name = str(request.form.get("name", "")).strip()
        category = str(request.form.get("category", "")).strip()
        color = str(request.form.get("color", "")).strip()
        notes = str(request.form.get("notes", "")).strip()

        try:
            warmth_level = int(request.form.get("warmth_level", 2))
        except Exception:
            warmth_level = 2

        try:
            waterproof = int(request.form.get("waterproof", 0))
        except Exception:
            waterproof = 0

        try:
            formal_level = int(request.form.get("formal_level", 1))
        except Exception:
            formal_level = 1

        if not name or not category:
            return jsonify({
                "success": False,
                "error": "Name and category are required"
            }), 400

        image_path = save_uploaded_image(request.files.get("image"))

        item_id = add_clothing_item(
            name=name,
            category=category,
            color=color,
            warmth_level=warmth_level,
            waterproof=waterproof,
            formal_level=formal_level,
            notes=notes,
            image_path=image_path,
        )

        return jsonify({
            "success": True,
            "message": "Clothing item added",
            "id": item_id,
            "image_path": image_path
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/closet/<int:item_id>", methods=["DELETE"])
def closet_delete(item_id):
    try:
        deleted = delete_clothing_item(item_id)

        if not deleted:
            return jsonify({"success": False, "error": "Item not found"}), 404

        return jsonify({"success": True, "message": "Item deleted"})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/recommend", methods=["POST"])
def recommend():
    try:
        data = request.get_json(silent=True) or {}

        city = data.get("city", os.getenv("DEFAULT_CITY", "Vechta"))
        country = data.get("country", os.getenv("DEFAULT_COUNTRY", "DE"))

        weather_data = get_weather(city, country)
        events = get_today_calendar_events()
        closet_items = get_clothing_items()

        if not closet_items:
            return jsonify({
                "success": False,
                "error": "Your closet is empty. Please add clothing items first."
            }), 400

        recommendation = generate_outfit_recommendation(
            weather_data,
            events,
            closet_items
        )

        return jsonify({
            "success": True,
            "weather": weather_data,
            "events": events,
            "closet_count": len(closet_items),
            "recommendation": recommendation,
            "closet_items": closet_items
        })

    except Exception as e:
        print("RECOMMENDATION ERROR:", str(e))
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/outfit-image", methods=["POST"])
def outfit_image():
    return jsonify({
        "success": False,
        "error": "Real AI image generation is not available. Using uploaded closet images instead."
    }), 200


@app.route("/api/favorites", methods=["GET"])
def favorites_list():
    try:
        outfits = get_favorite_outfits()
        return jsonify({"success": True, "favorites": outfits})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/favorites", methods=["POST"])
def favorites_add():
    try:
        data = request.get_json(silent=True) or {}

        title = str(data.get("title", "Favorite Outfit")).strip()
        outfit_text = str(data.get("outfit_text", "")).strip()
        weather_summary = str(data.get("weather_summary", "")).strip()
        calendar_summary = str(data.get("calendar_summary", "")).strip()

        if not title:
            title = "Favorite Outfit"

        if not outfit_text:
            return jsonify({"success": False, "error": "Outfit text is required"}), 400

        existing_outfits = get_favorite_outfits()

        for outfit in existing_outfits:
            if outfit.get("outfit_text", "").strip() == outfit_text:
                return jsonify({
                    "success": True,
                    "duplicate": True,
                    "message": "This outfit is already saved",
                    "id": outfit.get("id")
                })

        favorite_id = save_favorite_outfit(
            title,
            outfit_text,
            weather_summary,
            calendar_summary
        )

        return jsonify({
            "success": True,
            "duplicate": False,
            "message": "Favorite outfit saved",
            "id": favorite_id
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/favorites/<int:outfit_id>", methods=["DELETE"])
def favorites_delete(outfit_id):
    try:
        deleted = delete_favorite_outfit(outfit_id)

        if not deleted:
            return jsonify({"success": False, "error": "Favorite outfit not found"}), 404

        return jsonify({"success": True, "message": "Favorite outfit deleted"})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.errorhandler(404)
def not_found(error):
    return jsonify({"success": False, "error": "Route not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({"success": False, "error": "Internal server error"}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)
