var mm = com.modestmaps,
    timeout = undefined,
    mmap = undefined;

function limitAndFix(value, lowest, highest)
{
    return (new Number(Math.max(lowest, Math.min(highest, value)))).toFixed(3);
}

function makeUserdata(style, north, south, east, west)
{
    console.log([north, south, east, west]);
    
    var req = new XMLHttpRequest(),
        userdata = document.getElementById('userdata');

    userdata.className = 'loading';
    userdata.innerHTML = '\n\n\n';
    
    req.onreadystatechange = function()
    {
        try {
            if(req.status == 200)
            {
                userdata.className = '';
                userdata.innerHTML = req.responseText;
            }
        } catch(e) {
        }
    }
    
    req.open('POST', 'check-bounds.cgi');
    req.send(['north='+north, 'south='+south, 'east='+east, 'west='+west, 'style='+style].join('&'));
}

function onChanged()
{
    var buffer = 33; // extra space around the visible map
    
    var topleft = new mm.Point(-buffer, -buffer);
    var bottomright = new mm.Point(mmap.dimensions.x + buffer, mmap.dimensions.y + buffer);

    var northwest = mmap.pointLocation(topleft);
    var southeast = mmap.pointLocation(bottomright);
    
    var north = limitAndFix(northwest.lat, -85, 85);
    var south = limitAndFix(southeast.lat, -85, 85);
    var east = limitAndFix(southeast.lon, -180, 180);
    var west = limitAndFix(northwest.lon, -180, 180);
    
    var styleform = document.forms.style;
    
    if(styleform)
    {
        window.clearTimeout(timeout);
        timeout = window.setTimeout(makeUserdata, 500, styleform.elements.url.value, north, south, east, west);
    }
}

function chooseStyle(url)
{
    document.forms.style.elements.url.value = url;
    onChanged();
    
    return false;
}

var tileURL = function(coord)
{
    return 'http://tile.cloudmade.com/f1fe9c2761a15118800b210c0eda823c/1/256/' + coord.zoom + '/' + coord.column + '/' + coord.row + '.png';
    var sub = ['a', 'b', 'c'][(coord.zoom + coord.column + coord.row) % 3];
    return 'http://' + sub + '.tile.openstreetmap.org/' + coord.zoom + '/' + coord.column + '/' + coord.row + '.png';
}

window.onload = function(e)
{
    mmap = new mm.Map('map', new mm.MapProvider(tileURL), new mm.Point(446, 446));

    mmap.addCallback('zoomed',    function(m, a) { return onChanged(); });
    mmap.addCallback('centered',  function(m, a) { return onChanged(); });
    mmap.addCallback('extentset', function(m, a) { return onChanged(); });
    mmap.addCallback('panned',    function(m, a) { return onChanged(); });
    
    mmap.setCenterZoom(new mm.Location(0, 0), 1);
    mmap.draw();

    /*
    var head = document.getElementById('header'),
        top = 185;
    
    window.onscroll = function(e)
    {
        head.className = (document.body.scrollTop > top) ? 'pegged' : '';
    }
    
    window.onscroll();
    */
}
