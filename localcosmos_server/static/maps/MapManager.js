const MAPMANAGER_MODES = {
    POINT: 'point',
    AREA: 'area',
}


class MapManager {

    constructor(widgetId, initialLatitude, initialLongitude, readonly, value) {

        this.mode = MAPMANAGER_MODES.POINT;
        this.readonly = readonly;

        value = value || null;

        this.mapDivId = `${widgetId}_map`;

        this.watchId = null;
        this.position = null; // the position of the map marker if it was set by a human, not the position of the inputs or the gps sensor

        // the buttons
        this.positionJsonInput = document.getElementById(`${widgetId}_1`);
        this.verbosePosition = document.getElementById(`${widgetId}_0`);
        this.gpsButton = document.getElementById(`${widgetId}_gpsbutton`);
        this.deleteButton = document.getElementById(`${widgetId}_delete`);

        // area or point widget buttons
        this.pointInputButton = document.getElementById(`${widgetId}_PointInput`);
        this.areaInputButton = document.getElementById(`${widgetId}_AreaInput`);

        this.gpsIndicator = null;

        if (this.gpsButton != null) {
            this.gpsIndicator = this.gpsButton.firstElementChild;
        }

        this.map = this.createMap(initialLatitude, initialLongitude);

        if (value == null) {
            this.marker = null;
        }
        else {
            this.placeMarker(initialLatitude, initialLongitude);
        }

        if (this.readonly == false) {

            this.map.on('click', this.setMarker.bind(this));

            this.attachButtonListeners();

            // start watching position if possible
            if (navigator.geolocation) {
                // conditionally start position fetching
                if (typeof (this.positionJsonInput.value) == "undefined" || this.positionJsonInput.value == null || this.positionJsonInput.value == "") {
                    this.watchPosition();
                }
            }
        }

    }

    attachButtonListeners() {
        this.deleteButton.addEventListener('click', this.deleteMarker.bind(this));

        this.gpsButton.addEventListener('click', this.watchPosition.bind(this));

        if (this.pointInputButton != null) {
            this.pointInputButton.addEventListener('click', this.enablePointInput.bind(this));
        }

        if (this.areaInputButton != null) {
            this.areaInputButton.addEventListener('click', this.enableAreaInput.bind(this));
        }
    }

    createMap(initialLatitude, initialLongitude) {
        const layerSources = {
            "osm": L.tileLayer('https://{s}.tile.openstreetmap.de/{z}/{x}/{y}.png',
                {
                    attribution: 'Map data &copy; OpenStreetMap contributors',
                    subdomains: 'ab',
                    maxZoom: 20,
                    maxNativeZoom: 18
                }),

            "satellite_tiles": L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
                {
                    attribution: 'Tiles &copy; Esri',
                    maxZoom: 20,
                    maxNativeZoom: 18
                })
        };

        const center = [initialLatitude, initialLongitude];
        const zoom = 15;

        const map = L.map(this.mapDivId, {
            center: center,
            zoom: zoom,
            maxZoom: 24,
            scrollWheelZoom: false
        });

        // add tile layers
        const satellite = L.layerGroup([layerSources.satellite_tiles]);

        satellite.addTo(map);

        const baseLayers = {
            "Satellite": satellite,
            "Streets": layerSources["osm"]
        };

        L.control.layers(baseLayers, {}, { "position": "topright" }).addTo(map);

