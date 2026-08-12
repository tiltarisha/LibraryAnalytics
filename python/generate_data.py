import pandas as pd
import numpy as np
from faker import Faker
from sqlalchemy import create_engine
import urllib.parse
import random
from datetime import timedelta

# фиксация рандом, чтобы результаты были воспроизводимы
Faker.seed(42)
random.seed(42)
np.random.seed(42)

fake = Faker("ru_RU")  # генерация данных в русской локали 

SERVER = r"np:\\.\pipe\LOCALDB#626D9F15\tsql\query" 
DATABASE = "LibraryAnalytics"
DRIVER = "ODBC Driver 17 for SQL Server" 

odbc_str = (
    f"DRIVER={{{DRIVER}}};"
    f"SERVER={SERVER};"
    f"DATABASE={DATABASE};"
    f"Trusted_Connection=yes;"
)
connection_string = "mssql+pyodbc:///?odbc_connect=" + urllib.parse.quote_plus(odbc_str)

engine = create_engine(connection_string, fast_executemany=True)


# генерация авторов
N_AUTHORS = 20

authors = pd.DataFrame({
    "first_name": [fake.first_name() for _ in range(N_AUTHORS)],
    "last_name": [fake.last_name() for _ in range(N_AUTHORS)],
    "country": [fake.country() for _ in range(N_AUTHORS)],
    "birth_year": [fake.random_int(min=1930, max=1995) for _ in range(N_AUTHORS)],
})


# генерация жанров с фиксированным списком
genre_list = [
    "Фантастика", "Детектив", "Роман", "Классика", "Фэнтези",
    "Триллер", "Нон-фикшн", "Поэзия", "Ужасы", "Биография"
]
genres = pd.DataFrame({"genre_name": genre_list})


# генерация издательств
N_PUBLISHERS = 10

publishers = pd.DataFrame({
    "publisher_name": [fake.company() for _ in range(N_PUBLISHERS)],
    "country": [fake.country() for _ in range(N_PUBLISHERS)],
})

# генерация книг
N_BOOKS = 80

def random_isbn():
    return fake.isbn13(separator="-")

books_raw = pd.DataFrame({
    "title": [fake.sentence(nb_words=3).rstrip(".") for _ in range(N_BOOKS)],
    "publish_year": [fake.random_int(min=1960, max=2024) for _ in range(N_BOOKS)],
    "isbn": [random_isbn() for _ in range(N_BOOKS)],
    "total_copies": [fake.random_int(min=1, max=10) for _ in range(N_BOOKS)],
})


# генерация читателей
N_READERS = 150

readers = pd.DataFrame({
    "first_name": [fake.first_name() for _ in range(N_READERS)],
    "last_name": [fake.last_name() for _ in range(N_READERS)],
    "email": [fake.unique.email() for _ in range(N_READERS)],
    "phone": [fake.phone_number() for _ in range(N_READERS)],
    "registration_date": [fake.date_between(start_date="-3y", end_date="today") for _ in range(N_READERS)],
})


# загрузка данных в БД
authors.to_sql("Authors", engine, if_exists="append", index=False)
genres.to_sql("Genres", engine, if_exists="append", index=False)
publishers.to_sql("Publishers", engine, if_exists="append", index=False)
readers.to_sql("Readers", engine, if_exists="append", index=False)

print("Authors, Genres, Publishers, Readers загружены ✓")


# получаем id обратно из БД
author_ids = pd.read_sql("SELECT author_id FROM Authors", engine)["author_id"].tolist()
genre_ids = pd.read_sql("SELECT genre_id FROM Genres", engine)["genre_id"].tolist()
publisher_ids = pd.read_sql("SELECT publisher_id FROM Publishers", engine)["publisher_id"].tolist()
reader_ids = pd.read_sql("SELECT reader_id FROM Readers", engine)["reader_id"].tolist()

# дополняем книги
books = books_raw.copy()
books["author_id"] = [random.choice(author_ids) for _ in range(N_BOOKS)]
books["genre_id"] = [random.choice(genre_ids) for _ in range(N_BOOKS)]
books["publisher_id"] = [random.choice(publisher_ids) for _ in range(N_BOOKS)]

books.to_sql("Books", engine, if_exists="append", index=False)
print("Books загружены ✓")

book_ids = pd.read_sql("SELECT book_id FROM Books", engine)["book_id"].tolist()


# генерация выдачи книг
N_LOANS = 400

loan_rows = []
for _ in range(N_LOANS):
    book_id = random.choice(book_ids)
    reader_id = random.choice(reader_ids)
    loan_date = fake.date_between(start_date="-2y", end_date="today")
    due_date = loan_date + timedelta(days=14)  # стандартный срок — 2 недели

    # 70% книг уже вернули, 30% — ещё на руках
    is_returned = random.random() < 0.7

    if is_returned:
        # книгу могли вернуть вовремя ИЛИ с опозданием
        delay_days = random.choice([-3, -1, 0, 0, 1, 2, 5, 10])  # чаще без опоздания
        return_date = due_date + timedelta(days=delay_days)
        if return_date < loan_date:
            return_date = loan_date
        status = "returned"
    else:
        return_date = None
        status = "overdue" if due_date < fake.date_between(start_date="today", end_date="today") else "active"

    loan_rows.append({
        "book_id": book_id,
        "reader_id": reader_id,
        "loan_date": loan_date,
        "due_date": due_date,
        "return_date": return_date,
        "status": status,
    })

loans = pd.DataFrame(loan_rows)
loans.to_sql("Loans", engine, if_exists="append", index=False)
print("Loans загружены ✓")

loans_from_db = pd.read_sql("SELECT loan_id, due_date, return_date, status FROM Loans", engine)


# генерация штрафов
FINE_PER_DAY = 10  # условные рубли за день просрочки

fine_rows = []
for _, row in loans_from_db.iterrows():
    if row["status"] == "returned" and row["return_date"] is not None:
        delay = (row["return_date"] - row["due_date"]).days
        if delay > 0:
            fine_rows.append({
                "loan_id": row["loan_id"],
                "amount": delay * FINE_PER_DAY,
                "issued_date": row["return_date"],
                "paid": random.random() < 0.8,  # 80% штрафов оплачено
            })

fines = pd.DataFrame(fine_rows)
if not fines.empty:
    fines.to_sql("Fines", engine, if_exists="append", index=False)

print(f"Fines загружены ✓ ({len(fines)} штрафов)")
print("Готово! Все таблицы наполнены.")
