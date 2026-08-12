USE LibraryAnalytics;
GO

-- 1. Топ-10 самых популярных книг (по числу выдач)

SELECT TOP 10
    b.title,
    COUNT(l.loan_id) AS times_loaned
FROM Books b
JOIN Loans l ON l.book_id = b.book_id
GROUP BY b.title
ORDER BY times_loaned DESC;
GO

-- 2. Популярность жанров (число выдач по жанру)

SELECT
    g.genre_name,
    COUNT(l.loan_id) AS total_loans
FROM Genres g
JOIN Books b ON b.genre_id = g.genre_id
JOIN Loans l ON l.book_id = b.book_id
GROUP BY g.genre_name
ORDER BY total_loans DESC;
GO

-- 3. Топ-10 самых активных читателей

SELECT TOP 10
    r.reader_id,
    r.first_name + ' ' + r.last_name AS reader_name,
    COUNT(l.loan_id) AS total_loans
FROM Readers r
JOIN Loans l ON l.reader_id = r.reader_id
GROUP BY r.reader_id, r.first_name, r.last_name
ORDER BY total_loans DESC;
GO

-- 4. Доля просроченных выдач (среди возвращённых)

SELECT
    COUNT(CASE WHEN return_date > due_date THEN 1 END) AS overdue_count,
    COUNT(*) AS returned_total,
    CAST(
        100.0 * COUNT(CASE WHEN return_date > due_date THEN 1 END) / COUNT(*)
        AS DECIMAL(5,2)
    ) AS overdue_pct
FROM Loans
WHERE status = 'returned';
GO

-- 5. Средний срок фактического пользования книгой (в днях)

SELECT
    AVG(DATEDIFF(DAY, loan_date, return_date)) AS avg_days_held
FROM Loans
WHERE status = 'returned';
GO

-- 6. Динамика выдач по месяцам

SELECT
    FORMAT(loan_date, 'yyyy-MM') AS loan_month,
    COUNT(*) AS loans_count
FROM Loans
GROUP BY FORMAT(loan_date, 'yyyy-MM')
ORDER BY loan_month;
GO

-- 7. Книги, которые ни разу не брали (неликвид)

SELECT
    b.title,
    b.publish_year
FROM Books b
LEFT JOIN Loans l ON l.book_id = b.book_id
WHERE l.loan_id IS NULL;
GO

-- 8. Сумма штрафов по каждому читателю (только неоплаченные)

SELECT
    r.first_name + ' ' + r.last_name AS reader_name,
    SUM(f.amount) AS unpaid_fines
FROM Readers r
JOIN Loans l ON l.reader_id = r.reader_id
JOIN Fines f ON f.loan_id = l.loan_id
WHERE f.paid = 0
GROUP BY r.first_name, r.last_name
ORDER BY unpaid_fines DESC;
GO

-- 9. Издательства по числу изданных книг в фонде

SELECT
    p.publisher_name,
    COUNT(b.book_id) AS books_count
FROM Publishers p
JOIN Books b ON b.publisher_id = p.publisher_id
GROUP BY p.publisher_name
ORDER BY books_count DESC;
GO

-- 10. Ранжирование читателей по активности внутри каждого месяца

WITH monthly_activity AS (
    SELECT
        r.reader_id,
        r.first_name + ' ' + r.last_name AS reader_name,
        FORMAT(l.loan_date, 'yyyy-MM') AS loan_month,
        COUNT(*) AS loans_in_month
    FROM Readers r
    JOIN Loans l ON l.reader_id = r.reader_id
    GROUP BY r.reader_id, r.first_name, r.last_name, FORMAT(l.loan_date, 'yyyy-MM')
)
SELECT
    reader_name,
    loan_month,
    loans_in_month,
    RANK() OVER (PARTITION BY loan_month ORDER BY loans_in_month DESC) AS rank_in_month
FROM monthly_activity
ORDER BY loan_month, rank_in_month;
GO

-- 11. Накопительный итог выдач по месяцам 

WITH monthly_loans AS (
    SELECT
        FORMAT(loan_date, 'yyyy-MM') AS loan_month,
        COUNT(*) AS loans_count
    FROM Loans
    GROUP BY FORMAT(loan_date, 'yyyy-MM')
)
SELECT
    loan_month,
    loans_count,
    SUM(loans_count) OVER (ORDER BY loan_month ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS running_total
FROM monthly_loans
ORDER BY loan_month;
GO

-- 12. Средний возраст читательского "стажа" (дней с регистрации)

SELECT
    CASE
        WHEN DATEDIFF(DAY, registration_date, GETDATE()) < 180 THEN 'до 6 мес'
        WHEN DATEDIFF(DAY, registration_date, GETDATE()) < 365 THEN '6-12 мес'
        WHEN DATEDIFF(DAY, registration_date, GETDATE()) < 730 THEN '1-2 года'
        ELSE 'более 2 лет'
    END AS registration_segment,
    COUNT(*) AS readers_count
FROM Readers
GROUP BY
    CASE
        WHEN DATEDIFF(DAY, registration_date, GETDATE()) < 180 THEN 'до 6 мес'
        WHEN DATEDIFF(DAY, registration_date, GETDATE()) < 365 THEN '6-12 мес'
        WHEN DATEDIFF(DAY, registration_date, GETDATE()) < 730 THEN '1-2 года'
        ELSE 'более 2 лет'
    END
ORDER BY readers_count DESC;
GO

-- 13. Читатели без единой просрочки (надёжные читатели)

SELECT
    r.reader_id,
    r.first_name + ' ' + r.last_name AS reader_name,
    COUNT(l.loan_id) AS total_loans
FROM Readers r
JOIN Loans l ON l.reader_id = r.reader_id
WHERE l.status = 'returned'
GROUP BY r.reader_id, r.first_name, r.last_name
HAVING SUM(CASE WHEN l.return_date > l.due_date THEN 1 ELSE 0 END) = 0
ORDER BY total_loans DESC;
GO

-- 14. Средняя сумма штрафа по жанру книги

SELECT
    g.genre_name,
    AVG(f.amount) AS avg_fine_amount,
    COUNT(f.fine_id) AS fines_count
FROM Genres g
JOIN Books b ON b.genre_id = g.genre_id
JOIN Loans l ON l.book_id = b.book_id
JOIN Fines f ON f.loan_id = l.loan_id
GROUP BY g.genre_name
ORDER BY avg_fine_amount DESC;
GO
