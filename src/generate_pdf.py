#MODULES PART

import folium
from datetime import datetime
import contextily as ctx
import geopandas as gpd
import geopy.distance
import matplotlib.image as mpimg
import matplotlib.pyplot as plt
import os
from owslib.wfs import WebFeatureService
from owslib.wms import WebMapService
from owslib.wcs import WebCoverageService
from owslib.fes import *
from owslib.etree import etree
import pandas as pd
import PIL.Image
import PIL.ImageOps
import pyproj
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Image, Spacer, Table, TableStyle, PageBreak 
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
import requests
import socket
from shapely.geometry import box
from shapely.geometry import mapping
from lxml import etree


## NOTES
# parcel KG: Wichenham and GNR: 9 has geology issues
# water risk zones issue with rendering nothing after cutting the dataframe









import rasterio
from rasterio.mask import mask
from mpl_toolkits.axes_grid1.inset_locator import inset_axes
import numpy as np
import sys

## WEB SERVICES URL
#WMS urls
#wms_aspect = WebMapService('https://zgis188.geo.sbg.ac.at/arcgis/services/23S856162/aspect_10m_ua/MapServer/WMSServer?')

# WCS urls
#wcs_aspect_old = WebCoverageService('https://zgis188.geo.sbg.ac.at/arcgis/services/23S856162/aspect_10m_ua/MapServer/WCSServer?', version='2.0.1')
#wcs_aspect = WebCoverageService('https://zgis188.geo.sbg.ac.at/arcgis/services/23S856162/aspect_ua_3857/MapServer/WCSServer?', version='2.0.1')
#wcs_dem = WebCoverageService('https://zgis188.geo.sbg.ac.at/arcgis/services/23S856162/dgm_10m_UA/ImageServer/WMSServer?')
wcs_slope = WebCoverageService('https://zgis188.geo.sbg.ac.at/arcgis/services/23S856162/slope_ua_3857/ImageServer/WCSServer?')

# WMS urls
wms_aspect = WebMapService('https://zgis188.geo.sbg.ac.at/arcgis/services/23S856162/aspect_ua_3857/MapServer/WMSServer?')
wms_dem = WebMapService('https://zgis188.geo.sbg.ac.at/arcgis/services/23S856162/dgm_10m_UA/ImageServer/WMSServer?')
wms_slope = WebMapService('https://zgis188.geo.sbg.ac.at/arcgis/services/23S856162/slope_3857_2/MapServer/WMSServer?')

## USER INPUT PART
#standard testing parcel
#gemeinde_input, gnr_input, kg_input = "Lochen am See", "465", "Oberweissau"

#new testing parcel - basemap returns error
#gemeinde_input, gnr_input, kg_input = "Lochen am See", "638", "Oberweissau"

#new testing parcel 2 - basemap returns error
#gemeinde_input, gnr_input, kg_input = "Lochen am See", "465", "Oberweissau"

#new testing parcel 3 - basemap works for this one
#gemeinde_input, gnr_input, kg_input = "Lochen am See", "427", "Oberweissau"



## FUNCTIONS PART


## Download the WMS legend
def get_WMS_legend(wms, layer_name):
    legend_url = wms['0'].styles['default']['legend']

    # Get the image data
    response = requests.get(legend_url)

    # Check that the request was successful
    response.raise_for_status()

    output_path_legend = os.path.join("output/legend", "legend_{}.png".format(layer_name))
    # Write the image data to a file
    with open(output_path_legend, 'wb') as f:
        f.write(response.content)

    img = PIL.Image.open(output_path_legend)
    # Upscale the image
    upscaled_image = img.resize((img.width * 2, img.height * 2), PIL.Image.LANCZOS)
    upscaled_image.save(output_path_legend)
    return output_path_legend

# Define a function to calculate approximate map scale
def calculate_scale(gdf):
    # Get the bounds of the geodataframe
    xmin, ymin, xmax, ymax = gdf.total_bounds

    # Calculate the distance between the center and a point on the edge, in meters
    center_x, center_y = (xmin+xmax)/2, (ymin+ymax)/2
    edge_x, edge_y = xmax, center_y

    # Convert the coordinates from Web Mercator to WGS84 (latitude/longitude)
    center_lon, center_lat = pyproj.transform(pyproj.Proj(init='epsg:3857'), pyproj.Proj(init='epsg:4326'), center_x, center_y)
    edge_lon, edge_lat = pyproj.transform(pyproj.Proj(init='epsg:3857'), pyproj.Proj(init='epsg:4326'), edge_x, edge_y)

    ground_distance = geopy.distance.geodesic((center_lat, center_lon), (edge_lat, edge_lon)).meters

    # Get the size of the map in inches (replace these values with the actual size of your map)
    map_width_inches = 11.69
    map_height_inches = 8.27

    # Calculate the scale
    map_distance = map_width_inches * 0.0254  # convert inches to meters
    scale = ground_distance / map_distance

    return f"1:{int(scale)}"

