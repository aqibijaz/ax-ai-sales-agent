from .db import engine, Base
from .lead import Lead
from .conversation import Conversation

def create_all():
    Base.metadata.create_all(bind=engine)
