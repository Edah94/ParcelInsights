

function init (){
    var attribution = new ol.control.Attribution({
        collapsible: false
        });
    
        
    // Define the extent of the parcel for map initial extent load

    var parcel_extent = [13.12121945, 47.96986414, 13.2127009 , 48.03987031]
    
    //map view
    const view = new ol.View({
        center: ol.proj.fromLonLat([13.17147776284516, 48.00516770034534]),
        maxZoom: 18,
        zoom: 13
    })

    // Load the map
    var map = new ol.Map({
    controls: ol.control.defaults({attribution: false}).extend([attribution]),
    layers: [
        new ol.layer.Tile({
        source: new ol.source.OSM({
            url: 'https://tile.openstreetmap.be/osmbe/{z}/{x}/{y}.png',
            attributions: [ ol.source.OSM.ATTRIBUTION, 'Tiles courtesy of <a href="https://geo6.be/">GEO-6</a>' ],
            maxZoom: 18
            })
        })
    ],
        target: 'map',
        view: view
        });

    // Coordinate event clicker
    map.on('click', function(event) {
        var coordinate = ol.proj.toLonLat(event.coordinate);
        //console.log(coordinate);
    });

    //Base layers
    //1st raster tile layer - OSM Standard
    var OSMStandard = new ol.layer.Tile({
        source: new ol.source.OSM({
            url: 'https://{a-c}.tile.openstreetmap.fr/hot/{z}/{x}/{y}.png'
        }),
        visible: false,
        title: 'OSMStandard'
    })
    //2nd raster tile layer - EsriWorldImagery
    var EsriWorldImagery = new ol.layer.Tile({
        source: new ol.source.XYZ({
            attributions: 'Tiles © <a href="https://services.arcgisonline.com/ArcGIS/' +
                'rest/services/World_Imagery/MapServer">ArcGIS</a>',
            url: 'https://server.arcgisonline.com/ArcGIS/rest/services/' +
                'World_Imagery/MapServer/tile/{z}/{y}/{x}'
        }),
        visible: true,
        title: 'EsriWorldImagery'
    });
    
    //raster group for displaying different layers on radio button request
    var baseLayerGroup = new ol.layer.Group({
        layers: [EsriWorldImagery, OSMStandard]
    })
    map.addLayer(baseLayerGroup);

    //Layer switcher 
    const baseLayerElements = document.querySelectorAll('.sidebar2 > input[type=radio]')
    for(let baseLayerElement of baseLayerElements){
        baseLayerElement.addEventListener('change', function(){
            let baseLayerValue = this.value;
            baseLayerGroup.getLayers().forEach(function(element, index, array){
                let baselayerName = element.get('title');
                element.setVisible(baselayerName === baseLayerValue)
            })
        })
    }

    
    // Load the parcel as GeoJSON
    var vectorSource = new ol.source.Vector({
        url: '/gdf_parcel_geojson',
        format: new ol.format.GeoJSON()
    });
    
    // Create a vector layer to contain the GeoJSON
    var vectorLayer = new ol.layer.Vector({
        source: vectorSource,
        style: function(feature) {
            return new ol.style.Style({
                //fill: new ol.style.Fill({
                //    color: 'rgba(255, 255, 255, 0.6)'
                //}),
                fill: new ol.style.Fill({
                    color: 'rgba(0, 0, 0, 0)'  // Fully transparent fill
                }),
                stroke: new ol.style.Stroke({
                    color: '#319FD3',
                    width: 1
                }),
                text: new ol.style.Text({
                    font: '12px Calibri,sans-serif',
                    fill: new ol.style.Fill({
                        color: '#000'
                    }),
                    stroke: new ol.style.Stroke({
                        color: '#fff',
                        width: 3
                    }),
                    // this will be the text shown as label
                    text: feature.get('GNR') // replace 'name' with the attribute name you want to display
                })
            });
        }
    });
    
    // Add your vector layer to the map
    map.addLayer(vectorLayer);
    

    // Get references to the input fields and generate PDF button
    const kgInput = document.getElementById('kgInput');
    const gnrInput = document.getElementById('gnrInput');
    const generatePdfButton = document.getElementById('generatePdfButton');

    // Event listener for input fields
    kgInput.addEventListener('input', enableGenerateButton);
    gnrInput.addEventListener('input', enableGenerateButton);

    // Function to enable the generate PDF button
    function enableGenerateButton() {
        const kgValue = kgInput.value;
        const gnrValue = gnrInput.value;

        generatePdfButton.disabled = !((kgValue && gnrValue) || (attributevalue1 && attributevalue2));
    }

    // Declare attribute value variables
    let attributevalue1 = '';
    let attributevalue2 = '';

    // Event listener for the generate PDF button
    generatePdfButton.addEventListener('click', function() {
        
        
        // Check if the attribute values are already set (clicked on map)
        if (attributevalue1 && attributevalue2) {
            generatePdf();
        } else {
            // Check if both input fields have values
            if (kgInput.value && gnrInput.value) {
                attributevalue1 = gnrInput.value;
                attributevalue2 = kgInput.value;
                
                generatePdf();
            }
        }

        document.getElementById('attributeValues').textContent = '';
        document.getElementById('attributeValues').innerHTML = `<strong>STATUS:</strong> Your parcel KG: <strong>${attributevalue2}</strong>, GNR: <strong>${attributevalue1}</strong> is being processed...`;
        
    });

    // Function to generate the PDF
    function generatePdf() {
        // Use the fetch API to make a POST request
        fetch('/create_pdf', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: 'attributevalue1=' + attributevalue1 + '&attributevalue2=' + attributevalue2
        })
        .then(response => response.blob())
        .then(blob => {
            var url = window.URL.createObjectURL(blob);
            var a = document.createElement('a');
            a.href = url;
            a.download = 'output.pdf';
            document.body.appendChild(a); // Required for this to work in FireFox
            a.click();

            // Hide the loading text and change to "Done!" text
            const attributeValuesElement = document.getElementById('attributeValues');
            attributeValuesElement.textContent = '';
            attributeValuesElement.innerHTML = `<strong>STATUS:</strong> Successfully processed and generated the KG: <strong>${attributevalue2}</strong>, GNR: <strong>${attributevalue1}</strong> parcel-based PDF report!`;
        })
        .catch(error => console.error('Error:', error));
    }

    // Function to display the attribute values with bold formatting
    function displayAttributeValues() {
        const attributeValuesElement = document.getElementById('attributeValues');
        attributeValuesElement.innerHTML = `<strong>STATUS: </strong>Your current selection is on on KG: <strong>${attributevalue2}</strong> and GNR: <strong>${attributevalue1}</strong>. Are you sure you want this parcel to be processed?`;
    }

    // Map click event listener
    map.on('click', function(e) {
        map.forEachFeatureAtPixel(e.pixel, function(feature, layer) {
            // assuming these are the attributes you're interested in
            attributevalue1 = feature.get('GNR');
            attributevalue2 = feature.get('KG');
            
            // Enable the generate PDF button
            generatePdfButton.disabled = false;

            // Display the attribute values
            displayAttributeValues();
        });
    });









}// init() function
