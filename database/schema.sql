-- =========================================
-- LibraryAnalytics — создание базы данных
-- MS SQL Server
-- =========================================

CREATE DATABASE LibraryAnalytics;
GO

USE LibraryAnalytics;
GO

-- =========================================
-- Таблица: Authors
-- =========================================
CREATE TABLE Authors (
    author_id     INT IDENTITY(1,1) PRIMARY KEY,
    first_name    NVARCHAR(50)  NOT NULL,
    last_name     NVARCHAR(50)  NOT NULL,
    country       NVARCHAR(50)  NULL,
    birth_year    INT           NULL
);
GO

-- =========================================
-- Таблица: Genres
-- =========================================
CREATE TABLE Genres (
    genre_id      INT IDENTITY(1,1) PRIMARY KEY,
    genre_name    NVARCHAR(50)  NOT NULL UNIQUE
);
GO

-- =========================================
-- Таблица: Publishers
-- =========================================
CREATE TABLE Publishers (
    publisher_id  INT IDENTITY(1,1) PRIMARY KEY,
    publisher_name NVARCHAR(100) NOT NULL,
    country       NVARCHAR(50)  NULL
);
GO

-- =========================================
-- Таблица: Books
-- =========================================
CREATE TABLE Books (
    book_id       INT IDENTITY(1,1) PRIMARY KEY,
    title         NVARCHAR(200) NOT NULL,
    author_id     INT           NOT NULL,
    genre_id      INT           NOT NULL,
    publisher_id  INT           NOT NULL,
    publish_year  INT           NULL,
    isbn          NVARCHAR(20)  NULL,
    total_copies  INT           NOT NULL DEFAULT 1,
    CONSTRAINT FK_Books_Authors FOREIGN KEY (author_id) REFERENCES Authors(author_id),
    CONSTRAINT FK_Books_Genres FOREIGN KEY (genre_id) REFERENCES Genres(genre_id),
    CONSTRAINT FK_Books_Publishers FOREIGN KEY (publisher_id) REFERENCES Publishers(publisher_id)
);
GO

-- =========================================
-- Таблица: Readers
-- =========================================
CREATE TABLE Readers (
    reader_id     INT IDENTITY(1,1) PRIMARY KEY,
    first_name    NVARCHAR(50)  NOT NULL,
    last_name     NVARCHAR(50)  NOT NULL,
    email         NVARCHAR(100) NULL,
    phone         NVARCHAR(20)  NULL,
    registration_date DATE     NOT NULL DEFAULT CAST(GETDATE() AS DATE)
);
GO

-- =========================================
-- Таблица: Loans (выдача книг)
-- =========================================
CREATE TABLE Loans (
    loan_id       INT IDENTITY(1,1) PRIMARY KEY,
    book_id       INT           NOT NULL,
    reader_id     INT           NOT NULL,
    loan_date     DATE          NOT NULL,
    due_date      DATE          NOT NULL,
    return_date   DATE          NULL,
    status        NVARCHAR(20)  NOT NULL DEFAULT 'active',  -- active / returned / overdue
    CONSTRAINT FK_Loans_Books FOREIGN KEY (book_id) REFERENCES Books(book_id),
    CONSTRAINT FK_Loans_Readers FOREIGN KEY (reader_id) REFERENCES Readers(reader_id),
    CONSTRAINT CHK_Loans_Status CHECK (status IN ('active', 'returned', 'overdue'))
);
GO

-- =========================================
-- Таблица: Fines (штрафы за просрочку)
-- =========================================
CREATE TABLE Fines (
    fine_id       INT IDENTITY(1,1) PRIMARY KEY,
    loan_id       INT           NOT NULL,
    amount        DECIMAL(8,2) NOT NULL,
    issued_date   DATE          NOT NULL DEFAULT CAST(GETDATE() AS DATE),
    paid          BIT           NOT NULL DEFAULT 0,
    CONSTRAINT FK_Fines_Loans FOREIGN KEY (loan_id) REFERENCES Loans(loan_id)
);
GO

-- =========================================
-- Индексы для ускорения аналитических запросов
-- =========================================
CREATE INDEX IX_Loans_ReaderId ON Loans(reader_id);
CREATE INDEX IX_Loans_BookId ON Loans(book_id);
CREATE INDEX IX_Books_GenreId ON Books(genre_id);
GO
