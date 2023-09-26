"""
###############################################################################
# Copyright 2019-2021 CERN. See the COPYRIGHT file at the top-level directory
# of this distribution. For licensing information, see the COPYING file at
# the top-level directory of this distribution.
###############################################################################
"""
import json
import logging
import multiprocessing
import os
import random
from os import path

UNITS = {'HS06': 1., 'SI00': 1. / 344.}

_log = logging.getLogger(__name__)


def get_cpu_normalization(i, reference='HS06', iterations=1):
    """
    Get Normalized Power of the current CPU in [reference] units
    """
    if reference not in UNITS:
        print(f'Unknown Normalization unit {str(reference)}')

    # return S_ERROR( 'Unknown Normalization unit %s' % str( reference ) )

    try:
        iter = max(min(int(iterations), 10), 1)
    except (TypeError, ValueError) as e:
        print(e)

    # return S_ERROR( x )

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
    # wall = end[4] - start[4]

    # if not cput:
    #     return S_ERROR( 'Can not get used CPU' )

    return calib * iterations / cput

    # print( {'CPU': cput, 'WALL':wall, 'NORM': calib * iterations / cput, 'UNIT': reference } )
    # return S_OK({'CPU': cput, 'WALL':wall, 'NORM': calib * iterations / cput, 'UNIT': reference })


def run_db12(rundir=".", cpu_num=multiprocessing.cpu_count(), reference='HS06'):
    """
    Runs DB12 Benchmark and outputs result.

    Args:
      rundir:  The running directory of benchmark
      cpu_num: The number of CPUs allowed for benchmark

    Returns:
      A dict containing DB12 result { 'DB12': { 'value': SCORE, 'unit': "est. {REFERENCE}"} }
    """

    _log.debug("Running DB12 with rundir=%s cpu_num=%s", rundir, cpu_num)

    cores = int(cpu_num)
    with multiprocessing.Pool(processes=cores) as pool:
        result = {
            'DB12': {
                'value': (float(sum(pool.map(get_cpu_normalization, range(cores))))),
                'unit': f"est. {reference}"
            }
        }

    # Save result to json
    # Change encoding in python >= 3.10 [https://peps.python.org/pep-0597/#encoding-locale]
    with open(path.join(rundir, 'db12_result.json'), 'w', encoding='utf8') as fout:
        json.dump(result, fout)

    _log.debug("Result from DB12: %s", result)

    return result
