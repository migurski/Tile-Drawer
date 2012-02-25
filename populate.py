#!/usr/bin/env python

from os import chdir, remove
from sys import stderr, stdout
from optparse import OptionParser
from subprocess import Popen, PIPE
from xml.etree.ElementTree import parse, SubElement
from os.path import dirname, basename, splitext, join
from urlparse import urlparse, urljoin
from tempfile import mkstemp
from StringIO import StringIO
from zipfile import ZipFile
from urllib import urlopen
from time import strftime
import json

import cascadenik
import mapnik

epsg900913 = '+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0 +k=1.0 +units=m +nadgrids=@null'

parser = OptionParser(usage="""%prog [options] [url...]""")

defaults = dict(style='https://raw.github.com/migurski/OSM-Solar/tiledrawer/tiledrawer.cfg',
                bbox=(37.777, -122.352, 37.839, -122.226))

parser.set_defaults(**defaults)

parser.add_option('-s', '--style', dest='style',
                  help='URL of a style description, default %(style)s.' % defaults)

parser.add_option('-b', '--bbox', dest='bbox',
                  help='Bounding box in floating point geographic coordinates: south west north east.',
                  type='float', nargs=4)

def download_file(url):
    """ Shell out to curl to download extract and return its local filename.
    """
    s, h, path, p, q, f = urlparse(url)
    base, ext = splitext(basename(path))
    handle, filename = mkstemp(dir='progress', prefix=base+'-', suffix=ext)
    
    curl = 'curl', '-s', '-o', filename, '-L', url

    print >> stderr, '+', ' '.join(curl)

    curl = Popen(curl, stdout=stdout, stderr=PIPE)
    curl.wait()
    
    if curl.returncode:
        raise Exception('wuh-woh')
    
    return filename

def combine_extracts(bbox, files):
    """ Shell out to osmosis to combine extracts and pull out a bounding box.
    """
    osmosis = ['osmosis']
    
    for file in files:
        osmosis += ['--rb', file, '--log-progress']
    
    osmosis += ['--merge'] * len(files[1:])
    osmosis += ['--bb'] + ['%s=%.6f' % kv for kv in zip('bottom left top right'.split(), bbox)]
    osmosis += ['--wx', '-']

    handle, filename = mkstemp(dir='progress', prefix='out-', suffix='.osm.bz2')
    
    print >> stderr, '+', ' '.join(osmosis), '| bzip2 >', filename
    
    osmosis = Popen(osmosis, stderr=open('progress/osmosis.log', 'w'), stdout=PIPE)
    bzout = Popen(['bzip2'], stdin=osmosis.stdout, stdout=open(filename, 'w'))
    
    osmosis.wait()
    bzout.wait()
    
    if osmosis.returncode:
        raise Exception('wuh-woh')
    
    if bzout.returncode:
        raise Exception('wuh-woh')
    
    return filename

def import_extract_osm2pgsql(filename):
    """ Shell out to osm2pgsql to import extract file to Postgis.
    """

    # Remove possible existing line table to get rid of its High Road views
    
    psql = Popen('psql -U osm planet_osm'.split(), stdin=PIPE, stderr=PIPE, stdout=PIPE)
    psql.stdin.write('DROP TABLE IF EXISTS planet_osm_line CASCADE;')
    psql.stdin.close()
    psql.wait()
    
    if psql.returncode:
        raise Exception('wuh-woh')
    
    # Import new OSM data
    
    # TODO: is it safe to ask for 4GB of RAM here? Check /proc/meminfo MemFree.
    osm2pgsql = 'osm2pgsql -smucK -C 4096 -U osm -d planet_osm -S osm2pgsql/default.style'.split()
    osm2pgsql += [filename]
    
    print >> stderr, '+', ' '.join(osm2pgsql)
    
    logfile = open('progress/osm2pgsql.log', 'w')
    osm2pgsql = Popen(osm2pgsql, stdout=logfile, stderr=logfile)
    
    osm2pgsql.wait()
    
    if osm2pgsql.returncode:
        raise Exception('wuh-woh')
    
    # Apply new High Road views
    
    highroad_sql = urlopen('https://raw.github.com/migurski/HighRoad/master/views.pgsql').read()
    
    psql = Popen('psql -U osm planet_osm'.split(), stdin=PIPE, stderr=PIPE, stdout=PIPE)
    psql.stdin.write(highroad_sql)
    psql.stdin.close()
    psql.wait()
    
    if psql.returncode:
        raise Exception('wuh-woh')
    
