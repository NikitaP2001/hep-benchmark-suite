"""
###############################################################################
# Copyright 2019-2021 CERN. See the COPYRIGHT file at the top-level directory
# of this distribution. For licensing information, see the COPYING file at
# the top-level directory of this distribution.
###############################################################################
"""
import os
import json
import logging
import random
import multiprocessing

UNITS = {'HS06': 1., 'SI00': 1. / 344.}

_log = logging.getLogger(__name__)


def get_cpu_normalization(i, reference='HS06', iterations=1):
    """
    Get Normalized Power of the current CPU in [reference] units
    """
    if reference not in UNITS:
        print('Unknown Normalization unit %s' % str(reference))
    """
        return S_ERROR( 'Unknown Normalization unit %s' % str( reference ) )
    """
    try:
        iter = max(min(int(iterations), 10), 1)
    except (TypeError, ValueError) as x:
        print(x)
    """
        return S_ERROR( x )
    """

    # This number of iterations corresponds to 360 HS06 seconds
    n = int(1000 * 1000 * 12.5)
    calib = 360.0 / UNITS[reference]

    m = 0
    m2 = 0
    p = 0
    p2 = 0
    # Do one iteration extra to allow CPUs with variable speed
    for i in range(iterations + 1):
        if i == 1:
            start = os.times()
        # Now the iterations
        for j in range(n):
            t = random.normalvariate(10, 1)
            m += t
            m2 += t * t
            p += t
            p2 += t * t

    end = os.times()
    cput = sum(end[:4]) - sum(start[:4])
    wall = end[4] - start[4]

    """
    if not cput:
        return S_ERROR( 'Can not get used CPU' )
    """

    return calib * iterations / cput
    """
    print( {'CPU': cput, 'WALL':wall, 'NORM': calib * iterations / cput, 'UNIT': reference } )
    return S_OK( {'CPU': cput, 'WALL':wall, 'NORM': calib * iterations / cput, 'UNIT': reference } )
    """


def run_db12(rundir=".", cpu_num=multiprocessing.cpu_count(), reference='HS06'):
    """
    Runs DB12 Benchmark and outputs result.

    Args:
      rundir:  The running directory of benchmark
      cpu_num: The number of CPUs allowed for benchmark

    Returns:
      A dict containing DB12 result { 'DB12' : value }
    """

    _log.debug("Running DB12 with rundir={} cpu_num={}".format(rundir, cpu_num))

    cores = int(cpu_num)
    pool = multiprocessing.Pool(processes=cores)
    result = {}
    result['DB12'] = {
        'value': (float(sum(pool.map(get_cpu_normalization, range(cores))))),
        'unit': "est. {}".format(reference)
    }

    # Save result to json
    with open(os.path.join(rundir, 'db12_result.json'), 'w') as fout:
        json.dump(result, fout)

    _log.debug("Result from DB12: {} ".format(result))

    return result
