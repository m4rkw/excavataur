
class Ethminer:
  params = {
    "device_id": "--cuda-devices",
    "primary_endpoint": "-S",
    "failover_endpoint": "-FS",
    "username": "-O"
  }
  fixed_params = ["--cuda", "--stratum-protocol", "1", "--report-hashrate", "--farm-recheck", "1000", "-SC", "2"]
  hashrate_regex = "Speed.*?[\d]+.*?[\d]+.*?([\d\.]+).*?([a-zA-Z]{1,3})\/[sS]"
  algo_remap = {
  }
  disallowed_params = [
    '-O',
  ]
