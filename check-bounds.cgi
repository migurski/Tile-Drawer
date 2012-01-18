#!/usr/bin/env python

from sys import stdin, stdout
from urlparse import parse_qsl
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

def find_selections(open_shape, new_extracts, working_set=[], selections=[]):
    """ Get a list of valid extract selections for a shape and a list of extracts.
    
        A valid selection is a list of extracts that completely covers the
        shape with no leftover areas. Selections are returned as a list of
        (size, hrefs) tuples, each a total byte size and list of URLs.
        
        For the sake of speed, don't exhaust the whole search space and stop
        once a reasonable list of selections has been found.
    """
    if len(selections) >= 64:
        # We have enough to work with.
        return
    
    if len(new_extracts) == 0:
        # There are no more extracts to look at.
        return
    
    # Pop a fresh extract from the front of the list of new extracts.
    (href, size, extract_shape), new_extracts = new_extracts[0], new_extracts[1:]
    
    new_working_set = working_set[:] + [(href, size, extract_shape)]

    if open_shape.within(extract_shape):
        # The uncovered area is covered up by new extract, yay!
        # Add it to our list of good-enough selections.

        hrefs, sizes, geoms = zip(*new_working_set)
        selection = sum(sizes), hrefs
        selections.append(selection)
    
    elif open_shape.disjoint(extract_shape) or open_shape.touches(extract_shape):
        # The extract won't meaningfully affect the uncovered area.
        pass
    
    else:
        # The open_shape area is not covered up the next extract,
        # but it was at least partially obscured. Dig deeper.

        remaining_shape = open_shape.difference(extract_shape)
        find_selections(remaining_shape, new_extracts, new_working_set, selections)
    
    # Try looking deeper at other combinations without the new area.
    find_selections(open_shape, new_extracts, working_set, selections)
    
    return selections

db = connect(database='tiledrawer', user='tiledrawer').cursor()

db.execute("""SELECT href, size, AsBinary(geom)
              FROM extracts,
              (
                SELECT SetSRID(GeomFromText(%s), 4326) AS bbox
              ) AS bbox
              WHERE geom && bbox
                AND Intersects(geom, bbox)
                AND Area(geom) > Area(bbox)/4
                AND IsValid(geom)""", 
           (str(bbox), ))

extracts = [(href, size, loads(str(geom))) for (href, size, geom) in db.fetchall()]

db.close()

from sys import stderr

selections = sorted(find_selections(bbox, extracts))
size, href_list = selections[0]

bounds = '%.4f %.4f %.4f %.4f' % (bbox.bounds[1], bbox.bounds[0], bbox.bounds[3], bbox.bounds[2])
hrefs = ' '.join(href_list)

directory = join(dirname(__file__), 'scripts')
handle, filename = mkstemp(dir=directory, prefix='script-', suffix='.sh.txt')
close(handle)

chmod(filename, 0666)
script = open(filename, 'w')

print >> script, 'apt-get -y install git htop >> /var/log/tiledrawer.log 2>&1'
print >> script, 'git clone -b config http://tiledrawer.com/.git/ /usr/local/tiledrawer >> /var/log/tiledrawer.log 2>&1'
print >> script, '/usr/local/tiledrawer/setup.sh >> /var/log/tiledrawer.log 2>&1'
print >> script, '/usr/local/tiledrawer/populate.py -b %(bounds)s -s %(style)s %(hrefs)s >> /var/log/tiledrawer.log 2>&1' % locals()
print >> script, '/usr/local/tiledrawer/draw.sh >> /var/log/tiledrawer.log 2>&1'

print >> stdout, 'X-Extract-Count: %s' % len(href_list)
print >> stdout, 'X-Extract-Size: %s' % nice_size(size)
print >> stdout, 'Content-Type: text/plain\n'
print >> stdout, '#!/bin/sh -ex\n# Download %s of OSM data from %s extract%s.\ncurl -s http://%s%s/scripts/%s | /bin/sh -ex' % (nice_size(size), len(href_list), len(href_list) > 1 and 's' or '', environ['HTTP_HOST'], dirname(environ['SCRIPT_NAME']), basename(filename))
