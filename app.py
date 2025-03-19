from flask import Flask, render_template, jsonify, request
from flask_pymongo import PyMongo
import pandas as pd
import os
from PIL import Image

app = Flask(__name__)

# MongoDB Configuration
app.config["MONGO_URI"] = "mongodb://localhost:27017/Fashion"
mongo = PyMongo(app)

# Static folder for images
STATIC_FOLDER = "static/images"
RESIZED_FOLDER = "static/resized_images"

# Load dataset
try:
    dataset = pd.read_csv("labels_front.csv")
    dataset = dataset.map(lambda x: x.lower() if isinstance(x, str) else x)
  # Convert all to lowercase
except Exception as e:
    print(f"Error loading dataset: {e}")
    dataset = pd.DataFrame()

def resize_images(image_paths, output_folder, size=(30, 40)):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    for image_path in image_paths:
        try:
            img = Image.open(image_path)
            img = img.resize(size, Image.ANTIALIAS)
            img.save(os.path.join(output_folder, os.path.basename(image_path)))
        except Exception as e:
            print(f"Error resizing image {image_path}: {e}")
@app.route("/")
def index():
    return render_template("index.html")

@app.route('/register')
def register():
    return render_template('register.html')

@app.route("/dashboard")
def dashboard():
    return render_template("home.html")
@app.route("/my_wardrobe")
def my_wardrobe():
    return render_template("MyWardrobe.html")

@app.route("/profile")
def profile():
    return render_template("Profile.html")

@app.route("/save_preferences", methods=["POST"])
def save_preferences():
    data = request.json
    username = data.get("username")
    if username:
        mongo.db.user_preferences.update_one(
            {"username": username},
            {"$set": {"preferences": data.get("preferences", {})}},
            upsert=True,
        )
        return jsonify({"message": "Preferences saved successfully!"})
    return jsonify({"message": "Username not provided!"}), 400

@app.route("/get_recommendations", methods=["GET"])
def get_recommendations():
    username = request.args.get("username")
    user_preferences = mongo.db.user_preferences.find_one({"username": username})

    if not user_preferences:
        return jsonify({"message": "No preferences found!", "recommendations": []})

    # Extract user preferences
    preferences = user_preferences.get("preferences", {})
    preferred_gender = preferences.get("gender", "").lower()
    preferred_types = preferences.get("type", [])
    preferred_sleeve = preferences.get("sleeveType", [])
    preferred_pattern = preferences.get("pattern", [])
    preferred_fabric = preferences.get("fabric", [])
    preferred_neckline = preferences.get("neckline", [])

    # Filter by gender
    if preferred_gender and preferred_gender != "none":
        dataset_filtered = dataset[dataset["gender"] == preferred_gender]
    else:
        dataset_filtered = dataset.copy()
    
    # Apply AND-based filtering
    def filter_column(df, column, values):
        if values and "none" not in values:
            return df[df[column].str.contains('|'.join(values), case=False, na=False)]
        return df
    
    dataset_filtered = filter_column(dataset_filtered, "caption", preferred_types)
    dataset_filtered = filter_column(dataset_filtered, "caption", preferred_sleeve)
    dataset_filtered = filter_column(dataset_filtered, "caption", preferred_pattern)
    dataset_filtered = filter_column(dataset_filtered, "caption", preferred_fabric)
    dataset_filtered = filter_column(dataset_filtered, "caption", preferred_neckline)
    
    # Get recommendations
    recommendations = dataset_filtered.head(50)
    recommendation_list = [
        {
            "product_id": row["product_id"],
            "caption": row["caption"],
            "image": f"/static/images/{row['path']}",
            "product_type": row["product_type"]
        }
        for _, row in recommendations.iterrows()
    ]
    
    if not recommendation_list:
        return jsonify({"message": "No matching recommendations found!", "recommendations": []})
    
    print("User Preferences:", preferences)
    print("Filtered Dataset Shape:", dataset_filtered.shape)
    print("Dataset Sample After Filtering:", dataset_filtered.head())
    
    return jsonify({"message": "Recommendations found!", "recommendations": recommendation_list})

BASE_DIR = "Clothing"
CATEGORIES = {
    "male": os.path.join(BASE_DIR, "MenClothing"),
    "female": os.path.join(BASE_DIR, "WomenClothing")
}
@app.route('/get_images', methods=['POST'])
def get_images():
    data = request.get_json()
    gender = data.get("gender").lower()

    if gender not in CATEGORIES:
        return jsonify({"error": "Invalid gender"}), 400

    # Get image file names from the respective folder
    image_folder = CATEGORIES[gender]
    images = [f"/static/{gender}/{img}" for img in os.listdir(image_folder) if img.endswith(('png', 'jpg', 'jpeg','webp'))]

    return jsonify({"images": images})

if __name__ == "__main__":
    app.run(debug=True)
