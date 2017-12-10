#! /usr/bin/env python
# -*- encoding: utf-8 -*-
'''2017PDA PA2 - Channel Router
Students are required to implement a greedy channel router.
'''

import sys
import enum
import errno
import argparse
from collections import namedtuple, defaultdict

HWire = namedtuple('HWire', ['net', 'left_x', 'left_y', 'right_x'])
VWire = namedtuple('VWire', ['net', 'bottom_x', 'bottom_y', 'top_y'])
COLUMN_W = 1
TRACK_H = 1

class WireLayer(enum.Enum):
    '''Enumeration of wire layer: horizonal and vertical.
    '''
    HORIZONTAL = 0
    VERTICAL = 1

class Router:
    '''Naive channel router.
    '''
    def __init__(self, top_pins, bot_pins, out_file):
        self._top_pins = top_pins
        self._bot_pins = bot_pins
        self._pins = set(top_pins + bot_pins)
        self._out_file = out_file
        self._h_wire = defaultdict(list)
        self._v_wire = defaultdict(list)
        self._track_cnt = 0

    def _add_h_wire(self, net, left_x, left_y, right_x):
        '''Create horizontal wire.
        '''
        self._h_wire[net].append(HWire(net, left_x, left_y, right_x))

    def _add_v_wire(self, net, bottom_x, bottom_y, top_y):
        '''Create top wire.
        '''
        self._v_wire[net].append(VWire(net, bottom_x, bottom_y, top_y))

    def track_cnt(self, file=sys.stdout):
        '''Dump track utilization to file.
        '''
        print('Track count: {}'.format(self._track_cnt), file=file)

    def route(self):
        '''Route wires in channel.
        # TODO: Detail the routing tactics
        '''
        last_track_idx = 0 # the index of horizontal wire latest created
        last_col_idx = 0 # the index of column where latest vertical wire was created
        bot_pins_not_in_top = set(self._bot_pins) - set(self._top_pins)
        top_pins_not_in_bot = set(self._top_pins) - set(self._bot_pins)
        # start from bottom pins
        bot_pin_to_y = {}
        h_wire_runners = [] # unfinished horizontal metal strip
        for idx, pin in enumerate(self._bot_pins):
            last_col_idx = idx
            # extend every unfinished horizontal wire strip
            for h_wire in h_wire_runners:
                h_wire[1][2] += COLUMN_W
            # skip pin 0
            if pin == 0:
                continue
            # create a vertical wire from a terminal to a track
            if pin not in bot_pin_to_y:
                self._add_v_wire(pin, idx*COLUMN_W, 0, (last_track_idx+1)*TRACK_H)
                bot_pin_to_y[pin] = (last_track_idx+1)*TRACK_H
                # create a horizontal wire for current terminal, update last_track_idx
                h_wire_runners.append((pin, [idx*COLUMN_W, (last_track_idx+1)*TRACK_H,
                                             (idx+1)*COLUMN_W]))
                last_track_idx += 1
            else:
                self._add_v_wire(pin, idx*COLUMN_W, 0, bot_pin_to_y[pin])
        # create horizontal wires for pins which only occupy bottom terminals
        for pin in bot_pins_not_in_top:
            h_wire = next(wire for wire in h_wire_runners if wire[0] == pin)
            self._add_h_wire(h_wire[0], *h_wire[1])
        # route top pins in reverse
        top_pin_to_y = {}
        for idx, pin in reversed(tuple(enumerate(self._top_pins))):
            # skip pin 0 or pin whose top horizontal wire is already created
            if pin == 0 or pin in top_pin_to_y:
                continue
            # find x-range of this pin at top
            idxs = [idx_ for (idx_, pin_) in enumerate(self._top_pins) if pin_ == pin]
            min_x = min(idxs) * COLUMN_W
            max_x = max(idxs) * COLUMN_W
            # create new horizontal wire for this pin
            # if this pin only occupy top terminals
            if pin in top_pins_not_in_bot:
                self._add_h_wire(pin, min_x, (last_track_idx+1)*TRACK_H, max_x)
            # general case
            else:
                # bottom horizontal wire from left to right
                h_strip = next(wire for wire in h_wire_runners if wire[0] == pin)
                self._add_h_wire(pin, h_strip[1][0], h_strip[1][1], (last_col_idx+1)*COLUMN_W)
                # right vertical wire from bottom to top
                self._add_v_wire(pin, (last_col_idx+1)*COLUMN_W, h_strip[1][1], (last_track_idx+1)*TRACK_H)
                # top horizontal wire from left to right
                self._add_h_wire(pin, min_x, (last_track_idx+1)*TRACK_H, (last_col_idx+1)*COLUMN_W)
                last_col_idx += 1
            top_pin_to_y[pin] = (last_track_idx+1)*TRACK_H
            last_track_idx += 1
        # create vertical wire from top terminal to channel
        self._track_cnt = last_track_idx
        top_terminal_track_idx = last_track_idx + 1
        top_terminal_y = top_terminal_track_idx * TRACK_H
        for idx, pin in enumerate(self._top_pins):
            if pin == 0:
                continue
            self._add_v_wire(pin, idx*COLUMN_W, top_pin_to_y[pin], top_terminal_y)

    def write_result(self):
        '''Write output file.
        '''
        with open(self._out_file, 'wt') as out_file:
            for pin in self._pins:
                if pin == 0:
                    continue
                print('.begin {}'.format(pin), file=out_file)
                # output horizontal wires
                for wire in self._h_wire[pin]:
                    print('.H {left_x} {left_y} {right_x}'.format(**wire._asdict()), file=out_file)
                # output vertical wires
                for wire in self._v_wire[pin]:
                    print('.V {bottom_x} {bottom_y} {top_y}'.format(**wire._asdict()), file=out_file)
                print('.end', file=out_file)

def parse():
    '''Parse command line.
    '''
    parser = argparse.ArgumentParser(description='PDA PA2 - A Channel Router')
    parser.add_argument('pin_map', metavar='<pin_spec>', help='pin location info of a channel')
    parser.add_argument('output', metavar='<output>', help='output routing')
    args = parser.parse_args()
    return parse_terminal_spec(args)

def parse_terminal_spec(args):
    '''Parse input file and generate a Router object.
    '''
    try:
        with open(args.pin_map, 'rt') as in_file:
            top_pins = [int(pin_str) for pin_str in in_file.readline().split()]
            bot_pins = [int(pin_str) for pin_str in in_file.readline().split()]
    except OSError:
        print('Cannot open file: {}'.format(args.pin_map), file=sys.stderr)
        sys.exit(errno.ENOENT)
    assert len(top_pins) == len(bot_pins), 'Terminal lengths at top and bottom are unequal'
    print('Pin count: {}'.format(len(top_pins)))
    return Router(top_pins, bot_pins, args.output)

def main():
    '''Main function.
    '''
    print('PDA PA2 - Channel Router')
    router = parse()
    router.route()
    router.track_cnt()
    router.write_result()

if __name__ == '__main__':
    main()
