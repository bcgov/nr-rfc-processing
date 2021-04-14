import datetime
import sys
now = datetime.datetime.now()
nowstr = now.strftime ('%Y.%m.%d')
sys.stdout.write(nowstr)
