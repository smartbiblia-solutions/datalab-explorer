var summaries = [
  {
    "name": "affiliation_et_partenaires_brgm",
    "panel": "left",
	"value": function () {
                if(this["affiliation_et_partenaires_brgm"]){
                    return this["affiliation_et_partenaires_brgm"].split(";");
                }
            },
    "collapsed": false
  },
  {
    "name": "auteur_correspondant",
    "panel": "left",
    "collapsed": false,
    "value": "auteur_correspondant"
  },
  {
    "name": "auteurs_brgm",
    "panel": "left",
	"value": function () {
                if(this["auteurs_brgm"]){
                    return this["auteurs_brgm"].split(";");
                }
            },
    "collapsed": true
  },
  {
    "name": "directions_reorg_2025",
    "panel": "right",
	"value": function () {
                if(this["directions_reorg_2025"]){
                    return this["directions_reorg_2025"].split(";");
                }
            },
    "collapsed": false
  },
  {
    "name": "financements",
    "panel": "left",
	"value": function () {
                if(this["financements"]){
                    return this["financements"].split(";");
                }
            },
    "collapsed": false
  },
  {
    "name": "oa",
    "panel": "middle",
    "collapsed": false,
    "value": "oa"
  },
  {
    "name": "open_access.oa_status",
    "panel": "middle",
    "collapsed": false,
    "value": "open_access.oa_status"
  },
  {
    "name": "prog_2025_retenu",
    "panel": "right",
    "collapsed": false,
    "value": "prog_2025_retenu"
  },
  {
    "name": "programme_doctoral",
    "panel": "right",
    "collapsed": false,
    "value": "programme_doctoral"
  },
  {
    "name": "py2",
    "panel": "middle",
    "collapsed": false,
    "value": function () {
                if(this["py2"]){
                    return parseInt(this["py2"]);
                }
            },
  }
];

var recordDisplay = {
    viewAs: "list",
    textBy: function anonymous(
) {
var str = "";
return str;
},
    listViewConfig: [
  {
    "include": false,
    "field": "affiliation_et_partenaires_brgm",
    "label": "",
    "bold": false,
    "newline": false
  },
  {
    "include": false,
    "field": "auteur_correspondant",
    "label": "",
    "bold": false,
    "newline": false
  },
  {
    "include": false,
    "field": "auteurs_brgm",
    "label": "",
    "bold": false,
    "newline": false
  },
  {
    "include": false,
    "field": "co-publication",
    "label": "",
    "bold": false,
    "newline": false
  },
  {
    "include": false,
    "field": "collaborations",
    "label": "",
    "bold": false,
    "newline": false
  },
  {
    "include": false,
    "field": "directions_reorg_2025",
    "label": "",
    "bold": false,
    "newline": false
  },
  {
    "include": false,
    "field": "discipline_brgm",
    "label": "",
    "bold": false,
    "newline": false
  },
  {
    "include": false,
    "field": "display_name",
    "label": "",
    "bold": false,
    "newline": false
  },
  {
    "include": false,
    "field": "document_type",
    "label": "",
    "bold": false,
    "newline": false
  },
  {
    "include": false,
    "field": "doi",
    "label": "",
    "bold": false,
    "newline": false
  },
  {
    "include": false,
    "field": "financements",
    "label": "",
    "bold": false,
    "newline": false
  },
  {
    "include": false,
    "field": "geo_affiliation_brgm_dat",
    "label": "",
    "bold": false,
    "newline": false
  },
  {
    "include": false,
    "field": "oa",
    "label": "",
    "bold": false,
    "newline": false
  },
  {
    "include": false,
    "field": "open_access.oa_status",
    "label": "",
    "bold": false,
    "newline": false
  },
  {
    "include": false,
    "field": "pays",
    "label": "",
    "bold": false,
    "newline": false
  },
  {
    "include": false,
    "field": "premier_auteur_brgm",
    "label": "",
    "bold": false,
    "newline": false
  },
  {
    "include": false,
    "field": "prog_2025_retenu",
    "label": "",
    "bold": false,
    "newline": false
  },
  {
    "include": false,
    "field": "programme_doctoral",
    "label": "",
    "bold": false,
    "newline": false
  },
  {
    "include": false,
    "field": "py2",
    "label": "",
    "bold": false,
    "newline": false
  },
  {
    "include": false,
    "field": "resume",
    "label": "",
    "bold": false,
    "newline": false
  },
  {
    "include": false,
    "field": "times_cited",
    "label": "",
    "bold": false,
    "newline": false
  }
]
};
