#!/usr/bin/env python

from sys import stdin, stdout
from urlparse import parse_qsl
from itertools import chain, combinations

from psycopg2 import connect
from shapely.wkb import loads
from shapely.geometry import Polygon

bounds = dict(parse_qsl(stdin.read()))
x1, y1, x2, y2 = [float(bounds[key]) for key in 'west south east north'.split()]
bbox = Polygon([(x1, y1), (x2, y1), (x2, y2), (x1, y2), (x1, y1)])

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
selections = [hrefs for (size, left, hrefs) in sorted(selections) if left == 0]

#

hrefs = selections[0]

print >> stdout, 'Content-Type: text/plain\n'
print >> stdout, '%.4f %.4f %.4f %.4f' % (bbox.bounds[1], bbox.bounds[0], bbox.bounds[3], bbox.bounds[2]),
print >> stdout, ' '.join(hrefs)
