"use strict";

function getCenter(shape) {
    return {
        x: shape.x +
            (shape.width / 2) * Math.cos(shape.rotation) +
            (shape.height / 2) * Math.sin(-shape.rotation),
        y: shape.y +
            (shape.height / 2) * Math.cos(shape.rotation) +
            (shape.width / 2) * Math.sin(shape.rotation),
    };
}
function rotateAroundPoint(shape, angleRad, point) {
    const x = point.x +
        (shape.x - point.x) * Math.cos(angleRad) -
        (shape.y - point.y) * Math.sin(angleRad);
    const y = point.y +
        (shape.x - point.x) * Math.sin(angleRad) +
        (shape.y - point.y) * Math.cos(angleRad);
    return Object.assign(Object.assign({}, shape), { rotation: shape.rotation + angleRad, x,
        y });
}
function rotateAroundCenter(shape, deltaRad) {
    const center = getCenter(shape);
    return rotateAroundPoint(shape, deltaRad, center);
}
function getSnap(snaps, newRotationRad, tol) {
    let snapped = newRotationRad;
    for (let i = 0; i < snaps.length; i++) {
        const angle = Konva.getAngle(snaps[i]);
        const absDiff = Math.abs(angle - newRotationRad) % (Math.PI * 2);
        const dif = Math.min(absDiff, Math.PI * 2 - absDiff);
        if (dif < tol) {
            snapped = angle;
        }
    }
    return snapped;
}

class InteractiveImageField {

    constructor(container, imageInput, cropParametersInput, featuresInput, options){

        options = options || {};

        this.DEBUG = false;

        // the element where the image is displayed and where the transformations take place
        this.container = container;
        this.container.classList.add("interactiveImageField-container");

        this.imageInput =  imageInput;
        this.cropParametersInput = cropParametersInput;
        this.featuresInput = featuresInput;

        this.options = {
            "cropAreaRatio" : "1:1",
            "allowFeatures" : true,
            "greyAreaFillColor" : "rgba(0,0,0,0.5)",
            "relativeArrowStrokeWidth" : 0.02,
            "relativeArrowLength" : 0.5,
            "defaultArrowColor" : "#000000",
            "cropMode" : "contains", // contained: crop area contained inside image, contains: crop area contains image (can be larger than image)
            "stageBackground" : "#FFFFFF" // only used if cropMode == "contains"
        };

        for (let key in options){
            this.options[key] = options[key];
        }

        this.stage = null;
        this.konvaImage = null;
        this.cropArea = null;
        this.cropAreaGrey = null;
        this.image = null;

        this.cropLayer = null;
        this.cropAreaTransformLayer = null;
		this.arrowLayer = null;
		this.arrowsTransformLayer = null;
		this.activeArrow = null;

        // transformers
        this.cropTransformer = null;

        this.arrowTransformerMap = {};

        this.createHTML();

        this.toolbar = new InteractiveImageFieldToolbar(this);

        this.bindImageField();

    }

    readImageFieldImage (onsuccess, onfail) {
        var reader = new FileReader();
		reader.onloadend = function(e) {

			onsuccess(this.result);
		};

        reader.onerror = onfail;

		let file = this.imageInput.files[0];
		reader.readAsDataURL(file);
		
    }

    bindImageField(){
        var self = this;

        this.imageInput.addEventListener("change", function(event){

            self.readImageFieldImage(function(imageSrc){

                self.setImage(imageSrc);

            }, function(){
                // failed
                alert("[InteractiveImageField.js] error reading image");
            });
		});
    }

    createHTML (){
        this.imageContainer = document.createElement("div");
        this.imageContainer.id = "InterActiveImageField-image";
        this.container.prepend(this.imageContainer);
    }

    /*
    * The origin (0/0) of the coordinate system which the crop paramters refer to is the top left corner of the image
    * this way, the stage can be altered without compromising the validity of the crop parameters
    */
    setCropParametersInputValue (){
        if (this.cropArea != null){

            let reverseScalingFactor = 1 / this.getScalingFactor();

            let cropAreaRect = this.cropArea.getClientRect();

            let imageRect = this.konvaImage.getClientRect();

            var data = {
                "x" : Math.round( (cropAreaRect.x - imageRect.x) * reverseScalingFactor),
                "y" : Math.round( (cropAreaRect.y - imageRect.y) * reverseScalingFactor),
                "width" : Math.round(cropAreaRect.width * reverseScalingFactor),
                "height" : Math.round(cropAreaRect.height * reverseScalingFactor),
                "rotate" : 0,
                "scaleX" : 1,
                "scaleY" : 1
            };

            this.cropParametersInput.value = JSON.stringify(data);
        }
    }

    setFeaturesInputValue () {

        let reverseScalingFactor = 1 / this.getScalingFactor();

        if (this.featuresInput != null){
            
            let arrows = [];

            if (this.arrowLayer != null && this.arrowLayer.hasChildren() == true){

                let children = this.arrowLayer.getChildren(function(node){
                    return node.getClassName() === 'Arrow';
                });

                for (let c=0; c<children.length; c++){
                    let arrow = children[c];

                    let color = arrow.fill();

                    let points = arrow.points();

                    let initialPoint = {
                        x : points[0],
                        y : points[1]
                    };

                    let terminalPoint = {
                        x : points[2],
                        y: points[3]
                    };

                    let transformedInitialPoint = arrow.getAbsoluteTransform().point(initialPoint);
                    let transformedTerminalPoint = arrow.getAbsoluteTransform().point(terminalPoint);

                    let arrowJson = {
                        "type" : "arrow",
                        "initialPoint" : { 
                            "x" : parseInt(transformedInitialPoint.x * reverseScalingFactor),
                            "y" : parseInt(transformedInitialPoint.y * reverseScalingFactor)
                        },
                        "terminalPoint" : {
                            "x" : parseInt(transformedTerminalPoint.x * reverseScalingFactor),
                            "y" : parseInt(transformedTerminalPoint.y * reverseScalingFactor)
                        },
                        "color": color
                    };

                    arrows.push(arrowJson);
                }

            }

            if (arrows.length){
                let arrowsJson_str = JSON.stringify(arrows);
                this.featuresInput.value = arrowsJson_str;
            }
            else {
                this.featuresInput.value = "";
            }
            
        }
    }

