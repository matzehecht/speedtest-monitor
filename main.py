from speedtest import Speedtest, SpeedtestResults
import timeit
import os
import json
import time
import traceback
import logging
from influxdb import InfluxDBClient

DB = {
  'HOST': os.environ.get('DB_HOST'),
  'PORT': int(os.environ.get('DB_PORT')),
  'USER': os.environ.get('DB_USER'),
  'PASSWORD': os.environ.get('DB_PASSWORD'),
  'DATABASE': os.environ.get('DB_DATABASE')
}

SPEEDTEST = {
  'INTERVAL': int(os.environ.get('INTERVAL')),
  'FAIL_INTERVAL': int(os.environ.get('FAIL_INTERVAL'))
}

influx = InfluxDBClient(DB['HOST'], DB['PORT'], DB['USER'], DB['PASSWORD'], DB['DATABASE'])

def do_nothing(*args, **kwargs):
  pass

class ExtendedSpeedtestResults(SpeedtestResults):
  
  def __init__(self, download=0, upload=0, ping=0, server=None, client=None,
                 opener=None, secure=False, download_elapsed=0, upload_elapsed=0):
    super().__init__(download, upload, ping, server, client, opener, secure)
    
    self.download_elapsed = 0
    self.upload_elapsed = 0
  
  def json(self, pretty=False):
    kwargs = {}
    if pretty:
      kwargs.update({
        'indent': 2,
        'sort_keys': True
      })
    return json.dumps(self.dict(), **kwargs)
  
  def influxdb(self):
    data = [
      {
        'measurement': 'ping',
        'fields': {
          # Currently not supported
          # 'jitter': self.jitter,
          'latency': self.ping
        }
      },
      {
        'measurement': 'download',
        'fields': {
          # Byte to Megabit
          'bandwidth': self.download / 125000,
          'bytes': self.bytes_received,
          'elapsed': self.download_elapsed
        }
      },
      {
        'measurement': 'upload',
        'fields': {
          # Byte to Megabit
          'bandwidth': self.upload / 125000,
          'bytes': self.bytes_sent,
          'elapsed': self.upload_elapsed
        }
      }
      # Currently not supported
      # {
      #   'measurement': 'packetLoss',
      #   'fields': {
      #     'packetLoss': self.pktLoss
      #   }
      # }
    ]
    
    for data_part in data:
      data_part['tags'] = {
        'server_id': self.server['id'],
        'server_name': self.server['sponsor'],
        'server_location': self.server['name'] + ', ' + self.server['country']
      }
      data_part['time'] = self.timestamp
    
    if influx.write_points(data) != True:
      raise

class ExtendedSpeedtest(Speedtest):
  
  def __init__(self, config=None, source_address=None, timeout=10,
                 secure=False, shutdown_event=None):
    super().__init__(config, source_address, timeout, secure, shutdown_event)
    
    self.results = ExtendedSpeedtestResults(
      client=self.config['client'],
      opener=self._opener,
      secure=secure,
    )

  def download(self, callback=do_nothing, threads=None):
    start = timeit.default_timer()
    super().download(callback, threads)
    self.results.download_elapsed = timeit.default_timer() - start

  def upload(self, callback=do_nothing, pre_allocate=True, threads=None):
    start = timeit.default_timer()
    super().upload(callback, pre_allocate, threads)
    self.results.upload_elapsed = timeit.default_timer() - start

def run():
  servers = []
  threads = None
  
  s = ExtendedSpeedtest()
  s.get_best_server()
  s.download()
  s.upload()
  s.results.influxdb()

def main():
  print('Influxdb configuration:')
  print(DB)
  print('Speedtest configuration:')
  print(SPEEDTEST)
  while (True):
    try:
      run()
      print('Data succesfully stored')
      time.sleep(SPEEDTEST['INTERVAL'])
    except Exception as e:
      print('ERROR during speedtest')
      logging.error(traceback.format_exc())
      time.sleep(SPEEDTEST['FAIL_INTERVAL'])

if __name__ == '__main__':
  main()