#!/usr/bin/env python3

import csv, argparse, datetime
import numpy as np
import xml.etree.ElementTree
import sys

MIN_PYTHON = (3, 6)
if sys.version_info < MIN_PYTHON:
    sys.exit('Python %s.%s or later is required.\n' % MIN_PYTHON)

parser = argparse.ArgumentParser(description='Convert ARISense sampled data to KML files')
parser.add_argument('-g', required=True, metavar='GPX-FILE', help='the GPX file describing the path')
parser.add_argument('-d', required=True, metavar='D-DATA-FILE', help='the ARISense D-data file (gas and environmental data)')
parser.add_argument('-p', required=True, metavar='P-DATA-FILE', help='the ARISense P-data file (particle data)')

args = parser.parse_args()


##############################################################################
# Read GPX file

tree = xml.etree.ElementTree.parse(args.g)
root = tree.getroot()
trkpts = root.findall('.//{http://www.topografix.com/GPX/1/1}trkpt')
track_timestamps = []
track_lat = []
track_lon = []
for trkpt in trkpts:
    track_lat.append(trkpt.attrib['lat'])
    track_lon.append(trkpt.attrib['lon'])
    trkpt_time = trkpt.findall('./{http://www.topografix.com/GPX/1/1}time')
    time_string = trkpt_time[0].text
    time = datetime.datetime.strptime(time_string, '%Y-%m-%dT%H:%M:%SZ')
    track_timestamps.append(time.timestamp())
track_timestamps = np.array(track_timestamps, np.float64)
track_lat = np.array(track_lat, np.float64)
track_lon = np.array(track_lon, np.float64)
print(track_timestamps)
print(track_lat)
print(track_lon)


##############################################################################
# ARISense file reading

def read_arisense(filename, data_type, fields):
    data = {'timestamps': []}
    for field in fields:
        data[field['name']] = []
    with open(filename, newline='') as inf:
        reader = csv.reader(inf, delimiter=',')
        for (i, row) in enumerate(reader):
            if (len(row) < 1):
                continue
            if row[0] != data_type:
                raise Exception(f'{filename}:{i+1}: line does not start with "{data_type}"')
            time_string = row[1]
            try:
                time = datetime.datetime.strptime(time_string, '%m/%d/%Y %H:%M:%S')
            except ValueError:
                raise Exception(f'{filename}:{i+1}: unable to interpret the date string: {date_string}')
            data['timestamps'].append(time.timestamp())
            for field in fields:
                data[field['name']].append(row[field['index']])
    data['timestamps'] = np.array(data['timestamps'], dtype=np.float64)
    for field in fields:
        data[field['name']] = np.array(data[field['name']], dtype=np.float64)
    return data


##############################################################################
# Read D-data file

d_fields = [
    {'name': 'CO', 'index': 13},
]

d_data = read_arisense(args.d, 'D', d_fields)
print(d_data['timestamps'])
for d_field in d_fields:
    print(d_data[d_field['name']])


##############################################################################
# Read P-data file

p_fields = [
    {'name': 'small_conc', 'index': 25},
]

p_data = read_arisense(args.p, 'P', p_fields)
print(p_data['timestamps'])
for p_field in p_fields:
    print(p_data[p_field['name']])