    setImage (imageSrc) {

        let self = this;
        
        this.image = new Image();

		this.image.onload = function(event){

            console.log("[InteractiveimageField] loaded image wxh: " + self.image.width + "x" + self.image.height);
            self.onImageLoad(event);
        };

        this.image.src = imageSrc;

    }


    addStage () {

        let stageWidth = this.imageContainer.offsetWidth;
        let stageHeight = stageWidth;

        if (this.options.cropMode == "contained"){

            let originalHeight = this.image.height;

            let scalingFactor = this.getScalingFactor();

            if (this.DEBUG == true){
                console.log("[InteractiveImageField] loading stage. image height: " + this.image.height + " , image width : " + this.image.width + " scalingFactor: " + scalingFactor);
            }
            
            stageHeight = parseInt(originalHeight * scalingFactor);


            if (this.DEBUG == true){
                console.log("instantiating Konva.Stage width: " + stageWidth + " height: " + stageHeight);
            }
        }

        if (this.stage != null){
            this.stage.destroy();
        }
        
        this.stage = new Konva.Stage({
            container: this.imageContainer.id,   // id of container <div>
            width: stageWidth,
            height: stageHeight
        });
    }

    // if the image contains the crop area, the image has the same size like the stage
    // if the crop area contains the image (crop area can extend image), only one dimension (height or width) fits into the stage and equals the stage
    addKonvaImage () {

        // in "contained" mode, the image dimensions equal the stage dimensions
        let imageWidth = this.stage.width();
        let imageHeight = this.stage.height();
        let offsetX = 0;
        let offsetY = 0;

        // in "contains" mode, the stage is square and the image fits into the stage
        if (this.options.cropMode == "contains") {
            // crop area contains image

            let scalingFactor = this.getScalingFactor();

            imageWidth = this.image.width * scalingFactor;
            imageHeight = this.image.height * scalingFactor;

            offsetX = ( this.stage.width() / 2 ) - ( imageWidth / 2)
            offsetY = ( this.stage.height() / 2 ) - ( imageHeight / 2 ) 
        }

        this.konvaImage = new Konva.Image({
            x: offsetX,
            y: offsetY,
            image: this.image,
            width: imageWidth,
            height: imageHeight
        });

        let imageLayer = new Konva.Layer();

        let background = new Konva.Rect({
            x: 0,
            y: 0,
            width: this.stage.width(),
            height: this.stage.height(),
            fill : this.options.stageBackground
        });

        imageLayer.add(background);

        imageLayer.add(this.konvaImage);

        this.stage.add(imageLayer);

    }

    onCropAreaMove (){

        const boxes = this.cropTransformer.nodes().map((node) => node.getClientRect());
        const box = this.getTotalBox(boxes);
        this.cropTransformer.nodes().forEach((shape) => {
            const absPos = shape.getAbsolutePosition();
            // where are shapes inside bounding box of all shapes?
            const offsetX = box.x - absPos.x;
            const offsetY = box.y - absPos.y;

            // we total box goes outside of viewport, we need to move absolute position of shape
            const newAbsPos = { ...absPos };
            if (box.x < 0) {
                newAbsPos.x = -offsetX;
            }
            if (box.y < 0) {
                newAbsPos.y = -offsetY;
            }
            if (box.x + box.width > this.stage.width()) {
                newAbsPos.x = this.stage.width() - box.width - offsetX;
            }
            if (box.y + box.height > this.stage.height()) {
                newAbsPos.y = this.stage.height() - box.height - offsetY;
            }
            shape.setAbsolutePosition(newAbsPos);
        });

        this.updateCropArea();
        this.setCropParametersInputValue();
    }

