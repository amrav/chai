#!/usr/bin/env python

import argparse
import re
import indianrail as ir
import sys
import networkx as nx

def main():
    p = argparse.ArgumentParser(description="A command line tool to help book tickets on the Indian Railways.")
    p.add_argument("-v", "--verbose", help="turn on verbose mode",
                   action='store_false', dest='verbose', default=False)
    sp = p.add_subparsers(help="sub-command help")

    p.add_argument("-t", "--train_no", help="train number", required=True, dest='train_no')
    p.add_argument("-s", "--src", help="source station code", required=True, dest='src')
    p.add_argument("-d", "--dst", help="destination station code", required=True, dest='dst')
    p.add_argument("-D", "--day", help="day of travel (dd)", required=True, dest='day')
    p.add_argument("-m", "--month", help="month of travel (mm)", required=True, dest='month')
    p.add_argument("-c", "--class", help="class of travel",
                            choices=['1A', '2A', '3A', 'SL', 'CC'], default='3A', dest='class_')
    p.add_argument("-q", "--quota", help="class code",
                   choices=['GN', 'CK'], default='GN', dest='quota')

    def _optimize(args):
        optimize(args.train_no, args.src, args.dst, args.day, args.month, args.class_, args.quota)

    def _get_avail(args):
        print ir.get_avail(args.train_no, args.src, args.dst, args.day, args.month, args.class_, args.quota)

    p_availability = sp.add_parser('avail', help="find availability between two stations")
    p_optimize = sp.add_parser('optimize', help="calculate the best possible route to take between two stations")

    p_optimize.set_defaults(func=_optimize)
    p_availability.set_defaults(func=_get_avail)

    args = p.parse_args()

    args.func(args)

def cost_tuple(v1, v2, avail, indices):
    #if v1 is ahead of v2
    if (indices[v1] >= indices[v2]):
        return (0, 0, 10 * (indices[v1] - indices[v2]))
    elif re.match("AVAILABLE", avail[v1][v2]):
        return (0, 0, 1)
    elif re.match("RAC", avail[v1][v2]):
        return (0, 1, 0)
    wl = re.findall('/WL(\d+)', avail[v1][v2])
    if len(wl) == 1:
        return (int(wl[0]), indices[v2] - indices[v1], 0)
    else:
        return (float("inf"), 0, 0)

def numerical_cost(cost_tuple):
    LARGE_BASE = 100
    return (LARGE_BASE*LARGE_BASE) * cost_tuple[0] + LARGE_BASE * cost_tuple[1] + cost_tuple[2]

def shortest_path(src, dst, names, cost):
    G = nx.DiGraph()
    G.add_nodes_from(names)

    indices = {}
    for i in range(len(names)):
        indices[names[i]] = i

    # Add edges from src to stations before it
    for i in range(indices[src]):
        G.add_edge(src, names[i],
                   weight=cost(src, names[i]))
    # Add edges from stations after dst to dst
    for i in range(indices[dst] + 1, len(names)):
        G.add_edge(names[i], dst, weight=cost(names[i], dst))
    # Add reverse edges from every station after src back
    for i in range(indices[src] + 1, len(names)):
        for j in range(indices[src] + 1, i):
            G.add_edge(names[i], names[j], weight=cost(names[i], names[j]))
    # Add edges from every station before dst to
    # every station after src
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            if i >= indices[dst] or j <= indices[src]:
                continue
            G.add_edge(names[i], names[j],
                       weight=cost(names[i], names[j]))
    nx.write_multiline_adjlist(G, "test.adjlist")
    return nx.shortest_path(G, src, dst, weight='weight')

def optimize(train_no, src, dst, day, month, class_, quota):
    sys.stdout.write("Fetching stations on route... ")
    sys.stdout.flush()
    stations = ir.get_stations(train_no)
    print "done."

    if (src not in stations['names'] or dst not in stations['names']):
        print "%s not in route of train %s. Aborting." \
            %(src if src not in stations['names'] else dst, train_no)
        sys.exit(1)

    indices = {}
    for i in range(len(stations['names'])):
        indices[stations['names'][i]] = i

    avail = ir.get_all_avail(train_no, day, month, class_, quota, stations)

    def cost(src, dst):
        return numerical_cost(cost_tuple(src, dst, avail, indices))

    print_plan(shortest_path(src, dst, stations['names'], cost), avail, indices)

def print_plan(shortest_path, avail, indices):
    src = shortest_path[0]
    dst = shortest_path[-1]
    print "Best plan is: "
    for i in range(len(shortest_path) - 1):
        print shortest_path[i], " --> ", shortest_path[i + 1],
        print "(", indices[shortest_path[i + 1]] - indices[shortest_path[i]], " stations )",
        if (indices[shortest_path[i+1]] > indices[shortest_path[i]]):
            print ":", avail[shortest_path[i]][shortest_path[i+1]]
        else:
            if indices[shortest_path[i+1]] < indices[src]:
                print ":", "Get on at %s" %shortest_path[i]
            elif shortest_path[i + 1] == dst:
                print ":", "Get off at %s" %shortest_path[i+1]
            else:
                print ":", "Switch at %s" %shortest_path[i+1]

if __name__ == '__main__':
    main()
