import re, sys, os
sys.path.append(os.pardir)
import algorithm.parse as parse
from exactInference import enumerateAsk, eliminateAsk


def query(fname, method, query):

    try:
        net = parse.buildNet(fname)
    except:
        print('Failed to parse %s' % fname)
        exit()

    match = re.match(r'P\((.*)\|(.*)\)', query)
    if match:
        X = match.group(1).strip()
        e = match.group(2).strip().split(',')
        edict = dict((x[0], True if x[2] == 't' else False) for x in e)
    else:
        match = re.match(r'P\((.*)\)', query)
        X = match.group(1).strip()
        e = []
        edict = {}

    dist = enumerateAsk(net, X, edict) if method == 'enum' else eliminateAsk(net, X, edict)
    print("\nRESULT:")
    for prob, x in zip(dist, [False, True]):
        print("P(%s = %s | %s) = %.4f" % (X, 't' if x else 'f', ', '.join(
            '%s = %s' % tuple(v.split('=')) for v in e), prob))


if __name__ == '__main__':
    query('/home/enminz/Research/Bayesian Network/unittest/testGraphs/alarm.bn',
          'elim', 'P(B|J=t,M=t)')