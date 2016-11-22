"""
Constants.py
"""

import string

HOST_NAME = "localhost"
HOST_IP = "127.0.0.1"
RP_PORT = 80
WEB_HOST_PORT = 8008
SKT_BUF_SIZE = 4096
HOST_SERVER_IP = "127.0.0.1"
MEMCACHE_PORT = 11211
MEMCACHE_SERVER = "127.0.0.1"


#

#Character set definitions
HAS_AL           =    1
HAS_NUM          =    2
HAS_SYMBOL       =    4

specialChars = set(string.punctuation+' ')
