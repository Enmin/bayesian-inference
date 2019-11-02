import sys, re, copy, itertools, os
sys.path.append(os.pardir)
import algorithm.parse as parse


def normalize(dist):
    return tuple(x * 1 / (sum(dist)) for x in dist)


def topoSort(net):
    variables = list(net.keys())
    variables.sort()
    variablesSet = set()  # used to mark variables
    variableList = []
    while len(variablesSet) < len(variables):
        for variable in variables:
            if variable not in variablesSet and all(parent in variablesSet for parent in net[variable]['parents']):
                # add the variable `v` into the set `s` iff
                # all parents of `v` are already in `s`.
                variablesSet.add(variable)
                variableList.append(variable)
    return variableList


def queryGiven(net, Y, e):
        if net[Y]['prob'] != -1:
            prob = net[Y]['prob'] if e[Y] else 1 - net[Y]['prob']

        # Y has at least 1 parent
        else:
            # get the value of parents of Y
            parents = tuple(e[p] for p in net[Y]['parents'])

            # query for prob of Y = y
            prob = net[Y]['condprob'][parents] if e[Y] else 1 - \
                                                                 net[Y][
                                                                     'condprob'][
                                                                     parents]
        return prob


def genPermutations(length):
    permutationsmemo = {}
    assert (length >= 0)
    if length in permutationsmemo:
        return permutationsmemo[length]
    else:
        perms = set()
        for comb in itertools.combinations_with_replacement([False, True],length):
            for perm in itertools.permutations(comb):
                perms.add(perm)
        perms = list(perms)
        # perms = [(False, False, False), (False, False, True), ...]
        assert (len(perms) == pow(2, length))
        permutationsmemo[length] = perms
    return perms


def makeFactor(net, var, factorvars, e):
    variables = factorvars[var]
    variables.sort()

    allvars = copy.deepcopy(net[var]['parents'])
    allvars.append(var)

    perms = genPermutations(len(allvars))

    entries = {}
    asg = {}
    for perm in perms:
        violate = False
        for pair in zip(allvars, perm):  # tuples of ('var', value)
            if pair[0] in e and e[pair[0]] != pair[1]:
                violate = True
                break
            asg[pair[0]] = pair[1]

        if violate:
            continue
        key = tuple(asg[v] for v in variables)
        prob = queryGiven(net, var, asg)
        entries[key] = prob
    return (variables, entries)


def pointwise(var, factor1, factor2):
    newvariables = []
    newvariables.extend(factor1[0])
    newvariables.extend(factor2[0])
    newvariables = list(set(newvariables))
    newvariables.sort()

    perms = genPermutations(len(newvariables))
    newtable = {}
    asg = {}
    for perm in perms:
        for pair in zip(newvariables, perm):
            asg[pair[0]] = pair[1]
        key = tuple(asg[v] for v in newvariables)
        key1 = tuple(asg[v] for v in factor1[0])
        key2 = tuple(asg[v] for v in factor2[0])
        prob = factor1[1][key1] * factor2[1][key2]
        newtable[key] = prob
    return (newvariables, newtable)


def sumOut(var, factors):
    pwfactors = []  # list of factors containing var
    indices = []
    for i, factor in enumerate(factors):
        if var in factor[0]:
            pwfactors.append(factor)
            indices.append(i)
    if len(pwfactors) > 1:
        for i in reversed(indices):
            del factors[i]
        result = pwfactors[0]
        for factor in pwfactors[1:]:
            result = pointwise(var, result, factor)
        factors.append(result)

    for i, factor in enumerate(factors):
        for j, v in enumerate(factor[0]):
            if v == var:
                newvariables = factor[0][:j] + factor[0][j + 1:]
                newentries = {}
                for entry in factor[1]:
                    entry = list(entry)
                    newkey = tuple(entry[:j] + entry[j + 1:])

                    entry[j] = True
                    prob1 = factor[1][tuple(entry)]
                    entry[j] = False
                    prob2 = factor[1][tuple(entry)]
                    prob = prob1 + prob2

                    newentries[newkey] = prob
                factors[i] = (newvariables, newentries)
                if len(newvariables) == 0:
                    del factors[i]
    return factors


