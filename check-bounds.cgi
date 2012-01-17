#!/usr/bin/env python

from sys import stdin, stdout
from urlparse import parse_qsl
from itertools import chain, combinations
from os.path import dirname, basename, join
from os import close, environ, chmod
from tempfile import mkstemp

from psycopg2 import connect
from shapely.wkb import loads
from shapely.geometry import Polygon

form = dict(parse_qsl(stdin.read()))
x1, y1, x2, y2 = [float(form[key]) for key in 'west south east north'.split()]
bbox = Polygon([(x1, y1), (x2, y1), (x2, y2), (x1, y2), (x1, y1)])
style = form['style']

def nice_size(size):
    KB = 1024.
    MB = 1024. * KB
    GB = 1024. * MB
    TB = 1024. * GB
    
    if size < KB:
        size, suffix = size, ''
    elif size < MB:
        size, suffix = size/KB, 'KB'
    elif size < GB:
        size, suffix = size/MB, 'MB'
    elif size < TB:
        size, suffix = size/GB, 'GB'
    else:
        size, suffix = size/TB, 'TB'
    
    if size < 10:
        return '%.1f %s' % (size, suffix)
    else:
        return '%d %s' % (size, suffix)

def eval_selection(bbox, extracts):
    """
    """
    hrefs, sizes, polys = zip(*extracts)
    
    try:
        union = reduce(lambda a, b: a.union(b), polys)
        remainder = bbox.difference(union)
        size = sum(sizes)
    
    except Exception, e:
        return float('inf'), 0, []
    
    else:
        return size, remainder.area, hrefs

db = connect(database='tiledrawer', user='tiledrawer').cursor()

db.execute("""SELECT href, size, AsBinary(geom)
              FROM extracts,
              (
                SELECT SetSRID(GeomFromText(%s), 4326) AS bbox
              ) AS bbox
              WHERE geom && bbox
                AND Intersects(geom, bbox)
                AND Area(geom) > Area(bbox)/4""", 
           (str(bbox), ))

extracts = [(href, size, loads(str(geom))) for (href, size, geom) in db.fetchall()]

db.close()

# generate a list of possible combinations of extracts
selections = chain(*[combinations(extracts, length+1) for length in range(len(extracts))])

# measure each selection's total size and uncovered area
selections = [eval_selection(bbox, selection) for selection in selections]

# find the smallest download that covers the area we want
selections = [(size, hrefs) for (size, left, hrefs) in sorted(selections) if left == 0]

#

size, href_list = selections[0]
bounds = '%.4f %.4f %.4f %.4f' % (bbox.bounds[1], bbox.bounds[0], bbox.bounds[3], bbox.bounds[2])
hrefs = ' '.join(href_list)

directory = join(dirname(__file__), 'scripts')
handle, filename = mkstemp(dir=directory, prefix='script-', suffix='.sh.txt')
close(handle)

chmod(filename, 0666)
script = open(filename, 'w')

print >> script, 'apt-get -y install git htop'
print >> script, 'git clone -b config http://linode.teczno.com/~migurski/tiledrawer/.git/ /usr/local/tiledrawer'
print >> script, '/usr/local/tiledrawer/setup.sh'
print >> script, '/usr/local/tiledrawer/populate.py -b %(bounds)s -s %(style)s %(hrefs)s' % locals()
print >> script, '/usr/local/tiledrawer/draw.sh'

print >> stdout, 'X-Extract-Count: %s' % len(href_list)
print >> stdout, 'X-Extract-Size: %s' % nice_size(size)
print >> stdout, 'Content-Type: text/plain\n'
print >> stdout, '#!/bin/sh -ex\n# Download %s of OSM data from %s extract%s.\ncurl -s http://%s%s/scripts/%s | /bin/sh -ex' % (nice_size(size), len(href_list), len(href_list) > 1 and 's' or '', environ['HTTP_HOST'], dirname(environ['SCRIPT_NAME']), basename(filename))
