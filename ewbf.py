
class Ewbf:
  params = {
    "device_id": "--cuda_devices",
    "server": "--server",
    "port": "--port",
    "username": "--user",
    "password": "--pass"
  }
  fixed_params = []
  hashrate_regex = "Total speed: ([\d\.]+) (Sol)\/s"
  algo_remap = {}
  disallowed_params = [
    '--server',
    '--port',
    '--user',
    '--pass'
  ]
