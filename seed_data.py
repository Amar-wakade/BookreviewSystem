from app import app, db, User, Book
from werkzeug.security import generate_password_hash


with app.app_context():

    db.create_all()

    # Demo user
    user = User.query.filter_by(
        email="admin@gmail.com"
    ).first()

    if not user:

        user = User(
            username="admin",
            email="admin@gmail.com",
            password=generate_password_hash("admin123")
        )

        db.session.add(user)

    # Sample books

    sample_books = [

        Book(
            title="Python Programming",
            author="Mark Lutz",
            category="Programming",
            description="A detailed book for learning Python programming."
        ),

        Book(
            title="Clean Code",
            author="Robert C. Martin",
            category="Software Engineering",
            description="A practical guide to writing clean and maintainable code."
        ),

        Book(
            title="The Pragmatic Programmer",
            author="Andrew Hunt",
            category="Programming",
            description="A popular software development and programming book."
        ),

        Book(
            title="Introduction to Algorithms",
            author="Thomas H. Cormen",
            category="Algorithms",
            description="A comprehensive book about algorithms and data structures."
        )

    ]

    for book in sample_books:

        existing = Book.query.filter_by(
            title=book.title
        ).first()

        if not existing:

            db.session.add(book)

    db.session.commit()

    print("Sample data inserted successfully.")
    print("Demo Email: admin@gmail.com")
    print("Demo Password: admin123")