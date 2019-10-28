import re

def parse(net, lines):
    if len(lines) == 1:
        # single line node/buffer
        match = re.match(r'P\((.*)\) = (.*)\n', lines[0])
        var, prob = match.group(1).strip(), float(match.group(2).strip())
        net[var] = {
            'parents': [],
            'children': [],
            'prob': prob,
            'condprob': {}
        }
    else:
        # multi line node/buffer
        # table header
        match = re.match(r'(.*) \| (.*)', lines[0])
        parents, var = match.group(1).split(), match.group(2).strip()
        for p in parents:
            net[p]['children'].append(var)
        net[var] = {
            'parents': parents,
            'children': [],
            'prob': -1,
            'condprob': {}
        }
        # table rows/distributions
        for probline in lines[2:]:
            match = re.match(r'(.*) \| (.*)', probline)
            truth, prob = match.group(1).split(), float(
                match.group(2).strip())
            truth = tuple(True if x == 't' else False for x in truth)
            net[var]['condprob'][truth] = prob
    return net


def buildNet(fname):
    net = {}
    lines = []  # buffer
    with open(fname) as f:
        for line in f:
            if line == '\n':
                # parse the buffer if encounter a blank line
                net = parse(net, lines)
                lines = []
            else:
                lines.append(line)
    if len(lines) != 0:
        net = parse(net, lines)
    return net