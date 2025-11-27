from .db import Base, engine
from .lead import Lead
from .conversation import Conversation
from .message import Message

def create_all():
    Base.metadata.create_all(bind=engine)
