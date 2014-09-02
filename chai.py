#!/usr/bin/env python

import argparse
import re
from irctc import IrctcClient as irctc
import sys

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
        optimize(args.train_no, args.src, args.dst, args.day, args.month, args.class_, args.quota, args.verbose)

    def __get_avail(args):
        print irctc.get_avail(args.train_no, args.src, args.dst, args.day, args.month, args.class_, args.quota)

    p_availability = sp.add_parser('avail', help="find availability between two stations")
    p_optimize = sp.add_parser('optimize', help="calculate the best possible route to take between two stations")

    p_optimize.set_defaults(func=__optimize)
    p_availability.set_defaults(func=__get_avail)

    args = p.parse_args()

    args.func(args)

def __segment_cost(v1, v2, avail, names, indices):
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
        return (1000, 0, 0)

def __cost_lt(cost1, cost2):
    for i in range(len(cost1)):
        if (cost1[i] < cost2[i]):
            return True
        elif (cost1[i] > cost2[i]):
            return False
    return False

def __cost_sum(cost1, cost2):
    return (cost1[0] + cost2[0], cost1[1] + cost2[1], cost1[2] + cost2[2])

def optimize(train_no, src, dst, day, month, class_, quota, verbose = False):
    sys.stdout.write("Fetching stations on route... ")
    sys.stdout.flush()
    stations = irctc.get_stations(train_no)
    print "done."
    names = stations['names']
    offsets = stations['offsets']
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
            if __cost_lt(__cost_sum(__segment_cost(v1, v2, avail, names, indices), cost[src][v1]), cost[src][v2]):
                cost[src][v2] = __cost_sum(__segment_cost(v1, v2, avail, names, indices), cost[src][v1])
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
    print "Optimum plan is: "
    for i in range(len(optimum) - 1):
        print optimum[i], " --> ", optimum[i + 1],
        print "(", indices[optimum[i + 1]] - indices[optimum[i]], " stations )",
        if (indices[optimum[i+1]] > indices[optimum[i]]):
            print ":", avail[optimum[i]][optimum[i+1]]
        else:
            if indices[optimum[i+1]] < indices[src]:
                print ":", "Get on at %s" %optimum[i]
            else:
                print ":", "Get off at %s" %optimum[i+1]

if __name__ == '__main__':
    main()
