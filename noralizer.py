#!/usr/bin/python
#  noralizer.py - NOR flasher for PS3
#
# Copyright (C) 2010-2011  Hector Martin "marcan" <hector@marcansoft.com>
#
# This code is licensed to you under the terms of the GNU GPL, version 2;
# see file COPYING or http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt

from libusb1 import usb1
import time, sys, struct

class TwlfpgaError(Exception):
	pass

class Twlfpga(object):
	VID = 0xe461
	PID = 0x0014

	BUFSIZE = 16384
	NUM_XFERS = 64
	XFER_SIZE = 32768

	EP_IN = 0x81
	EP_OUT = 0x02

	def __init__(self):
		self.usb = usb1.LibUSBContext()
		self.dev = self.usb.openByVendorIDAndProductID(self.VID, self.PID)
		if self.dev is None:
			raise TwlfpgaError("twlfpga not found")

		self.obuf = ""
		self.ibuf = ""
		self.start_in()
		time.sleep(0.2)
		self.ibuf = ""

	def _cb_out(self, xfer):
		pass

	def xfer_out(self, data):
		xfer = self.dev.getTransfer()
		xfer.setBulk(self.EP_OUT, data, self._cb_out, None, 0)
		xfer.submit()

	def write(self, s):
		if isinstance(s,int):
			s = chr(s)
		elif isinstance(s,tuple) or isinstance(s,list):
			s = ''.join([chr(c) for c in s])
		self.obuf += s
		while len(self.obuf) > self.BUFSIZE:
			self.xfer_out(self.obuf[:self.BUFSIZE])
			self.obuf = self.obuf[self.BUFSIZE:]
	def flush(self):
		if len(self.obuf):
			self.xfer_out(self.obuf)
			self.obuf = ""

	def _cb_in(self, xfer):
		status = xfer.getStatus()
		if status != 0:
			raise TwlfpgaError("IN transfer returned status %d"%status)
		data = xfer.getBuffer()[:xfer.getActualLength()]
		pkts = (len(data) + 511) // 512
		for i in xrange(0,512*pkts,512):
			pkt = data[i:i+512]
			if len(pkt) < 2:
				raise TwlfpgaError("Packet header missing (got %d bytes)"%len(pkt))
			self.ibuf += pkt[2:]
		xfer.submit()

	def start_in(self):

		for i in range(self.NUM_XFERS):
			xfer = self.dev.getTransfer()
			xfer.setBulk(self.EP_IN, self.XFER_SIZE, self._cb_in, None, 0)
			xfer.submit()

	def read(self, size):
		self.flush()
		while len(self.ibuf) < size:
			self.usb.handleEvents()
		data = self.ibuf[:size]
		self.ibuf = self.ibuf[size:]
		return data

	def readbyte(self):
		return ord(self.read(1))

class NORError(Exception):
	pass

STATUS_DRIVE = 0x80
STATUS_VCC = 0x40
STATUS_TRIST_N = 0x20
STATUS_RESET_N = 0x10
STATUS_READY = 0x08
STATUS_CE_N = 0x04
STATUS_WE_N = 0x02
STATUS_OE_N = 0x01