# Classes section
class HeaderInsertImage(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        canvas.Canvas.__init__(self, *args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        """add page info to each page (page x of y)"""
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_footer()  # draw a header on each page
            self.draw_page_number(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_number(self, page_count):
        self.setFont("Helvetica", 9)
        self.drawRightString(7.6 * inch, 0.75 * inch,
                             "Page %d of %d" % (self._pageNumber, page_count))

    def draw_footer(self):
    # draw the image in the top-right corner
        self.drawImage("static/images/PI_logo.png", self._pagesize[0] - 1 * inch, self._pagesize[1] - 1 * inch, width=40, height=40, mask='auto')
        self.drawString(1 * inch, self._pagesize[1] - 1 * inch, "ParcelInsights")
        self.setFont("Helvetica", 9)
        self.drawString(1 * inch, 0.75 * inch, "Edah Sahinovic")
        





########### WEB FEATURE SERVICES PART
#gemeinde_input, gnr_input, kg_input = "Lochen am See", "427", "Oberweissau"

def create_pdf(gnr_input, kg_input, output_path):
    print("Generating PDF initiated..")
    print("\n GNR: {}, KG: {}".format(gnr_input, kg_input))
    
    gnr_input = str(gnr_input)
    kg_input = str(kg_input)
    
    #BEV link
    wfs_url = "https://geoserver22s.zgis.at/geoserver/BEV/ows?service=WFS"
    layer_parcel = "BEV:gst_vgd_3857_20221001" #native CRS = 3857

    #University geoserver link
    url_riskzones = "https://geoserver22s.zgis.at/geoserver/IPSDI_WT22/ows?service=WFS"
    #geology layer link
    layer_geology = "IPSDI_WT22:GEOLOGIE20" #native CRS = 31255
    #riskzones layer link
    layer_riskzones_water = "IPSDI_WT22:HQ_RISIKOZONEN"

    
    #lists containing layers and other information to be populated
    layers_list = []


    response = requests.get(wfs_url, params={
        "request": "GetFeature",
        "version": "1.1.0",
        "typeName": layer_parcel,
        "srsName": "EPSG:31255",
        "CQL_FILTER": "{}='{}' AND {}='{}'".format("GNR", gnr_input, "KG", kg_input),
        "outputFormat": "application/json"
    })

    if response.status_code == 200:
        data = response.json()
        
        gdf_parcel = gpd.GeoDataFrame.from_features(data["features"])
        gdf_parcel = gdf_parcel.set_crs("EPSG:31255")
        
        print("\nSuccessfully extracted the parcel..")
        gdf_parcel_3857 = gdf_parcel.to_crs(epsg=3857)
        
        output_file_parcel = os.path.join("output/shapefile", "bev_parcel_434_3857.shp")
        gdf_parcel_3857.to_file(output_file_parcel)
        #populate list with parcel information
        layers_list.append("gdf_parcel")

        
        gdf_parcel_bbox = gdf_parcel.total_bounds
        
        #old bbox for filering, doesn't work
        bbox_str = ','.join(map(str, gdf_parcel_bbox))
        bbox_str = f"{gdf_parcel_bbox[1]},{gdf_parcel_bbox[0]},{gdf_parcel_bbox[3]},{gdf_parcel_bbox[2]}"
        
        #set the bbox for filtering
        xmin, ymin, xmax, ymax = gdf_parcel.total_bounds
        #print("Parcel bbox separate: ", xmin, ymin, xmax, ymax)
        
        #bbox for parcel_neighbors
        bbox = gdf_parcel_3857.total_bounds  # returns a list [xmin, ymin, xmax, ymax]

        # Expand the bounding box by a certain percentage (e.g., 10%)
        expansion_factor = 0.1
        width = bbox[2] - bbox[0]
        height = bbox[3] - bbox[1]
        bbox_expanded = [bbox[0] - expansion_factor * width, bbox[1] - expansion_factor * height, bbox[2] + expansion_factor * width, bbox[3] + expansion_factor * height]

        # Create a spatial filter to only retrieve parcels within the expanded bounding box
        bbox_filter = box(*bbox_expanded)  # creates a shapely Polygon representing the expanded bounding box

        # Send another request to retrieve all parcels within the expanded bounding box
        response_parcel_neighbors = requests.get(wfs_url, params={
            "request": "GetFeature",
            "version": "1.1.0",
            "typeName": layer_parcel,
            "srsName": "EPSG:3857",
            "BBOX": f'{bbox_expanded[0]},{bbox_expanded[1]},{bbox_expanded[2]},{bbox_expanded[3]}',
            "outputFormat": "application/json"
        })

        
        print("Parcel bbox: ", bbox_str)
        response2 = requests.get(url_riskzones, params={
            "request": "GetFeature",
            "version": "1.1.0", 
            "typeName": layer_geology,
            "srsName": "EPSG:31255",
            "bbox": bbox_str,
            "outputFormat": "application/json"
        })

        response3 = requests.get(url_riskzones, params={
            "request": "GetFeature",
            "version": "1.1.0", 
            "typeName": layer_riskzones_water,
            "srsName": "EPSG:31255",
            "bbox": bbox_str,
            "outputFormat": "application/json"
        })


        if response_parcel_neighbors.status_code == 200:
            data_neighbors = response_parcel_neighbors.json()
            gdf_parcel_neighbors = gpd.GeoDataFrame.from_features(data_neighbors["features"])
            gdf_parcel_neighbors_3857 = gdf_parcel_neighbors.set_crs("EPSG:3857", inplace=True)

            if gdf_parcel_neighbors.empty:
                print("Parcel neighbors layer is empty.")
            else:
                #gdf_parcel_neighbors_3857 = gdf_parcel_neighbors.to_crs(epsg=3857)
                print("\nSuccessfully extracted the parcel neighbors..")
                
                output_file_neighbors = os.path.join("output/shapefile", "parcel_neighbors_3857.shp")
                gdf_parcel_neighbors_3857.to_file(output_file_neighbors)
                #layers_list.append("gdf_parcel_neighbors")

        if response2.status_code == 200:
            data_geology = response2.json()
            gdf_geology = gpd.GeoDataFrame.from_features(data_geology["features"])
            gdf_geology.set_crs("EPSG:31255", inplace=True)

            
            # convert bbox_str to a list of floats - not used?
            bbox = list(map(float, bbox_str.split(',')))

            #reduces from multiple to single feature
            gdf_geology_filtered = gdf_geology.cx[xmin:xmax, ymin:ymax]

            if gdf_geology_filtered.empty:
                print("Geology is empty for this one.")
            else:
                
                print("\nSuccessfully extracted the geology layer..")

                gdf_geology_filtered_3857 = gdf_geology_filtered.to_crs(epsg=3857)
                layers_list.append("gdf_geology")
            # save the clipped GeoDataFrame as a shapefile
            #output_file = os.path.join("output", "geology_within_bbox_clipped.shp")
            #gdf_geology_filtered.to_file(output_file)

                output_file_geology = os.path.join("output/shapefile", "geology_3857.shp")
                gdf_geology_filtered_3857.to_file(output_file_geology)
        else:
            print("Error: Unable to fetch features from the second WFS.")

        if response3.status_code == 200:
            data_riskzones = response3.json()
            gdf_riskzones_water = gpd.GeoDataFrame.from_features(data_riskzones["features"])
            gdf_riskzones_water.set_crs("EPSG:31255", inplace=True)

            #reduces from multiple to single feature
            gdf_riskzones_water_filtered = gdf_riskzones_water.cx[xmin:xmax, ymin:ymax]


            if gdf_riskzones_water_filtered.empty:
                print("Riskzones water is empty for this one.")
            else:
                
                print("\nSuccessfully extracted the water riskzones layer..")
                
                gdf_riskzones_filtered_3857 = gdf_riskzones_water_filtered.to_crs(epsg=3857)

                output_file = os.path.join("output/shapefile", "riskzones_3857.shp")
                gdf_riskzones_filtered_3857.to_file(output_file)

                layers_list.append("gdf_riskzones_water")
            
        else:
            print("Cannot fetch flood riskzones feature")
        layers_list.append("dem")
        layers_list.append("aspect")
        layers_list.append("slope")
        print("\nSuccessfully extracted the WFS layers.. proceeding to WMS and PDF generation")
    else:
        print("Error: Unable to fetch features.")




    #BUIDLING FULL CALLABLE PDF DOCUMENT BUILDER - WORKING ON THIS ONE
    #layers names = gdf_parcel ,gdf_parcel_neighbors, gdf_geology, dem, aspect, slope

    # ISSUES
    #table cells can not wrap up the text, therefore leaving the width of complete table to the mercy of the row information each column has
    #change bbox variable name in the WMS fetching code so it doesn't conflict with bbox variable of the adding axes function
    # Results generated from aspect and slope layers seem incorrect
    # The DEM png derived from DEM tif is created with wrong color pallette, it should be grayscale instead of random colors.
    # TODO
    #add labels for the geology map so we can distinguish between different layers
        #try by clipping the layers first and than adding as center labels for each feature

    ## Set up the document
    # Create a new PDF document with A4 page size
    #output_path_pdf = os.path.join("output/pdf", "report_parcel.pdf")
    print("Generating and populating a PDF document..")
    pdf = SimpleDocTemplate(output_path, pagesize=A4)
    # Create a story list to populate with PDF elements
    pdf_elements_list = []

    # Set up the document's styles
    styles = getSampleStyleSheet()

    frontpage_title_style = ParagraphStyle('Frontpage', parent=styles['Heading1'], alignment=1, textColor=colors.black, spaceAfter=12, fontSize=20, fontName='Helvetica-Bold')
    frontpage_subtitle_style = ParagraphStyle('Frontpage', parent=styles['Heading1'], alignment=1, textColor=colors.black, spaceAfter=12, fontSize=14, fontName='Helvetica-Bold')
    
    
    title_style = ParagraphStyle('Heading1', parent=styles['Heading1'], alignment=1, textColor=colors.black, spaceAfter=12)
    title_style.fontName = 'Helvetica-Bold'

    text_style = ParagraphStyle('intro', parent=styles['Normal'], spaceAfter=12, alignment=TA_JUSTIFY)

    map_text_style = ParagraphStyle('centered', parent=styles['Normal'], alignment=1)
    table_text_style = ParagraphStyle('intro', parent=styles['Normal'], fontSize=10, spaceAfter=2)

    table_style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.gray),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ])

    ## Calculate standard elements beforehand (scale)
    map_scale_parcel_neighbors = calculate_scale(gdf_parcel_neighbors_3857)
    map_scale_parcel = calculate_scale(gdf_parcel_3857)
    gdf_parcel_total_area = gdf_parcel_3857.geometry.area.sum()
    bbox_parcel_3857 = gdf_parcel_3857.total_bounds
    count_page = 0

    ## Set up first two generic pages
    # FRONTPAGE
    frontpage_title = "I3 Project: ParcelInsights"
    frontpage_subtitle = "Automated Parcel-based Reports for Different Environmental Conditions based on Open-source Technologies"


    frontpage_title_text = Paragraph(frontpage_title, frontpage_title_style)
    frontpage_subtitle_text = Paragraph(frontpage_subtitle, frontpage_subtitle_style)

    pdf_elements_list.extend([
        Spacer(1, 250),
        frontpage_title_text,
        frontpage_subtitle_text,
        PageBreak()
    ])


    # TABLE OF CONTENTS
    # Create a list to store the content pages and TOC entries


    for layer in layers_list:
        #print(layer)
        
        if layer == "gdf_parcel":
            count_page += 1
            ##building parcel and parcel neighbors map image

            fig, ax = plt.subplots(figsize=(8.27, 9.69/2))  # Half A4 size map # 8.27, 9.69/2

            gdf_parcel_neighbors_3857.boundary.plot(ax=ax, edgecolor='red', linewidth=1.5)

            # Plot the boundaries of the geodataframe - gdf_parcel
            gdf_parcel_3857.boundary.plot(ax=ax, edgecolor='#FFA500', linewidth=3)

            # Add labels for gdf_neighbors using "GNR" attribute
            for x, y, label in zip(gdf_parcel_neighbors_3857.geometry.centroid.x, gdf_parcel_neighbors_3857.geometry.centroid.y, gdf_parcel_neighbors_3857["GNR"]):
                ax.annotate(label, (x, y), color='red', fontsize=8, ha='center', va='center')

            for x, y, label in zip(gdf_parcel_3857.geometry.centroid.x, gdf_parcel_3857.geometry.centroid.y, gdf_parcel_3857["GNR"]):
                ax.annotate(label, (x, y), color='#FFA500', fontsize=8, ha='center', va='center')
            #ax.text(0.5, 1.05, 'This parcel here is a parcel, duhh', transform=ax.transAxes, ha='center', fontsize=12)# Plot the boundaries of the geodataframe - gdf_neighbors

            # Add the basemap
            ctx.add_basemap(ax, source=ctx.providers.BasemapAT.orthofoto)

            ax.axis('off')

            
            # Add the small box with text as a map scale representation
            ax.text(0.01, 0.01, 'Scale: {}'.format(map_scale_parcel_neighbors), transform=ax.transAxes, 
                    fontsize=10, verticalalignment='bottom', 
                    bbox=dict(facecolor='#D3D3D3', edgecolor='black', boxstyle='square,pad=0.2'))


            # Save the map to an image file
            output_path_parcel = os.path.join("output/maps", "map_parcel.png")
            #ax.set_aspect('equal')
            plt.savefig(output_path_parcel, bbox_inches='tight', dpi=300)
            plt.close(fig)

            # Create an image frame 
            img = PIL.Image.open(output_path_parcel)
            bordered_img = PIL.ImageOps.expand(img, border=1, fill='black')
        
            # Save the new image
            bordered_img.save(output_path_parcel)

            

            # datetime object containing current date and time
            now = datetime.now()
            # dd/mm/YY H:M:S
            dt_string = now.strftime("%d/%m/%Y %H:%M:%S")


            #convert parcel_data to a list
            parcel_gnr_value = gdf_parcel["GNR"].tolist()
            gnr_values_str = ', '.join(map(str, parcel_gnr_value))

            parcel_kg_nr_value = gdf_parcel["KG_NR"].tolist()
            kg_nr_values_str = ', '.join(map(str, parcel_kg_nr_value))

            parcel_kg_value = gdf_parcel["KG"].tolist()
            kg_values_str = ', '.join(map(str, parcel_kg_value))

            parcel_gemeinde_value = gdf_parcel["Gemeinde"].tolist()
            gemeinde_values_str = ', '.join(map(str, parcel_gemeinde_value))

            parcel_bezirk_value = gdf_parcel["Bezirk"].tolist()
            bezirk_values_str = ', '.join(map(str, parcel_bezirk_value))

            parcel_bundesland_value = gdf_parcel["Bundesland"].tolist()
            bundesland_values_str = ', '.join(map(str, parcel_bundesland_value))

            parcel_staat_value = gdf_parcel["Staat"].tolist()
            staat_values_str = ', '.join(map(str, parcel_staat_value))

            parcel_size = gdf_parcel_3857.geometry.area[0]
            parcel_size = round(parcel_size, 2)

            parcel_perimeter = gdf_parcel_3857.geometry.length[0]
            parcel_perimeter = round(parcel_perimeter, 2)

            # Create a coordinate transformation object
            #transformer = pyproj.Transformer.from_crs(gdf_parcel_3857, "EPSG:4326", always_xy=True)


            #central_lon, central_lat = transformer.transform(central_x_meters, central_y_meters)
            #print(central_lon, central_lat)

            #transform coordiantes from planar to lat/lon
            parcel_centroid = gdf_parcel_3857.geometry.centroid[0]
            # Extract the central x and y coordinates in meters
            central_x_meters = parcel_centroid.x
            central_y_meters = parcel_centroid.y

            # Convert the central x and y coordinates to latitude and longitude
            transformed_central_x, transformed_central_y = pyproj.transform(gdf_parcel_3857.crs, "EPSG:4326", central_x_meters, central_y_meters)
            transformed_central_x = round(transformed_central_x, 2)
            transformed_central_y = round(transformed_central_y, 2)

            # Define data as a pandas DataFrame or GeoDataFrame
            data = pd.DataFrame({
                #'GNR': [gnr_values_str],
                #'KG' : [kg_values_str],
                'Municipality' : [gemeinde_values_str],
                'District' : [bezirk_values_str],
                'Province' : [bundesland_values_str],
                'Country' : [staat_values_str],
                'Size (m²)' : [parcel_size],
                'Perimeter' : [parcel_perimeter],
                'Lat' : [transformed_central_x],
                'Lon' : [transformed_central_y]

            })

            #Adding elements to the file
            fileName = "parcel_404.pdf"
            documentTitle = "sample"
            title = "PARCEL (KG: {}, GNR: {}) ".format(kg_input, gnr_input)
            intro = """ On a date <b>{}</b> an automated PDF document for the parcel in administrative unit <b>{}</b> with parcel number <b>{}</b> is issued. 
                        The neighboring parcels that share borders with our primary parcel are presented as their environmental characteristics could provide vital insights
                        into local factors that may influence or interact with conditions within our primary parcel.""".format(dt_string, kg_input, gnr_input)
            map_figure_text = "<b>Map {}.</b> Parcel <b>{}</b>, <b>{}</b> Boundary and Neighboring Parcels".format(count_page, kg_input, gnr_input)
            table_figure_text = "<b>Table {}.</b> Comprehensive Summary of Parcel <b>{}</b>, <b>{}</b> Attributes".format(count_page, kg_input, gnr_input)
            text = """ The parcel is located in the municipality of <b>{}</b>, which is part of the <b>{}</b> district in the <b>{}</b> province of <b>{}</b>. 
                        The parcel has a size of <b>{}</b> square meters, which is enclosed within a perimeter of <b>{}</b> meters. 
                        The central geographical location of the parcel is given by the latitude <b>{}</b> and longitude <b>{}</b>.
                    """.format(gemeinde_values_str, bezirk_values_str, bundesland_values_str, staat_values_str, parcel_size, parcel_perimeter, transformed_central_x, transformed_central_y)
            
            # Create the content flowables
            title_text = Paragraph(title, title_style)
            intro_text = Paragraph(intro, text_style)
            map_text = Paragraph(map_figure_text, map_text_style)
            table_text = Paragraph(table_figure_text, table_text_style)
            text_text = Paragraph(text, text_style)

            # Create the content flowables
            image = Image(output_path_parcel, width=380, height=380)
            table_data = [list(data.columns)] + [list(row) for row in data.values]
            table = Table(table_data, style=table_style)

            # Build the story (content)
            pdf_elements_list.extend([
                title_text,
                Spacer(1, 0),
                intro_text,
                Spacer(1, 0),
                image,
                Spacer(1, 10),
                map_text,
                Spacer(1, 10),
                table_text,
                table,
                Spacer(1, 10),
                text_text,
                PageBreak()
            ])

            #pdf_elements_list.append(PageBreak())
        
        if layer == "gdf_geology":
            count_page += 1
            ## Create a geology map
            fig, ax = plt.subplots(figsize=(8.27, 9.69/2))  # Half A4 size map

            #clipping the layer to the extend of the parcel for further analysis
            gdf_geology_filtered_clipped_3857 = gpd.overlay(gdf_geology_filtered_3857, gdf_parcel_3857, how='intersection')
            gdf_geology_filtered_clipped_3857.plot(ax=ax, edgecolor='red', linewidth=1.5, alpha=0.5)

            # Plot the boundaries of the geodataframe - gdf_parcel
            gdf_parcel_3857.boundary.plot(ax=ax, edgecolor='#FFA500', linewidth=3,)

            for x, y, label in zip(gdf_geology_filtered_clipped_3857.geometry.centroid.x, gdf_geology_filtered_clipped_3857.geometry.centroid.y, gdf_geology_filtered_clipped_3857['code']):
                ax.annotate(label, xy=(x, y), xytext=(3, 3), color="red", textcoords="offset points")

            # Set the extent of the plot to match the extent of gdf_parcel
            minx, miny, maxx, maxy = gdf_parcel_3857.total_bounds
            ax.set_xlim(minx, maxx)
            ax.set_ylim(miny, maxy)

            # Add the basemap
            ctx.add_basemap(ax, source=ctx.providers.BasemapAT.orthofoto)

            ax.axis('off')

            # Add the small box with text as a map scale representation
            ax.text(0.01, 0.01, 'Scale: {}'.format(map_scale_parcel), transform=ax.transAxes, 
                    fontsize=10, verticalalignment='bottom', 
                    bbox=dict(facecolor='#D3D3D3', edgecolor='black', boxstyle='square,pad=0.2'))

            # Save the map to an image file
            output_path_geology = os.path.join("output/maps", "geology_map.png")
            plt.savefig(output_path_geology, bbox_inches='tight', dpi=300)
            plt.close(fig)

            # Create an image frame 
            img = PIL.Image.open(output_path_geology)
            bordered_img = PIL.ImageOps.expand(img, border=1, fill='black')
        
            # Save the new image
            bordered_img.save(output_path_geology)
        
            #convert geology data to a list
            
            geology_code_value = gdf_geology_filtered_3857["code"].tolist()
            geology_formation_value = gdf_geology_filtered_3857["formation"].tolist()
            geology_lithomain_value = gdf_geology_filtered_3857["litho_haup"].tolist()
            geology_lithonebe_value = gdf_geology_filtered_3857["litho_nebe"].tolist()
            geology_kurztitel_value = gdf_geology_filtered_3857["kurztitel"].tolist()

            # Calculate the percentage for each feature within a parcel
            gdf_geology_filtered_clipped_3857['area'] = gdf_geology_filtered_clipped_3857.geometry.area
            gdf_geology_filtered_clipped_3857['percentage'] = (gdf_geology_filtered_clipped_3857['area'] / gdf_parcel_total_area) * 100
            gdf_geology_filtered_clipped_3857['percentage'] = gdf_geology_filtered_clipped_3857['percentage'].round(2)
            geology_coverage_value = gdf_geology_filtered_clipped_3857['percentage'].tolist()
        
            data = pd.DataFrame({
                'Code' : geology_code_value,
                'Formation' : geology_formation_value,
                'Litho main' : geology_lithomain_value,
                'Litho nearby' : geology_lithonebe_value,
                'Short title' : geology_kurztitel_value,
                'Coverage (%)' : geology_coverage_value
            })

            num_rows = len(gdf_geology_filtered_clipped_3857)

            #Adding elements to the file - geology
            title = "PARCEL (KG: {}, GNR: {}): GEOLOGY".format(kg_input, gnr_input)
            intro = """Geology can provide invaluable information about specific piece of land, aiding in understanding its past, present and potential future.
                        The geological formation gives insight into the age and type of rock layers present, indicating the land's past environemnts and processes it underwent,
                        while the lithology reveals the predominant rock types in the parcel, providing hints about soil properties, stability and potential uses."""
            if num_rows == 1:
                text = """The parcel of interest comprises <b>{}</b> distinct geological feature: The parcel includes <b>{}</b> geological code, which is associated with the <b>{}</b> formation. 
                The main lithological types in this formation are <b>{}</b>, and nearby, one can also find <b>{}</b>. In the geological records, this formation is 
                referred to as '<b>{}</b>'. This geological formation covers <b>{}</b>% of the total parcel area.""".format(num_rows, geology_code_value[0], geology_formation_value[0], geology_lithomain_value[0], geology_lithonebe_value[0], geology_kurztitel_value[0], geology_coverage_value[0])
            else:
                iterator = 0
                text = "The parcel of interest comprises <b>{}</b> distinct geological features: ".format(num_rows)

                # Iterate through number of features to create separate paragraph for each geological feature
                for iterator in range(num_rows):
                    text += """For the <b>{}</b>. feature, the geological code is <b>{}</b>, whbich is associated with the <b>{}</b> formnation. The main lithological types in this formation are <b>{}</b>, and nearby,
                    one can also find <b>{}</b>. In the geological records, this formation is referred to as '<b>{}</b>'. This geological formation covers approximately <b>{}</b>% of the total parcel 
                    area. <br/><br/>""".format(iterator + 1, geology_code_value[iterator], geology_formation_value[iterator], geology_lithomain_value[iterator], geology_lithonebe_value[iterator], geology_kurztitel_value[iterator], geology_coverage_value[iterator])
                    iterator += 1
            
            map_figure_text = "<b>Map {}</b>. Geological Composition Map of the Parcel <b>{}</b>, <b>{}</b>".format(count_page, kg_input, gnr_input)
            table_figure_text = "<b>Table {}.</b> Detailed Geological Features and Coverage Table".format(count_page)

            # Create the content flowables
            title_text = Paragraph(title, title_style)
            intro_text = Paragraph(intro, text_style)
            map_text = Paragraph(map_figure_text, map_text_style)
            table_text = Paragraph(table_figure_text, table_text_style)
            text_text = Paragraph(text, text_style)

            # Create the content flowables
            image = Image(output_path_geology, width=380, height=380)
            table_data = [list(data.columns)] + [list(row) for row in data.values]
            table = Table(table_data, style=table_style) #colWidths=colWidths

            pdf_elements_list.extend([
                title_text,
                Spacer(1, 0),
                intro_text,
                Spacer(1, 0),
                image,
                Spacer(1, 10),
                map_text,
                Spacer(1, 10),
                table_text,
                table,
                Spacer(1, 10),
                text_text,
                PageBreak()
            ])

        if layer == "gdf_riskzones_water":
            count_page += 1
            fig, ax = plt.subplots(figsize=(8.27, 9.69/2))  # Half A4 size map # 8.27, 9.69/2
            gdf_riskzones_filtered_clipped_3857 = gpd.overlay(gdf_riskzones_filtered_3857, gdf_parcel_3857, how='intersection')
            
            gdf_riskzones_filtered_clipped_3857.plot(ax=ax, edgecolor='red', linewidth=1.5, alpha=0.5)
            # Plot the boundaries of the geodataframe - gdf_parcel
            gdf_parcel_3857.boundary.plot(ax=ax, edgecolor='#FFA500', linewidth=3)

            # Add labels for gdf_neighbors using "GNR" attribute
            for x, y, label in zip(gdf_riskzones_filtered_clipped_3857.geometry.centroid.x, gdf_riskzones_filtered_clipped_3857.geometry.centroid.y, gdf_riskzones_filtered_clipped_3857["art"]):
                ax.annotate(label, (x, y), color='red', fontsize=8, ha='center', va='center')

            # Add the basemap
            ctx.add_basemap(ax, source=ctx.providers.BasemapAT.orthofoto)

            ax.axis('off')

            
            # Add the small box with text as a map scale representation
            ax.text(0.01, 0.01, 'Scale: {}'.format(map_scale_parcel), transform=ax.transAxes, 
                    fontsize=10, verticalalignment='bottom', 
                    bbox=dict(facecolor='#D3D3D3', edgecolor='black', boxstyle='square,pad=0.2'))


            # Save the map to an image file
            output_path_riskzones = os.path.join("output/maps", "map_riskzones.png")
            #ax.set_aspect('equal')
            plt.savefig(output_path_riskzones, bbox_inches='tight', dpi=300)
            plt.close(fig)

            # Create an image frame 
            img = PIL.Image.open(output_path_riskzones)
            bordered_img = PIL.ImageOps.expand(img, border=1, fill='black')
        
            # Save the new image
            bordered_img.save(output_path_riskzones)

            riskzones_landid_value = gdf_riskzones_filtered_clipped_3857["land_id"].tolist()
            riskzones_zone_value = gdf_riskzones_filtered_clipped_3857["art"].tolist()
            gdf_riskzones_filtered_clipped_3857['area'] = gdf_riskzones_filtered_clipped_3857.geometry.area
            gdf_riskzones_filtered_clipped_3857['percentage'] = (gdf_riskzones_filtered_clipped_3857['area'] / gdf_parcel_total_area) * 100
            gdf_riskzones_filtered_clipped_3857['percentage'] = gdf_riskzones_filtered_clipped_3857['percentage'].round(3)
            riskzones_coverage_value = gdf_riskzones_filtered_clipped_3857['percentage'].tolist()
        
            data = pd.DataFrame({
                'Land ID' : riskzones_landid_value,
                'Zone' : riskzones_zone_value,
                'Coverage (%)' : riskzones_coverage_value
            })

            #Adding elements to the file - riskzones
            title = "PARCEL (KG: {}, GNR: {}): WATER RISKZONES".format(kg_input, gnr_input)
            intro = """The parcel under discussion is located within an area that is susceptible to certain flood risks. These risks are categorized into six distinct zones: Red, Formerly a Red Zone, Red-Yellow, Yellow, Blue and Residual Risk zone. 
            Each of these zones represents varying levels of flood risk, necessitating different degrees of management and precautionary measures. The categorization of these zones is integral to comprehending the safety, 
            developmental potential, and environmental implications of the parcel."""

            text = "The parcel of interest comprises <b>{}</b> distinct flood risk zone(s):".format(len(riskzones_zone_value))
            for zone, coverage in zip(riskzones_zone_value, riskzones_coverage_value):
                text += "<br/><br/>"
                if zone == "Rote Zone":
                    text += "The '<b>Red Zone</b>' signifies an area where construction is prohibited due to the high flood risk. This zone covers approximately <b>{}%</b> of the total parcel area.".format(coverage)
                elif zone == "vormals Rote Zone":
                    text += "The '<b>Formerly a Red Zone</b>' classification refers to areas that were once deemed to be in high flood risk and were classified as 'Red Zones'. Due to changes in environmental conditions, these areas have seen a reduction in their flood risk. This zone covers approximately <b>{}%</b> of the total parcel area.".format(coverage)
                elif zone == "RotGelbe Zone":
                    text += "The '<b>Red-Yellow Zone</b>' is a priority area for the implementation of retention, runoff, and water management strategies. This zone covers approximately <b>{}%</b> of the total parcel area.".format(coverage)
                elif zone == "Gelbe Zone":
                    text += "The '<b>Yellow Zone</b>' mandates precautions and signifies a lower risk, yet still potential for flooding. This zone covers approximately <b>{}%</b> of the total parcel area.".format(coverage)
                elif zone == "Blaue Zone":
                    text += "The '<b>Blue Zone</b>' marks regions where water management needs are prioritized. This zone covers approximately <b>{}%</b> of the total parcel area.".format(coverage)
                elif zone == "Restrisiko":
                    text += "The '<b>Residual Risk</b>' category in flood danger zones represents areas that are safeguarded by flood protection measures such as dams or levees, but are still at risk in the event of a failure or overtopping of these defenses. While protection measures considerably reduce the risk, they cannot entirely eliminate it. This zone covers approximately <b>{}%</b> of the total parcel area.".format(coverage)
                    
            
            map_figure_text = "<b>Map {}.</b> Spatial Distribution of Flood Risk Zones in the Parcel <b>{}</b>, <b>{}</b> ".format(count_page, kg_input, gnr_input)
            table_figure_text = "<b>Table {}.</b> Classification and Proportions of Flood Risk Zones within the Parcel".format(count_page)

            # Create the content flowables
            title_text = Paragraph(title, title_style)
            intro_text = Paragraph(intro, text_style)
            map_text = Paragraph(map_figure_text, map_text_style)
            table_text = Paragraph(table_figure_text, table_text_style)
            text_text = Paragraph(text, text_style)

            image = Image(output_path_riskzones, width=380, height=380)
            table_data = [list(data.columns)] + [list(row) for row in data.values]
            table = Table(table_data, style=table_style) #colWidths=colWidths

            pdf_elements_list.extend([
                title_text,
                Spacer(1, 0),
                intro_text,
                Spacer(1, 0),
                image,
                Spacer(1, 10),
                map_text,
                Spacer(1, 10),
                table_text,
                table,
                Spacer(1, 10),
                text_text,
                PageBreak()
            ])
            
        if layer == "dem":
            count_page += 1


            timeout = 5
            wms_hillshade_available = "no"
            """
            try:
                wms_hillshade = WebMapService('https://zgis188.geo.sbg.ac.at/arcgis/services/23S856162/hillshade_ua_3857/MapServer/WMSServer?')
                print("WMS request successful.")
                wms_hillshade_available = "yes"
            except socket.timeout:
                print("WMS hillshade request timed out.")
                wms_hillshade_available = "no"
            except Exception as e:
                print(f"WMS hillshade request failed with an error: {e}")
                wms_hillshade_available = "no"
            
            """
            
            if wms_hillshade_available == "yes":
                img_hillshade = wms_hillshade.getmap(layers=['0'],
                        srs='EPSG:3857',
                        bbox=bbox_parcel_3857,
                        size=(512, 512),
                        format='image/png', #image/png
                        transparent=True)

                # You can save the response to a file
                output_path_hillshade = os.path.join("output/wms_img", "output_hillshade.png")
                with open(output_path_hillshade, 'wb') as out:
                    out.write(img_hillshade.read())

                # Read the image file
                im = PIL.Image.open(output_path_hillshade)

                # Create a figure and axes
                fig, ax = plt.subplots(figsize=(8.27, 9.69/2))

                # Get the extent of your geopandas dataframe
                minx, miny, maxx, maxy = gdf_parcel_3857.total_bounds
                
                # Display the image, stretched to the extent of your geopandas dataframe
                ax.imshow(im, extent=[minx, maxx, miny, maxy], aspect=0.5, alpha=0.7)
                
                # Plot the boundaries of the geodataframe - gdf_parcel
                gdf_parcel_3857.boundary.plot(ax=ax, edgecolor='#FFA500', linewidth=3)

                # Add the small box with text as a map scale representation
                ax.text(0.01, 0.01, 'Scale: {}'.format(map_scale_parcel), transform=ax.transAxes, 
                        fontsize=10, verticalalignment='bottom', 
                        bbox=dict(facecolor='#D3D3D3', edgecolor='black', boxstyle='square,pad=0.2'))

                ax.axis('off')

                # Save the map to an image file
                output_path_hillshade = os.path.join("output/maps", "map_hillshade.png")
                plt.savefig(output_path_hillshade, bbox_inches='tight', dpi=300)
                plt.close(fig)

                # Create an image frame 
                img = PIL.Image.open(output_path_hillshade)
                bordered_img = PIL.ImageOps.expand(img, border=1, fill='black')
            
                # Save the new image
                bordered_img.save(output_path_hillshade)

            wcs = WebCoverageService('https://zgis188.geo.sbg.ac.at/arcgis/services/23S856162/dem_10m_ua_3857/ImageServer/WCSServer?', version='1.0.0')

            # Extract the layer by conerting bbox to tuple
            bbox_parcel_3857_tuple = tuple(bbox_parcel_3857)  # Convert the list to a tuple

            response_wcs_dem = wcs.getCoverage(identifier='1', 
                                    bbox=bbox_parcel_3857_tuple, 
                                    format='GeoTIFF', 
                                    crs='EPSG:3857', 
                                    width=256, 
                                    height=256)

            # Save the response to a file
            output_path_dem = os.path.join("output/tiff", "output_dem.tif")
            with open(output_path_dem, 'wb') as f:
                f.write(response_wcs_dem.read())

            if wms_hillshade_available == "no":
                # Open the image
                img = PIL.Image.open(output_path_dem)

                # Convert the image data to an array
                img_data = np.array(img)

                # Rescale the image data to 0-255
                img_data_rescaled = ((img_data - img_data.min()) * (1/(img_data.max() - img_data.min()) * 255)).astype('uint8')

                # Convert the rescaled data back into an image
                img_rescaled = PIL.Image.fromarray(img_data_rescaled)
                img_gray = img_rescaled.convert('L')
                
                # Save the rescaled image
                output_dem = os.path.join("output/wms_img", "output_dem.png")
                img_gray.save(output_dem)

                # Read the image file
                im = PIL.Image.open(output_dem)

                # Create a figure and axes
                fig, ax = plt.subplots(figsize=(8.27, 9.69/2))

                # Get the extent of your geopandas dataframe
                minx, miny, maxx, maxy = gdf_parcel_3857.total_bounds

                # Display the image, stretched to the extent of your geopandas dataframe
                ax.imshow(im, extent=[minx, maxx, miny, maxy], alpha=0.5)

                # Plot the boundaries of the geodataframe - gdf_parcel
                gdf_parcel_3857.boundary.plot(ax=ax, edgecolor='#FFA500', linewidth=3, alpha=0.5)

                # Add the small box with text as a map scale representation
                ax.text(0.01, 0.01, 'Scale: {}'.format(map_scale_parcel), transform=ax.transAxes, 
                        fontsize=10, verticalalignment='bottom', 
                        bbox=dict(facecolor='#D3D3D3', edgecolor='black', boxstyle='square,pad=0.2'))

                ax.axis('off')

                # Save the map to an image file
                output_path_dem_png = os.path.join("output/maps", "map_dem.png")
                plt.savefig(output_path_dem_png, bbox_inches='tight', dpi=300)
                plt.close(fig)

                # Create an image frame 
                img = PIL.Image.open(output_path_dem_png)
                bordered_img = PIL.ImageOps.expand(img, border=1, fill='black')
            
                # Save the new image
                bordered_img.save(output_path_dem_png)

            # Analyze the data - calculate min, average and max elevation values
            with rasterio.open(output_path_dem) as src:
                # Read the first band into an array
                band1 = src.read(1)

                # If the band is a 2D array
                if len(band1.shape) == 2:
                    elev_min_val = np.round(np.nanmin(band1), 2)  # Use np.nanmin to exclude NaN values
                    elev_avg_val = np.round(np.nanmean(band1), 2)  # Use np.nanmean to exclude NaN values
                    elev_max_val = np.round(np.nanmax(band1), 2)  # Use np.nanmax to exclude NaN values
                else:  # If the band is a 3D array
                    elev_min_val = np.round(np.nanmin(band1, axis=(1, 2)), 2)
                    elev_avg_val = np.round(np.nanmean(band1, axis=(1, 2)), 2)
                    elev_max_val = np.round(np.nanmax(band1, axis=(1, 2)), 2)

                #print(f'Minimum: {elev_min_val}')
                #print(f'Average: {elev_avg_val}')
                #print(f'Maximum: {elev_max_val}')

            
            data = pd.DataFrame({
                'Min value' : [elev_min_val],
                'Avg value' : [elev_avg_val],
                'Max value' : [elev_max_val]
            })

            #Adding elements to the file - DEM
            title = "PARCEL (KG: {}, GNR: {}): DIGITAL ELEVATION MODEL".format(kg_input, gnr_input)
            intro = """The Digital Elevation Model provides valuable topographical information about the parcel in question. It presents a three-dimensional view of the terrain, 
                        providing the detailed insights into the physical attributes of the parcel, allowing for better planning and decision-making."""
            text = """The analysis of the DEM reveals that the elevation within the parcel varies, indicating a diverse terrain. The minimum elevation recorded is <b>{:.2f}</b> meters, 
                        while the maximum stands at <b>{:.2f}</b> meters. The average elevation across the parcel is around <b>{:.2f}</b> meters.""".format(elev_min_val, elev_max_val, elev_avg_val)
            map_figure_text = "<b>Map {}.</b>. Topographical Representation of Parcel <b>{}</b>, <b>{}</b> ".format(count_page, kg_input, gnr_input) 
            table_figure_text = "<b>Table {}.</b> Elevation Characteristics Summary in Meters".format(count_page)

            # Create the content flowables
            title_text = Paragraph(title, title_style)
            intro_text = Paragraph(intro, text_style)
            map_text = Paragraph(map_figure_text, map_text_style)
            table_text = Paragraph(table_figure_text, table_text_style)
            text_text = Paragraph(text, text_style)

            # Create the content flowables
            if wms_hillshade_available == "yes":
                image = Image(output_path_hillshade, width=380, height=380)
            else:
                image = Image(output_path_dem_png, width=380, height=380)
            table_data = [list(data.columns)] + [list(row) for row in data.values]
            table = Table(table_data, style=table_style) #colWidths=colWidths

            pdf_elements_list.extend([
                title_text,
                Spacer(1, 0),
                intro_text,
                Spacer(1, 0),
                image,
                Spacer(1, 10),
                map_text,
                Spacer(1, 10),
                table_text,
                table,
                Spacer(1, 10),
                text_text,
                PageBreak()
            ])


        #the aspect layer doesn't work for some reason
        if layer == "aspect":
            count_page += 1
            
            img_aspect = wms_aspect.getmap(layers=['0'],
                        srs='EPSG:3857',
                        bbox=bbox_parcel_3857,
                        size=(512, 512),
                        format='image/png',
                        transparent=True)

            # You can save the response to a file
            output_path_aspect = os.path.join("output/wms_img", "output_aspect.png")
            with open(output_path_aspect, 'wb') as out:
                out.write(img_aspect.read())
            
            # Read the image file
            im = PIL.Image.open(output_path_aspect)

            # Create a figure and axes
            fig, ax = plt.subplots(figsize=(8.27, 9.69/2))

            # Get the extent of your geopandas dataframe
            minx, miny, maxx, maxy = gdf_parcel_3857.total_bounds

            # Display the image, stretched to the extent of your geopandas dataframe
            ax.imshow(im, extent=[minx, maxx, miny, maxy], alpha=0.5)

            # Plot the boundaries of the geodataframe - gdf_parcel
            gdf_parcel_3857.boundary.plot(ax=ax, edgecolor='#FFA500', linewidth=3)

            # Add the small box with text as a map scale representation
            ax.text(0.01, 0.01, 'Scale: {}'.format(map_scale_parcel), transform=ax.transAxes, 
                    fontsize=10, verticalalignment='bottom', 
                    bbox=dict(facecolor='#D3D3D3', edgecolor='black', boxstyle='square,pad=0.2'))

            
            ax.axis('off')
            
            # Save the map to an image file
            output_path_aspect = os.path.join("output/maps", "map_aspect.png")
            plt.savefig(output_path_aspect, bbox_inches='tight', dpi=300)
            plt.close(fig)

            # Add the legend to the image, lower right corner
            main_img = mpimg.imread(output_path_aspect)
            fig, ax = plt.subplots()
            ax.imshow(main_img)
            
            # Fetch the legend from WMS with this function
            legend = get_WMS_legend(wms_aspect, "aspect")

            legend_img = mpimg.imread(legend)
            
            # Create inset axes for the legend
            axins = inset_axes(ax, width="20%", height="20%", loc='lower right') 

            # Display legend in the inset axes
            axins.imshow(legend_img)

            # Hide axes for a cleaner look
            ax.axis('off')
            axins.axis('off')

            # Save the map to an image file
            output_path_aspect = os.path.join("output/maps", "map_aspect_with_legend.png")
            plt.savefig(output_path_aspect, bbox_inches='tight', dpi=300)
            plt.close()

            # Create an image frame 
            img = PIL.Image.open(output_path_aspect)
            bordered_img = PIL.ImageOps.expand(img, border=1, fill='black')
        
            # Save the new image
            #output_path_aspect_frame = os.path.join("output/maps", "map_aspect_frame.png")
            bordered_img.save(output_path_aspect)

            ## Fetch the values (percentages of ) aspect/orientation within the parcel extent
            # Set up the WCS connection
            wcs = WebCoverageService('https://zgis188.geo.sbg.ac.at/arcgis/services/23S856162/aspect_ua_3857/ImageServer/WCSServer?', version='1.0.0')

            # Fetch the data
            response = wcs.getCoverage(identifier='1', 
                bbox=bbox_parcel_3857_tuple, 
                format='GeoTIFF', 
                crs='EPSG:3857', 
                width=256, 
                height=256)

            # Save to a file
            output_path_aspect_coverage = os.path.join("output/tiff", "output_aspect_coverage.tif")
            with open(output_path_aspect_coverage, 'wb') as file:
                file.write(response.read())

            ## Clip the raster to the extent of parcel
            # Transform GeoDataFrame geometries into a format that rasterio wants
            geoms = gdf_parcel_3857.geometry.values  # returns a numpy array of Shapely geometries
            geometry = [mapping(geom) for geom in geoms]  # Loop over geometries if your DataFrame has more than one geometry

            # Open the raster file you want to clip
            with rasterio.open(output_path_aspect_coverage) as src:
                out_image, out_transform = mask(src, geometry, crop=True)
                out_meta = src.meta

            # Update the metadata to have the new transform
            out_meta.update({"driver": "GTiff",
                            "height": out_image.shape[1],
                            "width": out_image.shape[2],
                            "transform": out_transform})

            # Write the clipped raster to a new file
            output_path_aspect_coverage_clipped = os.path.join("output/tiff", "output_aspect_coverage_clipped.tif")
            with rasterio.open(output_path_aspect_coverage_clipped, "w", **out_meta) as dest:
                dest.write(out_image)

            ## Calculate the percentage of each orientation within the parcel extent
            # Open the file with rasterio
            with rasterio.open(output_path_aspect_coverage_clipped) as dataset:
                # Read the first (and only) band into a 2D array
                band1 = dataset.read(1)

            # Exclude 'no data' values
            band_remove_nodata = band1[band1 != dataset.nodata]
            # Classify the values based on the aspect orientation
            #classification = np.digitize(band1, bins=[-1, 22.5, 67.5, 112.5, 157.5, 202.5, 247.5, 292.5, 337.5, 360])
            # Count the number of pixels of each class
            #counts = np.bincount(classification.ravel())
            counts, _ = np.histogram(band_remove_nodata, bins=[-1, 22.5, 67.5, 112.5, 157.5, 202.5, 247.5, 292.5, 337.5, 360, np.inf])

            # Compute the percentages
            percentages = counts / counts.sum() * 100

            # Add the percentages of 'north' categories together
            #percentages[1] = percentages[1] + percentages[9]

            # Create a list with the results and round it to two decimals
            orientation_list = [round(value, 2) for value in percentages]

            # Calculate two separate north calculations
            orientation_list[1] = orientation_list[1] + orientation_list[9]
            
            # Remove the second north to avoid residuals in data
            orientation_list.pop(9)
            
            data = pd.DataFrame({
                'Flat' : [orientation_list[0]],
                'N' : [orientation_list[1]],
                'NE' : [orientation_list[2]],
                'E' : [orientation_list[3]],
                'SE' : [orientation_list[4]],
                'S' : [orientation_list[5]],
                'SW' : [orientation_list[6]],
                'W' : [orientation_list[7]],
                'NW' : [orientation_list[8]],

            })
            
            # Transpose the DataFrame and sort by the only row (0)
            sorted_data = data.T.sort_values(by=0)

            # Extract most and least dominant orientations
            most_dominant = sorted_data.tail(2)
            least_dominant = sorted_data.head(2)

            # Format the data for insertion into the paragraph
            most_dominant_orientations = most_dominant.index.to_list()
            most_dominant_percentages = most_dominant[0].to_list()

            least_dominant_orientations = least_dominant.index.to_list()
            least_dominant_percentages = least_dominant[0].to_list()



            #Adding elements to the file - aspect
            title = "PARCEL (KG: {}, GNR: {}): ASPECT".format(kg_input, gnr_input)
            intro = """This aspect can play an essential role in determining the microclimate, soil properties, and vegetation types within the parcel, as it influences sun exposure and moisture levels. 
                        An in-depth understanding of the aspect within a parcel can guide decisions related to land use and management, construction planning, or environmental studies."""
            text = """
            In terms of the parcel's terrain orientation, the most dominant aspects are <b>{0}</b> and <b>{1}</b>, 
            which cover approximately <b>{2}%</b> and <b>{3}%</b> of the total parcel area respectively. 
            On the other hand, the least represented orientations in the parcel are <b>{4}</b> and <b>{5}</b>, 
            which account for approximately <b>{6}%</b> and <b>{7}%</b> of the area respectively.
            """.format(most_dominant_orientations[0], most_dominant_orientations[1], most_dominant_percentages[0], most_dominant_percentages[1], least_dominant_orientations[0], least_dominant_orientations[1], least_dominant_percentages[0], least_dominant_percentages[1])
            map_figure_text = "<b>Map {}.</b>. Aspect Orientation of the Parcel <b>{}</b>, <b>{}</b> ".format(count_page, kg_input, gnr_input)
            table_figure_text = "<b>Table {}.</b> Distribution of Aspect Orientations within the Parcel in Percentages".format(count_page)

            # Create the content flowables
            title_text = Paragraph(title, title_style)
            intro_text = Paragraph(intro, text_style)
            map_text = Paragraph(map_figure_text, map_text_style)
            table_text = Paragraph(table_figure_text, table_text_style)
            text_text = Paragraph(text, text_style)


            # Create the content flowables
            image = Image(output_path_aspect, width=380, height=380)
            table_data = [list(data.columns)] + [list(row) for row in data.values]
            table = Table(table_data, style=table_style) #colWidths=colWidths

            pdf_elements_list.extend([
                title_text,
                Spacer(1, 0),
                intro_text,
                Spacer(1, 0),
                image,
                Spacer(1, 10),
                map_text,
                Spacer(1, 10),
                table_text,
                table,
                Spacer(1, 10),
                text_text,
                PageBreak()
            ])


        if layer == "slope":
            count_page += 1
            
            img_slope = wms_slope.getmap(layers=['0'],
                        srs='EPSG:3857',
                        bbox=bbox_parcel_3857,
                        size=(512, 512),
                        format='image/png', #image/png
                        transparent=True)

            # You can save the response to a file
            output_path_slope = os.path.join("output/wms_img", "output_slope.png")
            with open(output_path_slope, 'wb') as out:
                out.write(img_slope.read())
            
            # Read the image file
            im = PIL.Image.open(output_path_slope)

            # Create a figure and axes
            fig, ax = plt.subplots(figsize=(8.27, 9.69/2))

            # Get the extent of your geopandas dataframe
            minx, miny, maxx, maxy = gdf_parcel_3857.total_bounds

            # Display the image, stretched to the extent of your geopandas dataframe
            ax.imshow(im, extent=[minx, maxx, miny, maxy], alpha=0.5)

            # Plot the boundaries of the geodataframe - gdf_parcel
            gdf_parcel_3857.boundary.plot(ax=ax, edgecolor='#FFA500', linewidth=3)

            # Add the small box with text as a map scale representation
            ax.text(0.01, 0.01, 'Scale: {}'.format(map_scale_parcel), transform=ax.transAxes, 
                    fontsize=10, verticalalignment='bottom', 
                    bbox=dict(facecolor='#D3D3D3', edgecolor='black', boxstyle='square,pad=0.2'))
            
            ax.axis('off')
            
            # Save the map to an image file
            output_path_slope = os.path.join("output/maps", "map_slope.png")
            plt.savefig(output_path_slope, bbox_inches='tight', dpi=300)
            plt.close(fig)

            # Add the legend to the image, lower right corner
            main_img = mpimg.imread(output_path_slope)
            fig, ax = plt.subplots()
            ax.imshow(main_img)
            
            # Fetch the legend from WMS with this function
            legend = get_WMS_legend(wms_slope, "slope")

            legend_img = mpimg.imread(legend)
            
            # Create inset axes for the legend
            axins = inset_axes(ax, width="20%", height="20%", loc='lower right') 

            # Display legend in the inset axes
            axins.imshow(legend_img)

            # Hide axes for a cleaner look
            ax.axis('off')
            axins.axis('off')

            # Save the map to an image file
            output_path_slope = os.path.join("output/maps", "map_slope_with_legend.png")
            plt.savefig(output_path_slope, bbox_inches='tight', dpi=300)
            plt.close()

            # Create an image frame 
            img = PIL.Image.open(output_path_slope)
            bordered_img = PIL.ImageOps.expand(img, border=1, fill='black')
        
            # Save the new image
            bordered_img.save(output_path_slope)

            ## Fetch the values (percentages of ) aspect/orientation within the parcel extent
            # Set up the WCS connection - trying out new one
            wcs = WebCoverageService('https://zgis188.geo.sbg.ac.at/arcgis/services/23S856162/slope_3857_nmew/ImageServer/WCSServer?', version='1.0.0')

            #change the 3857 because it is a distorted image.
            #wcs = WebCoverageService('https://zgis188.geo.sbg.ac.at/arcgis/services/23S856162/slope_ua_3857/ImageServer/WCSServer?', version='1.0.0')

            # Fetch the data
            response = wcs.getCoverage(identifier='1', # '1'
                bbox=bbox_parcel_3857_tuple, 
                format='GeoTIFF', 
                crs='EPSG:3857', 
                width=256, 
                height=256)

            # Save to a file
            output_path_slope_coverage = os.path.join("output/tiff", "output_slope_coverage.tif")
            with open(output_path_slope_coverage, 'wb') as file:
                file.write(response.read())

            ## Clip the raster to the extent of parcel
            # Transform GeoDataFrame geometries into a format that rasterio wants
            geoms = gdf_parcel_3857.geometry.values  # returns a numpy array of Shapely geometries
            geometry = [mapping(geom) for geom in geoms]  # Loop over geometries if your DataFrame has more than one geometry

            # Open the raster file you want to clip
            with rasterio.open(output_path_slope_coverage) as src:
                out_image, out_transform = mask(src, geometry, crop=True)
                out_meta = src.meta

            # Update the metadata to have the new transform
            out_meta.update({"driver": "GTiff",
                            "height": out_image.shape[1],
                            "width": out_image.shape[2],
                            "transform": out_transform})

            # Write the clipped raster to a new file
            output_path_slope_coverage_clipped = os.path.join("output/tiff", "output_slope_coverage_clipped.tif")
            with rasterio.open(output_path_slope_coverage_clipped, "w", **out_meta) as dest:
                dest.write(out_image)

            ## Calculate the percentage of each orientation within the parcel extent
            # Open the file with rasterio
            with rasterio.open(output_path_slope_coverage_clipped) as dataset:
                # Read the first (and only) band into a 2D array
                band1 = dataset.read(1)
            
            # Exclude 'no data' values
            band_remove_nodata = band1[band1 != dataset.nodata]

            # Classify the values based on the aspect orientation
            #classification = np.digitize(band1, bins=[-1, 22.5, 67.5, 112.5, 157.5, 202.5, 247.5, 292.5, 337.5, 360])
            # Count the number of pixels of each class
            #counts = np.bincount(classification.ravel())
            counts, _ = np.histogram(band_remove_nodata, bins=[0, 5, 10, 15, 25, 35, np.inf])

            # Compute the percentages
            percentages = counts / counts.sum() * 100

            # Create a list with the results and round it to two decimals
            slope_list = [round(value, 2) for value in percentages]
            
            
            data = pd.DataFrame({
                'Very gentle' : [slope_list[0]], # 0 -5
                'Gentle' : [slope_list[1]], # 5 - 10
                'Moderate' : [slope_list[2]], # 10 - 15
                'Moderately steep' : [slope_list[3]], # 15 - 25
                'Steep' : [slope_list[4]], # 25 - 35
                'Very steep' : [slope_list[5]] # 35+
            })

            # Sort the DataFrame by values
            data_sorted = data.sort_values(by=0, axis=1, ascending=False)

            # Extract the two most and two least dominant slopes along with their values
            most_dominant_slopes = data_sorted.iloc[0, :2].to_dict()
            least_dominant_slopes = data_sorted.iloc[0, -2:].to_dict()

            #Adding elements to the file - slope
            title = "PARCEL (KG: {}, GNR: {}): SLOPE".format(kg_input, gnr_input)
            intro = """Slope provides significant insights into the steepness of the terrain in the parcel under concern. This information is crucial when it comes to drainage patterns and for soil erosion.
                        Understanding the slope aspects of the parcel can benefit to informed land management and planning, ensuring stability, safety and sustainable use of the parcel's terrain. The following
                        information illustrates the distribution of different slope categories within the parcel."""
            text = """The parcel displays a diversity of slopes, influencing various environmental factors and potential uses of the land. The most dominant slope category in this parcel is '<b>{}</b>' at <b>{}%</b>, followed by 
                        '<b>{}</b>' at <b>{}%</b>, accounting for the majority of the area.""".format(list(most_dominant_slopes.keys())[0], list(most_dominant_slopes.values())[0], list(most_dominant_slopes.keys())[1], list(most_dominant_slopes.values())[1])
            map_figure_text = "<b>Map {}.</b>. Slope Distribution Map of the Parcel <b>{}</b>, <b>{}</b> ".format(count_page, kg_input, gnr_input)
            table_figure_text = "<b>Table {}.</b> Slope Categories and their Distribution within the Parcel in Percentages".format(count_page)

            # Create the content flowables
            title_text = Paragraph(title, title_style)
            intro_text = Paragraph(intro, text_style)
            map_text = Paragraph(map_figure_text, map_text_style)
            table_text = Paragraph(table_figure_text, table_text_style)
            text_text = Paragraph(text, text_style)

            # Create the content flowables
            image = Image(output_path_slope, width=380, height=380)
            table_data = [list(data.columns)] + [list(row) for row in data.values]
            table = Table(table_data, style=table_style) #colWidths=colWidths

            pdf_elements_list.extend([
                title_text,
                Spacer(1, 0),
                intro_text,
                Spacer(1, 0),
                image,
                Spacer(1, 10),
                map_text,
                Spacer(1, 10),
                table_text,
                table,
                Spacer(1, 10),
                text_text,
                PageBreak()
            ])





    # Add the story to the PDF document
    pdf.build(pdf_elements_list, canvasmaker=HeaderInsertImage) #onFirstPage=footer, onLaterPages=footer - adds only page number
    print("Successfully generated the PDF document!")

def main():
    attributevalue1 = sys.argv[1]
    attributevalue2 = sys.argv[2]
    output_pdf_path = sys.argv[3]
    create_pdf(attributevalue1, attributevalue2, output_pdf_path)

if __name__ == '__main__':
    main()