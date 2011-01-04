/*
 * Main file for loadbit, a standalone FPGA bitstream loader for the twlfpga
 *
 * Copyright (C) 2009 Micah Dowty
 * Copyright (C) 2010 Hector Martin <hector@marcansoft.com>
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in
 * all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
 * THE SOFTWARE.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <getopt.h>
#include <unistd.h>
#include <stdbool.h>

#include "fastftdi.h"
#include "fpgaconfig.h"
#include "ftdieep.h"

static void usage(const char *argv0)
{
	fprintf(stderr,
	        "Usage: %s [bit-file]\n"
	        "Load an FPGA bitfile to the twlfpga board\n"
	        "Copyright (C) 2009 Micah Dowty <micah@navi.cx>\n"
	        "Copyright (C) 2010 Hector Martin <hector@marcansoft.com>\n",
	        argv0);
	exit(1);
}


int main(int argc, char **argv)
{
	FTDIDevice dev;
	int err;

	if (argc != 2)
		usage(argv[0]);

	err = FTDIDevice_Open(&dev);
	if (err) {
		fprintf(stderr, "USB: Error opening device\n");
		return 1;
	}
	
	err = FTDIEEP_CheckAndProgram(&dev);
	if (err) {
		fprintf(stderr, "EEPROM: Error checking/programming EEPROM\n");
		return 1;
	}

	err = FPGAConfig_LoadFile(&dev, argv[1]);
	if (err) {
		fprintf(stderr, "FPGA: Error loading bitstream\n");
		return 1;
	}

	err = FTDIDevice_SetMode(&dev, FTDI_INTERFACE_A,
	                         FTDI_BITMODE_SYNC_FIFO, 0xFF, 0);
	if (err) {
		fprintf(stderr, "USB: Error setting SYNC FIFO mode\n");
		return 1;
	}
	
	fprintf(stderr, "USB: Set SYNC FIFO mode\n");

	FTDIDevice_Close(&dev);

	return 0;
}