    // crop area consists of a tranformer (rectangle), and 4 grey, translucent rectangles outside the crop area
    addCropArea (resetCropArea) {

        let self = this;

        let initialCropAreaWidth;
        let initialCropAreaHeight;
        let xOffset = 0;
        let yOffset = 0;

        let ratioParameters = this.options.cropAreaRatio.split(":");

        let ratioRelativeWidth = ratioParameters[0];
        let ratioRelativeHeight = ratioParameters[1];
        let ratioFactor = ratioRelativeWidth / ratioRelativeHeight;

        let xDiff = this.stage.width() - ratioRelativeWidth;
        let yDiff = this.stage.height() - ratioRelativeHeight;

        if (xDiff < yDiff){
            // width
            initialCropAreaWidth = this.stage.width();
            initialCropAreaHeight = initialCropAreaWidth * ( 1 / ratioFactor);
            yOffset = ( this.stage.height() / 2 ) - ( initialCropAreaHeight / 2 );
        }
        else {
            initialCropAreaHeight = this.stage.height();
            initialCropAreaWidth = initialCropAreaHeight * ratioFactor;
            xOffset = ( this.stage.width() / 2 ) - ( initialCropAreaWidth / 2 );
        }

        // add the crop area
        let cropParameters = {
            x: xOffset,
            y: yOffset,
            width: initialCropAreaWidth,
            height: initialCropAreaHeight
        };
        

        // the cropparams in the db and .value of the field are relative to the actual image size, not the responsive image size (which changes all the time)
        if (this.cropParametersInput.value.length && resetCropArea == false){

            let scalingFactor = this.getScalingFactor();

            let cropParametersInputValue = JSON.parse(this.cropParametersInput.value);

            let cropAreaWidth = cropParametersInputValue.width * scalingFactor;
            let cropAreaHeight = cropParametersInputValue.height * scalingFactor; 

            if (cropAreaWidth > initialCropAreaWidth || cropAreaHeight > initialCropAreaHeight){
                cropAreaWidth = initialCropAreaWidth;
                cropAreaHeight = initialCropAreaHeight;
            }

            cropParameters = {

                x : ( cropParametersInputValue.x * scalingFactor) + this.konvaImage.x(),
                y : ( cropParametersInputValue.y * scalingFactor) + this.konvaImage.y(),
                width : cropAreaWidth,
                height: cropAreaHeight

            };
        }

        this.cropArea = new Konva.Rect({
            x : cropParameters.x,
            y : cropParameters.y,
            width: cropParameters.width,
            height: cropParameters.height,
            fillEnabled: false,
            strokeEnabled: false
        });

        let cropLayer = new Konva.Layer();
        cropLayer.add(this.cropArea);

        // grey out area outside the selection
        this.cropAreaGrey = {
            top : new Konva.Rect({fill: this.options.greyAreaFillColor}),
            bottom: new Konva.Rect({fill: this.options.greyAreaFillColor}),
            left: new Konva.Rect({fill: this.options.greyAreaFillColor}),
            right: new Konva.Rect({fill: this.options.greyAreaFillColor})
        };

        // calculate the grey rectangles
        this.updateCropArea();

        let greyLayer = new Konva.Layer();
        greyLayer.add(this.cropAreaGrey.top);
        greyLayer.add(this.cropAreaGrey.bottom);
        greyLayer.add(this.cropAreaGrey.left);
        greyLayer.add(this.cropAreaGrey.right);


        // manual transform of crop layer
        this.cropAreaTransformLayer = new Konva.Layer();

        this.cropTransformer = new Konva.Transformer({
            flipEnabled : false,
            rotateEnabled: false,
            keepRatio : true,
            centeredScaling : false,
            enabledAnchors :['top-left','top-right', 'bottom-left', 'bottom-right'],
            shouldOverdrawWholeArea : true,
            boundBoxFunc: (oldBox, newBox) => {

                const box = this.getClientRect(newBox);
                const isOut =
                    box.x < 0 ||
                    box.y < 0 ||
                    Math.round(box.x + box.width) > this.stage.width() ||
                    Math.round(box.y + box.height) > this.stage.height();
                // if new bounding box is out of visible viewport, let's just skip transforming
                // this logic can be improved by still allow some transforming if we have small available space
                // apply Math.round() to prevent scaling the rect resulting box.x + box.width in something like 300.00000003 while stage.width() being 300
                if (isOut) {

                    if (this.DEBUG == true){
                        console.log(box.x + box.width + "   VS stage " + this.stage.width())
                        console.log("[InteractiveImageField] isOut, using old box");
                    }

                    return oldBox;
                }
                return newBox;
            }
        });

        this.cropTransformer.on('dragmove', function(){
            self.onCropAreaMove();
        });

        this.cropTransformer.on('transform', () => {
            this.updateCropArea();
            this.updateAllArrows();
        });

        this.cropTransformer.on('transformend', () => {
            this.updateCropArea();
            this.setCropParametersInputValue();
            this.setFeaturesInputValue();
        });

        this.cropTransformer.on('dragend', () => {
            this.setCropParametersInputValue();
        });

        this.cropTransformer.nodes([this.cropArea]);

        this.cropAreaTransformLayer.add(this.cropTransformer);

        this.stage.add(greyLayer);
        this.stage.add(cropLayer);
        this.stage.add(this.cropAreaTransformLayer);
    }

    updateCropArea () {

        let cropAreaRect = this.cropArea.getClientRect();

        let stageRect = {
            width: this.stage.width(),
            height: this.stage.height()
        };

        let greyRectangles = {
            top : {
                x: 0,
                y: 0,
                width: stageRect.width,
                height: cropAreaRect.y
            },
            bottom : {
                x: 0,
                y: cropAreaRect.y + cropAreaRect.height,
                width: stageRect.width,
                height: stageRect.height - cropAreaRect.y - cropAreaRect.height
            },
            left : {
                x: 0,
                y: cropAreaRect.y,
                width: cropAreaRect.x,
                height: cropAreaRect.height 
            },
            right : {
                x: cropAreaRect.x + cropAreaRect.width,
                y: cropAreaRect.y,
                width: stageRect.width - cropAreaRect.width - cropAreaRect.x,
                height: cropAreaRect.height
            }
        };

        let topAttrs = {
            x: greyRectangles.top.x,
            y: greyRectangles.top.y,
            width: greyRectangles.top.width,
            height: greyRectangles.top.height
        };

        this.cropAreaGrey.top.setAttrs(topAttrs);


        var bottomAttrs = {
            x: greyRectangles.bottom.x,
            y: greyRectangles.bottom.y,
            width: greyRectangles.bottom.width,
            height: greyRectangles.bottom.height
        };

        this.cropAreaGrey.bottom.setAttrs(bottomAttrs);


        let leftAttrs = {
            x: greyRectangles.left.x,
            y: greyRectangles.left.y,
            width: greyRectangles.left.width,
            height: greyRectangles.left.height
        };

        this.cropAreaGrey.left.setAttrs(leftAttrs);


        let rightAttrs = {
            x: greyRectangles.right.x,
            y: greyRectangles.right.y,
            width: greyRectangles.right.width,
            height: greyRectangles.right.height
        };

        this.cropAreaGrey.right.setAttrs(rightAttrs);
    }

