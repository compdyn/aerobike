#!/usr/bin/env python3

##############################################################################
# ARISense file format: https://arisense.io/docs/api#data-format

d_fields = [
    {'name': 'CO', 'index': 13, 'subtract_index': 12},
]

p_fields = [
    {'name': 'small_conc', 'index': 25},
]


##############################################################################
# library imports

import sys
MIN_PYTHON = (3, 6)
if sys.version_info < MIN_PYTHON:
    sys.exit('Python %s.%s or later is required.\n' % MIN_PYTHON)

import csv, argparse, datetime, os
import numpy as np
import xml.etree.ElementTree as ET
import matplotlib, matplotlib.cm


##############################################################################
# commandline argument parsing

def get_args():
    parser = argparse.ArgumentParser(description='Convert ARISense sampled data to interpolated data on a track')
    parser.add_argument('-g', required=True, metavar='GPX-FILE', help='the GPX file describing the track')
    parser.add_argument('-d', required=True, metavar='D-DATA-FILE', help='the ARISense D-data file (gas and environmental data)')
    parser.add_argument('-p', required=True, metavar='P-DATA-FILE', help='the ARISense P-data file (particle data)')
    parser.add_argument('-o', required=True, metavar='OUTPUT-FILE', help='the output CSV filename')

    args = parser.parse_args()
    return args


##############################################################################
# GPX file reading

def read_gpx(filename):
    tree = ET.parse(filename)
    root = tree.getroot()
    trkpts = root.findall('.//{http://www.topografix.com/GPX/1/1}trkpt')
    track = {}
    track['timestrings'] = []
    track['timestamps'] = []
    track['lat'] = []
    track['lon'] = []
    for trkpt in trkpts:
        track['lat'].append(trkpt.attrib['lat'])
        track['lon'].append(trkpt.attrib['lon'])
        trkpt_time = trkpt.findall('./{http://www.topografix.com/GPX/1/1}time')
        time_string = trkpt_time[0].text
        time = datetime.datetime.strptime(time_string, '%Y-%m-%dT%H:%M:%SZ')
        track['timestrings'].append(time.isoformat() + 'Z')
        track['timestamps'].append(time.timestamp())
    track['timestamps'] = np.array(track['timestamps'], np.float64)
    track['lat'] = np.array(track['lat'], np.float64)
    track['lon'] = np.array(track['lon'], np.float64)
    return track


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
                val = float(row[field['index']])
                if 'subtract_index' in field:
                    val -= float(row[field['subtract_index']])
                data[field['name']].append(val)
    data['timestamps'] = np.array(data['timestamps'], dtype=np.float64)
    for field in fields:
        data[field['name']] = np.array(data[field['name']], dtype=np.float64)
    return data


##############################################################################
# data interpolation

def interp(ari_data, fields, track):
    interp_data = {}
    for field in fields:
        interp_data[field['name']] = np.interp(track['timestamps'], ari_data['timestamps'], ari_data[field['name']])
    return interp_data


##############################################################################
# write CSV output

def write_csv(filename, ari_interp_data, fields, track):
    with open(filename, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)

        row = ['time','lat','lon']
        for field in fields:
            row.append(field['name'])
        writer.writerow(row)

        for i in range(len(track['timestamps'])):
            row = []
            row.append(track['timestrings'][i])
            row.append(track['lat'][i])
            row.append(track['lon'][i])
            for field in fields:
                row.append(ari_interp_data[field['name']][i])
            writer.writerow(row)


##############################################################################
# write KML output

def write_kml(filename, name, data, track, cmap):
    ns = 'http://www.opengis.net/kml/2.2'
    ns_prefix = '{' + ns + '}'
    kml = ET.Element(ns_prefix + 'kml')
    document = ET.SubElement(kml, ns_prefix + 'Document')
    document_name = ET.SubElement(document, ns_prefix + 'name')
    document_name.text = name
    document_name.tail = '\n'

    norm = matplotlib.colors.Normalize(vmin=data.min(), vmax=data.max())
    cm = matplotlib.cm.ScalarMappable(norm=norm, cmap=cmap)
    for i in range(len(data) - 1):
        color = cm.to_rgba(data[i], bytes=True)
        color_string = f'{color[0]:02x}{color[1]:02x}{color[2]:02x}'

        placemark = ET.SubElement(document, ns_prefix + 'Placemark')
        placemark.tail = '\n'
        placemark_name = ET.SubElement(placemark, ns_prefix + 'name')
        placemark_name.text = f'{name} = {data[i]}'
        description = ET.SubElement(placemark, ns_prefix + 'description')
        description.text = f'time = {track["timestrings"][i]}'
        linestring = ET.SubElement(placemark, ns_prefix + 'LineString')
        coordinates = ET.SubElement(linestring, ns_prefix + 'coordinates')
        coordinates.text = '%f,%f %f,%f' % (track['lon'][i], track['lat'][i], track['lon'][i+1], track['lat'][i+1])
        style = ET.SubElement(placemark, ns_prefix + 'Style')
        linestyle = ET.SubElement(style, ns_prefix + 'LineStyle')
        linecolor = ET.SubElement(linestyle, ns_prefix + 'color')
        linecolor.text = color_string
        width = ET.SubElement(linestyle, ns_prefix + 'width')
        width.text = '4'

    tree = ET.ElementTree(kml)
    with open(filename, 'wb') as outf:
        tree.write(outf, encoding='utf-8', xml_declaration=True, default_namespace=ns)

        
##############################################################################
# main program

if __name__ == '__main__':
    args = get_args()
    track = read_gpx(args.g)
    d_data = read_arisense(args.d, 'D', d_fields)
    p_data = read_arisense(args.p, 'P', p_fields)

    d_data_interp = interp(d_data, d_fields, track)
    p_data_interp = interp(p_data, p_fields, track)

    all_fields = d_fields + p_fields
    all_data_interp = d_data_interp.copy()
    all_data_interp.update(p_data_interp)

    write_csv(args.o, all_data_interp, all_fields, track)

    output_head, output_tail = os.path.split(args.o)
    output_root, _ = os.path.splitext(output_tail)
    kml_prefix = os.path.join(output_head, output_root)
    for field in all_fields:
        filename = kml_prefix + '_' + field['name'] + '.kml'
        write_kml(filename, field['name'], all_data_interp[field['name']], track, 'jet')