def enum_ask(net, X, e):
    dist = []
    for x in [False, True]:
        e = copy.deepcopy(e)
        e[X] = x

        variables = topoSort(net)

            # enumerate
        dist.append(enum_all(net, variables, e))

        # normalize & return
    return normalize(dist)


def enum_all(net, variables, e):
    if len(variables) == 0:
        return 1.0
    Y = variables[0]
    if Y in e:
        ret = queryGiven(net, Y, e) * enum_all(net, variables[1:], e)
    else:
        probs = []
        e2 = copy.deepcopy(e)
        for y in [True, False]:
            e2[Y] = y
            probs.append(
                queryGiven(net, Y, e2) * enum_all(net, variables[1:], e2))
        ret = sum(probs)

    print("%-14s | %-20s = %.8f" % (
        ' '.join(variables),
        ' '.join('%s=%s' % (v, 't' if e[v] else 'f') for v in e),
        ret
    ))
    return ret


def elim_ask(net, X, e):
    eliminated = set()
    factors = []

    while len(eliminated) < len(net):
        variables = filter(lambda v: v not in eliminated,
                            list(net.keys()))

        variables = filter(
            lambda v: all(c in eliminated for c in net[v]['children']),variables)

        factorvars = {}
        for v in variables:
            factorvars[v] = [p for p in net[v]['parents'] if p not in e]  # and p != X]
            if v not in e:  # and v != X:
                factorvars[v].append(v)

        var = sorted(factorvars.keys(), key=(lambda x: (len(factorvars[x]), x)))[0]
        print('----- Variable: %s -----' % var)

        if len(factorvars[var]) > 0:
            factors.append(makeFactor(var, factorvars, e, net))

        if var != X and var not in e:
            factors = sumOut(var, factors)

        eliminated.add(var)
        print('Factors:')
        for factor in factors:
            asg = {}
            perms = list(genPermutations(len(factor[0])))
            perms.sort()
            for perm in perms:
                for pair in zip(factor[0], perm):
                    asg[pair[0]] = pair[1]
                key = tuple(asg[v] for v in factor[0])
                print('%s: %.4f' % (
                    ' '.join('%s=%s' % (k, 't' if asg[k] else 'f') for k in
                             sorted(asg.keys())),
                    factor[1][key]
                ))
            print()

    if len(factors) >= 2:
        result = factors[0]
        for factor in factors[1:]:
            result = pointwise(var, result, factor)
    else:
        result = factors[0]
    return normalize((result[1][(False,)], result[1][(True,)]))


def query(fname, alg, q):

    # construct the net from the given file name
    try:
        net = parse.buildNet(fname)
    except:
        print('Failed to parse %s' % fname)
        exit()

    # parse the given query
    match = re.match(r'P\((.*)\|(.*)\)', q)
    if match:
        X = match.group(1).strip()
        e = match.group(2).strip().split(',')
        edict = dict((x[0], True if x[2] == 't' else False) for x in e)
    else:
        match = re.match(r'P\((.*)\)', q)
        X = match.group(1).strip()
        e = []
        edict = {}

    # call the appropriate function
    dist = enum_ask(net, X, edict) if alg == 'enum' else elim_ask(net, X, edict)
    print("\nRESULT:")
    for prob, x in zip(dist, [False, True]):
        print("P(%s = %s | %s) = %.4f" %
              (X,
               't' if x else 'f',
               ', '.join('%s = %s' % tuple(v.split('=')) for v in e),
               prob))


def main():
    try:
        fname = sys.argv[1]

        alg = sys.argv[2]
        assert (alg == 'enum' or alg == 'elim')

        q = sys.argv[3]
    except SyntaxError:
        print('Invalid syntax for bayes net file %s' % sys.argv[1])
    except IndexError:
        print('Not enough argument.')
        print('Usage: %s <bayesnet> <enum|elim> <query>' % sys.argv[0])
    query(fname, alg, q)


if __name__ == '__main__':
    # import doctest
    # doctest.testmod()
    query('/home/enminz/Research/Bayesian Network/unittest/testGraphs/alarm.bn', 'enum', 'A')