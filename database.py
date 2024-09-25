import pyodbc
import os
import logging
from dotenv import load_dotenv
import pandas as pd
import streamlit as st

load_dotenv()

class DatabaseManager:
    def __init__(self):
        # self.server = os.getenv("DB_SERVER")
        # self.database = os.getenv("DB_NAME")
        # self.username = os.getenv("DB_USERNAME")
        # self.password = os.getenv("DB_PASSWORD")
        self.server = st.secrets.get("DB_SERVER")
        self.database = st.secrets.get("DB_NAME")
        self.username = st.secrets.get("DB_USERNAME")
        self.password = st.secrets.get("DB_PASSWORD")
        self.conn = None
        self.cursor = None

    def connect(self):
        """Establish a connection to the SQL Server database."""
        try:
            logging.warning(self.server)
            self.conn = pyodbc.connect(
                f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                f"SERVER={self.server};"
                f"DATABASE={self.database};"
                f"UID={self.username};"
                f"PWD={self.password};"
                f"Timeout=30;"
            )
            self.cursor = self.conn.cursor()
            logging.warning("Database connection established.")
        except pyodbc.Error as e:
            logging.error(f"Error connecting to SQL Server: {e}")

    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()
            logging.warning("Database connection closed.")
            
    def load_content_data(self):
        """Load all content data from the database."""
        query = """
        SELECT id, title, title_persian, date, content, content_persian, url, author, views, source, 
               summary, summary_persian, final_score, type
        FROM Content
        ORDER BY date DESC
        """
        try:
            df = pd.read_sql(query, self.conn)
            logging.warning("Loaded content data from the database.")
            return df
        except pyodbc.Error as e:
            logging.error(f"Error loading content data: {e}")
            return pd.DataFrame()

    def load_images(self, content_id):
        """Load images associated with a specific content item."""
        query = """
        SELECT image_url
        FROM ContentImages
        WHERE content_id = ?
        """
        try:
            df = pd.read_sql(query, self.conn, params=[content_id])
            logging.warning(f"Loaded images for content ID {content_id}.")
            return df
        except pyodbc.Error as e:
            logging.error(f"Error loading images: {e}")
            return pd.DataFrame()
        
    def load_tags(self, content_id):
        """Load tags associated with a specific content item."""
        query = """
        SELECT t.tag
        FROM ContentTags ct
        JOIN Tags t ON ct.tag_id = t.id
        WHERE ct.content_id = ?
        """
        try:
            df = pd.read_sql(query, self.conn, params=[content_id])
            logging.warning(f"Loaded tags for content ID {content_id}.")
            return df
        except pyodbc.Error as e:
            logging.error(f"Error loading tags for content ID {content_id}: {e}")
            return pd.DataFrame()
        
    def content_exists(self, url):
        """Check if a content item already exists in the database by its URL."""
        self.ensure_connection() 
        query = "SELECT COUNT(*) FROM Content WHERE url = ?"
        try:
            self.cursor.execute(query, (url,))
            count = self.cursor.fetchone()[0]
            return count > 0
        except pyodbc.Error as e:
            logging.error(f"Error checking if content exists: {e}")
            return False
        
    def alter_tables_for_unicode(self):
        """Alter tables to ensure they support Unicode characters."""
        alter_content_table_sql = """
        IF OBJECT_ID('Content', 'U') IS NOT NULL
        BEGIN
            -- Alter columns to NVARCHAR(MAX) for Unicode support
            IF COL_LENGTH('Content', 'content') IS NOT NULL
            BEGIN
                ALTER TABLE Content
                ALTER COLUMN content NVARCHAR(MAX);
            END

            IF COL_LENGTH('Content', 'content_persian') IS NOT NULL
            BEGIN
                ALTER TABLE Content
                ALTER COLUMN content_persian NVARCHAR(MAX);
            END

            IF COL_LENGTH('Content', 'summary') IS NOT NULL
            BEGIN
                ALTER TABLE Content
                ALTER COLUMN summary NVARCHAR(MAX);
            END

            IF COL_LENGTH('Content', 'summary_persian') IS NOT NULL
            BEGIN
                ALTER TABLE Content
                ALTER COLUMN summary_persian NVARCHAR(MAX);
            END
        END
        """

        try:
            self.cursor.execute(alter_content_table_sql)
            self.conn.commit()
            logging.warning("Tables altered to support Unicode characters.")
        except pyodbc.Error as e:
            logging.error(f"Error altering tables: {e}")

    def create_tables(self):
        """Create necessary tables if they don't exist, or alter them to match the current item structure."""
        # Create or update Content table
        create_or_alter_content_table_sql = """
        IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[Content]') AND type in (N'U'))
        BEGIN
            CREATE TABLE Content (
                id INT IDENTITY(1,1) PRIMARY KEY,
                title NVARCHAR(255),
                title_persian NVARCHAR(255),
                date DATETIME,
                content NVARCHAR(MAX),           -- Changed from TEXT to NVARCHAR(MAX)
                content_persian NVARCHAR(MAX),    -- Changed from TEXT to NVARCHAR(MAX)
                url NVARCHAR(500),
                author NVARCHAR(255),
                views INT,
                source NVARCHAR(255),
                summary NVARCHAR(MAX),            -- Changed from TEXT to NVARCHAR(MAX)
                summary_persian NVARCHAR(MAX),    -- Changed from TEXT to NVARCHAR(MAX)
                final_score FLOAT,
                type NVARCHAR(100)
            );
        END
        ELSE
        BEGIN
            -- Alter table to add new columns if they don't already exist
            IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID(N'[dbo].[Content]') AND name = 'title_persian')
                ALTER TABLE Content ADD title_persian NVARCHAR(255);
            IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID(N'[dbo].[Content]') AND name = 'content_persian')
                ALTER TABLE Content ADD content_persian TEXT;
            IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID(N'[dbo].[Content]') AND name = 'summary_persian')
                ALTER TABLE Content ADD summary_persian TEXT;
        END
        """

        create_images_table_sql = """
        IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[ContentImages]') AND type in (N'U'))
        BEGIN
            CREATE TABLE ContentImages (
                id INT IDENTITY(1,1) PRIMARY KEY,
                content_id INT,
                image_url NVARCHAR(500),
                FOREIGN KEY (content_id) REFERENCES Content(id) ON DELETE CASCADE
            );
        END
        """
        create_tags_table_sql = """
        IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[Tags]') AND type in (N'U'))
        BEGIN
            CREATE TABLE Tags (
                id INT IDENTITY(1,1) PRIMARY KEY,
                tag NVARCHAR(255) UNIQUE
            );
        END
        """

        create_content_tags_table_sql = """
        IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[ContentTags]') AND type in (N'U'))
        BEGIN
            CREATE TABLE ContentTags (
                content_id INT,
                tag_id INT,
                PRIMARY KEY (content_id, tag_id),
                FOREIGN KEY (content_id) REFERENCES Content(id) ON DELETE CASCADE,
                FOREIGN KEY (tag_id) REFERENCES Tags(id) ON DELETE CASCADE
            );
        END
        """
        try:
            self.cursor.execute(create_or_alter_content_table_sql)
            self.cursor.execute(create_images_table_sql)
            self.cursor.execute(create_tags_table_sql)
            self.cursor.execute(create_content_tags_table_sql)
            self.alter_tables_for_unicode()
            self.conn.commit()
            logging.warning("Tables created or verified successfully.")
        except pyodbc.Error as e:
            logging.error(f"Error creating or altering tables: {e}")



    def ensure_connection(self):
        """Ensure that the database connection is active, and reconnect if necessary."""
        try:
            self.conn.cursor().execute("SELECT 1")
        except pyodbc.Error:
            logging.warning("Database connection lost. Reconnecting...")
            self.connect()

    def insert_content_item(self, item):
        """Insert a content item into the database and return the inserted row's ID."""
        self.ensure_connection()  # Ensure connection is active before inserting
        insert_sql = """
        INSERT INTO Content (title, title_persian, date, content, content_persian, url, author, views, source, summary, summary_persian, final_score, type)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        values = (
            item.get('title', ''),
            item.get('title_persian', ''), 
            item['date'],
            item.get('content', ''),
            item.get('content_persian', ''),
            item['url'],
            item['author'],
            item.get('views', 0),
            item['source'],
            item.get('summary', ''),
            item.get('summary_persian', ''), 
            item.get('final_score', 0),
            item.get('type', 'News')
        )
        
        try:
            self.cursor.execute(insert_sql, values)
            self.cursor.execute("SELECT @@IDENTITY AS ID")  # Get the newly inserted content ID
            content_id = self.cursor.fetchone()[0]
            self.conn.commit()

            logging.warning(f"Inserted content item into database: {item['title']}, ID: {content_id}")
            
            # Insert tags and link them to the content
            if 'tags' in item:
                tag_ids = self.insert_tags(item['tags'])
                self.insert_content_tags(content_id, tag_ids)

            return content_id
        except pyodbc.Error as e:
            print(item)
            logging.error(f"Error inserting item into database: {e}")
            return None


    def insert_images(self, content_id, images):
        """Insert multiple images for a given content item."""
        sql = """
        INSERT INTO ContentImages (content_id, image_url)
        VALUES (?, ?)
        """
        try:
            for image_url in images:
                self.cursor.execute(sql, (content_id, image_url))
            self.conn.commit()
            logging.warning(f"Inserted {len(images)} images for content item ID {content_id}.")
        except pyodbc.Error as e:
            logging.error(f"Error inserting images into database: {e}")
            
    def insert_translation(self, content_id, translation):
        """Insert or update the Persian translation for a given content item."""
        self.ensure_connection()

        update_sql = """
        UPDATE Content
        SET content_persian = ?
        WHERE id = ?
        """
        
        try:
            self.cursor.execute(update_sql, (translation, content_id))
            self.conn.commit()
            logging.warning(f"Inserted/updated Persian translation for content ID {content_id}.")
        except pyodbc.Error as e:
            logging.error(f"Error inserting translation for content ID {content_id}: {e}")

       
            
    def insert_tags(self, tags):
        """Insert tags into the Tags table and return their IDs."""
        tag_ids = []
        for tag in tags:
            select_sql = "SELECT id FROM Tags WHERE tag = ?"
            insert_sql = "INSERT INTO Tags (tag) VALUES (?)"

            try:
                self.cursor.execute(select_sql, (tag,))
                row = self.cursor.fetchone()

                if row:
                    tag_ids.append(row[0])
                else:
                    self.cursor.execute(insert_sql, (tag,))
                    self.cursor.execute("SELECT @@IDENTITY AS ID")
                    new_tag_id = self.cursor.fetchone()[0]
                    tag_ids.append(new_tag_id)

            except pyodbc.Error as e:
                logging.error(f"Error inserting tag '{tag}': {e}")
        
        return tag_ids
    
    def insert_content_tags(self, content_id, tag_ids):
        """Link content with tags in the ContentTags table."""
        insert_sql = "INSERT INTO ContentTags (content_id, tag_id) VALUES (?, ?)"
        
        try:
            for tag_id in tag_ids:
                self.cursor.execute(insert_sql, (content_id, tag_id))
            self.conn.commit()
            logging.warning(f"Linked {len(tag_ids)} tags to content ID {content_id}.")
        except pyodbc.Error as e:
            logging.error(f"Error linking tags to content: {e}")




db_manager = DatabaseManager()
db_manager.connect()
db_manager.create_tables()