    onImageLoad (){

        let resetCropArea = false;
        if (this.stage != null){
            resetCropArea = true; // on new image or image change
        }
        
        this.addStage();
        
        this.addKonvaImage();
        
        this.addCropArea(resetCropArea);

        this.setCropParametersInputValue();

        this.addArrows(resetCropArea);
        this.setFeaturesInputValue();

        // start in crop mode
        this.toolbar.show();
        this.toolbar.activateCropMode();
        
    }

    getArrowStrokeWidth () {

        let cropAreaRect = this.cropArea.getClientRect();
        let absoluteArrowStrokeWidth = cropAreaRect.width * this.options.relativeArrowStrokeWidth;

        return absoluteArrowStrokeWidth;
    }

    // the arrow length is the length of the vector
    getArrowLength () {
        
        let cropAreaRect = this.cropArea.getClientRect();
        let absoluteArrowLength = cropAreaRect.width * this.options.relativeArrowLength;

        return absoluteArrowLength;
    }

    getPointerWidth () {
        let pointerWidth = this.getArrowStrokeWidth() * 3;
        return pointerWidth;
    }

    getPointerLength () {
        let pointerLength = this.getArrowStrokeWidth() * 3;
        return pointerLength;
    }


    addArrows (resetCropArea) {
        
        // transform layer for arrows
        this.arrowsTransformLayer = new Konva.Layer();
        this.arrowsTransformLayer.visible(false);

        // arrows
        this.arrowLayer = new Konva.Layer();

        this.stage.add(this.arrowLayer);
        this.stage.add(this.arrowsTransformLayer);

        // read arrows
        if (resetCropArea == false && this.featuresInput != null){
            // load all arrows
            if (this.featuresInput.value.length){

                let scalingFactor = this.getScalingFactor();

                let features = JSON.parse(this.featuresInput.value);

                for (let f=0; f<features.length; f++){
                    let feature = features[f];
                    if (feature.hasOwnProperty("type") && feature.type == "arrow"){

                        let arrowDefinition = {
                            "type" : "arrow",
                            "initialPoint" : { 
                                "x" : feature.initialPoint.x * scalingFactor,
                                "y" : feature.initialPoint.y * scalingFactor
                            },
                            "terminalPoint" : {
                                "x" : feature.terminalPoint.x * scalingFactor,
                                "y" : feature.terminalPoint.y * scalingFactor
                            },
                            "color": feature.color
                        }
                        this.addArrow(arrowDefinition);
                    }
                }
            }
        }
        else {
            // delete all arrows
        }
    }

    // only covers Konva.Arrow.points, Konva.Arrow.x, Konva.Arrow.y
    arrowToKonvaArrow (arrowDefinition) {

        // x and y of the konva arrow have to be minX and minY of the arrow coordinates

        let minX = Math.min(arrowDefinition.initialPoint.x, arrowDefinition.terminalPoint.x);
        let maxX = Math.max(arrowDefinition.initialPoint.x, arrowDefinition.terminalPoint.x);
        let minY = Math.min(arrowDefinition.initialPoint.y, arrowDefinition.terminalPoint.y);
        let maxY = Math.max(arrowDefinition.initialPoint.y, arrowDefinition.terminalPoint.y);

        // Konva.Arrow requires points to be relative to the transform/bounding box of the arrow (not stage, not image)
        let relativeInitialPoint = {
            x : arrowDefinition.initialPoint.x - minX,
            y : arrowDefinition.initialPoint.y - minY
        };

        let relativeTerminalPoint = {
            x : arrowDefinition.terminalPoint.x - minX,
            y : arrowDefinition.terminalPoint.y - minY
        };

        let konvaArrowDefinition = {
            x : minX,
            y : minY,
            points : [relativeInitialPoint.x, relativeInitialPoint.y, relativeTerminalPoint.x, relativeTerminalPoint.y]
        }

        return konvaArrowDefinition;
    }

    addArrow (arrowDefinition) {

        var self = this;

        let strokeWidth = this.getArrowStrokeWidth();

        let konvaArrowDefinition = this.arrowToKonvaArrow(arrowDefinition);

        let arrow = new Konva.Arrow({
            id: new Date().getTime().toString(),
            x: konvaArrowDefinition.x,
            y: konvaArrowDefinition.y,
            points: konvaArrowDefinition.points,
            pointerLength: this.getPointerLength(),
            pointerWidth: this.getPointerWidth(),
            fill: arrowDefinition.color,
            stroke: arrowDefinition.color,
            strokeWidth: strokeWidth
        });

        this.arrowLayer.add(arrow);

        let arrowTransformer = new Konva.Transformer({
            flipEnabled : false,
            resizeEnabled: false,
            rotateEnabled: true,
            rotateAnchorOffset: 30,
            keepRatio : true,
            centeredScaling : false,
            enabledAnchors :['rotater-top','rotater-bottom', 'rotater-left', 'rotater-right'],
            shouldOverdrawWholeArea : true
        });


        arrowTransformer.on('transformend', () => {
            this.setFeaturesInputValue();
        });

        arrowTransformer.on('dragend', () => {
            this.setFeaturesInputValue();
        });

        arrowTransformer.nodes([arrow]);

        this.arrowsTransformLayer.add(arrowTransformer);

        this.activeArrow = arrow;

        this.arrowTransformerMap[arrow.id()] = arrowTransformer;

        this.activateArrow(arrow);
        arrow.on("click", function(event){
            if (self.DEBUG == true){
                console.log("[InteractiveImageField] activating arrow " + event.currentTarget.id());
            }
            self.activateArrow(event.currentTarget);
        });

        this.setFeaturesInputValue();
    }

