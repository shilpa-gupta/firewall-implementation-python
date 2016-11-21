import tornado
import socket
import processData

class SessionFactory(object):
    def __init__(self):
        pass

    def new(self, *args, **kwargs):
        return Session(*args, **kwargs)

    def delete(self, session):
        assert (isinstance(session, Session))
        del session


class Session(object):

    class State:
        def __int__(self):
            pass
        CLOSED, CONNECTING, CONNECTED = range(3)

    def __init__(self):
        pass

    def new_connection(self, stream, address, proxy):
        assert isinstance(stream, tornado.iostream.IOStream)
        self.proxy = proxy
        self.c2p_reading = False
        self.c2p_writing = False
        self.p2s_writing = False
        self.p2s_reading = False
        self.c2p_stream = stream
        self.c2p_address = address
        self.c2p_state = Session.State.CONNECTED
        self.c2s_queued_data = []
        self.s2c_queued_data = []

        self.c2p_stream.set_nodelay(True)
        self.c2p_stream.set_close_callback(self.on_c2p_close)

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)

        if self.proxy.server_ssl_options is not None:
            self.p2s_stream = tornado.iostream.SSLIOStream(s, ssl_options=self.proxy.server_ssl_options)
        else:
            self.p2s_stream = tornado.iostream.IOStream(s)
        self.p2s_stream.set_nodelay(True)
        self.p2s_stream.set_close_callback(self.on_p2s_close)
        self.p2s_state = self.p2s_state = Session.State.CONNECTING
        self.p2s_stream.connect((proxy.target_server, proxy.target_port), self.on_p2s_done_connect)
        self.c2p_start_read()

    def c2p_start_read(self):
        assert (not self.c2p_reading)
        self.c2p_reading = True
        try:
            self.c2p_stream.read_until_close(lambda x: None, self.on_c2p_done_read)
        except tornado.iostream.StreamClosedError:
            self.c2p_reading = False

    def p2s_start_read(self):
        assert (not self.p2s_reading)
        self.p2s_reading = True
        try:
            self.p2s_stream.read_until_close(lambda x: None, self.on_p2s_done_read)
        except tornado.iostream.StreamClosedError:
            self.p2s_reading = False

    def on_c2p_done_read(self, data):
        assert (self.c2p_reading)
        assert (data)
        if processData.parseData(data):
            self.p2s_start_write(data)
        else:
            #data = "you are doing something mischevious\n"
            data = processData.prep_error_response("you are doing something mischevious")
            self.c2p_start_write(data)
            self.p2s_stream.close()


    def on_p2s_done_read(self, data):
        assert (self.p2s_reading)
        assert (data)
        self.c2p_start_write(data)

    def _c2p_io_write(self, data):
        if data is None:
            # None means (gracefully) close-socket  (a "close request" that was queued...)
            self.c2p_state = Session.State.CLOSED
            try:
                self.c2p_stream.close()
            except tornado.iostream.StreamClosedError:
                self.c2p_writing = False
        else:
            self.c2p_writing = True
            try:
                self.c2p_stream.write(data, callback=self.on_c2p_done_write)
            except tornado.iostream.StreamClosedError:
                # Cancel the write, we will get on_close instead...
                self.c2p_writing = False

    def _p2s_io_write(self, data):
        if data is None:
            self.p2s_state = Session.State.CLOSED
            try:
                self.p2s_stream.close()
            except tornado.iostream.StreamClosedError:
                self.p2s_writing = False
        else:
            self.p2s_writing = True
            try:
                self.p2s_stream.write(data, callback=self.on_p2s_done_write)
            except tornado.iostream.StreamClosedError:
                self.p2s_writing = False

    def c2p_start_write(self, data):
        if self.c2p_state != Session.State.CONNECTED: return

        if not self.c2p_writing:
            # If we're not currently writing
            assert (not self.s2c_queued_data)  # we expect the  queue to be empty

            # Start the "real" write I/O operation
            self._c2p_io_write(data)
        else:
            # Just add to the queue
            self.s2c_queued_data.append(data)

    def p2s_start_write(self, data):
        if self.p2s_state == Session.State.CONNECTING:
            self.c2s_queued_data.append(data)
            return
        if self.p2s_state == Session.State.CLOSED:
            return
        assert (self.p2s_state == Session.State.CONNECTED)

        if not self.p2s_writing:
            self._p2s_io_write(data)
        else:
            self.c2s_queued_data.append(data)

    def on_c2p_done_write(self):
        assert (self.c2p_writing)
        if self.s2c_queued_data:
            self._c2p_io_write(self.s2c_queued_data.pop(0))
            return
        self.c2p_writing = False

    def on_p2s_done_write(self):
        assert (self.p2s_writing)
        if self.c2s_queued_data:
            self._p2s_io_write(self.c2s_queued_data.pop(0))
            return
        self.p2s_writing = False

    def c2p_start_close(self, gracefully=True):
        if self.c2p_state == Session.State.CLOSED:
            return
        if gracefully:
            self.c2p_start_write(None)
            return

        self.c2p_state = Session.State.CLOSED
        self.s2c_queued_data = []
        self.c2p_stream.close()
        if self.p2s_state == Session.State.CLOSED:
            self.remove_session()

    def p2s_start_close(self, gracefully=True):
        if self.p2s_state == Session.State.CLOSED:
            return
        if gracefully:
            self.p2s_start_write(None)
            return

        self.p2s_state = Session.State.CLOSED
        self.c2s_queued_data = []
        self.p2s_stream.close()
        if self.c2p_state == Session.State.CLOSED:
            self.remove_session()

    def on_c2p_close(self):
        self.c2p_state = Session.State.CLOSED
        if self.p2s_state == Session.State.CLOSED:
            self.remove_session()
        else:
            self.p2s_start_close(gracefully=True)

    def on_p2s_close(self):
        self.p2s_state = Session.State.CLOSED
        if self.c2p_state == Session.State.CLOSED:
            self.remove_session()
        else:
            self.c2p_start_close(gracefully=True)

    def on_p2s_done_connect(self):
        assert (self.p2s_state == Session.State.CONNECTING)
        self.p2s_state = Session.State.CONNECTED
        self.p2s_start_read()
        assert (not self.p2s_writing)

        if self.c2s_queued_data:
            self.p2s_start_write(self.c2s_queued_data.pop(0))

    def remove_session(self):
        self.proxy.remove_session(self)



