# AeroBike data-processing code

[ARISense data file format](https://arisense.io/docs/api#data-format)

Example usage:
```
python ari2track.py -g data/Ride_1.gpx -d data/D_181011.TXT -p data/P_181011.TXT -o out/Ride_1_interp.csv
```

This script merges ARISense observations with GPS track data (a GPX file) to produce concentration profiles along the track. This is output in both CSV and KML formats.

## Viewing KML in Google Maps

1. Go to https://maps.google.com

2. Click on the hamburger menu in the upper left of the window, just to the left of the search box.

3. Select "Your places"

4. Select "MAPS" from the tab bar

5. Click "CREATE MAP" at the bottom of the left-hand panel

6. In the new map, click "Import" in the upper-left panel

7. Click "Select a file from your computer" and select the KML file

8. To remove the KML data, click the three vertical dots next to the layer heading in the left-hand panel and select "Delete this layer"
