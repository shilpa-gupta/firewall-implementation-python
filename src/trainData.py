import urllib
import settings
import Constants
from collections import Counter
import string

values_dict = {'requestCount': 0, 'maxParams': 0}


def merge_entry(refererURL, entry_dict):
    #settings.referer_dict[refererURL]

    print entry_dict
    #if dictionary is already present for the referer URL, get it.
    #Else init a new empty one

    if not settings.mc.get(refererURL):
        merge_dict = {}
    else:
        merge_dict = settings.mc[refererURL]


    for key in entry_dict:

        if key not in merge_dict:
            merge_dict[key] = {}
        for k in entry_dict[key]:
            if k not in merge_dict[key]:
                merge_dict[key][k] = 0
            if k == 'length':
                merge_dict[key][k] += entry_dict[key][k]
            if k == 'characterSet':
                merge_dict[key][k] |= entry_dict[key][k]
            if k == 'count':
                merge_dict[key][k] += 1


    if 'maxParams' not in merge_dict:
            merge_dict['maxParams'] = 0


    merge_dict['maxParams'] = max(merge_dict['maxParams'], len(entry_dict))

    print "Merge dict"
    print merge_dict

    #add the merge_dict to memcache key of refererURL
    settings.mc[refererURL] = merge_dict


    #Check and update the max_parameters in memcache
    if not settings.mc.get('maxParams'):
            settings.mc['maxParams'] = 0

    prevMax = settings.mc.get('maxParams')
    settings.mc['maxParams'] = max(prevMax, len(entry_dict))


    print settings.mc['maxParams']

def trainHeader(request):
    if hasattr(request, 'headers'):
         print request.headers
         print "header present"


    else:
        print "No header attribute"
        return False

    # code to train WAF with header params
    return True


def findCharacterSet(s):
    bitmap = 0

    if any(c.isalpha() for c in s):
        bitmap |= Constants.HAS_AL
        print "has alpha"

    if any(c.isdigit() for c in s):
        bitmap |= Constants.HAS_NUM
        print "has num"

    if any(char in Constants.specialChars for char in s):
        bitmap |=  Constants.HAS_SYMBOL
        print "has symbol"

    print s
    print bin(bitmap)
    print "*************"
    return bitmap



def get_counts_dict(entry_dict):

    for entry in entry_dict:
        # add the bitmap corresponding to character set of the parameter
        entry_value = entry_dict[entry]
        entry_length = len(entry_dict[entry])
        entry_dict[entry] = {}
        # Update the average length of the parameter for the specific URL
        entry_dict[entry]['characterSet'] = findCharacterSet(entry_value)

        entry_dict[entry]['length'] = entry_length

        #To sum +1 to the cache
        entry_dict[entry]['count'] = 1

    return entry_dict


def processEntries(refererURL, entry_dict):
    print "referer: "+refererURL
    #refererURL = request.headers.getheader('Referer')
    if refererURL == None:
        print "BLLLLLL"
        return
    with settings.lock:
        if refererURL not in settings.referer_dict:
            # Create a new dictionary for the referer URL if not present already
            settings.referer_dict[refererURL] = {}
            settings.referer_dict[refererURL]['count'] = 0
            settings.referer_dict[refererURL]['maxParams'] = 0


        settings.referer_dict[refererURL]['count'] += 1
        settings.referer_dict[refererURL]['maxParams'] = max(settings.referer_dict[refererURL]['maxParams'],
                                                             len(entry_dict))

        # for entry in entry_dict:
        #     #add the bitmap corresponding to character set of the parameter
        #     entry_value = entry_dict[entry]
        #     entry_length = len(entry_dict[entry])
        #     entry_count = settings.referer_dict[refererURL]['count']
        #
        #     entry_dict[entry] = {}
        #     #Update the average length of the parameter for the specific URL
        #     entry_dict[entry]['characterSet'] = findCharacterSet(entry_value)
        #
        #
        #     # average length of characters for the value entry
        #     #entry_dict[entry]['averageLength'] = ( entry_dict[entry]['averageLength'] * (entry_count - 1)+ entry_length )/entry_count
        #     entry_dict[entry]['length'] = entry_length

        entry_dict = get_counts_dict(entry_dict)
        print "ENTRY DICT* "
        print entry_dict
        print(settings.referer_dict)
        print("######################\n")


def splitValues(request):
    print(request.command)
    print "PATH = "+request.path
    entry_dict = {}
    paramString = ""
    referer = ""
    if request.command == "GET":

            paramString = request.path.split('?')
            referer =paramString[0]

            print "REFERER = "+referer


            if len(paramString) == 2:
                paramString = paramString[1]
            else:
                print("no need to go")
                return [False, False]
    elif request.command == "POST":
            referer = request.path
            paramString = request.post_body

    else:
        print "not get/post"

    print "PARAM STRING = "+paramString

    bodyEntries = paramString.split('&')

    correct_values = False
    for entry in bodyEntries:
        entry = entry.split('=')

        if len(entry) == 2:  # to prevent garbage/unknown requests

            correct_values = True

            #decode the characters which were encoded during HTTP request conversion
            entry[0] = urllib.unquote_plus(entry[0])
            entry[1] = urllib.unquote_plus(entry[1])
            entry_dict[entry[0]] = entry[1]

        else:
            print "BAD PARAMS"
            return [False,False]

    if correct_values == True:
        values_dict['requestCount'] += 1


    print(entry_dict)
    return [referer,entry_dict]





def trainValues(request):
    if hasattr(request, 'command'):
        print request.command
    else:
        print "No command attribute"
        return

    # print(request.post_body)
    referer, entry_dict = splitValues(request)

    print "********"
    print referer
    print entry_dict
    if referer != False and entry_dict != False:
        processEntries(referer, entry_dict)
    else:
        return -1


    values_dict['maxParams'] = max(values_dict['maxParams'], len(entry_dict))

    merge_entry(referer,entry_dict)

    print "From cache: "
    print settings.mc['maxParams']



def trainRequest(request):
    result = trainHeader(request)

    if result == True:
        trainValues(request)



