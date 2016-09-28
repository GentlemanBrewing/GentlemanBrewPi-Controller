#! /usr/bin/env python3

import tornado.ioloop
import tornado.web
import tornado.websocket
import tornado.httpserver
import threading
import time
import queue
import json
import yaml

class WSHandler(tornado.websocket.WebSocketHandler):
    waiters = set()

    def open(self):
        self.set_nodelay(True)
        print('new connection')
        self.write_message(QueueMonitor.processJSON)
        self.write_message(QueueMonitor.processtemplateJSON)
        time.sleep(2)
        WSHandler.waiters.add(self)

    def on_message(self, message):
        QueueMonitor.updatequeues(message)

    def on_close(self):
        WSHandler.waiters.remove(self)
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
        # Variables needed for web page generation
        processdict = QueueMonitor.processdictionary
        outputlist = ['Temperature', 'Setpoint', 'Duty', 'DateTime', 'SafetyTemp', 'SafetyTrigger', 'Status']
        dictionarylist = ["setpoint", "relayduty", "relaypin"]
        processtemplate = QueueMonitor.processtemplate
        counter = 0


        self.render("index.html", pdict=processdict, outputlist=outputlist, dictionarylist=dictionarylist, counter=counter, ptemp=processtemplate )
        print("new web page opened")


application = tornado.web.Application([
    (r'/ws', WSHandler),
    (r'/', IndexHandler),
])
class QueueMonitor(threading.Thread):

    processdictionary = {}
    processtemplate = {}
    processtemplateJSON = ""
    processJSON = ""
    runninginstances = set()

    def __init__(self, inputqueue, outputqueue):
        threading.Thread.__init__(self)
        print('Queuemonitor started')
        QueueMonitor.runninginstances.add(self)
        QueueMonitor.processtemplate = self.loadconfig('Template.yaml')
        QueueMonitor.processtemplateJSON = json.dumps(QueueMonitor.processtemplate, sort_keys=True)
        self.inputqueue = inputqueue
        self.outputqueue = outputqueue
        self.newinput = {}
        self.newoutput = {}
        self.processdata = {}
        self.inputdifference = {}
        self.jsoninputdifference = ""
        self.iterations = 0

    # Function for loading config file
    def loadconfig(self, filename):
        try:
            f = open(filename)
        except FileNotFoundError:
            print('%s not found loading Default' % filename)
            defaultfilename = "Default" + filename
            f = open(defaultfilename)
        datamap = yaml.safe_load(f)
        f.close()
        return datamap

    def sendtomanager(self,data):
        self.newoutput = json.loads(data)
        self.outputqueue.put(self.newoutput)
        print('data in outputqueue - QueueManager')
        #print(self.newoutput)


    @classmethod
    def updatequeues(cls, data):
        for instance in cls.runninginstances:
            instance.sendtomanager(data)

    def run(self):
        # Check for new data from main process
        while True:
            while True:
                try:
                    deletelist = []
                    self.newinput = self.inputqueue.get_nowait()
                    # Delete processes no longer running
                    for process in self.processdata.keys():
                        if process not in self.newinput:
                            deletelist.append(process)
                    for process in deletelist:
                        del self.processdata[process]

                    for process in self.newinput.keys():
                        # If process is not in dictionary create process add whole process to difference dictionary
                        if process not in self.processdata:
                            self.processdata[process] = self.newinput[process]
                            self.inputdifference[process] = self.newinput[process]
                        # If process variables are not the same as the new variables update the required variables
                        elif self.processdata[process] != self.newinput[process]:
                            self.inputdifference[process] = {}
                            for variable in self.newinput[process].keys():
                                if variable not in self.processdata[process]:
                                    self.processdata[process][variable] = ""
                                if self.processdata[process][variable] != self.newinput[process][variable]:
                                    self.processdata[process][variable] = self.newinput[process][variable]
                                    self.inputdifference[process][variable] = self.newinput[process][variable]
                    self.jsoninputdifference = json.dumps(self.inputdifference, sort_keys=True)
                    WSHandler.send_updates(self.jsoninputdifference)
                    #self.processdata = self.newinput
                    QueueMonitor.processdictionary = self.processdata
                    QueueMonitor.processJSON = json.dumps(self.processdata,sort_keys=True)
                    self.inputdifference = {}
                except queue.Empty:
                    break

            if self.iterations > 60:
                QueueMonitor.processtemplate = self.loadconfig('Template.yaml')
                QueueMonitor.processtemplateJSON = json.dumps(QueueMonitor.processtemplate, sort_keys=True)
                self.iterations = 0
            self.iterations += 1

            time.sleep(1)

def main(inputqueue, outputqueue):

    QueueMonitor(inputqueue, outputqueue).start()
    #time.sleep(10) # Ensure Queuemonitor has time to initialize before starting tornado
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(8000)
    print('Tornado started')
    tornado.ioloop.IOLoop.instance().start()
    print('Tornado Exiting')

if __name__ == "__main__":
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(8000)
    tornado.ioloop.IOLoop.instance().start()