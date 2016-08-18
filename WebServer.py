#! /usr/bin/env python3

import tornado.ioloop
import tornado.web
import tornado.websocket
import tornado.httpserver
import threading
import multiprocessing
import time
import queue

class WSHandler(tornado.websocket.WebSocketHandler):
    waiters = set()

    def open(self):
        self.set_nodelay(True)
        print('new connection')
        self.write_message("Hello World")
        WSHandler.waiters.add(self)

    def on_message(self, message):
        print('message received %s' % message)
        self.write_message('You wrote: %s' % message )

    def on_close(self):
      print('connection closed')

    @classmethod
    def send_updates(cls, index):
        for waiter in cls.waiters:
            try:
                waiter.write_message(index)
            except:
                print("Error sending message")

class IndexHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    def get(self):
        #self.write("This is your response")
        newdict = {"Steam Boiler": 100, "Fermenter1": 10, "Fermenter2": 12, "Fermenter3": 30}
        pdict = {"Steam Boiler": 90, "Fermenter1": 17, "Fermenter2": 18, "Fermenter3": 19}
        list = ["Item1", "Item2", "Item4"]
        self.render("index.html", items=list, pdict=pdict, newdict=newdict)
        print("new web page opened")
        #we don't need self.finish() because self.render() is fallowed by self.finish() inside tornado
        #self.finish()

application = tornado.web.Application([
    (r'/ws', WSHandler),
    (r'/', IndexHandler),
])

def queuemonitor(inputqueue, outputqueue):
    # Check for new data from main process
    print('queuemonitor started')
    data = {}
    while True:
        while True:
            try:
                data = inputqueue.get_nowait()
                WSHandler.send_updates(data)
                print('data aquired')
            except queue.Empty:
                print('no data')
                break
        # sleep
        time.sleep(1)

def main(inputqueue, outputqueue):

    threading.Thread(target=queuemonitor, args=(inputqueue, outputqueue)).start()
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(8000)
    tornado.ioloop.IOLoop.instance().start()

if __name__ == "__main__":
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(8000)
    tornado.ioloop.IOLoop.instance().start()