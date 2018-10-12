#!/usr/bin/env python3

import csv, argparse, datetime
import numpy as np
import xml.etree.ElementTree

parser = argparse.ArgumentParser(description='Convert ARISense sampled data to KML files')
parser.add_argument('-g', required=True, metavar='GPX-FILE', help='the GPX file describing the path')
parser.add_argument('-d', required=True, metavar='D-DATA-FILE', help='the ARISense D-data file (gas and environmental data)')
#parser.add_argument('-p', required=True, metavar='P-DATA-FILE', help='the ARISense P-data file (particle data)')

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
# Read D-data file

d_fields = [
    {'name': 'CO', 'index': 13},
]

d_data = {'timestamps': []}
for d_field in d_fields:
    d_data[d_field['name']] = []
with open(args.d, newline='') as d_file:
    d_reader = csv.reader(d_file, delimiter=',')
    for (i, row) in enumerate(d_reader):
        if (len(row) < 1):
            continue
        if row[0] != 'D':
            raise Exception(f'{args.d}:{i+1}: line does not start with "D"')
        time_string = row[1]
        try:
            time = datetime.datetime.strptime(time_string, '%m/%d/%Y %H:%M:%S')
        except ValueError:
            raise Exception(f'{args.d}:{i+1}: unable to interpret the date string: {date_string}')
        d_data['timestamps'].append(time.timestamp())
        for d_field in d_fields:
            d_data[d_field['name']].append(row[d_field['index']])
d_data['timestamps'] = np.array(d_data['timestamps'], dtype=np.float64)
print(d_data['timestamps'])
for d_field in d_fields:
    d_data[d_field['name']] = np.array(d_data[d_field['name']], dtype=np.float64)
    print(d_data[d_field['name']])

