from urllib import urlopen
from httplib import HTTPConnection
from urlparse import urlparse, urljoin
from StringIO import StringIO
from tarfile import TarFile
from gzip import GzipFile

from shapely.geometry import MultiPolygon
from psycopg2 import connect

if __name__ != '__main__':
    # don't import me, I'm expensive
    exit()

url = 'http://download.geofabrik.de/clipbounds/clipbounds.tgz'
base_href = 'http://download.geofabrik.de/osm/'

archive = StringIO(urlopen(url).read())
archive = GzipFile(fileobj=archive)
archive = TarFile(fileobj=archive)

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

db = connect(database='tiledrawer', user='tiledrawer').cursor()

db.execute('BEGIN')
db.execute('DELETE FROM extracts')

for member in archive.getmembers():
    if not member.name.endswith('.poly'):
        continue
    
    extract_path = member.name[:-5] + '.osm.pbf'
    extract_href = urljoin(base_href, extract_path)
    
    print extract_href
    
    s, host, path, p, q, f = urlparse(extract_href)
    
    conn = HTTPConnection(host, 80)
    conn.request('HEAD', path)
    resp = conn.getresponse()
    
    content_length = resp.getheader('content-length')
    last_modified = resp.getheader('last-modified')
    
    lines = list(archive.extractfile(member))
    shape = parse_poly(lines)
    
    db.execute("""INSERT INTO extracts (href, size, date, geom)
                  VALUES (%s, %s, %s, SetSRID(GeomFromText(%s), 4326))""",
               (extract_href, content_length, last_modified, str(shape)))

db.execute('COMMIT')