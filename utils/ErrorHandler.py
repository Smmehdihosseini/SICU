import time
import random

class DatabaseError(Exception):
    pass

class BrokerError(Exception):
    pass

class MessageLoopError(Exception):
    pass