import datetime

from sqlalchemy import Column, String, Boolean, Integer, func
from sqlalchemy import DateTime, Text
from sqlalchemy import ForeignKey
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class ElementModel(Base):
    __tablename__ = 'elements'

    id = Column(String, primary_key=True)
    type = Column(String, nullable=False)
    name = Column(String, nullable=False)
    chainlit_key = Column(String)
    url = Column(String)
    object_key = Column(String)
    path = Column(String)
    display = Column(String, nullable=False)
    size = Column(String)
    for_id = Column(String)
    language = Column(String)
    mime = Column(String)
    content = Column(String)
    page = Column(Integer)
    thread_id = Column(String)
    persisted = Column(Boolean, default=False)
    updatable = Column(Boolean, default=False)

    def __repr__(self):
        return f"<ElementModel(id='{self.id}'>"


class PersistedUserModel(Base):
    __tablename__ = 'users'

    id = Column(String, primary_key=True)
    identifier = Column(String, nullable=False)
    createdAt = Column(String, nullable=False)
    metadata_ = Column(JSON)  # Using JSON field for metadata

    def __repr__(self):
        return f"<PersistedUser(id='{self.id}', identifier='{self.identifier}')>"


class Feedback(Base):
    __tablename__ = 'feedback'

    id = Column(Integer, primary_key=True)
    for_id = Column(String)
    value = Column(ENUM('-1', '0', '1', name="feedback_value_enum", create_type=False))
    strategy = Column(String, default='BINARY')
    comment = Column(String, nullable=True)

    def __repr__(self):
        return f"<Feedback(id={self.id}, for_id='{self.for_id}')>"

    # Relationship to StepModel
    # step = relationship("StepModel", back_populates="feedback")


class ThreadModel(Base):
    __tablename__ = 'threads'

    id = Column(String, primary_key=True)
    name = Column(String, nullable=True)
    createdAt = Column(String, nullable=False)
    metadata_ = Column(JSON)
    user_id = Column(String, ForeignKey('users.id'), nullable=True)
    tags = Column(JSON)

    # Relationship to PersistedUserModel
    user = relationship("PersistedUserModel", backref="threads")

    def __repr__(self):
        return f"<ThreadModel(id='{self.id}', name='{self.name}')>"


# PersistedUserModel.threads = relationship("ThreadModel", order_by=ThreadModel.id, back_populates="user")


class StepModel(Base):
    __tablename__ = 'steps'

    id = Column(String, primary_key=True)
    thread_id = Column(String, ForeignKey('threads.id'), nullable=False)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)
    input = Column(Text)
    output = Column(Text)
    metadata_ = Column(JSON)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    start_time = Column(DateTime)
    end_time = Column(DateTime)

    # Relationships
    thread = relationship("ThreadModel", back_populates="steps")

    def __repr__(self):
        return f"<StepModel(id='{self.id}', name='{self.name}', type='{self.type}')>"


ThreadModel.steps = relationship("StepModel", order_by=StepModel.id, back_populates="thread")
