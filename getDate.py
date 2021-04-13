import datetime
import sys
now = datetime.datetime.now()
nowstr = now.strftime ('%Y.%M.%d')
sys.stdout.write(nowstr)
