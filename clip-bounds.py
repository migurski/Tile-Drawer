from urllib import urlopen
from urlparse import urljoin
from StringIO import StringIO
from tarfile import TarFile
from gzip import GzipFile

from shapely.geometry import MultiPolygon

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

for member in archive.getmembers():
    if not member.name.endswith('.poly'):
        continue
    
    extract_path = member.name[:-5] + '.osm.pbf'
    extract_href = urljoin(base_href, extract_path)
    
    print extract_href
    
    lines = list(archive.extractfile(member))
    shape = parse_poly(lines)
