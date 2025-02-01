#!/usr/bin/env python

from collections import defaultdict
from datetime import datetime
import os
import pandas as pd
import re
import sys
from tqdm import tqdm

def get_hour_from_logline(logline:str) -> str:
  """
  Returns the hour found in a timestamp of a logline following REGEX pattern
  given in 'timestamp_pattern'.

  :param str logline: The logline to search for the timestamp
  :return: The hour of the day as in between 0 and 23
  :rtype: int
  """
  timestamp_pattern = re.compile(r'(?P<timestamp>\w{3} \d{2} \d{2}:\d{2}:\d{2})\.\d{6} .*')
  timestamp = re.search(timestamp_pattern, logline).group('timestamp')
  timestamp = f"{str(datetime.now().year)} {timestamp}"
  hour = int(datetime.strptime(timestamp, '%Y %b %d %H:%M:%S').strftime('%H'))
#  minute = int(datetime.strptime(timestamp, '%Y %b %d %H:%M:%S').strftime('%M'))
#  second = int(datetime.strptime(timestamp, '%Y %b %d %H:%M:%S').strftime('%S'))
#  return (hour, minute, second)
  return hour

def get_log_level(logline:str) -> str:
  """
  Splits a logline to isolate the loglevel

  :param str logline: The logline to search for the timestamp
  :return: The loglevel
  :rtype: str
  """
  parts = logline.split(': ')
  if len(parts) > 2:  # Check if there's enough parts
    loglevel = parts[1].split()[0]  # First word after the first ": "
    return loglevel
  else:
    return None

def count_call_setups_and_sip_messages(log_file_path):
  """
  Zählt die Anzahl der Call-Aufbauten (A-LEG und B-LEG), aller SIP-Nachrichten sowie die durchschnittliche Gesprächsdauer und Concurrent Calls.
  Counts number of call setups (A-Leg and B-Leg), number of SIP-messages, number Average Call Duration (ACD) and Concurrent Calls

  :param str log_file_path: path to logfile
  :return: dictionary with the KPI per hour
  :rtype: dict
  """
  # REGEX paterns for data extraction
  a_leg_pattern = re.compile(r"(New request on proxy.*M=INVITE)")
  b_leg_pattern = re.compile(r"(New request on proxy for the B LEG of the call.*M=INVITE)")
  sip_method_pattern = re.compile(r"M=(\w+)")  # Fängt alle SIP-Methoden
  dialog_end_pattern = re.compile(r"dialog:end.*callid: ([^ ]+) .* start_time: (\d+) duration: (\d+)")
  dialog_failed_pattern = re.compile(r"dialog:failed.*callid: ([^ ]+)")

  print(f"Skimming {log_file_path} ...", end='\r', flush=True)
  # Need file encoding as logfiles seem to contain UTF-8 characters
  with open(log_file_path, "r", encoding="utf-8", errors="replace") as logfile:
    line_count = sum(1 for line in logfile)
    logfile.seek(0)

    for line in tqdm(logfile, desc=f'Processing {os.path.basename(log_file_path)}', unit='lines', total=line_count, ascii=('-', '=')):
#    for line in logfile:

      match line:
        case _ if bool(a_leg_pattern.search(line)):
          hour = get_hour_from_logline(line)
          method = 'INVITE A-LEG'
          data[hour][method] += 1
        case _ if bool(b_leg_pattern.search(line)):
          hour = get_hour_from_logline(line)
          method = 'INVITE B-LEG'
          data[hour][method] += 1
        case _ if (m := sip_method_pattern.search(line)):
          hour = get_hour_from_logline(line)
          method = m.group(1)
          data[hour][method] += 1
        case _ if (m := dialog_failed_pattern.search(line)):
          hour = get_hour_from_logline(line)
          method = 'Failed calls'
          data[hour][method] += 1
        case _ if (m := dialog_end_pattern.search(line)):
          hour = get_hour_from_logline(line)
          data[hour]['Successfull calls'] += 1
          method = 'Concurrent Calls'
          start_time = int(m.group(2))
          call_duration = int(m.group(3))
          data[hour]['Total call time'] += call_duration
          end_time = start_time + call_duration
          # Make sure list for storing Concurrent Call data exists in dict (3600 entries per hour)
          if method not in data[hour]:
            data[hour][method] = [0] * 3600
          # Update Concurrent Calls for every second of the hour
          for t in range(start_time % 3600, end_time % 3600 + 1):
            data[hour][method][t] += 1
      loglevel = get_log_level(line)
      if loglevel == 'DEBUG':
        continue


  return data

if __name__ == "__main__":
  # Check command line parameters
  if len(sys.argv) < 2:
    print("ERROR: No logfiles given.")
    sys.exit(1)

  data = defaultdict(lambda: defaultdict(int))

  for log_file_path in sys.argv[1:]:
    if not os.path.exists(log_file_path):
      print(f"ERROR: File '{log_file_path}' not found.")
      continue  # Try next file

    data = count_call_setups_and_sip_messages(log_file_path)

  # Aggregate hour-based KPI
  for hour in data:
    data[hour]['Max CC'] = max(data[hour]['Concurrent Calls'])
    del data[hour]['Concurrent Calls'] # Delete list of calls per second - no longer needed
    if data[hour]['Successfull calls']:
      data[hour]['ACD'] = round(data[hour]['Total call time']/data[hour]['Successfull calls'])
    if data[hour]['INVITE']:
      data[hour]['ASR'] = round(data[hour]['Successfull calls']/data[hour]['INVITE A-LEG']*100)

  # Dataframe operations
  df = pd.DataFrame(data)
  df = df.fillna(0) # Fill NAN values with 0
  df = df[sorted(df.columns)]
  df = df.round(0).astype(int)
  df = df.rename(columns=lambda hour: f"{hour:02d}:00")

  print(df)