    addSecondRotationAnchor (transformer) {

        var name = 'second_rotater';

        transformer._handleAlternativeRotation = function(e){

            var x, y, newHypotenuse;
          var anchorNode = this.findOne('.' + 'rotater'); //this.findOne('.' + this._movingAnchorName);
          var stage = anchorNode.getStage();
          stage.setPointersPositions(e);
          const pp = stage.getPointerPosition();
          let newNodePos = {
              x: pp.x - this._anchorDragOffset.x,
              y: pp.y - this._anchorDragOffset.y,
          };
          const oldAbs = anchorNode.getAbsolutePosition();
          if (this.anchorDragBoundFunc()) {
              newNodePos = this.anchorDragBoundFunc()(oldAbs, newNodePos, e);
          }
          anchorNode.setAbsolutePosition(newNodePos);
          const newAbs = anchorNode.getAbsolutePosition();
          // console.log(oldAbs, newNodePos, newAbs);
          if (oldAbs.x === newAbs.x && oldAbs.y === newAbs.y) {
              return;
          }
          // rotater is working very differently, so do it first
          if (this._movingAnchorName === 'rotater') {
              var attrs = this._getNodeRect();
              x = anchorNode.x() - attrs.width / 2;
              y = -anchorNode.y() + attrs.height / 2;
              // hor angle is changed?
              let delta = Math.atan2(-y, x) + Math.PI / 2;
              if (attrs.height < 0) {
                  delta -= Math.PI;
              }
              var oldRotation = Konva.getAngle(this.rotation());
              const newRotation = oldRotation + delta;
              const tol = Konva.getAngle(this.rotationSnapTolerance());
              const snappedRot = getSnap(this.rotationSnaps(), newRotation, tol);
              const diff = snappedRot - attrs.rotation;
              const shape = rotateAroundCenter(attrs, diff);
              this._fitNodesInto(shape, e);
              return;
          }
          var keepProportion = this.keepRatio() || e.shiftKey;
          var centeredScaling = this.centeredScaling() || e.altKey;
          if (this._movingAnchorName === 'top-left') {
              if (keepProportion) {
                  var comparePoint = centeredScaling
                      ? {
                          x: this.width() / 2,
                          y: this.height() / 2,
                      }
                      : {
                          x: this.findOne('.bottom-right').x(),
                          y: this.findOne('.bottom-right').y(),
                      };
                  newHypotenuse = Math.sqrt(Math.pow(comparePoint.x - anchorNode.x(), 2) +
                      Math.pow(comparePoint.y - anchorNode.y(), 2));
                  var reverseX = this.findOne('.top-left').x() > comparePoint.x ? -1 : 1;
                  var reverseY = this.findOne('.top-left').y() > comparePoint.y ? -1 : 1;
                  x = newHypotenuse * this.cos * reverseX;
                  y = newHypotenuse * this.sin * reverseY;
                  this.findOne('.top-left').x(comparePoint.x - x);
                  this.findOne('.top-left').y(comparePoint.y - y);
              }
          }
          else if (this._movingAnchorName === 'top-center') {
              this.findOne('.top-left').y(anchorNode.y());
          }
          else if (this._movingAnchorName === 'top-right') {
              if (keepProportion) {
                  var comparePoint = centeredScaling
                      ? {
                          x: this.width() / 2,
                          y: this.height() / 2,
                      }
                      : {
                          x: this.findOne('.bottom-left').x(),
                          y: this.findOne('.bottom-left').y(),
                      };
                  newHypotenuse = Math.sqrt(Math.pow(anchorNode.x() - comparePoint.x, 2) +
                      Math.pow(comparePoint.y - anchorNode.y(), 2));
                  var reverseX = this.findOne('.top-right').x() < comparePoint.x ? -1 : 1;
                  var reverseY = this.findOne('.top-right').y() > comparePoint.y ? -1 : 1;
                  x = newHypotenuse * this.cos * reverseX;
                  y = newHypotenuse * this.sin * reverseY;
                  this.findOne('.top-right').x(comparePoint.x + x);
                  this.findOne('.top-right').y(comparePoint.y - y);
              }
              var pos = anchorNode.position();
              this.findOne('.top-left').y(pos.y);
              this.findOne('.bottom-right').x(pos.x);
          }
          else if (this._movingAnchorName === 'middle-left') {
              this.findOne('.top-left').x(anchorNode.x());
          }
          else if (this._movingAnchorName === 'middle-right') {
              this.findOne('.bottom-right').x(anchorNode.x());
          }
          else if (this._movingAnchorName === 'bottom-left') {
              if (keepProportion) {
                  var comparePoint = centeredScaling
                      ? {
                          x: this.width() / 2,
                          y: this.height() / 2,
                      }
                      : {
                          x: this.findOne('.top-right').x(),
                          y: this.findOne('.top-right').y(),
                      };
                  newHypotenuse = Math.sqrt(Math.pow(comparePoint.x - anchorNode.x(), 2) +
                      Math.pow(anchorNode.y() - comparePoint.y, 2));
                  var reverseX = comparePoint.x < anchorNode.x() ? -1 : 1;
                  var reverseY = anchorNode.y() < comparePoint.y ? -1 : 1;
                  x = newHypotenuse * this.cos * reverseX;
                  y = newHypotenuse * this.sin * reverseY;
                  anchorNode.x(comparePoint.x - x);
                  anchorNode.y(comparePoint.y + y);
              }
              pos = anchorNode.position();
              this.findOne('.top-left').x(pos.x);
              this.findOne('.bottom-right').y(pos.y);
          }
          else if (this._movingAnchorName === 'bottom-center') {
              this.findOne('.bottom-right').y(anchorNode.y());
          }
          else if (this._movingAnchorName === 'bottom-right') {
              if (keepProportion) {
                  var comparePoint = centeredScaling
                      ? {
                          x: this.width() / 2,
                          y: this.height() / 2,
                      }
                      : {
                          x: this.findOne('.top-left').x(),
                          y: this.findOne('.top-left').y(),
                      };
                  newHypotenuse = Math.sqrt(Math.pow(anchorNode.x() - comparePoint.x, 2) +
                      Math.pow(anchorNode.y() - comparePoint.y, 2));
                  var reverseX = this.findOne('.bottom-right').x() < comparePoint.x ? -1 : 1;
                  var reverseY = this.findOne('.bottom-right').y() < comparePoint.y ? -1 : 1;
                  x = newHypotenuse * this.cos * reverseX;
                  y = newHypotenuse * this.sin * reverseY;
                  this.findOne('.bottom-right').x(comparePoint.x + x);
                  this.findOne('.bottom-right').y(comparePoint.y + y);
              }
          }
          else {
              console.error(new Error('Wrong position argument of selection resizer: ' +
                  this._movingAnchorName));
          }
          var centeredScaling = this.centeredScaling() || e.altKey;
          if (centeredScaling) {
              var topLeft = this.findOne('.top-left');
              var bottomRight = this.findOne('.bottom-right');
              var topOffsetX = topLeft.x();
              var topOffsetY = topLeft.y();
              var bottomOffsetX = this.getWidth() - bottomRight.x();
              var bottomOffsetY = this.getHeight() - bottomRight.y();
              bottomRight.move({
                  x: -topOffsetX,
                  y: -topOffsetY,
              });
              topLeft.move({
                  x: bottomOffsetX,
                  y: bottomOffsetY,
              });
          }
          var absPos = this.findOne('.top-left').getAbsolutePosition();
          x = absPos.x;
          y = absPos.y;
          var width = this.findOne('.bottom-right').x() - this.findOne('.top-left').x();
          var height = this.findOne('.bottom-right').y() - this.findOne('.top-left').y();
          this._fitNodesInto({
              x: x,
              y: y,
              width: width,
              height: height,
              rotation: Konva.getAngle(this.rotation()),
          }, e);
            
        }

        transformer._handleAlternativeRotation = transformer._handleAlternativeRotation.bind(transformer);

        var anchor = new Konva.Rect({
            x: transformer.getWidth() / 2,
            y: transformer.getHeight() + 30,
            width: 10,
            height: 10,
            stroke: 'rgb(0, 161, 255)',
            fill: 'white',
            strokeWidth: 1,
            name: 'rotater',
            dragDistance: 0,
            // make it draggable,
            // so activating the anchor will not start drag&drop of any parent
            draggable: true,
            hitStrokeWidth: 'auto'//TOUCH_DEVICE ? 10 : 'auto',
        });

        
          anchor.on('mousedown touchstart', function (e) {

                var transformer = this.getParent();

                transformer._movingAnchorName = 'rotater';
                var attrs = transformer._getNodeRect();
                var width = attrs.width;
                var height = attrs.height;
                var hypotenuse = Math.sqrt(Math.pow(width, 2) + Math.pow(height, 2));
                transformer.sin = Math.abs(height / hypotenuse);
                transformer.cos = Math.abs(width / hypotenuse);
                if (typeof window !== 'undefined') {
                    window.addEventListener('mousemove', transformer._handleAlternativeRotation);
                    window.addEventListener('touchmove', transformer._handleAlternativeRotation);
                    window.addEventListener('mouseup', transformer._handleMouseUp, true);
                    window.addEventListener('touchend', transformer._handleMouseUp, true);
                }
                transformer._transforming = true;
                var ap = e.target.getAbsolutePosition();
                var pos = e.target.getStage().getPointerPosition();
                transformer._anchorDragOffset = {
                    x: pos.x - ap.x,
                    y: pos.y - ap.y,
                };
                transformer._fire('transformstart', { evt: e.evt, target: transformer.getNode() });
                transformer._nodes.forEach((target) => {
                    target._fire('transformstart', { evt: e.evt, target });
                });
            

            //var self = this.getParent();
              //self._handleMouseDown(e);
          });
          anchor.on('dragstart', (e) => {
              anchor.stopDrag();
              e.cancelBubble = true;
          });
          anchor.on('dragend', (e) => {
              e.cancelBubble = true;
          });
          // add hover styling
          anchor.on('mouseenter', function(e){
              var cursor = 'crosshair';
              anchor.getStage().content &&
                  (anchor.getStage().content.style.cursor = cursor);
              this._cursorChange = true;
          });
          anchor.on('mouseout', () => {
              anchor.getStage().content &&
                  (anchor.getStage().content.style.cursor = '');
              this._cursorChange = false;
          });
          

        transformer.add(anchor);
    } 

