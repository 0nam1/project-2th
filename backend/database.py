# database.py

from databases import Database
import sqlalchemy
from dotenv import load_dotenv
import os

load_dotenv()
mysql_pw = os.getenv("MYSQLPW")
mysql_id = os.getenv("MYSQLID")
mysql_ip = os.getenv("MYSQLIP")
mysql_db = os.getenv("MYSQLDB")


DATABASE_URL = f"mysql+pymysql://{mysql_pw}:{mysql_pw}@{mysql_ip}/{mysql_db}"

database = Database(DATABASE_URL)