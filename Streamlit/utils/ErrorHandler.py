import time
import random

class DatabaseError(Exception):
    pass

class BrokerError(Exception):
    pass

class MessageLoopError(Exception):
    pass

class ConfError(Exception):
    pass

class SettError(Exception):
    pass

class CatError(Exception):
    pass