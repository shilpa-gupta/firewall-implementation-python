#!/usr/bin/env python
import tornado
import tornado.tcpserver
import session
import iomanager
from session import SessionFactory
from session import Session
import settings
import sys
import Constants
import pylibmc

class ProxyServer(tornado.tcpserver.TCPServer):

    def __init__(self,
                 target_server, target_port,
                 client_ssl_options=None, server_ssl_options=None,
                 session_factory=SessionFactory(),
                 *args, **kwargs):
        self.session_factory = session_factory

        self.target_server = target_server
        self.target_port = target_port

        self.client_ssl_options = client_ssl_options
        self.server_ssl_options = server_ssl_options

        if self.server_ssl_options is True:
            self.server_ssl_options = {}
        if self.server_ssl_options is False:
            self.server_ssl_options = None
        if self.client_ssl_options is False:
            self.client_ssl_options = None

        self.SessionsList = []

        super(ProxyServer, self).__init__(ssl_options=self.client_ssl_options, *args, **kwargs)

    def handle_stream(self, stream, address):
        assert isinstance(stream, tornado.iostream.IOStream)
        session = self.session_factory.new()
        session.new_connection(stream, address, self)
        self.SessionsList.append(session)

    def remove_session(self, session):
        assert (isinstance(session, Session))
        assert (session.p2s_state == Session.State.CLOSED)
        assert (session.c2p_state == Session.State.CLOSED)
        if session in self.SessionsList:
            self.SessionsList.remove(session)
        self.session_factory.delete(session)

    def get_connections_count(self):
        return len(self.SessionsList)


if(len(sys.argv) > 2 or len(sys.argv) < 2):
    print("Invalid number of arguments passed\n")
    exit()
cmd = sys.argv[1]
if(cmd == 'reset'):
    mod = "reset"
elif(cmd == 'start_train'):
    mod = "train"
elif(cmd == 'start_test'):
    mod = "test"
else:
    print("Please pass a valid command")
    exit()

settings.init()
settings.mc = pylibmc.Client([Constants.MEMCACHE_SERVER], binary=True,behaviors={"tcp_nodelay": True,"ketama": True})
settings.mod = mod
if settings.mod == 'reset':
    print("reseting cache\n")
    settings.mc.flush_all()
    exit()

g_IOManager = iomanager.IOManager()
server = ProxyServer(Constants.HOST_SERVER_IP, Constants.WEB_HOST_PORT)
server.listen(Constants.RP_PORT)
g_IOManager.add(server)
tornado.ioloop.IOLoop.instance().start()
