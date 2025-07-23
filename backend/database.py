# database.py
from databases import Database
import sqlalchemy
from dotenv import load_dotenv
import os

load_dotenv()
dbpassword = os.getenv("MYSQLPW")

DATABASE_URL = f"mysql+pymysql://7aiteam3:{dbpassword}@20.196.112.223:3306/gympt_db"

database = Database(DATABASE_URL)
