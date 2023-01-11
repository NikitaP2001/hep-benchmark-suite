#!/bin/python

import sys
import json
from dictdiffer import diff

json_list = []
for ajson in sys.argv[1:3]:
    print("Reading file %s" % ajson)
    json_list.append( json.load(open(ajson)) )
        
ignore_set=None
if len(sys.argv)>3:
    ignore_set = json.loads(sys.argv[3])
result = list(diff(json_list[0], json_list[1], ignore=ignore_set))

for entry in result:
    if len(entry[2]) == 1:
        print('\n\t %s :\n\t\t %s\t%s' % entry)
    else:
        print('\n\t %s :\n\t\t %s\n\t\t\t%s\n\t\t\t%s' % (entry[0], entry[1], entry[2][0], entry[2][1]))
        
exit(len(result))

