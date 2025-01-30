#!/usr/bin/env python

from collections import defaultdict
from datetime import datetime
import re
import sys
from tqdm import tqdm
import os

def count_call_setups_and_sip_messages(log_file_path):
  """
  Zählt die Anzahl der Call-Aufbauten (A-LEG und B-LEG), aller SIP-Nachrichten sowie die durchschnittliche Gesprächsdauer und Concurrent Calls.
  Counts number of call setups (A-Leg and B-Leg), number of SIP-messages, number Average Call Duration (ACD) and Concurrent Calls

  :param log_file_path: path to logfile
  :return: dictionary with the KPI per hour
  """
  # REGEX paterns for data extraction
  timestamp_pattern = re.compile(r'(?P<timestamp>\w{3} \d{2} \d{2}:\d{2}:\d{2})\.\d{6} .*')
  b_leg_pattern = re.compile(r"New request on proxy for the B LEG of the call.*M=INVITE")
  a_leg_pattern = re.compile(r"New request on proxy.*M=INVITE")
  sip_method_pattern = re.compile(r"M=(\w+)")  # Fängt alle SIP-Methoden
  dialog_end_pattern = re.compile(r"dialog:end.*callid: ([^ ]+) .* start_time: (\d+) duration: (\d+)")
  dialog_failed_pattern = re.compile(r"dialog:failed.*callid: ([^ ]+)")

  counts = defaultdict(lambda: defaultdict(int))
  call_durations = defaultdict(lambda: defaultdict(list))
  concurrent_calls = defaultdict(lambda: defaultdict(int))  # Hält die Anzahl aktiver Calls pro Sekunde
  log_lines_per_hour = defaultdict(int)  # Zählt die Anzahl der Logzeilen pro Stunde

  # Need file encoding as logfiles seem to contain UTF-8 characters
  with open(log_file_path, "r", encoding="utf-8", errors="replace") as logfile:
    line_count = sum(1 for line in logfile)
    logfile.seek(0)
    for line in tqdm(logfile, desc=f'Processing {os.path.basename(log_file_path)}', unit='lines', total=line_count):
#    for line in logfile:
      leg = None
      if b_leg_pattern.search(line):
        leg = 'INVITE B-LEG'
      elif a_leg_pattern.search(line):
        leg = 'INVITE A-LEG'

      sip_match = sip_method_pattern.search(line)
      duration_match = dialog_end_pattern.search(line)
      failed_match = dialog_failed_pattern.search(line)

      if leg or sip_match or duration_match or failed_match:
        regex = r'(?P<timestamp>\w{3} \d{2} \d{2}:\d{2}:\d{2})\.\d{6} .*'
        timestamp = re.search(regex, line).group('timestamp')
        timestamp = f"{str(datetime.now().year)} {timestamp}"
        hour = str(datetime.strptime(timestamp, '%Y %b %d %H:%M:%S').strftime('%H'))

        log_lines_per_hour[hour] += 1

        if leg:
          counts[hour][leg] += 1
        if sip_match:
          sip_method = sip_match.group(1)
          counts[hour][sip_method] += 1
        if duration_match:
          start_time = int(duration_match.group(2))
          call_duration = int(duration_match.group(3))
          end_time = start_time + call_duration
          call_durations[hour]['durations'].append(call_duration)

          # Update Concurrent Calls for every second
          for t in range(start_time, end_time + 1):
            concurrent_calls[hour][t] += 1
        if failed_match:
          counts[hour]['Failed Calls'] += 1

  return counts, call_durations, concurrent_calls, log_lines_per_hour

if __name__ == "__main__":
  # Check command line parameters
  if len(sys.argv) < 2:
    print("ERROR: No logfiles given.")
    sys.exit(1)

  # Result dictionaries
  total_counts = defaultdict(lambda: defaultdict(int))
  total_durations = defaultdict(lambda: defaultdict(list))
  total_concurrent_calls = defaultdict(int)  # Speichert max. gleichzeitige Calls pro Stunde
  total_log_lines = defaultdict(int)  # Speichert Anzahl der Logzeilen pro Stunde

  for log_file_path in sys.argv[1:]:
    if not os.path.exists(log_file_path):
      print(f"ERROR: File '{log_file_path}' not found.")
      continue  # Try next file

    counts, call_durations, concurrent_calls, log_lines_per_hour = count_call_setups_and_sip_messages(log_file_path)

    # Data accumulation per hour
    for hour, counter in counts.items():
      for key, value in counter.items():
        total_counts[hour][key] += value

    for hour, duration_data in call_durations.items():
      total_durations[hour]['durations'].extend(duration_data['durations'])

    for hour, times in concurrent_calls.items():
      total_concurrent_calls[hour] = max(times.values(), default=0)

    for hour, lines in log_lines_per_hour.items():
      total_log_lines[hour] += lines

  # Print values
  for hour, counter in sorted(total_counts.items()):
    print(f"Hour {hour}:")
    for key, value in counter.items():
      print(f"  {key}: {value}")
      
    # Berechnung der CAPS (Call Attempts Per Second)
    total_invites = counter.get("INVITE", 0)
    caps = total_invites / 3600 if total_invites > 0 else 0
    print(f"  CAPS (Call Attempts Per Second): {caps:.2f}")
      
    # ASR calculations
    successful_calls = counter.get("200 OK", 0)
    asr = (successful_calls / total_invites * 100) if total_invites > 0 else 0
    print(f"  ASR (Answer Seizure Ratio): {asr:.2f}%")

    if total_durations[hour]['durations']:
      avg_duration = sum(total_durations[hour]['durations']) / len(total_durations[hour]['durations'])
      print(f"  ACD (Average Call Duration): {avg_duration:.2f} seconds")
    else:
      print("  Average Call Duration: No data")
      
    # Ausgabe der maximalen gleichzeitigen Calls
    print(f"  Max. Concurrent Calls: {total_concurrent_calls[hour]}")
      
    # Anzahl der verarbeiteten Logzeilen
    print(f"  Loglines processed: {total_log_lines[hour]}")
