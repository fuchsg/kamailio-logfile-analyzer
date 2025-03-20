#!/usr/bin/env python

import argparse
from collections import defaultdict
from datetime import datetime
import os
import pandas as pd
import re
import sys
from tabulate import tabulate
from tqdm import tqdm

# Local modules
from modules.utils import Cursor, openlog

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

def get_kpi(log_file_path, kpi=None) -> dict[int, dict[str, int]]:
  """
  Zählt die Anzahl der Call-Aufbauten (A-LEG und B-LEG), aller SIP-Nachrichten sowie die durchschnittliche Gesprächsdauer und Concurrent Calls.
  Counts number of call setups (A-Leg and B-Leg), number of SIP-messages, number Average Call Duration (ACD) and Concurrent Calls

  :param str log_file_path: path to logfile
  :return: dictionary with the KPI per hour
  :rtype: dict
  """
  # REGEX paterns for data extraction
  a_leg_pattern = re.compile(r"New request on proxy - M=INVITE")
  b_leg_pattern = re.compile(r"New request on proxy for the B LEG of the call - M=INVITE")
  sip_request_method_pattern = re.compile(r"New request on proxy.*M=(\w+)")
  sip_reply_method_pattern = re.compile(r"New reply on proxy.*M=(\w+)")
  dialog_end_pattern = re.compile(r"dialog:end.*callid: ([^ ]+) .* start_time: (\d+) duration: (\d+)")
  dialog_failed_pattern = re.compile(r"dialog:failed.*callid: ([^ ]+)")

  # Open file to write log messages matching KPI to
  if kpi:
    kpi_trace_file_name = kpi.lower().replace(' ', '-') + '.log'
    kpi_trace_file = open(kpi_trace_file_name, 'w')

  print(f"Skimming {log_file_path} ...", end='\r', flush=True)
  # Need file encoding as logfiles seem to contain UTF-8 characters
  logfile = openlog(log_file_path)
  if logfile is None:
    print(f"Error: Cannot open file '{log_file_path}'")
    return

  with logfile:
    line_count = sum(1 for line in logfile)
    logfile.seek(0)

    pbar_format = "{desc}: {percentage:3.0f}%|{bar}| {n:7.0f}/{total_fmt} [{elapsed}<{remaining} {rate_fmt}]"
    pbar_desc = f"Processing {os.path.basename(log_file_path)}"
    for line in tqdm(logfile, desc=pbar_desc, unit='lines', total=line_count, ascii=('-', '='), bar_format=pbar_format, unit_scale=True):
#    for line in logfile:

      loglevel = get_log_level(line)
      if loglevel == 'DEBUG':
        continue

      if re.search(a_leg_pattern, line):
        hour = get_hour_from_logline(line)
        if hour not in data: data[hour] = {}
        method = 'INVITE A-leg'
        if method not in data[hour]:
          data[hour][method] = 0
        data[hour][method] += 1
        continue

      if re.search(b_leg_pattern, line):
        hour = get_hour_from_logline(line)
        if hour not in data: data[hour] = {}
        method = 'INVITE B-leg'
        if method not in data[hour]:
          data[hour][method] = 0
        data[hour][method] += 1
        continue

      if m := sip_request_method_pattern.search(line):
        hour = get_hour_from_logline(line)
        if hour not in data: data[hour] = {}
        method = f"{m.group(1)} request"
        if method not in data[hour]:
          data[hour][method] = 0
        data[hour][method] += 1
        continue

      if m := sip_reply_method_pattern.search(line):
        hour = get_hour_from_logline(line)
        if hour not in data: data[hour] = {}
        method = f"{m.group(1)} reply"
        if kpi:
          kpi_trace_file.write(line)
        if method not in data[hour]:
          data[hour][method] = 0
        data[hour][method] += 1
        continue

      if m := dialog_failed_pattern.search(line):
        hour = get_hour_from_logline(line)
        if hour not in data: data[hour] = {}
        method = 'Failed calls'
        if method not in data[hour]:
          data[hour][method] = 0
        data[hour][method] += 1
        continue

      if m := dialog_end_pattern.search(line):
        hour = get_hour_from_logline(line)

        method = 'Successful calls'
        if method not in data[hour]:
          data[hour][method] = 0
        data[hour][method] += 1

        start_time = int(m.group(2))
        call_duration = int(m.group(3))
        end_time = start_time + call_duration

        method = 'Total call time'
        if method not in data[hour]:
          data[hour][method] = 0
        data[hour][method] += call_duration

        method = 'ZDC (Zero Duration Calls)'
        if method not in data[hour]:
          data[hour][method] = 0
        data[hour][method] += 1

        method = 'Longest Call'
        if method not in data[hour]:
          data[hour][method] = 0
        data[hour][method] = call_duration if call_duration > data[hour][method] else data[hour][method]

        method = 'Concurrent calls'
        # Make sure list for storing Concurrent Call data exists in dict (3600 entries per hour)
        if method not in data[hour]:
          data[hour][method] = [0] * 3600
        # Update Concurrent Calls for every second of the hour
        for t in range(start_time % 3600, end_time % 3600 + 1):
          data[hour][method][t] += 1

  if kpi:
    kpi_trace_file.close()

  return data

