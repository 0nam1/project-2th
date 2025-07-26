# database.py

from databases import Database
import sqlalchemy

DATABASE_URL = "mysql+pymysql://7aiteam3:7aiteam3@20.196.112.223/gympt_db"

database = Database(DATABASE_URL)