    removeArrow () {
        // destroy the transformer
        if (this.activeArrow != null){
            let arrowTransformer = this.arrowTransformerMap[this.activeArrow.id()];
            arrowTransformer.destroy();
            this.activeArrow.destroy();
            this.activeArrow = null;
            this.setFeaturesInputValue();
        }
    }

    // update the size of all arrows during the resizing of the crop area
    // the terminalPoint has to stay the same
    // the offset/initialPopint have to be recalculated
    updateAllArrows () {

        if (this.arrowLayer != null && this.arrowLayer.hasChildren() == true){

            let children = this.arrowLayer.getChildren(function(node){
                return node.getClassName() === 'Arrow';
            });

            let strokeWidth = this.getArrowStrokeWidth();

            let newArrowLength = this.getArrowLength();

            for (let c=0; c<children.length; c++){

                let arrow = children[c];

                // update stroke width
                arrow.strokeWidth(strokeWidth);

                // update arrow length
                let points = arrow.points();

                let initialPoint = {
                    x : points[0],
                    y : points[1]
                };

                let terminalPoint = {
                    x : points[2],
                    y : points[3]
                };

                // get points relative to stage
                let transformedInitialPoint = arrow.getAbsoluteTransform().point(initialPoint);
                let transformedTerminalPoint = arrow.getAbsoluteTransform().point(terminalPoint);

                let oldVector = {
                    x : transformedTerminalPoint.x - transformedInitialPoint.x,
                    y : transformedTerminalPoint.y - transformedInitialPoint.y
                };

                if (this.DEBUG == true){
                    console.log("[InteractiveImageField] oldVector: (" + oldVector.x + "/" + oldVector.y + ")");
                };

                let currentArrowLength = Math.sqrt( Math.pow(oldVector.x, 2) + Math.pow(oldVector.y, 2) );

                let normalizedVector = {
                    x : oldVector.x / currentArrowLength,
                    y : oldVector.y / currentArrowLength
                };

                if (this.DEBUG == true){
                    console.log("[InteractiveImageField] normalizedVector: (" + normalizedVector.x + "/" + normalizedVector.y + ")");
                };

                let newVector = {
                    x : normalizedVector.x * newArrowLength,
                    y : normalizedVector.y * newArrowLength
                };

                if (this.DEBUG == true){
                    console.log("[InteractiveImageField] newVector: (" + newVector.x + "/" + newVector.y + ")");
                };

                // translate offset x/y
                let translationVector = {
                    x : oldVector.x - newVector.x,
                    y : oldVector.y - newVector.y
                };

                if (this.DEBUG == true){
                    console.log("[InteractiveImageField] translationVector: (" + translationVector.x + "/" + translationVector.y + ")");
                }

                let newInitialPoint = {
                    x : transformedInitialPoint.x + translationVector.x,
                    y : transformedInitialPoint.y + translationVector.y
                };

                let newArrowDefinition = {
                    initialPoint : newInitialPoint,
                    terminalPoint : transformedTerminalPoint
                };

                let newKonvaArrow = this.arrowToKonvaArrow(newArrowDefinition);

                arrow.x(newKonvaArrow.x);
                arrow.y(newKonvaArrow.y);

                arrow.points(newKonvaArrow.points);
                arrow.width(newVector.x);
                arrow.height(newVector.y);
                arrow.rotation(0);

                arrow.pointerLength(this.getPointerLength());
                arrow.pointerWidth(this.getPointerWidth());
                
            }
        }
    }

