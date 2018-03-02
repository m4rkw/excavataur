
class Ccminer2:
  params = {
    "algorithm": "-a", 
    "device_id": "-d",
    "endpoint": "-o",
    "username": "-u",
    "password": "-p"
  }
  fixed_params = []
  hashrate_regex = ", ([\d\.]+)([a-zA-Z]{1,2})\/s.*?yes"
  algo_remap = {
    "x11gost": "sib"
  }
  disallowed_params = [
    '-a',
    '-d',
    '-o',
    '-u',
    '-p',
    '--max-log-rate',
    '--max-log-rate=',
    '--algo',
    '--algo=',
    '--devices',
    '--devices=',
    '--url',
    '--url=',
    '--userpass',
    '--userpass=',
    '--user',
    '--user=',
    '--pass',
    '--pass='
  ]
