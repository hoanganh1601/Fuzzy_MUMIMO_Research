import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/'code'))
from calibrate import upper
assert abs(upper(0,59,.05)- (1-.05**(1/59)))<1e-10
assert upper(0,58,.05)>.05
assert upper(0,59,.05)<.05
print('calibration UCB threshold checks passed')
