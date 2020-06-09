import sys
from Lambda.dms_lambda.app.util.dms_util import *

# from ..app.util.dms_util import *

dms_util = DmsUtil()
print(str(dms_util.is_existing_endpoint('sourceEndpoint')))
