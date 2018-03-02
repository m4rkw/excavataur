
class Ccminer:
  params = {
    "algorithm": "-a", 
    "device_id": "-d",
    "endpoint": "-o",
    "username": "-u",
    "password": "-p"
  }
  fixed_params = ["--submit-stale", "--statsavg=1"]
  hashrate_regex = "GPU #[\d]+.*? ([\d\.]+) ([a-zA-Z]{1,3})\/[sS]"
  algo_remap = {
    "blake256r8": "blakecoin",
    "whirlpoolx": "whirlpool",
    "x11gost": "sib",
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
