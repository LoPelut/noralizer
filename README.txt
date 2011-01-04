This is the NOR flasher tool that was used to flash AsbestOS onto the demo PS3
at 27C3, and for experimentation.

Contents:
	hdl - Verilog code (for Xilinx Spartan3E XC3S500E) for the flasher
	hdl-sniffer - Verilog code (same board) for the sniffer
	loader - bitfile loader for the board (parallel 8bit mode, really fast)
	         also includes code to program the FTDI's EEPROM (required)
	sniffer - C client for the sniffer
	noralizer.py - Python client for the
	nor_testpoints.png - diagram of the NOR testpoints (for CECH-2504A)
	norinfo.py - simple NOR parser, prints the main sections of the NOR and their offsets.

Examples:
$ make -C hdl run
$ python noralizer.py dump foo.bin # dump the NOR
$ python noralizer.py write foo.bin # write the entire NOR
$ # write something at 0x123456, doing read-modify-write if necessary
$ python noralizer.py write lv2.self 0x123456
$ # same, but prepend a 16-byte length header
$ python noralizer.py writeimg rvk_prg0.sce 0x40000
$ python noralizer.py release # release NOR interface, so the PS3 can boot

$ make -C hdl-sniffer run
$ make -C sniffer
$ sniffer/sniffer > log.txt # log NOR address ranges accessed

Dependencies:
	ISE WebPACK to build the HDL
	python-libusb1 (https://github.com/vpelletier/python-libusb1)

Unfortunately, the exact board that I used was an internal project originally
developed for DSi hacking and is not commercially available. However, it's just
an FPGA and a FT2232H USB bridge with a ton of IOs on the board. You should be
able to retarget this to pretty much any other FPGA board with a FT2232H fairly
easily. There is more info on the expected connections in the .ucf files.
