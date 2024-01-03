from datetime import datetime
import pytz

def is_dst():
    x = datetime(datetime.now().year, 1, 1, 0, 0, tzinfo=pytz.timezone('US/Eastern') )
    y = datetime.now(pytz.timezone('US/Eastern'))

    # if dst is in effect, their offsets will be different
    return not (y.utcoffset() == x.utcoffset())

print(is_dst())