def output(df:pd.DataFrame, args: argparse.Namespace) -> None:
  outfile = open(args.file, 'w') if args.file else sys.stdout

  try:
    if args.table_format:
      print(tabulate(df, headers='keys', tablefmt=args.table_format, floatfmt=",.0f"), file=outfile)
    elif args.json:
      print(df.to_json(orient=args.json, indent=2), file=outfile)
    else:
      print(df.to_string(index=True), file=outfile)
  finally:
    if args.file:
      outfile.close() # Only close filehandle if it does not refer to STDOUT

if __name__ == "__main__":
  # Check command line parameters
  cli = argparse.ArgumentParser(description='Kamailio Proxy logfile parser')
  cli.add_argument('logfile', nargs='+', help='list of logfiles to parse')
  help = 'Filename for output to file'
  cli.add_argument('-f', '--file', help=help)
  help = 'Split logs for SIP message match as given as KPI in the output into a seperate logfile named after the KPI'
  cli.add_argument('-k', '--kpi-to-trace', help=help)
  group = cli.add_mutually_exclusive_group()
  help='JSON formatted output using Pandas DataFrame "orient" format (see https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.to_json.html), recomended value is "columns"'
  group.add_argument('-j', '--json', choices=['columns', 'index', 'records', 'split', 'table', 'values'], help=help)
  help='format table output using tabulate tablefmt (see https://pypi.org/project/tabulate/)'
  group.add_argument('-t', '--table-format', help=help)
  args = cli.parse_args()

  data = {}
  Cursor.hide()

  for logfile in args.logfile:
    if not os.path.exists(logfile):
      print(f"ERROR: File '{logfile}' not found.")
      continue  # Try next file

    data = get_kpi(logfile, kpi=args.kpi_to_trace)

  # Aggregate hour-based KPI
  for hour in data:
    data[hour]['Max CC'] = max(data[hour].get('Concurrent calls', [0]))
    data[hour].pop('Concurrent calls', None) # Delete list of calls per second - no longer needed
    if data[hour].get('Successful calls', 0):
      data[hour]['ACD'] = round(data[hour]['Total call time']/data[hour]['Successful calls'])
      if data[hour].get('INVITE A-leg', 0):
        data[hour]['ASR'] = round(data[hour]['Successful calls']/data[hour]['INVITE A-leg']*100)
    data[hour]['Erlang'] = round(data[hour].get('Total call time', 0)/3600) # https://en.wikipedia.org/wiki/Erlang_(unit)

  # Dataframe operations
  df = pd.DataFrame(data)
  df = df.fillna(0) # Fill NAN values with 0
  df = df[sorted(df.columns)]
  df = df.round(0).astype(int)
  df = df.rename(columns=lambda hour: f"{hour:02d}:00")

  output(df, args)

#  if args.table_format:
#    print(tabulate(df, headers='keys', tablefmt=args.table_format, floatfmt=",.0f"))
#  elif args.json:
#    print(df.to_json(orient=args.json, indent=2))
#  else:
#    print(df)

#  df = df.T
#  # ASCII-Balkendiagramm für den "Erlang"-Wert
#  max_value = df["Erlang"].max()
#  scale = 50 / max_value  # Skaliert auf 50 Zeichen Breite

#  print("Erlang-Werte pro Stunde\n")
#  for hour, value in df["Erlang"].items():
#    bar = "#" * int(value * scale)  # ASCII-Zeichen für Balken
#    print(f"{hour}: {bar} ({value})")

  Cursor.show()
