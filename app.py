import os
import re
from datetime import timedelta

from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import (
    JWTManager, create_access_token, get_jwt_identity, jwt_required
)
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

secret_key = os.environ.get("SECRET_KEY")
if not secret_key and os.environ.get("RENDER") == "true":
    raise RuntimeError("Set a strong SECRET_KEY environment variable on Render.")
app.config["SECRET_KEY"] = secret_key or "local-only-change-this-secret"
app.config["JWT_SECRET_KEY"] = secret_key or "local-only-change-this-jwt-secret"
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=2)

database_url = os.environ.get("DATABASE_URL", "sqlite:///users.db")
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql+psycopg://", 1)
elif database_url.startswith("postgresql://"):
    database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Set FRONTEND_ORIGIN to the exact Vercel origin, e.g. https://my-app.vercel.app
frontend_origin = os.environ.get("FRONTEND_ORIGIN", "http://127.0.0.1:5500").rstrip("/")
CORS(app, resources={r"/api/*": {"origins": [frontend_origin]}})

db = SQLAlchemy(app)
jwt = JWTManager(app)


class User(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)


with app.app_context():
    db.create_all()


def user_payload(user):
    return {"id": user.id, "name": user.name, "email": user.email}


@app.get("/")
def home():
    return jsonify({
        "message": "Login API is running.",
        "health": "/health",
        "endpoints": ["/api/register", "/api/login", "/api/me"]
    })


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


@app.post("/api/register")
def register():
    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()
    email = str(data.get("email", "")).strip().lower()
    password = data.get("password", "")

    if not name or len(name) > 80:
        return jsonify(error="Enter a valid name (maximum 80 characters)."), 400
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email) or len(email) > 254:
        return jsonify(error="Enter a valid email address."), 400
    if not isinstance(password, str) or len(password) < 8 or len(password) > 128:
        return jsonify(error="Password must be 8 to 128 characters long."), 400
    if User.query.filter_by(email=email).first():
        return jsonify(error="An account with this email already exists."), 409

    user = User(name=name, email=email, password_hash=generate_password_hash(password))
    db.session.add(user)
    db.session.commit()
    token = create_access_token(identity=str(user.id))
    return jsonify(message="Account created successfully.", user=user_payload(user),
                   access_token=token), 201


@app.post("/api/login")
def login():
    data = request.get_json(silent=True) or {}
    email = str(data.get("email", "")).strip().lower()
    password = data.get("password", "")
    if not email or not isinstance(password, str):
        return jsonify(error="Enter your email and password."), 400

    user = User.query.filter_by(email=email).first()
    if not user or not check_password_hash(user.password_hash, password):
        return jsonify(error="Invalid email or password."), 401

    token = create_access_token(identity=str(user.id))
    return jsonify(message="Login successful.", user=user_payload(user),
                   access_token=token)


@app.get("/api/me")
@jwt_required()
def me():
    user_id = get_jwt_identity()
    user = db.session.get(User, int(user_id))
    if not user:
        return jsonify(error="User account not found."), 404
    return jsonify(user=user_payload(user))


@app.errorhandler(404)
def not_found(_error):
    return jsonify(error="Endpoint not found."), 404


if __name__ == "__main__":
    app.run(debug=True, port=5000)
