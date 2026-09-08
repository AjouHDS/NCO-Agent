from dotenv import load_dotenv
import os
load_dotenv() 


config = {
    "host": os.getenv("DATABASE_HOST"),
    "database": os.getenv("DATABASE_DATABASE"),
    "user": os.getenv("DATABASE_USER"),
    "password": os.getenv("DATABASE_PASSWORD"),
    "port": 1433,
    "schema": "dbo"
}