class NORFlasher(Twlfpga):
	def __init__(self):
		Twlfpga.__init__(self)

	def ping(self):
		self.write(0x02)
		self.write(0x03)
		val = self.readbyte()
		if val != 0x42:
			raise NORError("Ping failed (expected 42, got %02x)"%val)
		val = self.readbyte()
		if val != 0xbd:
			raise NORError("Ping failed (expected bd, got %02x)"%val)

	def state(self):
		self.write(0x01)
		return self.readbyte()

	@property
	def vcc(self):
		return bool(self.state() & STATUS_VCC)

	def _s_drive(self, v):
		self.write(0x04 | bool(v))
	def _g_drive(self):
		return bool(self.state() & STATUS_DRIVE)
	drive = property(_g_drive, _s_drive)

	def _s_trist(self, v):
		self.write(0x06 | bool(v))
	def _g_trist(self):
		return not (self.state() & STATUS_TRIST_N)
	trist = property(_g_trist, _s_trist)

	def _s_reset(self, v):
		self.write(0x08 | bool(v))
	def _g_reset(self):
		return not (self.state() & STATUS_RESET_N)
	reset = property(_g_reset, _s_reset)

	def addr(self, v):
		assert 0 <= v <= 0x7FFFFF
		self.write((0x80 | (v >> 16), (v >> 8) & 0xff, v & 0xff))

	def wait(self, inc=False):
		self.write(0x0e | bool(inc))

	def writeword(self, data, inc=False):
		self.write((0x18 | bool(inc), (data>>8) & 0xff, data & 0xff))

	def writeat(self, addr, data, inc=False):
		self.addr(addr)
		self.writeword(data, inc)

	def readnor(self, off, count):
		self.addr(off)
		last = None
		buf = ""
		for addr in range(off, off+count):
			if last is not None and ((addr&3) == (last&3)):
				buf += "\x13"
			else:
				buf += "\x13"
		self.write(buf)
		d = self.read(2*count)
		return d

	def erasesector(self, off):
		assert off&0xFFFF == 0
		self.writeat(0x555, 0xaa)
		self.writeat(0x2aa, 0x55)
		self.writeat(0x555, 0x80)
		self.writeat(0x555, 0xaa)
		self.writeat(0x2aa, 0x55)
		self.writeat(off, 0x30)
		self.delay(10)
		self.wait()
		self.ping()

	def programline(self, off, data):
		assert off&0x1f == 0
		if isinstance(data, str):
			data = struct.unpack(">%dH"%(len(data)/2), data)
		assert len(data) <= 32
		saddr = off & ~0x1f
		self.writeat(0x555, 0xaa)
		self.writeat(0x2aa, 0x55)
		self.writeat(saddr, 0x25)
		self.writeat(saddr, len(data)-1)
		self.addr(off)
		for d in data:
			self.writeword(d, True)
		self.writeat(saddr, 0x29)
		self.wait()

	def writesector(self, addr, data):
		assert len(data) == 0x20000
		assert (addr & 0xffff) == 0
		odata = self.readnor(addr, 0x10000)
		if odata == data:
			return
		self.erasesector(addr)
		for off in range(0,0x20000,0x40):
			d = data[off:off+0x40]
			if d != "\xff"*0x40:
				n.programline(addr+(off/2), d)
		rdata = n.readnor(addr, 0x10000)
		if rdata != data:
			raise NORError("Verification failed")

	def rmwsector(self, addr, data):
		offset = addr & 0x1ffff
		endaddr = offset + len(data)
		assert endaddr <= 0x20000

		secaddr = (addr & ~0x1ffff)/2
		odata = self.readnor(secaddr, 0x10000)
		wdata = odata[:offset] + data + odata[endaddr:]
		if odata != wdata:
			self.writesector(secaddr, wdata)

	def writerange(self, addr, data):
		if len(data) == 0:
			return
		first_sector = addr & ~0x1ffff
		last_sector = (addr + len(data) - 1) & ~0x1ffff

		offset = addr & 0x1ffff

		sec_count = (last_sector + 0x20000 - first_sector)/0x20000
		done = 0
		if offset != 0:
			self.rmwsector(addr, data[:0x20000-offset])
			data = data[0x20000-offset:]
			print "\rSector %06x (%d/%d) [F]..."%(first_sector, done+1, sec_count),
			sys.stdout.flush()
			done += 1
			addr += 0x20000-offset

		while len(data) >= 0x20000:
			self.writesector(addr/2, data[:0x20000])
			print "\rSector %06x (%d/%d) [M]..."%(addr, done+1, sec_count),
			sys.stdout.flush()
			done += 1
			addr += 0x20000
			data = data[0x20000:]

		if len(data) != 0:
			self.rmwsector(addr, data)
			print "\rSector %06x (%d/%d) [L]..."%(addr, done+1, sec_count),
			sys.stdout.flush()
			done += 1

		assert done == sec_count
		print

	def delay(self, v):
		while v > 0x41:
			self.write(0x7f)
			v -= 0x41
		if v <= 0:
			return
		elif v == 1:
			self.write(0x00)
		else:
			self.write(0x40 | (v-2))

	def udelay(self, v):
		self.delay(v * 60)