    activateArrow(arrow){

        // switch to arrow mode if needed
        this.cropAreaTransformLayer.visible(false);
        this.arrowsTransformLayer.visible(true);

        let activeArrowId = arrow.id();
        let arrowTransformer = this.arrowTransformerMap[activeArrowId];
        arrowTransformer.visible(true);

        for (let arrowId in this.arrowTransformerMap){

            if (arrowId != activeArrowId){
                let arrowTransformer = this.arrowTransformerMap[arrowId];
                arrowTransformer.visible(false);
            }
            
        }

        this.activeArrow = arrow;

        this.toolbar.activateArrowMode();
    }

    // helper methods
    // the scaling factor describes the scaling of the image, which is necessary to fit it into the stage
    // if cropArea contains the image, the larger dimension of width/height defines the scaling factor
    getScalingFactor () {

        if (this.DEBUG == true){
            console.log("[InteractiveImageField] calculating scaling factor. container.offsetWidth: " + this.container.offsetWidth + " stage: " + this.stage + " image width: " + this.image.width);
        }

        let scalingFactor = null;

        let stageWidth = this.container.offsetWidth;

        if (this.stage != null){
            stageWidth = this.stage.width();
        }

        if (this.options.cropMode == "contains"){
            // stage is present
            let stageHeight = this.stage.height();
            

            if (this.image.height >= this.image.width){
                scalingFactor = stageHeight / this.image.height;
            }
            else {
                scalingFactor = stageWidth / this.image.width;
            }
        }
        else {
            scalingFactor = stageWidth / this.image.width;
        }

        return scalingFactor;
    }

    getClientRect(rotatedBox) {

        const { x, y, width, height } = rotatedBox;
        const rad = rotatedBox.rotation;

        const p1 = this.getCorner(x, y, 0, 0, rad);
        const p2 = this.getCorner(x, y, width, 0, rad);
        const p3 = this.getCorner(x, y, width, height, rad);
        const p4 = this.getCorner(x, y, 0, height, rad);

        const minX = Math.min(p1.x, p2.x, p3.x, p4.x);
        const minY = Math.min(p1.y, p2.y, p3.y, p4.y);
        const maxX = Math.max(p1.x, p2.x, p3.x, p4.x);
        const maxY = Math.max(p1.y, p2.y, p3.y, p4.y);

        return {
            x: minX,
            y: minY,
            width: maxX - minX,
            height: maxY - minY
        };
    }

    getCorner(pivotX, pivotY, diffX, diffY, angle) {
        const distance = Math.sqrt(diffX * diffX + diffY * diffY);

        /// find angle from pivot to corner
        angle += Math.atan2(diffY, diffX);

        /// get new x and y and round it off to integer
        const x = pivotX + distance * Math.cos(angle);
        const y = pivotY + distance * Math.sin(angle);

        return { x: x, y: y };
    }

