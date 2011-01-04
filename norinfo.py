#!/usr/bin/python
#  norinfo.py - NOR root info
#
# Copyright (C) 2010-2011  Hector Martin "marcan" <hector@marcansoft.com>
#
# This code is licensed to you under the terms of the GNU GPL, version 2;
# see file COPYING or http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt

import sys, struct

fd = open(sys.argv[1],"rb")


nor = fd.read()
ifiroot = nor[0x400:0x800]

foo, entries, totlen = struct.unpack(">II4xI", ifiroot[:0x10])

for i in range(entries):
	d = ifiroot[0x10+i*0x30:0x40+i*0x30]
	off, size, name = struct.unpack(">QQ32s", d)
	name = name.split("\0")[0]
	off += 0x400

	hdr = nor[off:off+0x10]
	lsize = struct.unpack(">12xI",hdr)[0]
	print "%08x..%08x [%8x/%8x] %s"%(off, off+size, lsize, size, name)
