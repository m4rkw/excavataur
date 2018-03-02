#!/usr/bin/env python

import time
import os
import signal
import sys
import yaml
from log import Log
from config import Config
import json
import socket
import threading
import daemon
import subprocess
from multiprocessing import Queue, Manager
import multiprocessing
from subprocess import Popen
import re
import select
import fcntl

from ccminer import Ccminer
from ccminer2 import Ccminer2
from xmrig_nvidia import Xmrig_Nvidia
from ethminer import Ethminer
from ewbf import Ewbf

class Excavataur:
  def __init__(self):
    Config().load()
    Config().validate()

    if self.already_running():
      Log().add('fatal', 'excavataur is already running')

    self.create_pid_file()

    self.algorithms = {}

    signal.signal(signal.SIGINT, self.sigint_handler)


  def already_running(self):
    if not os.path.exists("/var/run/excavataur"):
      try:
        ok.mkdir("/var/run/excavataur", 0755)
      except:
        Log().add('fatal', 'unable to create /var/run/excavataur')

    if os.path.exists("/var/run/excavataur/excavataur.pid"):
      pid = open("/var/run/excavataur/excavataur.pid").read().rstrip()

      return pid.isdigit() and os.path.exists("/proc/%s" % (pid))


  def create_pid_file(self):
    if self.already_running():
      Log().add('fatal', 'unable to start, there is another excavataur process running')

    with open("/var/run/excavataur/excavataur.pid", "w") as f:
      f.write("%d" % (os.getpid()))


  def usage(self):
    print "usage: %s <miner> <port>" % (sys.argv[0])
    sys.exit(0)


  def sigint_handler(self, a, b):
    Log().add('info', 'interrupt received, cleaning up')

    for miner_name in self.algorithms.keys():
      for algorithm_id in self.algorithms[miner_name].keys():
        for device_id in self.algorithms[miner_name][algorithm_id]['workers'].keys():
          self.terminate_process(self.algorithms[miner_name][algorithm_id]['workers'][device_id]['handle'])

    sys.exit(0)


  def terminate_process(self, handle):
    handle.terminate()
    handle.wait()


  def startup(self):
    Log().add('info', 'Excavataur initialising')

    self.manager = multiprocessing.Manager()
    self.worker_queue_in = self.manager.Queue()

    self.sockets = {}

    for miner_name in Config().get('miners').keys():
      port = Config().get('miners')[miner_name]['port']
      Log().add('info', 'starting excavataur daemon for miner: %s on port %d' % (miner_name, port))

      self.sockets[miner_name] = socket.socket()
      self.sockets[miner_name].setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
      self.sockets[miner_name].setblocking(0)
      self.sockets[miner_name].bind(('127.0.0.1', Config().get('miners')[miner_name]['port']))
      self.sockets[miner_name].listen(1)

    pipes = []

    x = 0

    while True:
      for miner_name in Config().get('miners').keys():
        readable, writable, errored = select.select([self.sockets[miner_name]], [], [], 0)

        if self.sockets[miner_name] in readable:
          conn, address = self.sockets[miner_name].accept()

          parent_queue = self.manager.Queue()
          child_queue = self.manager.Queue()

          thread = threading.Thread(target=self.handle_client, args=[conn, parent_queue, child_queue])
          thread.daemon = True
          thread.start()

          pipes.append({
            "miner_name": miner_name,
            "parent": parent_queue,
            "child": child_queue,
            "handle": thread
          })

      new_pipes = []

      for pipe in pipes:
        if not pipe['parent'].empty():
          message = pipe['parent'].get()
          resp = self.command(pipe['miner_name'], message['command'], message['params'])
          pipe['child'].put(resp)

        if pipe['handle'].is_alive():
          new_pipes.append(pipe)

      pipes = new_pipes

      if not self.worker_queue_in.empty():
        message = self.worker_queue_in.get()
        if message['miner_name'] in self.algorithms.keys() and message['algorithm_id'] in self.algorithms[message['miner_name']].keys() and message['device_id'] in self.algorithms[message['miner_name']][message['algorithm_id']]['workers'].keys():
          self.algorithms[message['miner_name']][message['algorithm_id']]['workers'][message['device_id']]['hashrate'] = message['hashrate']

      time.sleep(0.01)
      x += 1

      if x >= 50:
        self.cleanup_dead_workers()


  def handle_client(self, sock, parent_queue, child_queue):
    sock.setblocking(1)

    try:
      while True:
        msg = sock.recv(4096)
        sock.send(self.handle_message(msg, parent_queue, child_queue) + "\n")
    except socket.error:
      pass


  def handle_message(self, buf, parent_queue, child_queue):
    try:
      data = json.loads(buf)
    except:
      return json.dumps({"error": "invalid command"})

    if "method" in data.keys() and "params" in data.keys():
      parent_queue.put({
        "command": data["method"],
        "params": data["params"]
      })

      timeout = 30
      start = time.time()

      while child_queue.empty() and (time.time() - start) < timeout:
        time.sleep(0.1)

      if child_queue.empty():
        return json.dumps({"error": "timed out waiting for a response"})

      return json.dumps(child_queue.get())

    return json.dumps({"error": "invalid message"})


  def command(self, miner_name, method, params):
    if method == "algorithm.add":
      algorithm = params[0]
      endpoint = params[1]
      auth = params[2]

      if len(params) >3:
        backup_endpoint = params[3]
      else:
        backup_endpoint = None

      return self.add_algorithm(miner_name, algorithm, endpoint, auth, backup_endpoint)
    if method == "worker.add":
      algorithm_id = int(params[0])
      device_id = int(params[1])

      return self.add_worker(miner_name, algorithm_id, device_id)
    if method == "algorithm.list":
      resp = {"algorithms": [], "error": None}

      if miner_name in self.algorithms.keys():
        for algorithm_id in self.algorithms[miner_name].keys():
          algorithm = {
            "algorithm_id": algorithm_id,
            "name": self.algorithms[miner_name][algorithm_id]['algorithm'],
            "pools": [{
              "address": self.algorithms[miner_name][algorithm_id]['endpoint'],
              "login": self.algorithms[miner_name][algorithm_id]['auth']
            }],
            "workers": []
          }

          for device_id in self.algorithms[miner_name][algorithm_id]['workers'].keys():
            algorithm['workers'].append({
              "device_id": device_id,
              "speed": [self.algorithms[miner_name][algorithm_id]['workers'][device_id]['hashrate'], 0]
            })

          resp["algorithms"].append(algorithm)

      return resp
    if method == "algorithm.remove":
      if not miner_name in self.algorithms.keys():
        return {"error": "algorithm not found"}

      algorithm_id = int(params[0])

      if not algorithm_id in self.algorithms[miner_name].keys():
        return {"error": "algorithm not found"}

      if self.remove_algorithm(miner_name, int(algorithm_id)):
        return {"error": None}
      else:
        return {"error": "failed to stop algorithm"}


  def add_algorithm(self, miner_name, algorithm, endpoint, auth, backup_endpoint = None):
    if not miner_name in self.algorithms.keys():
      self.algorithms[miner_name] = {}

    if len(self.algorithms[miner_name]) == 0:
      algorithm_id = 1
    else:
      algorithm_id = max(self.algorithms[miner_name].keys()) + 1

    self.algorithms[miner_name][algorithm_id] = {
      "algorithm": algorithm,
      "endpoint": endpoint,
      "auth": auth,
      "backup_endpoint": backup_endpoint,
      "workers": {}
    }

    Log().add('info', 'added algorithm %d: %s at %s using auth %s' % (algorithm_id, algorithm, endpoint, auth))

    return {"error": None, "algorithm_id": algorithm_id}


  def remove_algorithm(self, miner_name, algorithm_id):
    if miner_name not in self.algorithms.keys() or algorithm_id not in self.algorithms[miner_name].keys():
      Log().add('error', 'request to remove algorithm %d for miner %s but it was not found' % (algorithm_id, miner_name))
      return False

    for device_id in self.algorithms[miner_name][algorithm_id]['workers'].keys():
      Log().add('info', '%s [%d]: stopping working for algorithm %s' % (miner_name, device_id, self.algorithms[miner_name][algorithm_id]['algorithm']))

      self.terminate_process(self.algorithms[miner_name][algorithm_id]['workers'][device_id]['handle'])

    self.algorithms[miner_name].pop(algorithm_id, None)

    Log().add('info', 'removed algorithm %d for miner %s' % (algorithm_id, miner_name))

    return True


  def add_worker(self, miner_name, algorithm_id, device_id):
    if not miner_name in self.algorithms.keys():
      return {"error": "miner has no algorithms"}

    if not algorithm_id in self.algorithms[miner_name].keys():
      return {"error": "algorithm not found"}

    if device_id in self.algorithms[miner_name][algorithm_id]["workers"].keys():
      return {"error": "device is already running this algorithm"}

    handle = self.create_worker_process(miner_name, algorithm_id, device_id)

    if not handle:
      return {"error": "failed to create worker process"}

    Log().add('info', '%s [%d]: starting worker for algorithm %s' % (miner_name, device_id, self.algorithms[miner_name][algorithm_id]['algorithm']))

    self.algorithms[miner_name][algorithm_id]["workers"][device_id] = {
      "handle": handle,
      "hashrate": 0
    }

    return {"error": None}


  def create_worker_process(self, miner_name, algorithm_id, device_id):
    miner = eval("%s()" % (miner_name.title()))

    username, password = self.algorithms[miner_name][algorithm_id]['auth'].split(":")

    args = [Config().get('miners')[miner_name]['path']]

    algorithm = self.algorithms[miner_name][algorithm_id]['algorithm']

    if algorithm in miner.algo_remap.keys():
      algorithm = miner.algo_remap[algorithm]

    if miner_name == "ethminer":
      param_map = {
        "device_id": str(device_id),
        "primary_endpoint": self.algorithms[miner_name][algorithm_id]['endpoint'],
        "failover_endpoint": self.algorithms[miner_name][algorithm_id]['backup_endpoint'],
        "username": username,
      }
    elif miner_name == "ewbf":
      server, port = self.algorithms[miner_name][algorithm_id]['endpoint'].split(':')
      param_map = {
        "device_id": str(device_id),
        "server": server,
        "port": port,
        "username": username,
        "password": password
      }
    else:
      param_map = {
        "algorithm": algorithm,
        "device_id": str(device_id),
        "endpoint": "stratum+tcp://" + self.algorithms[miner_name][algorithm_id]['endpoint'],
        "username": username,
        "password": password
      }

    for key in param_map.keys():
      if miner.params[key][-1] == '=':
        args.append(miner.params[key] + param_map[key])
      else:
        args.append(miner.params[key])
        args.append(param_map[key])

    if miner.fixed_params:
      for fixed in miner.fixed_params:
        args.append(fixed)

    if "args" in Config().get('miners')[miner_name].keys() and 'all' in Config().get('miners')[miner_name]['args'].keys():
      for key in Config().get('miners')[miner_name]['args']['all'].keys():
        if not self.key_disallowed(key, miner.disallowed_params):
          if key[-1] == '=':
            args.append("%s%s" % (key, Config().get('miners')[miner_name]['args'][key]))
          else:
            args.append(key)
            args.append(Config().get('miners')[miner_name]['args'][key])

    if "args" in Config().get('miners')[miner_name].keys() and algorithm in Config().get('miners')[miner_name]['args'].keys():
      for key in Config().get('miners')[miner_name]['args'][algorithm].keys():
        if not self.key_disallowed(key, miner.disallowed_params):
          if key[-1] == '=':
            args.append("%s%s" % (key, Config().get('miners')[miner_name]['args'][key]))
          else:
            args.append(key)
            args.append(Config().get('miners')[miner_name]['args'][key])

    p = Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    timeout = 5
    time_start = time.time()

    while p.poll() != None:
      time.sleep(0.1)

      if (time.time() - time_start) >= timeout:
        return False

    thread = threading.Thread(target=self.worker_hashrate_thread, args=[p, miner_name, algorithm_id, device_id, self.worker_queue_in])
    thread.daemon = True
    thread.start()

    return p


  def key_disallowed(self, key, disallowed_params):
    if " " in key:
      return True

    for disallowed_key in disallowed_params:
      if key == disallowed_key:
        return True

    return False


  def worker_hashrate_thread(self, p, miner_name, algorithm_id, device_id, queue):
    miner = eval("%s()" % (miner_name.title()))
    regex = miner.hashrate_regex

    while p.poll() == None:
      if miner_name == 'ethminer':
        line = p.stderr.readline()
      else:
        line = p.stdout.readline()

      if line == '':
        break

      match = re.search(regex, line)

      if match:
        hashrate = self.to_hs(float(match.group(1)), match.group(2))

        queue.put({
          "miner_name": miner_name,
          "algorithm_id": algorithm_id,
          "device_id": device_id,
          "hashrate": hashrate
        })


  def to_hs(self, value, unit):
    hs = value

    if unit.lower() == "kh":
      return hs * 1e3
    elif unit.lower() == "mh":
      return hs * 1e6
    elif unit.lower() == "gh":
      return hs * 1e9
    elif unit.lower() == "h" or unit.lower() == "sol":
      return hs
    else:
      raise Exception("unknown hashrate unit: %s" % (unit))


  def cleanup_dead_workers(self):
    for miner_name in self.algorithms.keys():
      for algorithm_id in self.algorithms[miner_name].keys():
        for device_id in self.algorithms[miner_name][algorithm_id]['workers'].keys():
          if self.algorithms[miner_name][algorithm_id]['workers'][device_id]['handle'].poll() != None:
            self.algorithms[miner_name].pop(algorithm_id, None)
            Log().add('info', '%s [%d]: worker seems to have died, cleaning up' % (miner_name, device_id))


e = Excavataur()
e.startup()
