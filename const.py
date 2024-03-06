from environs import Env
from sqlalchemy.orm import declarative_base

env = Env()
env.read_env()
PROTOCOL = env('PROTOCOL')
USER = env('USER')
PASSWORD = env.int('PASSWORD')
HOST = env('HOST')
PORT = env.int('PORT')
DB_NAME = env('DB_NAME')
GROUP_TOKEN = env('GROUP_TOKEN')
USER_TOKEN = env('USER_TOKEN')

Base = declarative_base()
