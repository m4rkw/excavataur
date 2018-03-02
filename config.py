
from singleton import Singleton
import os
import yaml
import sys

class Config(object):
  __metaclass__ = Singleton

  supported_miners = [
    'ccminer',
    'ccminer2',
    'xmrig_nvidia',
    'ethminer',
    'ewbf'
  ]

  def load(self):
    self.config_file = "/etc/excavataur.conf"

    if not os.path.exists(self.config_file):
      raise Exception("%s does not exist" % (self.config_file))

    self.config = yaml.load(open(self.config_file).read())

  def reload(self):
    self.load()

  def get(self, key):
    return self.config[key]

  def keys(self):
    return self.config.keys()

  def validate(self):
    if "miners" not in self.config.keys() or len(self.config["miners"]) == 0:
      print "fatal: no miners defined in %s" % (self.config_file)
      sys.exit(1)

    ports = {}

    for miner_name in self.config["miners"].keys():
      if not miner_name in self.supported_miners:
        print "fatal: miner %s is not supported" % (miner_name)
        sys.exit(1)

      if not "port" in self.config["miners"][miner_name].keys():
        print "fatal: no port specified for miner %s" % (miner_name)
        sys.exit(1)

      if not "path" in self.config["miners"][miner_name].keys():
        print "fatal: path to miner %s not specified" % (self.config["miners"][miner_name]["path"])
        sys.exit(1)

      if not os.path.exists(self.config["miners"][miner_name]["path"]):
        print "fatal: miner %s not found at %s" % (miner_name, self.config["miners"][miner_name]["path"])
        sys.exit(1)

      if self.config["miners"][miner_name]["port"] in ports.keys():
        print "fatal: port %d specified for more than one miner" % (self.config["miners"][miner_name]["port"])
        sys.exit(1)

      ports[self.config["miners"][miner_name]["port"]] = True
