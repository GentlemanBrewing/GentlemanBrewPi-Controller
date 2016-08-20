#! /usr/bin/env python3

import tornado.ioloop
import tornado.web
import tornado.websocket
import tornado.httpserver
import threading
import time
import queue
import json

class WSHandler(tornado.websocket.WebSocketHandler):
    waiters = set()

    def open(self):
        self.set_nodelay(True)
        print('new connection')
        WSHandler.waiters.add(self)
        self.write_message(QueueMonitor.processJSON)

    def on_message(self, message):
        print('message received %s' % message)
        QueueMonitor.updatequeues(message)
        #self.write_message(QueueMonitor.processdictionary)

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
        # Variables needed for web page generation
        processdict = QueueMonitor.processdictionary
        outputlist = ['Temperature', 'Setpoint']
        dictionarylist = ["setpoint", "relayduty", "relaypin"]
        counter = 0

        strvar = ""
        newdict = {"Steam Boiler": 100, "Fermenter1": 10, "Fermenter2": 12, "Fermenter3": 30}
        list = ["Item1", "Item2", "Item4"]
        self.render("newindex.html", items=list, pdict=processdict, newdict=newdict, strvar=strvar, outputlist=outputlist, dictionarylist=dictionarylist, counter=counter )
        print("new web page opened")


application = tornado.web.Application([
    (r'/ws', WSHandler),
    (r'/', IndexHandler),
])
class QueueMonitor(threading.Thread):

    processdictionary = {}
    processJSON = ""
    runninginstances = set()

    def __init__(self, inputqueue, outputqueue):
        threading.Thread.__init__(self)
        QueueMonitor.runninginstances.add(self)
        self.inputqueue = inputqueue
        self.outputqueue = outputqueue
        self.newinput = {}
        self.newoutput = {}
        self.processdata = {}
        self.inputdifference = {}
        self.jsoninputdifference = ""

    def sendtomanager(self,data):
        self.newoutput = json.loads(data)
        print(data)
        self.outputqueue.put(self.newoutput)

    @classmethod
    def updatequeues(cls, data):
        for instance in cls.runninginstances:
            instance.sendtomanager(data)

    def run(self):

        print('queuemonitor started')
        # Check for new data from main process
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
                    self.jsoninputdifference = json.dumps(self.inputdifference, sort_keys=True)
                    WSHandler.send_updates(self.jsoninputdifference)
                    QueueMonitor.processdictionary = self.processdata
                    QueueMonitor.processJSON = json.dumps(self.processdata,sort_keys=True)
                    self.inputdifference = {}
                except queue.Empty:
                    break

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