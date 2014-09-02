#!/usr/bin/env python

import argparse
import re
from irctc import IrctcClient as irctc
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

    def __optimize(args):
        optimize(args.train_no, args.src, args.dst, args.day, args.month, args.class_, args.quota)
        return
        optimize_(args.train_no, args.src, args.dst, args.day, args.month, args.class_, args.quota, args.verbose)

    def __get_avail(args):
        print irctc.get_avail(args.train_no, args.src, args.dst, args.day, args.month, args.class_, args.quota)

    p_availability = sp.add_parser('avail', help="find availability between two stations")
    p_optimize = sp.add_parser('optimize', help="calculate the best possible route to take between two stations")

    p_optimize.set_defaults(func=__optimize)
    p_availability.set_defaults(func=__get_avail)

    args = p.parse_args()

    args.func(args)

def __segment_cost(v1, v2, avail, indices):
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

def numerical_cost(segment_cost):
    LARGE_BASE = 100
    return (LARGE_BASE*LARGE_BASE) * segment_cost[0] + LARGE_BASE * segment_cost[1] + segment_cost[2]

def shortest_path(src, dst, names, cost):
    G = nx.DiGraph()
    G.add_nodes_from(names)
    G.add_nodes_from({name + "_" for name in names})
    indices = {}
    for i in range(len(names)):
        indices[names[i]] = i

    # Connect each node to its complement
    for name in names:
        G.add_edge(name + "_", name, weight=0)
    # Add edges from src to stations before it
    for i in range(indices[src]):
        G.add_edge(src, names[i],
                   weight=cost(src, names[i]))
    # Add edges from stations after dst to dst
    for i in range(indices[dst] + 1, len(names)):
        G.add_edge(names[i], dst, weight=cost(names[i], dst))
    # Add reverse edges from every station after src back
    # to complement stations
    for i in range(indices[src] + 1, len(names)):
        for j in range(indices[src] + 1, i):
            G.add_edge(names[i], names[j] + '_', weight=cost(names[i], names[j]))
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
    stations = irctc.get_stations(train_no)
    print "done."

    indices = {}
    for i in range(len(stations['names'])):
        indices[stations['names'][i]] = i

    avail = irctc.get_all_avail(train_no, day, month, class_, quota, stations)

    def cost(src, dst):
        return numerical_cost(__segment_cost(src, dst, avail, indices))

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
            else:
                print ":", "Get off at %s" %shortest_path[i+1]

def __cost_lt(cost1, cost2):
    for i in range(len(cost1)):
        if (cost1[i] < cost2[i]):
            return True
        elif (cost1[i] > cost2[i]):
            return False
    return False

def __cost_sum(cost1, cost2):
    return (cost1[0] + cost2[0], cost1[1] + cost2[1], cost1[2] + cost2[2])


def optimize_(train_no, src, dst, day, month, class_, quota, verbose = False):
    sys.stdout.write("Fetching stations on route... ")
    sys.stdout.flush()
    stations = irctc.get_stations(train_no)
    print "done."

    names = stations['names']
    indices = {}
    for i in range(len(names)):
        indices[names[i]] = i
    print "Stations found: ", indices
    src_no = indices[src]; dst_no = indices[dst]
    avail = irctc.get_all_avail(train_no, day, month, class_, quota, stations)
    cost = {}
    cost[names[dst_no]] = {}
    previous = {}
    for i in range(src_no, len(names) - 1):
        cost[names[i]] = {}
        cost[names[i]][names[i]] = (0, 0, 0)
        for j in range(i + 1, len(names)):
            cost[names[i]][names[j]] = (float("inf"), 0, 0)
    for i in range(dst_no + 1, len(names)):
        if names[i] not in cost:
            cost[names[i]] = {}
        cost[names[i]][dst] = (float("inf"), 0, 0)
    for i in range(0, src_no):
        cost[src][names[i]] = (float("inf"), 0, 0)
        if names[i] not in cost:
            cost[names[i]] = {}
            for j in range(src_no + 1, len(names)):
                cost[names[i]][names[j]] = (float("inf"), 0, 0)
    for v1 in [src] + names[0:src_no] + names[src_no + 1:]:
        if (verbose):
            print "v1 = ", v1
        for v2 in cost[v1]:
            if (v1 == v2):
                continue
            if (verbose):
                print "v2 = ", v2
                print "segment cost =", __segment_cost(v1, v2, avail, names, indices),
                if v1 in cost[src]:
                    print "cost[%s][%s] = %s" %(src, v1, cost[src][v1]),
                if v2 in cost[src]:
                    print "cost[%s][%s] = %s" %(src, v2, cost[src][v2]),
            if __cost_lt(__cost_sum(__segment_cost(v1, v2, avail, indices), cost[src][v1]), cost[src][v2]):
                cost[src][v2] = __cost_sum(__segment_cost(v1, v2, avail, indices), cost[src][v1])
                previous[v2] = v1
            if (verbose):
                print "Final cost[%s][%s] =" %(src, v2), cost[src][v2]
    if (verbose):
        print "Cost from ", src, " to ", dst, " is ", cost[src][dst]
    optimum = [dst]
    currentVertex = dst
    while (currentVertex != src):
        currentVertex = previous[currentVertex]
        optimum.insert(0, currentVertex)
    print_plan(optimum)

if __name__ == '__main__':
    main()
