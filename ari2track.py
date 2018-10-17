#!/usr/bin/env python3

##############################################################################
# Column indexes

# WARNING WARNING WARNING WARNING WARNING WARNING WARNING WARNING WARNING
#
# If you edit the values below, you should also update the
# process_data() function further down.
#
# WARNING WARNING WARNING WARNING WARNING WARNING WARNING WARNING WARNING

# ARISense file format: https://arisense.io/docs/api#data-format

# ARISense D-data (gas and environment)
D_NUM_COL      = 33 # total number of columns in D-data file
D_COL_TIME     = 1
D_COL_T        = 4
D_COL_RH       = 5
D_COL_CO_AUX   = 12
D_COL_CO_WORK  = 13
D_COL_NO2_AUX  = 16
D_COL_NO2_WORK = 17
D_COL_OX_AUX   = 20
D_COL_OX_WORK  = 21
D_COL_NO_AUX   = 24
D_COL_NO_WORK  = 25

# ARISense P-data (particulates)
P_NUM_COL      = 28 # total number of columns in P-data file
P_COL_TIME     = 1
P_COL_SML_CONC = 25
P_COL_MED_CONC = 26
P_COL_LRG_CONC = 27

# GPX data (track data from GPS)
GPX_NUM_COL  = 3 # total number of columns following below
GPX_COL_TIME = 0
GPX_COL_LAT  = 1
GPX_COL_LON  = 2

# output data
OUT_NUM_COL      = 12 # total number of columns following below
OUT_COL_TIME     = 0
OUT_COL_LAT      = 1
OUT_COL_LON      = 2
OUT_COL_T        = 3
OUT_COL_RH       = 4
OUT_COL_CO       = 5
OUT_COL_NO2      = 6
OUT_COL_OX       = 7
OUT_COL_NO       = 8
OUT_COL_SML_CONC = 9
OUT_COL_MED_CONC = 10
OUT_COL_LRG_CONC = 11

