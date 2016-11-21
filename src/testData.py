import urllib
import settings
import Constants
from collections import Counter
import string

def testValidate(referer,entry_dict):

    print settings.mc.get(referer)

    if referer in settings.mc:
            test_dict= settings.mc[referer]

            print test_dict
            print "%%%%%%%%%%%%%%%%%"
            print entry_dict
            for key in test_dict:
                for k in entry_dict:
                    if key == k:
                        value = settings.mc[referer][key]
                        print key

                        print k
                        print entry_dict
                        print value
                        print "!!!!!!!!!!!!!!"
                        print entry_dict[k]
                        print "count len char set"
                        if entry_dict[k]['length'] <= value['length'] and (entry_dict[k]['characterSet'] or value['characterSet']):
                            print "TEST PASS PROCEED TO SERVER BUT HOW???"

                        else:
                            print "TEST FAIL SEND SOME MISCHIVIOUS TO CONSOLE"
                            return -1

                        print value['count']
                        print value['length']
                        print value['characterSet']

                # value=settings.mc.get(key)
                # count = value['count']
                # length = value['length']
                # charset = value['characterSet']
                #print key
                print "##########################"
                # print count
                # print length
                # print charset
    return 1





# def testHeader(request):
#     if hasattr(request, 'headers'):
#          print request.headers
#          print "header present"
#     else:
#         print "No header attribute"
#         return False
#
#         # code to train WAF with header params
#     return True

def findCharacterSet(s):
    bitmap = 0
    # if s.isdigit():
    #     bitmap |= Constants.HAS_NUM_ONLY
    #     print "digits only"
    #
    # elif s.isalpha():
    #     bitmap |= Constants.HAS_AL_ONLY
    #     print "alpha only"

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

    return entry_dict

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


    print(entry_dict)
    return [referer,entry_dict]





def testValues(request):
    if hasattr(request, 'command'):
        print request.command
    else:
        print "No command attribute"
        return
    referer, entry_dict = splitValues(request)
    if referer != False and entry_dict != False:
        entry_dict = get_counts_dict(entry_dict)
    else:
        return
    print "%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%"
    print referer
    print entry_dict
    print  "&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&"
    check =testValidate(referer,entry_dict)
    if check == 1:
         print "reaching here testvalidate 1"
         return 1
    else:
        print "reaching here testvalidate -1"
        return -1



def testRequest(request):
    status = testValues(request)
    return status