        return map;
    }

    setMapCenter(latitude, longitude) {
        const latLng = L.latLng(latitude, longitude);
        this.map.setView(latLng);
    }


    enablePointInput() {
        this.mode = MAPMANAGER_MODES.POINT;
        this.deleteArea();
        this.disableDraw();
    }

    placeMarker(lat, lng) {
        if (this.marker != null) {
            this.marker.remove();
        }
        const marker = L.marker([lat, lng]).addTo(this.map);
        this.marker = marker;
    }

    setMarker(event) {

        if (this.mode == MAPMANAGER_MODES.POINT) {

            this.placeMarker(event.latlng.lat, event.latlng.lng);

            const position = this.latLngToPosition(event.latlng.lat, event.latlng.lng);
            this.position = position;
            this.setPositionFieldValues(position);
            this.clearWatch();
        }

    }

    latLngToPosition(latitude, longitude) {
        const position = {
            coords: {
                latitude: latitude,
                longitude: longitude,
                accuracy: 0
            }
        };

        return position;

    }

    setPositionFieldValues(position) {
        const geojson = {
            "type": "Feature",
            "geometry": {
                "crs": {
                    "type": "name",
                    "properties": {
                        "name": "EPSG:4326"
                    }
                },
                "type": "Point",
                "coordinates": [position.coords.longitude, position.coords.latitude]
            },
            "properties": {
                "accuracy": 0
            }
        };
        this.positionJsonInput.value = JSON.stringify(geojson);
        const verbose = "" + position.coords.latitude.toFixed(4) + "N " + position.coords.longitude.toFixed(4) + "E";
        this.verbosePosition.value = verbose;
    }

    deleteMarker() {
        this.positionJsonInput.value = null;
        this.verbosePosition.value = null;
        if (this.marker != null) {
            this.marker.remove();
        }
    }

    // GPS
    cleanPosition(position) {
        try {
            if (typeof (position.coords.latitude) == "number" && typeof (position.coords.longitude) == "number" && typeof (position.coords.accuracy == "number")) {
                var position_cleaned = {
                    coords: {
                        latitude: position.coords.latitude,
                        longitude: position.coords.longitude,
                        accuracy: position.coords.accuracy
                    }
                };
                return position_cleaned;
            }
            else {
                return null;
            }
        }
        catch (e) {
            return null;
        }
    }

    onGPSSuccess(position) {

        if (this.mode == MAPMANAGER_MODES.POINT) {
            var validPosition = this.cleanPosition(position);

            if (validPosition != null) {
                this.placeMarker(position.coords.latitude, position.coords.longitude);
                this.setMapCenter(position.coords.latitude, position.coords.longitude);

                if (position.coords.accuracy < 100) {
                    this.clearWatch();
                }
                this.setPositionFieldValues(validPosition);
            }
        }
    }

    onError(e) {
        console.log(e);
    }

    watchPosition() {

        var self = this;

        if (this.watchId == null) {
            this.watchId = navigator.geolocation.watchPosition(function (position) {
                self.onSuccess(position);
            },
                function (e) {
                    self.onError(e);
                }, { enableHighAccuracy: true, timeout: 60000, maximumAge: 0 });

            this.gpsIndicator.classList.remove("glyphicon-refresh");
            this.gpsIndicator.classList.add("blink");
            this.gpsIndicator.classList.add("glyphicon-hourglass");
        }
    }

    clearWatch() {
        navigator.geolocation.clearWatch(this.watchId);
        this.watchId = null;
        this.gpsIndicator.classList.remove("blink");
        this.gpsIndicator.classList.remove("glyphicon-hourglass");
        this.gpsIndicator.classList.add("glyphicon-refresh");
    }

    // Area Management
    enableAreaInput() {
        this.mode = MAPMANAGER_MODES.AREA;
        this.deleteMarker();
        this.enableDraw();
    }


    deleteArea() {
        this.map.removeLayer(this.drawnItems);
    }

    enableDraw() {

        const self = this;

        this.drawnItems = new L.FeatureGroup();
        this.map.addLayer(this.drawnItems);

        // Set the title to show on the polygon button
        L.drawLocal.draw.toolbar.buttons.polygon = 'Draw a sexy polygon!';
        const polygonDrawer = new L.Draw.Polygon(this.map, {shapeOptions: {color: '#f00'}});

        this.drawControl = new L.Control.Draw({
            position: 'topright',
            draw: {
                polyline: false,
                marker: false,
                circle: false,
                circlemarker: false,
                rectangle: false,
                polygon: {
                    allowIntersection: false,
                    showArea: true,
                    shapeOptions : {color: '#ff0000' }
                }

            },
            edit: {
                featureGroup: this.drawnItems,
                remove: true
            }
        });
        this.map.addControl(this.drawControl);

        this.map.on(L.Draw.Event.CREATED, function (e) {
            var layer = e.layer;
    
            self.drawnItems.addLayer(layer);
        });

    }

    disableDraw() {
        this.map.removeControl(this.drawControl);
    }

}