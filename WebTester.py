#! /usr/bin/env python3

import multiprocessing
import queue
import time
import yaml
import WebServer


class WebTest(multiprocessing.Process):

    def __init__(self):
        multiprocessing.Process.__init__(self)
        self.processinformation = self.loadconfig('Config.yaml')
        print("config loaded")
        self.processes = {'Steam Boiler': 90, 'Fermenter1': 17, 'Fermenter2': 18, 'Fermenter3': 19}
        self.process_output = {}
        self.process_output = self.processes

        # create communication queues
        self.inputqueue = multiprocessing.Queue()
        self.outputqueue = multiprocessing.Queue()

    # Function for loading config file
    def loadconfig(self, filename):
        f = open(filename)
        datamap = yaml.safe_load(f)
        f.close()
        return datamap

    def run(self):
        print("starting to run")
        # put data in queue
        self.inputqueue.put(self.process_output)
        # start web server
        webserv = multiprocessing.Process(target=WebServer.main, args=(self.inputqueue, self.outputqueue))
        webserv.start()
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
                self.process_output[process] = temp

            # Put updated data in queue
            self.inputqueue.put(self.process_output)

            print("data in queue")
            print(self.process_output)

            # Sleep
            time.sleep(10)


if __name__ == "__main__":
    man = WebTest()
    man.start()
    man.join()