if __name__ == "__main__":
	n = NORFlasher()
	print "Pinging..."
	n.ping()

	n.drive = 0
	n.reset = 0
	print "Set SB to tristate"
	n.trist = 1
	state = n.state()

	if not n.vcc:
		print "Waiting for VCC..."
		while not n.vcc:
			pass
		print "VCC up!"

	print "State: %02x"%n.state()
	n.drive = 1
	print "Resetting NOR..."
	n.reset = 1
	n.udelay(40)
	n.reset = 0
	n.udelay(40)
	#print "State: %02x"%n.state()
	n.ping()
	print "Ready."

	if len(sys.argv) == 3 and sys.argv[1] == "dump":
		BLOCK = 0x10000
		print "Dumping NOR..."
		fo = open(sys.argv[2],"wb")
		for offset in range(0, 0x800000, BLOCK):
			fo.write(n.readnor(offset, BLOCK))
			print "\r%dkB"%((offset+BLOCK)/512),
			sys.stdout.flush()
		print
		print "Done."
	elif len(sys.argv) == 3 and sys.argv[1] == "erase":
		addr = int(sys.argv[2], 16)
		if addr & 0x1ffff:
			print "Address must be aligned!"
			sys.exit(1)
		assert addr&1 == 0
		print "Erasing sector %06x..."%addr,
		sys.stdout.flush()
		n.erasesector(addr/2)
		print "Done."
	elif len(sys.argv) in (3,4) and sys.argv[1] == "write":
		data = open(sys.argv[2],"rb").read()
		addr = 0
		if len(sys.argv) == 4:
			addr = int(sys.argv[3],16)
		n.writerange(addr, data)
		print "Done."
	elif len(sys.argv) == 4 and sys.argv[1] == "writeimg":
		data = open(sys.argv[2],"rb").read()
		addr = int(sys.argv[3],16)
		data = struct.pack(">12xI", len(data)) + data
		n.writerange(addr, data)
		print "Done."
	elif len(sys.argv) in (3,4) and sys.argv[1] == "program":
		data = open(sys.argv[2],"rb").read()
		addr = 0
		if len(sys.argv) == 4:
			addr = int(sys.argv[3],16)
			if addr & 0x1ffff:
				print "Address must be aligned!"
				sys.exit(1)
			addr /= 2
		sectors = (len(data)+0x1ffff) / 0x20000
		if (sectors*0x20000) != len(data):
			left = len(data)%0x20000
			print "NOTE: padding file with 0x%x FF bytes to complete the sector"%(0x20000 - left)
		if len(data) & 1: # pad to 16 bits
			data += "\xff"

		for sec in range(sectors):
			secaddr = addr + sec * 0x10000
			print "\rSector %06x (%d/%d) E"%(secaddr, sec+1, sectors),
			sys.stdout.flush()
			n.erasesector(secaddr)

			print "\rSector %06x (%d/%d) P"%(secaddr, sec+1, sectors),
			sys.stdout.flush()
			d = data[sec*0x20000:sec*0x20000+0x20000]
			for off in range(0,len(d),0x40):
				n.programline(secaddr+(off/2), d[off:off+0x40])
			print "\rSector %06x (%d/%d) V"%(secaddr, sec+1, sectors),
			sys.stdout.flush()
			dv = n.readnor(secaddr, 0x10000)[:len(d)]
			if d != dv:
				print
				print "Verification failed!"
				sys.exit(1)
		print
		print "Done."
	elif len(sys.argv) == 2 and sys.argv[1] == "release":
		n.drive = 0
		n.trist = 0
		print "NOR Released"

	n.ping()
