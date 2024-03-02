import sys

from sqlalchemy import create_engine, exc
from sqlalchemy_utils import database_exists, create_database

from const import PROTOCOL, USER, PASSWORD, HOST, PORT, DB_NAME
from models import create_tables


def create_db():
    try:
        dsn = f"{PROTOCOL}://{USER}:{PASSWORD}@{HOST}:{PORT}/{DB_NAME}"
        engine = create_engine(dsn)
        if not database_exists(engine.url):
            create_database(engine.url)
    except exc.ArgumentError as err:
        print('Incorrect DSN connection string. Details:', err)
        sys.exit()
    else:
        return engine


if __name__ == '__main__':
    engine = create_db()
    create_tables(engine)
