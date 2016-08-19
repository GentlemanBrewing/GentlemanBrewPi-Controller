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
        self.write_message(QueueMonitor.processdictionary)

    def on_close(self):
      print('connection closed')

    @classmethod
    def send_updates(cls, index):
        for waiter in cls.waiters:
            try:
                waiter.write_message(index)
                print('msg sent to waiters')
            except:
                print("Error sending message")

class IndexHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    def get(self):
        #self.write("This is your response")
        processdict = QueueMonitor.processdictionary
        outputlist = ['Temperature', 'Setpoint']
        dictionarylist = ["setpoint", "relayduty", "relaypin"]
        counter = 0

        strvar = ""
        newdict = {"Steam Boiler": 100, "Fermenter1": 10, "Fermenter2": 12, "Fermenter3": 30}
        list = ["Item1", "Item2", "Item4"]
        self.render("newindex.html", items=list, pdict=processdict, newdict=newdict, strvar=strvar, outputlist=outputlist, dictionarylist=dictionarylist, counter=counter )
        print("new web page opened")
        #we don't need self.finish() because self.render() is fallowed by self.finish() inside tornado
        #self.finish()


application = tornado.web.Application([
    (r'/ws', WSHandler),
    (r'/', IndexHandler),
])
class QueueMonitor(threading.Thread):

    processdictionary = {}

    def __init__(self, inputqueue, outputqueue):
        threading.Thread.__init__(self)
        self.inputqueue = inputqueue
        self.outputqueue = outputqueue
        self.newinput = {}
        self.newoutput = {}
        self.processdata = {}
        self.inputdifference = {}

    def run(self):

        print('queuemonitor started')
        # Check for new data from main process every second
        while True:
            while True:
                try:
                    self.newinput = self.inputqueue.get_nowait()
                    for process, variables in self.newinput.items():
                        # If process is not in dictionary create it and add whole process to difference dictionary
                        if process not in self.processdata:
                            self.processdata[process] = variables
                            self.inputdifference[process] = variables
                        # If process variables are not the same as the new variables update the required variables
                        elif self.processdata[process] != variables:
                            self.inputdifference[process] = {}
                            for key, variable in variables.items():
                                if self.processdata[process][key] != variable:
                                    self.processdata[process][key] = variable
                                    self.inputdifference[process][key] = variable

                    WSHandler.send_updates(self.inputdifference)
                    QueueMonitor.processdictionary = self.processdata
                    self.inputdifference = {}
                except queue.Empty:
                    break

            # sleep
            time.sleep(1)

def main(inputqueue, outputqueue):

    QueueMonitor(inputqueue, outputqueue).start()
    #time.sleep(10) # Ensure Queuemonitor has time to initialize before starting tornado
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(8000)
    tornado.ioloop.IOLoop.instance().start()
    print('webserver started')

if __name__ == "__main__":
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(8000)
    tornado.ioloop.IOLoop.instance().start()