def import_extract_imposm(filename):
    """ Shell out to imposm to import extract file to Postgis.
    """
    imposm = 'imposm --read --write --table-prefix=imposm_'.split()
    imposm += '--connect postgis://osm:@127.0.0.1/planet_osm'.split()
    imposm += ['--cache-dir=/usr/local/tiledrawer/progress', filename]
    
    print >> stderr, '+', ' '.join(imposm)
    
    logfile = open('progress/imposm.log', 'w')
    imposm = Popen(imposm, stdout=logfile, stderr=logfile)
    
    imposm.wait()
    
    if imposm.returncode:
        raise Exception('wuh-woh')

def download_coastline():
    """ Download and unpack an unprojected "good" coastline from metro.teczno.com.
    """
    curl = 'curl -sL http://osm-metro-extracts.s3.amazonaws.com/coastline-good-latlon.tar.bz2'.split()
    
    print >> stderr, '+', ' '.join(curl), '| bzcat | tar -C progress -xf -'
    
    curl = Popen(curl, stdout=PIPE, stderr=PIPE)
    bzcat = Popen('bzcat'.split(), stdin=curl.stdout, stdout=PIPE, stderr=PIPE)
    tar = Popen('tar -C progress -xf -'.split(), stdin=bzcat.stdout, stderr=PIPE)
    
    curl.wait()
    bzcat.wait()
    tar.wait()
    
    if curl.returncode:
        raise Exception('wuh-woh')
    
    if bzcat.returncode:
        raise Exception('wuh-woh')
    
    if tar.returncode:
        raise Exception('wuh-woh')
    
    return 'progress/coastline-good.shp'

def import_coastline(filename, bbox=None):
    """ Shell out to shp2pgsql to import a coastline file to Postgis.
    
        The coastline file is understood to be unprojected (EPSG:4326).
    """
    handle, extract_filename = mkstemp(dir='progress', prefix='coastline-', suffix='.shp')
    remove(extract_filename)
    
    ogr2ogr = 'ogr2ogr -t_srs EPSG:900913'.split()
    
    if bbox is not None:
        ogr2ogr += ['-spat']
        ogr2ogr += map(str, [bbox[1], bbox[0], bbox[3], bbox[2]])
    
    ogr2ogr += [extract_filename, filename]
    
    print >> stderr, '+', ' '.join(ogr2ogr)
    
    ogr2ogr = Popen(ogr2ogr)
    ogr2ogr.wait()
    
    if ogr2ogr.returncode:
        raise Exception('wuh-woh')
    
    shp2pgsql = 'shp2pgsql', '-dID', '-s', '900913', extract_filename, 'coastline'
    psql = 'psql -U osm planet_osm'.split()
    
    print >> stderr, '+', ' '.join(shp2pgsql), '|', ' '.join(psql)
    
    shp2pgsql = Popen(shp2pgsql, stdout=PIPE, stderr=PIPE)
    psql = Popen(psql, stdin=shp2pgsql.stdout, stdout=PIPE, stderr=PIPE)
    
    shp2pgsql.wait()
    psql.wait()
    
    if shp2pgsql.returncode:
        raise Exception('wuh-woh')
    
    if psql.returncode:
        raise Exception('wuh-woh')

def import_style(url):
    """
    """
    if url.endswith('.zip'):
        import_style_tilemill(url)
    
        update_status('Building Mapnik 2.0 (populate.py)')
        build_mapnik2()

    elif url.endswith('.cfg'):
        import_style_tdcfg(url)
    
    elif url.endswith('.mml'):
        import_style_mml(url)

def build_mapnik2():
    """
    """
    print >> stderr, '+ ./mapnik2.sh'
    mapnik2 = Popen('./mapnik2.sh')
    mapnik2.wait()

