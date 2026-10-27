import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from sqlalchemy import URL, func
from jinja2 import FileSystemLoader

project_root = os.path.dirname(os.path.abspath(__file__))
templates_root = os.path.join(project_root, "templates")
template_paths = [path for path, _, _ in os.walk(templates_root)]
static_folder = next(
    os.path.join(path, "static")
    for path, directories, _ in os.walk(templates_root)
    if "static" in directories
    and os.path.isfile(os.path.join(path, "static", "style.css"))
)

app = Flask(__name__, static_folder=static_folder)
app.jinja_env.loader = FileSystemLoader(template_paths)

app.config["SECRET_KEY"] = "book-review-secret-key"

# MySQL Database
app.config["SQLALCHEMY_DATABASE_URI"] = (
    URL.create(
        "mysql+pymysql",
        username="root",
        password=os.environ.get("BOOK_REVIEW_DB_PASSWORD", ""),
        host="localhost",
        database="book_review_db",
    )
)

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


# =========================
# DATABASE MODELS
# =========================

class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)

    reviews = db.relationship("Review", backref="user", lazy=True)


class Book(db.Model):
    __tablename__ = "books"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    author = db.Column(db.String(150), nullable=False)
    category = db.Column(db.String(100))
    description = db.Column(db.Text)

    reviews = db.relationship(
        "Review",
        backref="book",
        lazy=True,
        cascade="all, delete-orphan"
    )

    ratings = db.relationship(
        "Rating",
        backref="book",
        lazy=True,
        cascade="all, delete-orphan"
    )


class Review(db.Model):
    __tablename__ = "reviews"

    id = db.Column(db.Integer, primary_key=True)
    review_text = db.Column(db.Text, nullable=False)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    book_id = db.Column(
        db.Integer,
        db.ForeignKey("books.id"),
        nullable=False
    )


class Rating(db.Model):
    __tablename__ = "ratings"

    id = db.Column(db.Integer, primary_key=True)
    rating = db.Column(db.Integer, nullable=False)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    book_id = db.Column(
        db.Integer,
        db.ForeignKey("books.id"),
        nullable=False
    )


# =========================
# LOGIN REQUIRED DECORATOR
# =========================

def login_required(function):

    @wraps(function)
    def wrapper(*args, **kwargs):

        if "user_id" not in session:
            flash("Please login first.", "warning")
            return redirect(url_for("login"))

        return function(*args, **kwargs)

    return wrapper


# =========================
# HOME
# =========================

@app.route("/")
def index():

    books = Book.query.order_by(Book.id.desc()).limit(6).all()

    return render_template(
        "index.html",
        books=books
    )


# =========================
# REGISTER
# =========================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]

        existing_user = User.query.filter(
            (User.username == username) |
            (User.email == email)
        ).first()

        if existing_user:
            flash("Username or email already exists.", "danger")
            return redirect(url_for("register"))

        hashed_password = generate_password_hash(password)

        user = User(
            username=username,
            email=email,
            password=hashed_password
        )

        db.session.add(user)
        db.session.commit()

        flash("Registration successful. Please login.", "success")

        return redirect(url_for("login"))

    return render_template("register.html")


# =========================
# LOGIN
# =========================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):

            session["user_id"] = user.id
            session["username"] = user.username

            flash("Login successful.", "success")

            return redirect(url_for("index"))

        flash("Invalid email or password.", "danger")

    return render_template("login.html")


# =========================
# LOGOUT
# =========================

@app.route("/logout")
def logout():

    session.clear()

    flash("You have been logged out.", "success")

    return redirect(url_for("index"))


# =========================
# BOOK LIST
# =========================

@app.route("/books")
def books():

    search = request.args.get("search", "")

    if search:

        books = Book.query.filter(
            (Book.title.ilike(f"%{search}%")) |
            (Book.author.ilike(f"%{search}%")) |
            (Book.category.ilike(f"%{search}%"))
        ).all()

    else:

        books = Book.query.all()

    return render_template(
        "books.html",
        books=books,
        search=search
    )


# =========================
# BOOK DETAIL
# =========================

@app.route("/book/<int:book_id>")
def book_detail(book_id):

    book = Book.query.get_or_404(book_id)

    reviews = Review.query.filter_by(
        book_id=book.id
    ).all()

    average_rating = db.session.query(
        func.avg(Rating.rating)
    ).filter(
        Rating.book_id == book.id
    ).scalar()

    if average_rating:
        average_rating = round(float(average_rating), 2)
    else:
        average_rating = 0

    return render_template(
        "book_detail.html",
        book=book,
        reviews=reviews,
        average_rating=average_rating
    )


# =========================
# ADD REVIEW
# =========================

@app.route("/book/<int:book_id>/review", methods=["POST"])
@login_required
def add_review(book_id):

    review_text = request.form["review_text"]

    review = Review(
        review_text=review_text,
        user_id=session["user_id"],
        book_id=book_id
    )

    db.session.add(review)
    db.session.commit()

    flash("Review added successfully.", "success")

    return redirect(
        url_for("book_detail", book_id=book_id)
    )


# =========================
# ADD RATING
# =========================

@app.route("/book/<int:book_id>/rating", methods=["POST"])
@login_required
def add_rating(book_id):

    rating_value = int(request.form["rating"])

    if rating_value < 1 or rating_value > 5:

        flash("Rating must be between 1 and 5.", "danger")

        return redirect(
            url_for("book_detail", book_id=book_id)
        )

    existing_rating = Rating.query.filter_by(
        user_id=session["user_id"],
        book_id=book_id
    ).first()

    if existing_rating:

        existing_rating.rating = rating_value

    else:

        rating = Rating(
            rating=rating_value,
            user_id=session["user_id"],
            book_id=book_id
        )

        db.session.add(rating)

    db.session.commit()

    flash("Rating submitted successfully.", "success")

    return redirect(
        url_for("book_detail", book_id=book_id)
    )


# =========================
# ADD BOOK
# =========================

@app.route("/add-book", methods=["GET", "POST"])
@login_required
def add_book():

    if request.method == "POST":

        title = request.form["title"]
        author = request.form["author"]
        category = request.form["category"]
        description = request.form["description"]

        book = Book(
            title=title,
            author=author,
            category=category,
            description=description
        )

        db.session.add(book)
        db.session.commit()

        flash("Book added successfully.", "success")

        return redirect(url_for("books"))

    return render_template("add_book.html")


# =========================
# REVIEW REPORT
# =========================

@app.route("/report")
@login_required
def report():

    total_books = Book.query.count()

    total_reviews = Review.query.count()

    total_ratings = Rating.query.count()

    average_rating = db.session.query(
        func.avg(Rating.rating)
    ).scalar()

    if average_rating:
        average_rating = round(float(average_rating), 2)
    else:
        average_rating = 0

    book_statistics = []

    books = Book.query.all()

    for book in books:

        avg = db.session.query(
            func.avg(Rating.rating)
        ).filter(
            Rating.book_id == book.id
        ).scalar()

        review_count = Review.query.filter_by(
            book_id=book.id
        ).count()

        book_statistics.append({
            "book": book,
            "average": round(float(avg), 2) if avg else 0,
            "reviews": review_count
        })

    return render_template(
        "report.html",
        total_books=total_books,
        total_reviews=total_reviews,
        total_ratings=total_ratings,
        average_rating=average_rating,
        book_statistics=book_statistics
    )


# =========================
# CREATE DATABASE
# =========================

with app.app_context():
    db.create_all()


# =========================
# RUN APPLICATION
# =========================

if __name__ == "__main__":
    app.run(debug=True)