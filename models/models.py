import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base

from config import CONFIG

Base = declarative_base()

engine = create_engine(CONFIG.DATABASE_CONNECTION, future=True)
if CONFIG.SQL_LOGGING:
    logging.basicConfig()
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
db_session = Session(bind=engine, future=True)


def auto_str(cls):
    def __repr__(self):
        value = ", ".join(
            "{}={}".format(*item)
            for item in vars(self).items()
            if item[0] != "_sa_instance_state"
        )
        return f"{type(self).__name__} {{{value}}}"

    cls.__repr__ = __repr__
    return cls