def get_shapefile_tablename(filepath):
    """
    """
    filename = basename(filepath)
    
    if filename == 'tile-drawer.osm2psgsql-polygon.shp':
        return 'planet_osm_polygon'
    
    elif filename == 'tile-drawer.osm2psgsql-point.shp':
        return 'planet_osm_point'
    
    elif filename == 'tile-drawer.osm2psgsql-line.shp':
        return 'planet_osm_line'
    
    elif filename == 'tile-drawer.imposm-admin.shp':
        return 'imposm_admin'
    
    elif filename == 'tile-drawer.imposm-aeroways.shp':
        return 'imposm_aeroways'
    
    elif filename == 'tile-drawer.imposm-amenities.shp':
        return 'imposm_amenities'
    
    elif filename == 'tile-drawer.imposm-buildings.shp':
        return 'imposm_buildings'
    
    elif filename == 'tile-drawer.imposm-landusages-gen0.shp':
        return 'imposm_landusages_gen0'
    
    elif filename == 'tile-drawer.imposm-landusages-gen1.shp':
        return 'imposm_landusages_gen1'
    
    elif filename == 'tile-drawer.imposm-landusages.shp':
        return 'imposm_landusages'
    
    elif filename == 'tile-drawer.imposm-mainroads-gen0.shp':
        return 'imposm_mainroads_gen0'
    
    elif filename == 'tile-drawer.imposm-mainroads-gen1.shp':
        return 'imposm_mainroads_gen1'
    
    elif filename == 'tile-drawer.imposm-mainroads.shp':
        return 'imposm_mainroads'
    
    elif filename == 'tile-drawer.imposm-minorroads.shp':
        return 'imposm_minorroads'
    
    elif filename == 'tile-drawer.imposm-motorways-gen0.shp':
        return 'imposm_motorways_gen0'
    
    elif filename == 'tile-drawer.imposm-motorways-gen1.shp':
        return 'imposm_motorways_gen1'
    
    elif filename == 'tile-drawer.imposm-motorways.shp':
        return 'imposm_motorways'
    
    elif filename == 'tile-drawer.imposm-places.shp':
        return 'imposm_places'
    
    elif filename == 'tile-drawer.imposm-railways-gen0.shp':
        return 'imposm_railways_gen0'
    
    elif filename == 'tile-drawer.imposm-railways-gen1.shp':
        return 'imposm_railways_gen1'
    
    elif filename == 'tile-drawer.imposm-railways.shp':
        return 'imposm_railways'
    
    elif filename == 'tile-drawer.imposm-roads-gen0.shp':
        return 'imposm_roads_gen0'
    
    elif filename == 'tile-drawer.imposm-roads-gen1.shp':
        return 'imposm_roads_gen1'
    
    elif filename == 'tile-drawer.imposm-roads.shp':
        return 'imposm_roads'
    
    elif filename == 'tile-drawer.imposm-transport-areas.shp':
        return 'imposm_transport_areas'
    
    elif filename == 'tile-drawer.imposm-transport-points.shp':
        return 'imposm_transport_points'
    
    elif filename == 'tile-drawer.imposm-waterareas-gen0.shp':
        return 'imposm_waterareas_gen0'
    
    elif filename == 'tile-drawer.imposm-waterareas-gen1.shp':
        return 'imposm_waterareas_gen1'
    
    elif filename == 'tile-drawer.imposm-waterareas.shp':
        return 'imposm_waterareas'
    
    elif filename == 'tile-drawer.imposm-waterways.shp':
        return 'imposm_waterways'
    
    elif filename == 'tile-drawer.coastline.shp':
        return 'coastline'
    
    else:
        # wat
        return ''

def import_style_tilemill(url):
    """ Load a zipped-up stylesheet created from Tilemill.
    """
    
    archive = ZipFile(StringIO(urlopen(url).read()))
    xmlname = [name for name in archive.namelist() if name.endswith('.xml')][0]
    doc = parse(StringIO(archive.read(xmlname)))
    
    # Map shapefiles to PostGIS datasources.
    
    def add_parameter(datasource, parameter, value):
        SubElement(datasource, 'Parameter', dict(name=parameter)).text = value
    
    for layer in doc.findall('Layer'):
        for ds in layer.findall('Datasource'):
            params = dict( [(p.attrib['name'], p.text)
                            for p in ds.findall('Parameter')] )
            
            if params.get('type', None) == 'shape' and 'file' in params:
                ds.clear()

                add_parameter(ds, 'type', 'postgis')
                add_parameter(ds, 'host', 'localhost')
                add_parameter(ds, 'user', 'osm')
                add_parameter(ds, 'dbname', 'planet_osm')
                add_parameter(ds, 'table', get_shapefile_tablename(params['file']))
                add_parameter(ds, 'extent', '-20037508,-20037508,20037508,20037508')
                add_parameter(ds, 'estimate_extent', 'false')
    
    out = open('gunicorn/mapnik2.xml', 'w')
    out.write('<?xml version="1.0" encoding="utf-8"?>\n')
    doc.write(out)
    
    # Build a new TileStache configuration file.
    
    config = json.load(open('gunicorn/tilestache.cfg'))
    
    config['layers'] = {'tiles': {'provider': {}}}
    layer = config['layers']['tiles']
    
    layer['provider']['name'] = 'mapnik'
    layer['provider']['mapfile'] = 'mapnik2.xml'
    layer['bounds'] = dict(zip('south west north east'.split(), options.bbox))
    layer['bounds'].update(dict(low=0, high=18))
    layer['preview'] = dict(zoom=15, lat=(options.bbox[0]/2 + options.bbox[2]/2), lon=(options.bbox[1]/2 + options.bbox[3]/2))
    
    # Done.
    
    json.dump(config, open('gunicorn/tilestache.cfg', 'w'), indent=2)

