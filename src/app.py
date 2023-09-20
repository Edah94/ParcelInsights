from flask import Flask, render_template, jsonify, send_file, request
import subprocess
import geopandas as gpd
import json
import os

app = Flask(__name__)
#
@app.route('/')
def map():
    return render_template('index.html')

@app.route('/gdf_parcel_geojson')
def geojson():
    gdf = gpd.read_file('data/bev_parcel_branau_lochen_am_see.geojson')
    return jsonify(json.loads(gdf.to_json()))


@app.route('/create_pdf', methods=['POST'])
def create_pdf():
    attributevalue1 = request.form['attributevalue1']
    attributevalue2 = request.form['attributevalue2']

    # Call the script
    output_pdf_path = 'output.pdf'.format(attributevalue2, attributevalue1)
    subprocess.run(['python', 'generate_pdf.py', attributevalue1, attributevalue2, output_pdf_path])

    # Send the PDF file
    return send_file(output_pdf_path, as_attachment=True, download_name='output.pdf', mimetype='application/pdf')




# (KG: Lochen, GNR: 416) - send this sample


if __name__ == '__main__':
    app.run(debug=True)



# IDEAS:
#1 - create dropdown element which by choosing bezirk/municipality it zooms to that place
    # makes life easier with selecting


### ISSUES

## JavaScript
# Clicking a map and subsequently populating the entries does leave information from a map, not from a manual entry.

## Python

# Can not add basemap under a geoTIFF/PNG layer in visualization
# Need to set the rule-based text-based analysis better
# Some parcels have issues with water risk zones and geology inconsistency
    # Geological incosistency: GNR: 55/1, KG: Wichenham  
    # Inconsistency with basemap within geological layer: KG: Oberweissau, GNR: 638 (but not within the parcel one)
    # Calling issue on waterzones, the geodataframe is empty? KG: Tannberg, GNR: 1304/2