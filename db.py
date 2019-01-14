from datetime import datetime

from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

engine = create_engine(
    'sqlite:///svitla.db', echo=False
)

Base = declarative_base()
Session = sessionmaker(bind=engine)
session = Session()


class Route(Base):
    __tablename__ = 'route'

    id = Column(Integer, primary_key=True)
    completed = Column(Boolean(), default=False)
    validated = Column(Boolean(), default=False)
    uploaded = Column(DateTime(), default=datetime.now())

class Instruction(Base):
    __tablename__ = 'instruction'

    id = Column(Integer, primary_key=True)
    route = Column(Integer, ForeignKey('route.id'))
    step = Column(Integer)
    x_direction = Column(Integer)
    y_direction = Column(Integer)
    distance = Column(Integer)
    start_x = Column(Integer)
    start_y = Column(Integer)


class Landmark(Base):
    __tablename__ = 'landmark'

    id = Column(Integer, primary_key=True)
    x_coordinate = Column(Integer)
    y_coordinate = Column(Integer)
    name = Column(String(100))

    def __str__(self):
        return self.name


directions = {
    "West": (-1, 0),
    "East": (1, 0),
    "South": (0, -1),
    "North": (0, 1),
}

Base.metadata.create_all(engine)
