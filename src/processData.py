from BaseHTTPServer import BaseHTTPRequestHandler
from StringIO import StringIO
import settings
import trainData
import re
import urllib
import testData

class HTTPRequest(BaseHTTPRequestHandler):
    def __init__(self, request_text):
        self.rfile = StringIO(request_text)
        self.raw_requestline = self.rfile.readline()
        self.error_code = self.error_message = None
        self.parse_request()
        if hasattr(self, 'headers'):
            content_len = int(self.headers.getheader('content-length', 0))
            print content_len
            self.post_body = self.rfile.read(content_len)



    def send_error(self, code, message):
        self.error_code = code
        self.error_message = message


def printRequest(request):

    print "command " + request.command  # "GET"
    print "path " + request.path  # "/who/ken/trust.html"
    print "version " + request.request_version  # "HTTP/1.1"
    print "len = " + str(len(request.headers))  # 3
    print  request.headers.keys()  # ['accept-charset', 'host', 'accept']
    print "host : " + request.headers['host']  # "cm.bell-labs.com"
    print "body : " + request.post_body

    if not request.error_code == None:
        print request.error_code  # 400
        print request.error_message  # "Bad request syntax ('GET')"


def parseData(data):

    request = HTTPRequest(data)
   # printRequest(request)

    # if err
    if not request.error_code == None:
        print request.error_code
        return

    # try:
    #     printRequest(request)
    # except AttributeError:
    #     print "Request header not present !"


    if settings.mod == 'train':
        #For training, send the parsed data to trainData.py
            print "Entered train mode"
            print"REQUEST RECV"
            trainData.trainRequest(request)
    elif settings.mod == 'test':
        print "validating signature"
        status = signatureValidation(request)
        if (status == -1):
            print "mischevious signature"
            return False
        print "signature validation successful"
        status = 1
        print "Entering testData File"
        status = testData.testRequest(request)
        if (status == -1):
            print "Anomaly validation failed"
            return False

    return  True


def signatureValidation(request):
    status = 1

    regex_sqlattack = r"\b(?i)(ALTER|CREATE|DELETE|DROP|EXEC(UTE){0,1}|INSERT( +INTO){0,1}|MERGE|SELECT|UPDATE|UNION( +ALL){0,1})\b"

    # The above regular expression says to search for the word,
    # ALTER, CREATE, DELETE, DROP, EXEC, EXECUTE, INSERT, INSERT INTO, MERGE, SELECT, UPDATE, UNION
    # or UNION ALL. The \b at the beginning and ending tell the regular expression engine to search for
    # whole word matches. That is, the word CREATED should not be treated as a match because it contains the
    # letters that make the word CREATE.

    regex_otherattack = r"(?i)((<script|script>)|(\b(bot)\b)|(\.\.\/))"

    raw_HeaderValueString = ''
    raw_ParamValueString = ''
    print "in signature validation"

    for value in request.headers.keys():
        raw_HeaderValueString = raw_HeaderValueString + str(request.headers.getrawheader(value))

    if re.search(regex_sqlattack,raw_HeaderValueString) or \
        re.search(regex_otherattack, raw_HeaderValueString):
        status = -1
        return status

    try:
        val_Command = request.command
    except AttributeError as e:
        print e.message
        return status

    if val_Command == 'GET':
        try:
            val_Parameters = request.path
        except AttributeError as e:
            print e.message
            return status
        val_Parameters = val_Parameters.split('?')
        if (len(val_Parameters) > 1):
            val_Parameters = val_Parameters[1]
        else:
            val_Parameters = val_Parameters[0]

        raw_ParamValueString = prep_ParamString(val_Parameters)

        if re.search(regex_sqlattack, raw_ParamValueString) or \
                re.search(regex_otherattack, raw_ParamValueString):
            status = -1
            return status
    else:
        try:
          #  content_len = int(request.headers.getheader('content-length', 0))
          #  val_Parameters = request.rfile.read(content_len)
          val_Parameters = request.post_body
        except AttributeError as e:
            print e.message
            return status
        raw_ParamValueString = prep_ParamString(val_Parameters)

        if re.search(regex_sqlattack, raw_ParamValueString) or \
                re.search(regex_otherattack, raw_ParamValueString):
            status = -1
            return status

    return status


def prep_ParamString(parameters):
    bodyEntries = parameters.split('&')
    param_ValueString = ''
    for entry in bodyEntries:
        entry = entry.split('=')
        if len(entry) == 2:  # concatenate all value strings
            #decode the characters which were encoded during HTTP request conversion
            entry[0] = urllib.unquote_plus(entry[0])
            entry[1] = urllib.unquote_plus(entry[1])
            param_ValueString = param_ValueString + str(entry[1])
        else:
            return parameters

    return param_ValueString


def prep_error_response(message):
    print message
    response_body_raw = '<html><body><h1> %s </h1></body></html>' % message
    # response_body_raw = ''.join(response_body)
    response_headers = {
        'Content-Type': 'text/html; encoding=utf8',
        'Content-Length': len(response_body_raw),
        'Connection': 'close',
    }
    response_headers_raw = ''.join('%s: %s\n' % (k, v) for k, v in \
                                   response_headers.iteritems())

    response_proto = 'HTTP/1.1'
    response_status = '400'
    response_status_text = 'page cannot be displayed'

    response = response_proto + ' ' + response_status + ' ' + response_status_text + '\n' + response_headers_raw + \
               '\n' + response_body_raw
    return response