def import_style_tdcfg(url):
    """ Load a Cascadenik style and its constituent pieces from a URL.
    """
    style = json.loads(urlopen(url).read())
    mapfile = urljoin(options.style, style['mapfile'])

    # Create a local style.xml file by way of a dummy mapnik.Map instance.
    
    mmap = mapnik.Map(1, 1)
    mmap.srs = epsg900913
    cascadenik.load_map(mmap, mapfile, 'gunicorn', verbose=False)
    mapnik.save_map(mmap, 'gunicorn/style.xml')
    
    # Build a new TileStache configuration file.
    
    config = json.load(open('gunicorn/tilestache.cfg'))
    
    config['layers'] = {'tiles': {'provider': {}}}
    layer = config['layers']['tiles']
    
    layer['provider']['name'] = 'mapnik'
    layer['provider']['mapfile'] = 'style.xml'
    layer['bounds'] = dict(zip('south west north east'.split(), options.bbox))
    layer['bounds'].update(dict(low=0, high=18))
    layer['preview'] = dict(zoom=15, lat=(options.bbox[0]/2 + options.bbox[2]/2), lon=(options.bbox[1]/2 + options.bbox[3]/2))
    
    # Apply various layer options.
    
    for (parameter, value) in style['layer'].items():
        if parameter == 'png options' and 'palette' in value:
            palette_url = urljoin(url, value['palette'])
            palette_data = urlopen(palette_url).read()
            palette_file = 'gunicorn/palette.act'
            
            print >> stderr, ' ', palette_file, '<--', palette_url
            
            open(palette_file, 'w').write(palette_data)
            value['palette'] = 'palette.act'
        
        layer[parameter] = value
    
    # Done.
    
    json.dump(config, open('gunicorn/tilestache.cfg', 'w'), indent=2)

def import_style_mml(url):
    """
    """
    # Create a local style.xml file by way of a dummy mapnik.Map instance.
    
    mmap = mapnik.Map(1, 1)
    mmap.srs = epsg900913
    cascadenik.load_map(mmap, url, 'gunicorn', verbose=False)
    mapnik.save_map(mmap, 'gunicorn/style.xml')
    
    # Build a new TileStache configuration file.
    
    config = json.load(open('gunicorn/tilestache.cfg'))
    
    config['layers'] = {'tiles': {'provider': {}}}
    layer = config['layers']['tiles']
    
    layer['provider']['name'] = 'mapnik'
    layer['provider']['mapfile'] = 'style.xml'
    layer['bounds'] = dict(zip('south west north east'.split(), options.bbox))
    layer['bounds'].update(dict(low=0, high=18))
    layer['preview'] = dict(zoom=15, lat=(options.bbox[0]/2 + options.bbox[2]/2), lon=(options.bbox[1]/2 + options.bbox[3]/2))
    
    # Done.
    
    json.dump(config, open('gunicorn/tilestache.cfg', 'w'), indent=2)

def update_status(message):
    """
    """
    status_file = open('/usr/local/tiledrawer/progress/status.txt', 'a')
    print >> status_file, strftime('%a %b %d %H:%M:%S %Z %Y'), message

if __name__ == '__main__':
    
    options, urls = parser.parse_args()
    
    if dirname(__file__):
        print >> stderr, '+ chdir', dirname(__file__)
        chdir(dirname(__file__))

    try:
        update_status('Preparing database (populate.py)')
        import_extract_osm2pgsql('postgres/init-data/null.osm')
        import_coastline('postgres/init-data/null.shp')
        
        update_status('Importing map style (populate.py)')
        import_style(options.style)
        
        update_status('Importing OpenStreetMap data (populate.py)')
        osm_files = map(download_file, urls)
        osm_filename = combine_extracts(options.bbox, osm_files)
        import_extract_osm2pgsql(osm_filename)
        import_extract_imposm(osm_filename)
        
        update_status('Importing coastline data (populate.py)')
        coast_filename = download_coastline()
        import_coastline(coast_filename, options.bbox)
        
    except:
        update_status('Something went wrong, sorry (populate.py)')
        exit(1)
    
    else:
        update_status('Finished (populate.py)')
