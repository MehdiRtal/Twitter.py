import string
import secrets
import random


def generate_csrf_token():
    return "".join([hex(x)[-1] for x in secrets.token_bytes(32)])

def generate_transaction_id():
    return "".join(random.choice(string.ascii_letters + string.digits + "+/") for _ in range(93))
