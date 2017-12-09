// scripts/copy_parts_fzp_files.js

var fs = require("fs");
var path = require("path");
var xml2js = require('xml2js').parseString;





var objects = []
var obj = [];

// read file directory
var p = "../../core/"
var parts = fs.readdirSync(p)

function main() {
  parts.map(function (file) {
    // console.log(p, file);
    return path.join(p, file);
  }).filter(function (file) {
    return fs.statSync(file).isFile();
  }).forEach(function (file) {

    if (path.extname(file) === '.fzp') {
      try {
        readFzp(file,path);
      } catch (e) {
        console.log("\nFILE: %s EXT: (%s)", file, path.extname(file));
        // console.log("ERROR:", e);
      }
    }
  })
  writeJson(objects);
}

function readFzp(file){
  var filename = path.basename(file)
  // console.log(filename);
  var obj = {};
  var data = fs.readFileSync(file, 'utf-8');

  obj.filename = filename || null;
  // convert xml to json
  xml2js(data, function (err, result) {
    // console.log('result:', JSON.stringify(result, null, 2));
    if (result === undefined) {
      return
    }


    // the part object
    if (result.module) {
      if (result.module.$) {
        obj.fritzingVersion = result.module.$.fritzingVersion || null;
        obj.moduleId = result.module.$.moduleId || null;
      }
      obj.version = result.module.version || null;
      obj.author = result.module.author || null;
      obj.title = result.module.title || null;
      obj.label = result.module.label || null;
      obj.url = result.module.url || null;
      obj.date = result.module.date || null;
      // if (result.module.tags) {
      //   obj.tags = result.module.tags[0].tag || null;
      // }
      obj.description = result.module.description || null;
    }


    // properties
    obj.properties = [];

    // console.log();
    if (result.module.properties !== undefined && result.module.properties.length > 0) {
      for (var a=0; a<result.module.properties[0].property.length; a++) {
        //console.log('properties', JSON.stringify(result.module.properties[0].property[i], null, 2));
        obj.properties.push({
          name: result.module.properties[0].property[a].$.name,
          value: result.module.properties[0].property[a]._
        });
      };
    };
    // views
    if (!result.module.views) {
      console.log("MISSING MODULE VIEWS");
    } else {
      obj.views = {
        icon: {},
        breadboard: {},
        pcb: {},
        schematic: {}
      }

        if (!result.module.views[0]) {
          console.log("MISSING views[0] ELEMENT");
        }
      obj.views.icon = {
          image: result.module.views[0].iconView[0].layers[0].$.image,
          layer: viewLayerHelper(result.module.views[0].iconView[0].layers[0].layer)
        }
      obj.views.breadboard = {
          image: result.module.views[0].breadboardView[0].layers[0].$.image,
          layer: viewLayerHelper(result.module.views[0].breadboardView[0].layers[0].layer)
        }
      obj.views.pcb = {
          image: result.module.views[0].pcbView[0].layers[0].$.image,
          layer: viewLayerHelper(result.module.views[0].pcbView[0].layers[0].layer)
        }
      obj.views.schematic = {
          image: result.module.views[0].schematicView[0].layers[0].$.image,
          layer: viewLayerHelper(result.module.views[0].schematicView[0].layers[0].layer)
        }

    }

    // connectors
    obj.connectors = [];
    //console.log(result.module.connectors);
    if (result.module.connectors[0].connector !== undefined) {
      for (var b=0; b<result.module.connectors[0].connector.length; b++) {
        // console.log('----------------------');
        // console.log(result.module.connectors[0].connector[i]);
        // console.log('----------------------');
        obj.connectors.push({
          id: result.module.connectors[0].connector[b].$.id,
          name: result.module.connectors[0].connector[b].$.name,
          type: result.module.connectors[0].connector[b].$.type,
          description: result.module.connectors[0].connector[b].description,
          views: result.module.connectors[0].connector[b].views //[]
        });

        // // connector views
        // for (var c=0; c<result.module.connectors[0].connector[b].views.length; c++) {
        //   //console.log( JSON.stringify(result.module.connectors[0].connector[b].views[c], null, 2) );
        //   var tmpObj = {};

        //   // breadboardView
        //   if (result.module.connectors[0].connector[b].views[c].breadboardView !== undefined) {
        //     //console.log(result.module.connectors[0].connector[b].views[c].breadboardView[0].p);
        //     // tmpObj.breadboard = {
        //     //   layer: result.module.connectors[0].connector[b].views[c].breadboardView[0].p[0].$.layer,
        //     //   svgId: result.module.connectors[0].connector[b].views[c].breadboardView[0].p[0].$.svgId,
        //     //   terminalId: result.module.connectors[0].connector[b].views[c].breadboardView[0].p[0].$.terminalId
        //     // };
        //     tmpObj.breadboard = viewConnectorHelper(result.module.connectors[0].connector[b].views[c].breadboardView[0].p);
        //   };
        //   // // schematicView

        //   // // pcbView
        //   obj.connectors[b].views.push(tmpObj);
        //   console.log(obj.connectors[b].views);
        // };

      };

    };

    fs.writeFileSync('../json/'+filename+'.json', JSON.stringify(obj));
    // console.log('obj', obj, obj.title);
    objects.push(obj)
  })
}

function viewLayerHelper(data) {
  if (data !== undefined && data.length > 0) {
    for (var i = 0; i < data.length; i++) {
      obj.push(data[i].$.layerId);
    };
  };
  return obj;
};

function writeJson(obj){
  var svgPaths = []
  for (var i = 0; i < obj.length; i++) {
        var  breadboard = removeExtention(path.basename(obj[i].views.breadboard.image))
          icon = removeExtention(path.basename(obj[i].views.icon.image))
          schematic= removeExtention(path.basename(obj[i].views.schematic.image))
          pcb = removeExtention(path.basename(obj[i].views.pcb.image))
      // console.log("we push", obj[i].filename);
      svgPaths.push({
        fzpFile:obj[i].filename || null,
        breadboard: breadboard  || null,
        schematic: icon || null,
        pcb: schematic || null,
        icon: pcb || null
      })


  }
fs.writeFileSync('../svg-paths.json', JSON.stringify(svgPaths, 2));
}

function removeExtention(x){
  var tmp = x.slice(0, -4);
  return tmp
}
// function viewConnectorHelper(data) {
//   console.log('data:', data);
//   var obj;
//   return obj;
// };

main()
