#!/usr/bin/python

import time
from lib.mylogger import MyLogger

from datetime import datetime

from collections import defaultdict

import paramiko
import socket
import os
import zipfile
from threading import Thread
from queue import Queue

THREAD_NO = 20

now = datetime.now()
start_time = time.time()
cdt_string = now.strftime("%d-%m-%Y-%H-%M-%S")

r_user = 'username'
r_pass = 'password'
r_port = 22


routers = [{"name": 'host01',
            "ip": '192.168.0.1'}
           ]

for router in routers:
    print(router)


commands = ["show version",
            "show chassis routing-engine"]

log = MyLogger("log", "collector.log")

logging = log.getlogger()
d = defaultdict(int)
sfolder = os.path.dirname(os.path.realpath(__file__))
currentdatetime = datetime.now().strftime('%Y%m%d%H%M%S')
temp_dir_list = [sfolder, "collector-temp", currentdatetime]
temp_dir = os.path.join(*temp_dir_list)


class ProcessExt(Thread):
    def __init__(self, queue, final_result, commands):
        """Init the object."""
        Thread.__init__(self)
        self.queue = queue
        self.final_result = final_result
        self.result = {}
        self.commands = commands
        self.cdt = datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')

    def run(self):
        """Run the run."""
        while True:
            router = self.queue.get()
            result = self.ssh_connect(router["ip"], self.commands)
            self.create_files(result, router["name"], temp_dir)
            self.final_result.append(result)
            self.queue.task_done()

    def ssh_connect(self, ip, commands):
        """Standard paramiko implementation."""
        client = paramiko.SSHClient()
        client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            client.connect(ip, username=r_user, password=r_pass)
            result = []
            for item in commands:
                logging.debug(item)
                stdin, stdout, stderr = client.exec_command(item.strip())
                logging.debug(stderr)
                result_before = stdout.read()
                logging.debug(result_before)
                result_command = [item, result_before]
                result.append(result_command)
            logging.info("Success!! connection")
        except paramiko.AuthenticationException:
            logging.info("Authentication problem")
            result = None
        except socket.error:
            logging.info("Comunication problem")
            result = None
        client.close()
        return result

    def create_files(self, result, new_rname, temp_dir):
        """Write to file."""
        logging.info("creating files")
        filename = temp_dir + "/" + new_rname + ".txt"
        logging.info(filename)
        logging.info("Writing to the file...".format(filename))
        target = open(filename, 'w')
        for item in result:
            command = str(item[0]).center(100, '-') + "\r\n"
            target.write(str(command))
            target.write(str(item[1]))
        target.close


def main():
    """Main Function."""
    print("collector running..")
    global commands
    queue = Queue()
    final_result = []
    task = True
    if task:
        print('task found')
        create_folder(temp_dir)

        #pp(commands)

        for x in range(THREAD_NO):
            worker = ProcessExt(queue, final_result, commands)
            worker.setName(x)
            worker.daemon = True
            worker.start()

        for router in routers:
            queue.put(router)
            print(router["name"], router["ip"])

        queue.join()
        #pp(final_result)
        end_time = time.time()
        total_time = end_time - start_time
        logging.info("Script end time:{}, script total time:{}".format(end_time,
                                                                       total_time))
        zip(currentdatetime, temp_dir)
        # task.completed_date = datetime.utcnow()
        # task.completed = True
        # task.result = "result/" + currentdatetime + '.zip'

    else:
        print("no task")


def create_folder(tem_dir):
    """Create a new folder."""
    if not os.path.exists(tem_dir):
        os.makedirs(tem_dir)


def zip(currentdatetime, temp_dir):
    """Create zip file."""
    dst = "result/" + currentdatetime
    zf = zipfile.ZipFile("%s.zip" % (dst), "w", zipfile.ZIP_DEFLATED)
    abs_src = os.path.abspath(temp_dir)
    for dirname, subdirs, files in os.walk(temp_dir):
        for filename in files:
            absname = os.path.abspath(os.path.join(dirname, filename))

            arcname = absname[len(abs_src) + 1:]
            logging.info('zipping %s as %s' % (os.path.join(dirname, filename),
                         arcname))

            zf.write(absname, arcname)
    zf.close()


def commands_split(command):
    """Split commands."""
    return command.splitlines()

if __name__ == "__main__":
    main()
