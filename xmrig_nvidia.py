
class Xmrig_Nvidia:
  params = {
    "algorithm": "-a", 
    "device_id": "--cuda-devices=",
    "endpoint": "-o",
    "username": "-u",
    "password": "-p"
  }
  fixed_params = ["--nicehash"]
  hashrate_regex = "speed.*?([\d\.]+) ([a-zA-Z]{1,2})\/[sS]"
  algo_remap = {
  }
  disallowed_params = [
    '-a',
    '-o',
    '-O',
    '-u',
    '-p',
    '-B',
    '--algo',
    '--algo=',
    '--url',
    '--url=',
    '--userpass',
    '--userpass=',
    '--user',
    '--user=',
    '--pass',
    '--pass=',
    '--background'
  ]
