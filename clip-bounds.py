from urllib import urlopen
from httplib import HTTPConnection
from urlparse import urlparse, urljoin
from StringIO import StringIO
from tarfile import TarFile
from gzip import GzipFile
from csv import DictReader

from shapely.geometry import MultiPolygon, Polygon
from psycopg2 import connect

def size_and_date(href):
    """ Get Content-Length and Last-Modified for a URL.
    """
    s, host, path, p, q, f = urlparse(href)
    
    conn = HTTPConnection(host, 80)
    conn.request('HEAD', path)
    resp = conn.getresponse()
    
    if resp.status != 200:
        raise IOError('not found')
    
    content_length = resp.getheader('content-length')
    last_modified = resp.getheader('last-modified')
    
    return content_length, last_modified

def parse_poly(lines):
    """ Parse an Osmosis polygon filter file.

        http://wiki.openstreetmap.org/wiki/Osmosis/Polygon_Filter_File_Format
    """
    in_ring = False
    coords = []
    
    for (index, line) in enumerate(lines):
        if index == 0:
            # first line is junk.
            continue
        
        elif index == 1:
            # second line is the first polygon ring.
            coords.append([[], []])
            ring = coords[-1][0]
            in_ring = True
        
        elif in_ring and line.strip() == 'END':
            # we are at the end of a ring, perhaps with more to come.
            in_ring = False
    
        elif in_ring:
            # we are in a ring and picking up new coordinates.
            ring.append(map(float, line.split()))
    
        elif not in_ring and line.strip() == 'END':
            # we are at the end of the whole polygon.
            break
    
        elif not in_ring and line.startswith('!'):
            # we are at the start of a polygon part hole.
            coords[-1][1].append([])
            ring = coords[-1][1][-1]
            in_ring = True
    
        elif not in_ring:
            # we are at the start of a polygon part.
            coords.append([[], []])
            ring = coords[-1][0]
            in_ring = True
    
    return MultiPolygon(coords)

metro_url = 'http://metro.teczno.com/cities.txt'
metro_pattern = 'http://osm-metro-extracts.s3.amazonaws.com/%s.osm.pbf'

gf_url = 'http://download.geofabrik.de/clipbounds/clipbounds.tgz'
gf_base_href = 'http://download.geofabrik.de/osm/'

if __name__ != '__main__':
    # don't import me, I'm expensive
    exit()



extracts = []

metro_list = StringIO(urlopen(metro_url).read())
metro_list = DictReader(metro_list, dialect='excel-tab')

for city in metro_list:
    extract_href = metro_pattern % city['slug']
    
    try:
        content_length, last_modified = size_and_date(extract_href)
        print extract_href

    except IOError:
        print 'Failed', extract_href
        continue
    
    y1, x1, y2, x2 = [float(city[key]) for key in ('top', 'left', 'bottom', 'right')]
    shape = Polygon([(x1, y1), (x2, y1), (x2, y2), (x1, y2), (x1, y1)])
    
    extracts.append((extract_href, content_length, last_modified, shape))



gf_archive = StringIO(urlopen(gf_url).read())
gf_archive = GzipFile(fileobj=gf_archive)
gf_archive = TarFile(fileobj=gf_archive)

for member in gf_archive.getmembers():
    if not member.name.endswith('.poly'):
        continue
    
    extract_path = member.name[:-5] + '.osm.pbf'
    extract_href = urljoin(gf_base_href, extract_path)
    
    try:
        content_length, last_modified = size_and_date(extract_href)
        print extract_href

    except IOError:
        print 'Failed', extract_href
        continue
    
    lines = list(gf_archive.extractfile(member))
    shape = parse_poly(lines)
    
    extracts.append((extract_href, content_length, last_modified, shape))



db = connect(database='tiledrawer', user='tiledrawer').cursor()

db.execute('BEGIN')
db.execute('DELETE FROM extracts')

for (href, size, date, shape) in extracts:
    db.execute("""INSERT INTO extracts (href, size, date, geom)
                  VALUES (%s, %s, %s, SetSRID(Multi(GeomFromText(%s)), 4326))""",
               (href, size, date, str(shape)))

db.execute('COMMIT')