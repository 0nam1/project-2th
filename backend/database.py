# database.py

from databases import Database
import sqlalchemy

DATABASE_URL = "mysql+pymysql://root:1234@localhost/testdb"

database = Database(DATABASE_URL)
