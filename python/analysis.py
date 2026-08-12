import pandas as pd
import numpy as np
from sqlalchemy import create_engine
import urllib.parse
import matplotlib.pyplot as plt
import os

# подключение
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

# создаём папки для результатов, если их ещё нет
os.makedirs("../powerbi/exports", exist_ok=True)
os.makedirs("charts", exist_ok=True)


# читаем таблицы из БД в DataFrame
authors = pd.read_sql("SELECT * FROM Authors", engine)
genres = pd.read_sql("SELECT * FROM Genres", engine)
publishers = pd.read_sql("SELECT * FROM Publishers", engine)
books = pd.read_sql("SELECT * FROM Books", engine)
readers = pd.read_sql("SELECT * FROM Readers", engine)
loans = pd.read_sql("SELECT * FROM Loans", engine)
fines = pd.read_sql("SELECT * FROM Fines", engine)

print("Данные загружены:", len(loans), "выдач,", len(readers), "читателей")

for col in ["loan_date", "due_date", "return_date"]:
    loans[col] = pd.to_datetime(loans[col])


# соединяем Loans с Books, Genres, Readers, чтобы в одной таблице были все нужные поля сразу
loans_full = (
    loans
    .merge(books, on="book_id", how="left")
    .merge(genres, on="genre_id", how="left")
    .merge(readers, on="reader_id", how="left", suffixes=("_book", "_reader"))
)

# создаём "полное имя" читателя одной колонкой
loans_full["reader_name"] = loans_full["first_name"] + " " + loans_full["last_name"]

# топ-10 книг по числу выдач
top_books = (
    loans_full
    .groupby("title")
    .size()
    .reset_index(name="times_loaned")   # превращаем результат обратно в обычную таблицу
    .sort_values("times_loaned", ascending=False)
    .head(10)
)

# популярность жанров
genre_popularity = (
    loans_full
    .groupby("genre_name")
    .size()
    .reset_index(name="total_loans")
    .sort_values("total_loans", ascending=False)
)

# % просроченных выдач
returned = loans[loans["status"] == "returned"].copy()
returned["is_overdue"] = returned["return_date"] > returned["due_date"]

overdue_pct = round(returned["is_overdue"].mean() * 100, 2) 
print(f"Просрочек: {overdue_pct}% от всех возвращённых книг")

# средний срок пользования книгой (в днях)
returned["days_held"] = (returned["return_date"] - returned["loan_date"]).dt.days
avg_days_held = round(returned["days_held"].mean(), 1)
print(f"В среднем книгу держат {avg_days_held} дней")

# динамика выдач по месяцам
loans_copy = loans.copy()
loans_copy["loan_month"] = pd.to_datetime(loans_copy["loan_date"]).dt.to_period("M").astype(str)

monthly_loans = (
    loans_copy
    .groupby("loan_month")
    .size()
    .reset_index(name="loans_count")
    .sort_values("loan_month")
)

# топ-10 активных читателей
top_readers = (
    loans_full
    .groupby("reader_name")
    .size()
    .reset_index(name="total_loans")
    .sort_values("total_loans", ascending=False)
    .head(10)
)

# сумма неоплаченных штрафов по читателям
fines_full = fines.merge(loans, on="loan_id", how="left").merge(readers, on="reader_id", how="left")
fines_full["reader_name"] = fines_full["first_name"] + " " + fines_full["last_name"]

unpaid_fines = (
    fines_full[fines_full["paid"] == False]
    .groupby("reader_name")["amount"]
    .sum()
    .reset_index(name="unpaid_amount")
    .sort_values("unpaid_amount", ascending=False)
)


# сохраняем как png 
plt.figure(figsize=(8, 5))
plt.bar(genre_popularity["genre_name"], genre_popularity["total_loans"], color="#6C5CE7")
plt.xticks(rotation=45, ha="right")
plt.title("Популярность жанров (число выдач)")
plt.tight_layout()
plt.savefig("charts/genre_popularity.png", dpi=120)
plt.close()

plt.figure(figsize=(8, 5))
plt.plot(monthly_loans["loan_month"], monthly_loans["loans_count"], marker="o", color="#00B894")
plt.xticks(rotation=45, ha="right")
plt.title("Динамика выдач по месяцам")
plt.tight_layout()
plt.savefig("charts/monthly_loans.png", dpi=120)
plt.close()

plt.figure(figsize=(5, 5))
overdue_counts = returned["is_overdue"].value_counts()
plt.pie(
    overdue_counts,
    labels=["Вовремя", "Просрочено"] if False in overdue_counts.index else ["Просрочено", "Вовремя"],
    autopct="%1.1f%%",
    colors=["#00B894", "#D63031"],
)
plt.title("Доля просроченных возвратов")
plt.tight_layout()
plt.savefig("charts/overdue_share.png", dpi=120)
plt.close()

print("Графики сохранены в papka charts/")

# выгрузка CSV для POWER BI
top_books.to_csv("../powerbi/exports/top_books.csv", index=False, encoding="utf-8-sig")
genre_popularity.to_csv("../powerbi/exports/genre_popularity.csv", index=False, encoding="utf-8-sig")
monthly_loans.to_csv("../powerbi/exports/monthly_loans.csv", index=False, encoding="utf-8-sig")
top_readers.to_csv("../powerbi/exports/top_readers.csv", index=False, encoding="utf-8-sig")
unpaid_fines.to_csv("../powerbi/exports/unpaid_fines.csv", index=False, encoding="utf-8-sig")
loans_full.to_csv("../powerbi/exports/loans_full.csv", index=False, encoding="utf-8-sig")

print("CSV выгружены в powerbi/exports/")
print("Готово!")
