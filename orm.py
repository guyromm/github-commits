import sqlalchemy as sa
from sqlalchemy.ext.declarative import declarative_base
engine = sa.create_engine('mysql://root@localhost/agg?charset=utf8', echo=True)
Base = declarative_base()
from sqlalchemy import Column, Integer, String, Numeric, Date, DateTime
from sqlalchemy.orm import sessionmaker
Session = sessionmaker(bind=engine)
s = Session()

class OdeskWork(Base):
    __tablename__='odesk_work'
    provider = Column(String(length=32),nullable=False,primary_key=True)
    worked_on = Column(Date,nullable=False,primary_key=True)
    memo = Column(String(length=32),primary_key=True)
    task = Column(String(length=32),nullable=True)
    hours = Column(Numeric(precision=13,scale=2),nullable=False)

class Repo(Base):
    __tablename__='repos'
    host = Column(String(length=32),nullable=False,primary_key=True)
    name = Column(String(length=32),nullable=False,primary_key=True)
    
class Commit(Base):
    __tablename__='commits'
    repo = Column(String(length=32),nullable=False,primary_key=True)
    rev = Column(String(length=40),nullable=False,primary_key=True)
    author = Column(String(length=64),nullable=False)
    commited_on = Column(DateTime(),nullable=False)
    message = Column(String(length=128),nullable=False)
    task = Column(String(length=32),nullable=True)
    size = Column(Integer(),nullable=False)

Base.metadata.create_all(engine)
