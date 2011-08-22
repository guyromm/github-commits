var lines={}; var keys=[]; var mink=null; var maxk=null; var minv=null; var minmax={};

var colarr = ['blue','cyan','red','yellow','pink','gray','purple','green'];
//var colors = {'create_index':'blue','drop_index':'cyan','insert':'red','select10':'yellow','select1000':'pink','data_size':'gray','chunks_amt':'yellow','chunks_deviation':'purple','shards_amt':'green'};
var colors={};
for (var i=0;i<data.length;i++)
    {
	if (!colors[data[i].action]) 
	    {
		var col = colarr.pop();
		colors[data[i].action]=col;
	    }
    }
console.log('colors = %o',colors);
var mikra = {};
var prev={};
window.onload = function() { 
    console.log('cycling colors %o',colors);
    for (var tp in colors)
    {
	var el = document.createElement('span');
	el.style.backgroundColor=colors[tp];
	el.style.marginRight='10px';
	el.innerHTML = tp;
	$('body').prepend(el); //document.getElementById('info').appendChild(el);
    }

var onlyres = /only=([^&]+)/.exec(location.href);
    if (onlyres) var only=onlyres[1].split(',');
    else var only=null;

var maxitemsres = /maxitems=([^&]+)/.exec(location.href);
if (maxitemsres) var maxitems=parseInt(maxitemsres[1]);
else var maxitems=0;

{
//console.log(rt)
	    var w = 920; var h = 200;
	    var paper = Raphael(10,50,w,h);
	    for (var i=0;i<data.length;i++)
		{
		    var d = data[i];
		    if (only && $.inArray(d.action,only)==-1) continue;
		    if (maxitems && d.curitems>maxitems) continue; 
		    if (!lines[d.action]) { lines[d.action]={}; minmax[d.action]={'min':null,'max':null}; }
		    lines[d.action][d.curitems]=d.time;
		    
		    if (minmax[d.action].max==null || d.time>=minmax[d.action].max) minmax[d.action].max=d.time;
		    if (minmax[d.action].min==null || d.time<=minmax[d.action].min) minmax[d.action].min=d.time;
		    
		    
		    if (keys.indexOf(d.curitems)==-1) keys.push(d.curitems);
		    
		    if (maxk==null || d.curitems>=maxk) maxk=d.curitems;
		    if (mink==null || d.curitems<=mink) mink=d.curitems;
		    
		}
	    
	    console.log('%o - %o ; %o',mink,maxk,minmax);
	    console.log(lines);
	    
	    var ds = [];
	    for (var k=0;k<keys.length;k++)
		{
		    var ci = keys[k];
		    //console.log(ci);
		    for (var dt in lines)
			{
			    if (!lines[dt][ci]) continue;
			
			    //calculate x
			    var xpcnt = (maxk-ci) / (maxk-mink);
			    var xpos = w - (w * xpcnt);
			    //console.log(xpos);
			    
			    //calc y
			    var ypcnt = lines[dt][ci] / (minmax[dt].max); // - minmax[dt].min);
			    var ypos = h - (h * ypcnt);
			
			    console.log("%o , %o -> %o , %o",ci,lines[dt][ci],xpos,ypos);
			    mikra[parseInt(xpos)+','+parseInt(ypos)]={dt:dt,ci:ci,val:lines[dt][ci]};
			    
			    var d = paper.circle(xpos,ypos,4);
			    
			    d.node.onmouseover = function(ev) { 
				var mikrakey = parseInt(ev.target.cx.animVal.value)+','+parseInt(ev.target.cy.animVal.value)
				var m = mikra[mikrakey];
				document.getElementById('info').innerHTML = m.dt+": "+m.val+" at "+new Date(m.ci*1000);
			     d.attr({fill:'black'});
			    }

			     d.attr({fill:colors[dt],stroke:colors[dt]});
			     if (false) //only.length)
				{
				    var rw = 4;
				    re = paper.rect(xpos-(rw/2)+(k),ypos,1,h);
			     re.attr({fill:colors[dt],stroke:colors[dt]}); //,'fill-opacity':0.1,'opacity':0.1});
				}
			     ds.push(d);
			    if (!prev[dt]) prev[dt]=[];
			    else
				{
				    var lpath = "M"+prev[dt][0]+" "+prev[dt][1]+"L"+xpos+" "+ypos;
				    //console.log(lpath);
				    //if (only)
				    {
					var l = paper.path(lpath);
					l.attr({stroke:colors[dt]});

				    }
				}
			    prev[dt]=[xpos,ypos];

			}
		}
	    }
}
