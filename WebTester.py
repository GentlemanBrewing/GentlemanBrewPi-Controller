#! /usr/bin/env python3

import multiprocessing
import queue
import time
import WebServer

class TestWeb(multiprocessing.Process):
    def __init__(self):
        multiprocessing.Process.__init__(self)
        self.processes = {'Steam Boiler': 90, 'Fermenter1': 17, 'Fermenter2': 18, 'Fermenter3': 19,}
        self.outputdict = {}

        # create communication queues
        self.inputqueue = multiprocessing.Queue
        self.outputqueue = multiprocessing.Queue

    def run(self):
        #start web server
        WebServer.main(self.inputqueue, self.outputqueue)
        while True:
            # Generate data for webserver
            for process, temp in self.processes.items():
                temp += 1
                if process == 'Steam Boiler':
                    if temp > 95:
                        temp = 90
                else:
                    if temp > 22:
                        temp = 17
                self.processes[process] = temp

            # Put updated data in queue
            self.outputqueue.put_nowait(self.processes)






if __name__ == "__main__":
    man = TestWeb()
    man.start()
    man.join()