# output header names, must match OUT_COL_* names above
OUT_HEADER = [None] * OUT_NUM_COL
OUT_HEADER[OUT_COL_TIME] = 'time'
OUT_HEADER[OUT_COL_LAT] = 'lat'
OUT_HEADER[OUT_COL_LON] = 'lon'
OUT_HEADER[OUT_COL_T] = 'T'
OUT_HEADER[OUT_COL_RH] = 'RH'
OUT_HEADER[OUT_COL_CO] = 'CO'
OUT_HEADER[OUT_COL_NO2] = 'NO2'
OUT_HEADER[OUT_COL_OX] = 'Ox'
OUT_HEADER[OUT_COL_NO] = 'NO'
OUT_HEADER[OUT_COL_SML_CONC] = 'small_conc'
OUT_HEADER[OUT_COL_MED_CONC] = 'medium_conc'
OUT_HEADER[OUT_COL_LRG_CONC] = 'large_conc'

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
    parser = argparse.ArgumentParser(
        description='Convert ARISense sampled data to interpolated data on a GPS track.',
        epilog='Example:\npython ari2track.py -g data/Ride_1.gpx -d data/D_181011.TXT -p data/P_181011.TXT -o out/Ride_1_interp.csv',
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument('-g', required=True, metavar='GPX-FILE', help='the GPX file describing the track')
    parser.add_argument('-d', required=True, metavar='D-DATA-FILE', help='the ARISense D-data file (gas and environmental data)')
    parser.add_argument('-p', required=True, metavar='P-DATA-FILE', help='the ARISense P-data file (particle data)')
    parser.add_argument('-o', required=True, metavar='OUTPUT-FILE', help='the output CSV filename')

    args = parser.parse_args()
    return args


##############################################################################
# GPX file reading

def read_gpx(filename):
    """Read a GPX file and return an N x 3 array, where the columns are
         column GPX_COL_TIME - the timestamp of the entry
         column GPX_COL_LAT - the latitude in degrees
         column GPX_COL_LON - the longitude in degrees
    """
    tree = ET.parse(filename)
    root = tree.getroot()
    trkpts = root.findall('.//{http://www.topografix.com/GPX/1/1}trkpt')
    track = np.zeros((len(trkpts), GPX_NUM_COL))
    for (i, trkpt) in enumerate(trkpts):
        trkpt_time = trkpt.findall('./{http://www.topografix.com/GPX/1/1}time')
        time_string = trkpt_time[0].text
        time = datetime.datetime.strptime(time_string, '%Y-%m-%dT%H:%M:%SZ')
        track[i,GPX_COL_TIME] = time.timestamp()
        track[i,GPX_COL_LAT] = trkpt.attrib['lat']
        track[i,GPX_COL_LON] = trkpt.attrib['lon']
    return track


##############################################################################
# ARISense file reading

def read_csv(filename):
    """Read a CSV file and return the rows as a list,
    where each row is a list of entries."""
    rows = []
    with open(filename, newline='') as inf:
        reader = csv.reader(inf, delimiter=',')
        for row in reader:
            if (len(row) < 1):
                continue
            rows.append(row)
    return rows

def read_arisense(filename, data_type, num_columns):
    """Read an ARISense data file (either P or D data).
    Return the data as an array where column 0 is all zeros,
    column 1 is the timestamp, and other columns are data."""
    rows = read_csv(filename)
    if len(rows) < 1:
        raise Exception(f'{filename}: no data rows found')
    data = np.zeros((len(rows), num_columns))
    for (i, row) in enumerate(rows):
        if len(row) != num_columns:
            raise Exception(f'{filename}:{i+1}: number of columns {len(row)} does not match {num_columns}')
        if row[0] != data_type:
            raise Exception(f'{filename}:{i+1}: line does not start with "{data_type}"')
        time_string = row[1]
        try:
            time = datetime.datetime.strptime(time_string, '%m/%d/%Y %H:%M:%S')
        except ValueError:
            raise Exception(f'{filename}:{i+1}: unable to interpret the date string: {date_string}')
        data[i,1] = time.timestamp()
        data[i,2:] = row[2:]
    return data


##############################################################################
# discard ARISense observations that are outside the timespan of the track data

def trim_to_track_timespan(ari_data, track):
    """Discards all ARISense observations with timestamps
    outside the range of track timestamps."""
    start_time = track[:,GPX_COL_TIME].min()
    end_time = track[:,GPX_COL_TIME].max()
    keep_rows = np.logical_and(ari_data[:,1] > start_time, ari_data[:,1] < end_time)
    new_data = ari_data[keep_rows, :].copy()
    return new_data

##############################################################################
# combine ARISense data and intperolate track data

def process_data(d_data, p_data, track):
    if d_data.shape[0] != p_data.shape[0]:
        raise Exception(f'D-data has {d_data.shape[0]} rows but P-data has {p_data.shape[0]} rows')
    delta_t = np.abs(d_data[:,D_COL_TIME] - p_data[:,D_COL_TIME])
    if delta_t.max() > 1e-6:
        raise Exception(f'D-data and P-data timestamps do not match: see row {delta_t.argmax() + 1}')

    out_data = np.zeros((d_data.shape[0], OUT_NUM_COL))
    out_data[:,OUT_COL_TIME] = d_data[:,D_COL_TIME]
    out_data[:,OUT_COL_LAT]  = np.interp(d_data[:,D_COL_TIME], track[:,GPX_COL_TIME], track[:,GPX_COL_LAT])
    out_data[:,OUT_COL_LON]  = np.interp(d_data[:,D_COL_TIME], track[:,GPX_COL_TIME], track[:,GPX_COL_LON])
    out_data[:,OUT_COL_T]    = d_data[:,D_COL_T]
    out_data[:,OUT_COL_RH]   = d_data[:,D_COL_RH]
    out_data[:,OUT_COL_CO]   = d_data[:,D_COL_CO_WORK] - d_data[:,D_COL_CO_AUX]
    out_data[:,OUT_COL_NO2]  = d_data[:,D_COL_NO2_WORK] - d_data[:,D_COL_NO2_AUX]
    out_data[:,OUT_COL_OX]   = d_data[:,D_COL_OX_WORK] - d_data[:,D_COL_OX_AUX]
    out_data[:,OUT_COL_NO]   = d_data[:,D_COL_NO_WORK] - d_data[:,D_COL_NO_AUX]
    out_data[:,OUT_COL_SML_CONC] = p_data[:,P_COL_SML_CONC]
    out_data[:,OUT_COL_MED_CONC] = p_data[:,P_COL_MED_CONC]
    out_data[:,OUT_COL_LRG_CONC] = p_data[:,P_COL_LRG_CONC]

    return out_data

##############################################################################
# write CSV output

def timestamp_to_string(timestamp):
    return datetime.datetime.fromtimestamp(timestamp).isoformat() + 'Z'

def write_csv(filename, data, header):
    """Write data to a CSV file with the given header.
    Column 0 of the data must be the timestamp,
    with other columns being the data."""
    if data.shape[1] != len(header):
        raise Exception(f'CSV header has length {len(header)} but data has {data.shape[1]} columns')
    if header[0] != 'time':
        raise Exception(f'CSV header must start with "time", not "{header[0]}"')
    with open(filename, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)

        writer.writerow(header)
        for i in range(data.shape[0]):
            row = [timestamp_to_string(data[i,0])] + list(data[i,1:])
            writer.writerow(row)


##############################################################################
# write KML output

def write_kml(filename, data, col, cmap):
    ns = 'http://www.opengis.net/kml/2.2'
    ns_prefix = '{' + ns + '}'
    kml = ET.Element(ns_prefix + 'kml')
    document = ET.SubElement(kml, ns_prefix + 'Document')
    document_name = ET.SubElement(document, ns_prefix + 'name')
    document_name.text = OUT_HEADER[col]
    document_name.tail = '\n'

    norm = matplotlib.colors.Normalize(vmin=data[:,col].min(), vmax=data[:,col].max())
    cm = matplotlib.cm.ScalarMappable(norm=norm, cmap=cmap)
    for i in range(data.shape[0] - 1):
        color = cm.to_rgba(data[i,col], bytes=True)
        color_string = f'{color[0]:02x}{color[1]:02x}{color[2]:02x}'

        placemark = ET.SubElement(document, ns_prefix + 'Placemark')
        placemark.tail = '\n'
        placemark_name = ET.SubElement(placemark, ns_prefix + 'name')
        placemark_name.text = f'{OUT_HEADER[col]} = {data[i,col]}'
        description = ET.SubElement(placemark, ns_prefix + 'description')
        description.text = f'time = {timestamp_to_string(data[i,OUT_COL_TIME])}'
        linestring = ET.SubElement(placemark, ns_prefix + 'LineString')
        coordinates = ET.SubElement(linestring, ns_prefix + 'coordinates')
        coordinates.text = '%f,%f %f,%f' % (data[i,OUT_COL_LON], data[i,OUT_COL_LAT], data[i+1,OUT_COL_LON], data[i+1,OUT_COL_LAT])
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

    print(f'Reading GPX data from {args.g}...')
    track = read_gpx(args.g)
    print(f'Read {track.shape[0]} track points')

    print(f'Reading ARISense D-data from {args.d}...')
    d_data = read_arisense(args.d, 'D', D_NUM_COL)
    print(f'Read {d_data.shape[0]} observations with {d_data.shape[1]} columns')

    print(f'Reading ARISense P-data from {args.p}...')
    p_data = read_arisense(args.p, 'P', P_NUM_COL)
    print(f'Read {p_data.shape[0]} observations with {p_data.shape[1]} columns')

    print(f'Trimming ARISense D-data to track timespan...')
    d_data = trim_to_track_timespan(d_data, track)
    print(f'Kept {d_data.shape[0]} observations')

    print(f'Trimming ARISense P-data to track timespan...')
    p_data = trim_to_track_timespan(p_data, track)
    print(f'Kept {p_data.shape[0]} observations')

    print(f'Interpolating and merging data...')
    data = process_data(d_data, p_data, track)
    print(f'Merged into {data.shape[0]} records with {data.shape[1]} columns')

    print(f'Writing CSV output to {args.o}...')
    write_csv(args.o, data, OUT_HEADER)
    print(f'Wrote {data.shape[0]} records')

    output_head, output_tail = os.path.split(args.o)
    output_root, _ = os.path.splitext(output_tail)
    kml_prefix = os.path.join(output_head, output_root)
    for i in range(3, OUT_NUM_COL):
        filename = kml_prefix + '_' + OUT_HEADER[i] + '.kml'
        print(f'Writing KML output to {filename}...')
        write_kml(filename, data, i, 'jet_r')
    print(f'Wrote all KML files')
