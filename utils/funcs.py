import random
from datetime import datetime


def UserGen(org_name):
    initials = ''.join(word[0].upper() for word in org_name.split(' '))
    num = str(random.randint(1, 99999))
    username = 'U' + initials + num
    return username

def TimeDiff(date1, date2):
    format_str = "%Y-%m-%d %H:%M:%S"
    datetime1 = datetime.strptime(date1, format_str)
    datetime2 = datetime.strptime(date2, format_str)
    timedelta = datetime2 - datetime1
    seconds = int(timedelta.total_seconds())
    return seconds