    getTotalBox(boxes) {
        let minX = Infinity;
        let minY = Infinity;
        let maxX = -Infinity;
        let maxY = -Infinity;

        boxes.forEach((box) => {
            minX = Math.min(minX, box.x);
            minY = Math.min(minY, box.y);
            maxX = Math.max(maxX, box.x + box.width);
            maxY = Math.max(maxY, box.y + box.height);
        });

        return {
            x: minX,
            y: minY,
            width: maxX - minX,
            height: maxY - minY
        };
    }

}


class InteractiveImageFieldToolbar {

    constructor (interactiveImageField) {

        this.interactiveImageField = interactiveImageField;

        this.createBasicToolBar();

        this.createArrowToolbar(); 

    }

    createToolBarHTML (id){

        let container = document.createElement("div");
        container.id = id;
        container.classList.add("mt-2", "py-1", "px-2", "d-none", "interactiveImageField-toolbar");

        return container;

    }

    createButtonHTML (imageSrc) {
        let button = document.createElement("span");
        button.classList.add("toolbar-button");
        let buttonImg = new Image();
        buttonImg.src = imageSrc;
        button.append(buttonImg);

        return button;
    }

    createBasicToolBar () {

        var self = this;

        this.toolsContainer = this.createToolBarHTML("InteractiveImageField-toolbar");
        this.interactiveImageField.container.append(this.toolsContainer);

        // crop mode button
        this.cropModeButton = this.createButtonHTML("/static/localcosmos_server/images/crop-tool.png");
        this.cropModeButton.classList.add("active");
        this.toolsContainer.append(this.cropModeButton);

        this.cropModeButton.addEventListener("click", function(event){
            self.activateCropMode();
        });

        // arrow mode button
        if (this.interactiveImageField.options.allowFeatures == true){
            this.arrowModeButton = this.createButtonHTML("/static/localcosmos_server/images/arrow-tool.png");
            this.toolsContainer.append(this.arrowModeButton);

            this.arrowModeButton.addEventListener("click", function(event){
                self.activateArrowMode();
            });
        }

    }

    createArrowToolbar () {

        var self = this;

        this.arrowToolsContainer = this.createToolBarHTML("InteractiveImageField-arrowtoolbar");
        this.interactiveImageField.container.append(this.arrowToolsContainer);

        // add arrow button
        let addArrowButton = this.createButtonHTML("/static/localcosmos_server/images/arrow-tool-add.png");
        this.arrowToolsContainer.append(addArrowButton);

        addArrowButton.addEventListener("click", function(event){
            self.addArrow(event);
        });

        // remove arrow button - only show this button if an arrow is selected
        this.removeArrowButton = this.createButtonHTML("/static/localcosmos_server/images/arrow-tool-remove.png");
        this.arrowToolsContainer.append(this.removeArrowButton);

        this.removeArrowButton.addEventListener("click", function(event){
            self.removeArrow(event);
        });

        // arrow color button
        let arrowColorButton = document.createElement("span");
        arrowColorButton.classList.add("toolbar-button");
        this.arrowColorInput = document.createElement("input");
        this.arrowColorInput.type = "color";
        this.arrowColorInput.name = "interactiveImageField-color";
        this.arrowColorInput.id = "InteractiveImageField-color";
        this.arrowColorInput.value = "#000000";
        arrowColorButton.append(this.arrowColorInput);
        this.arrowToolsContainer.append(arrowColorButton);

        this.arrowColorInput.addEventListener("change", function(event){
            if (self.interactiveImageField.activateArrow != null){

                let color = event.currentTarget.value;
                self.interactiveImageField.activeArrow.fill(color);
                self.interactiveImageField.activeArrow.stroke(color);
                self.interactiveImageField.setFeaturesInputValue();
            }
        });

    }

    show () {
        this.toolsContainer.classList.remove("d-none");
    }

    hide () {
        this.toolsContainer.classList.add("d-none");
    }

    activateArrowMode () {
        
        this.cropModeButton.classList.remove("active");
        this.interactiveImageField.cropAreaTransformLayer.visible(false);

        this.arrowModeButton.classList.add("active");
        this.arrowToolsContainer.classList.remove("d-none");
        this.interactiveImageField.arrowsTransformLayer.visible(true);

        if (this.interactiveImageField.activeArrow != null){
            this.arrowColorInput.value = this.interactiveImageField.activeArrow.fill();
        }

    }

    activateCropMode (){

        if (this.interactiveImageField.options.allowFeatures == true){
            this.arrowModeButton.classList.remove("active");
            this.arrowToolsContainer.classList.add("d-none");
            this.interactiveImageField.arrowsTransformLayer.visible(false);
        }

        this.cropModeButton.classList.add("active");
        this.interactiveImageField.cropAreaTransformLayer.visible(true);

    }

    addArrow () {

        let defaultColor = this.interactiveImageField.options.defaultArrowColor;

        if (this.arrowColorInput.value.length){
            defaultColor = this.arrowColorInput.value
        }

        let arrowLength = this.interactiveImageField.getArrowLength();

        let arrowOffset = this.interactiveImageField.cropArea.width() * 0.3; // offset is relative to the source image, not the crop area

        let xyCoordinate = arrowLength / Math.sqrt(2);

        let arrowDefinition = {
            "type" : "arrow",
            "initialPoint" : { 
                "x" : arrowOffset,
                "y" : arrowOffset
            },
            "terminalPoint" : {
                "x" : xyCoordinate + arrowOffset,
                "y" : xyCoordinate + arrowOffset
            },
            "color": defaultColor
        };


        this.interactiveImageField.addArrow(arrowDefinition);
    }

    // if no other arrow is present, hide the removeArrowButton
    removeArrow (arrow) {
        this.interactiveImageField.removeArrow(arrow);
    }
}