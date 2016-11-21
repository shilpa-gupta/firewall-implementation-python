import threading

def init():
    global mod
    global mc
    # dictionary structure for referer_dict
    #     Key => referer URL
    #     values => another dictionary
    #             => This dictionary will have key as each request body parameter(like name, id etc.)
    #                 and value as its corresponding value
    # TODO : move to cache

    global referer_dict
    referer_dict = {}

    #lock for the dictionary
    global lock
    lock = threading.Lock()

