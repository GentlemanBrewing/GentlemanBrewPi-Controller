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
        self.processes = {
            'Steam Boiler': {'Temperature': 90, 'Setpoint': 92},
            'Fermenter1': {'Temperature': 17, 'Setpoint': 17},
            'Fermenter2': {'Temperature': 18, 'Setpoint': 18},
            'Fermenter3': {'Temperature': 19, 'Setpoint': 19}
        }
        self.process_output = {}
        self.process_output = self.processinformation
        self.processes = self.processinformation
        print(self.processes)

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
        print('web server started')
        while True:
            # Generate data for webserver
            for process, variables in self.processes.items():
                variables['Temperature'] += 1
                if process == 'Steam Boiler':
                    if variables['Temperature'] > 95:
                        variables['Temperature'] = 90
                else:
                    if variables['Temperature'] > 22:
                        variables['Temperature'] = 17
                self.process_output[process] = variables

            # Put updated data in queue
            self.inputqueue.put(self.process_output)

            # Sleep
            time.sleep(10)


if __name__ == "__main__":
    webgen = WebTest()
    webgen.start()
