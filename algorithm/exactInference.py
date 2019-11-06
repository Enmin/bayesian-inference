import copy
import itertools


def normalize(dist):
    return tuple(x * 1 / (sum(dist)) for x in dist)


def topoSort(net):
    variables = list(net.keys())
    variables.sort()
    variablesSet = set()  # used to mark variables
    variableList = []
    while len(variablesSet) < len(variables):
        for variable in variables:
            if variable not in variablesSet and all(
                    parent in variablesSet
                    for parent in net[variable]['parents']):
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
        prob = net[Y]['condprob'][parents] if e[
            Y] else 1 - net[Y]['condprob'][parents]
    return prob


def generatePermutations(length):
    permutationsmemo = {}
    assert (length >= 0)
    if length in permutationsmemo:
        return permutationsmemo[length]
    else:
        perms = set()
        for comb in itertools.combinations_with_replacement([False, True],
                                                            length):
            for perm in itertools.permutations(comb):
                perms.add(perm)
        perms = list(perms)
        # perms = [(False, False, False), (False, False, True), ...]
        assert (len(perms) == pow(2, length))

        permutationsmemo[length] = perms
        return perms


def makeFactor(net, var, factorVars, e):
    variables = factorVars[var]
    variables.sort()
    allvars = copy.deepcopy(net[var]['parents'])
    allvars.append(var)
    perms = generatePermutations(len(allvars))
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


def pointwise(factor1, factor2):
    newvariables = []
    newvariables.extend(factor1[0])
    newvariables.extend(factor2[0])
    newvariables = list(set(newvariables))
    newvariables.sort()

    perms = generatePermutations(len(newvariables))
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
    for fIndex, factor in enumerate(factors):
        if var in factor[0]:
            pwfactors.append(factor)
            indices.append(fIndex)
    if len(pwfactors) > 1:
        for index in reversed(indices):
            del factors[index]
        result = pwfactors[0]
        for factor in pwfactors[1:]:
            result = pointwise(result, factor)
        factors.append(result)

    for fIndex, factor in enumerate(factors):
        for vIndex, v in enumerate(factor[0]):
            # if the variable is hidden
            if v == var:
                # variable list of the new factor
                newVariables = factor[0][:vIndex] + factor[0][vIndex + 1:]
                # probability table of the new factor
                newEntries = {}
                for entry in factor[1]:
                    entry = list(entry)
                    newkey = tuple(entry[:vIndex] + entry[vIndex + 1:])

                    entry[vIndex] = True
                    prob1 = factor[1][tuple(entry)]
                    entry[vIndex] = False
                    prob2 = factor[1][tuple(entry)]
                    prob = prob1 + prob2

                    newEntries[newkey] = prob

                # replace the old factor
                factors[fIndex] = (newVariables, newEntries)
                if len(newVariables) == 0:
                    del factors[fIndex]
    return factors


def enumerateAsk(net, X, e):
    dist = []
    for x in [False, True]:
        e = copy.deepcopy(e)
        e[X] = x
        variables = topoSort(net)
        # enumerate
        dist.append(enumrateAll(net, variables, e))
    return normalize(dist)


def enumrateAll(net, variables, e):
    if len(variables) == 0:
        return 1.0
    Y = variables[0]
    if Y in e:
        ret = queryGiven(net, Y, e) * enumrateAll(net, variables[1:], e)
    else:
        probs = []
        e2 = copy.deepcopy(e)
        for y in [True, False]:
            e2[Y] = y
            probs.append(
                queryGiven(net, Y, e2) * enumrateAll(net, variables[1:], e2))
        ret = sum(probs)
    print("%-14s | %-20s = %.8f" % (' '.join(variables), ' '.join(
        '%s=%s' % (v, 't' if e[v] else 'f') for v in e), ret))
    return ret


def eliminateAsk(net, X, e):
    eliminated = set()
    factors = []
    while len(eliminated) < len(net):
        variables = filter(lambda v: v not in eliminated, list(net.keys()))
        variables = filter(
            lambda v: all(c in eliminated for c in net[v]['children']),
            variables)
        factorvars = {}
        for v in variables:
            factorvars[v] = [p for p in net[v]['parents'] if p not in e]
            if v not in e:
                factorvars[v].append(v)
        var = sorted(factorvars.keys(),
                     key=(lambda x: (len(factorvars[x]), x)))[0]
        print('----- Variable: %s -----' % var)
        if len(factorvars[var]) > 0:
            factors.append(makeFactor(net, var, factorvars, e))
        if var != X and var not in e:
            factors = sumOut(var, factors)
        eliminated.add(var)
        print('Factors:')
        for factor in factors:
            asg = {}
            perms = list(generatePermutations(len(factor[0])))
            perms.sort()
            for perm in perms:
                for pair in zip(factor[0], perm):
                    asg[pair[0]] = pair[1]
                key = tuple(asg[v] for v in factor[0])
                print('%s: %.4f' %
                      (' '.join('%s=%s' % (k, 't' if asg[k] else 'f')
                                for k in sorted(asg.keys())), factor[1][key]))
    if len(factors) >= 2:
        result = factors[0]
        for factor in factors[1:]:
            result = pointwise(result, factor)
    else:
        result = factors[0]
    return normalize((result[1][(False,)], result[1][(True,)]))
