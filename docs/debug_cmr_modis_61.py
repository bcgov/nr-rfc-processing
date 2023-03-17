# figure out what needs to change to pivot from modis 6.0 to 6.1 product
# MOD10A1.A2023072.h10v03.061.2023074072724.hdf

# product code used for 6.0 product: MOD10A1.6

import cmr
import pprint
pp = pprint.PrettyPrinter(indent=4)

api = cmr.CollectionQuery()
collections = api.archive_center("LP DAAC").keyword("MOD10A*").get(5)
print(collections)

q = cmr.GranuleQuery()
prod, ver = 'MOD10A1', '61'
q.short_name(prod).version(ver)
bbox = [-140.977, 46.559, -112.3242, 63.134]
start_date = '2023-03-13'
end_date = '2023-03-15'

q.temporal(f"{start_date}T00:00:00Z", f"{end_date}T23:59:59Z")
if (len(bbox) >= 4):
    q.bounding_box(*bbox[:4])
_granules = q.get_all()
#print(_granules)
pp.pprint(_granules)
for gran in _granules:
    print(gran['producer_granule_id'], gran['time_end'], gran['time_start'])

# can use the code above to create code that determines if the data is available
# for the time range supplied.  In a nutshell if no granules are supplied for
# the time_end parameter than we can assume that the data has not been prepared
# for that date as of yet.
