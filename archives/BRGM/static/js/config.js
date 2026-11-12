/*-----------------------Dashbord config--------------------------*/
var summaries = [
//left panel
  {
    "name": "prog_2025_retenu",
    "panel": "left",
    "value": "prog_2025_retenu",
  },
    {
    "name": "programme_doctoral",
    "panel": "left",
    "value": "programme_doctoral",
  },
   {
    "name": "directions_reorg_2025",
    "panel": "left",
    "value": function () {
                if(this["directions_reorg_2025"]){
                    return this["directions_reorg_2025"].split(";");
                }
            },
  },
  {
    "name": "discipline_brgm",
    "panel": "left",
    "value": "discipline_brgm",
  },
  //middle panel
    {
    "name": "co-publication",
    "panel": "middle",
    "value": "co-publication",
  },
  {
    "name": "collaborations",
    "panel": "middle",
    "value": "collaborations",
  },
    {
    "name": "affiliation_et_partenaires_brgm",
    "panel": "middle",
    "value": function () {
                if(this["affiliation_et_partenaires_brgm"]){
                    return this["affiliation_et_partenaires_brgm"].split(";");
                }
            },
  },
  /*{
    "name": "pays",
    "panel": "middle",
    "collapsed": true,
    "value": function () {
                if(this["pays"]){
                    return this["pays"].split(";");
                }
            },
  },*/
  //right panel
    {
    "name": "document_type",
    "panel": "right",
    "value": "document_type",
  },

  {
    "name": "auteurs_brgm",
    "panel": "right",
    "value": function () {
                if(this["auteurs_brgm"]){
                    return this["auteurs_brgm"].split(";");
                }
            },
  },
    {
    "name": "premier_auteur_brgm",
    "panel": "right",
    "value": "premier_auteur_brgm",
  },
  {
    "name": "auteur_correspondant",
    "panel": "right",
    "value": "auteur_correspondant",
  },
  /*{
    "name": "times_cited",
    "panel": "right",
    "value": "times_cited",
    "collapsed": true 
  },*/
//bottom panel
  {
    "name": "Année de publication",
    "panel": "bottom",
    "value": function () {
                if(this["py2"]){
                    return new Date(Date.parse(this["py2"]));
                }
            },
  },

]

var recordDisplay = {
    viewAs: "list",
    textBy: "display_name",
    //sortBy: "py2",
    list_sortColWidth: 45,
    list_sortVizWidth: 0,
    list_sortInverse: true,
  }
