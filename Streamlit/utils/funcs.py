import random

def UserGen(org_name):
    initials = ''.join(word[0].upper() for word in org_name.split(' '))
    num = str(random.randint(1, 99999))
    username = 'U' + initials + num
    return username