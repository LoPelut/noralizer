/*
 * Main file for sniffer, a PS3 NOR address sniffer
 *
 * Copyright (C) 2009 Micah Dowty
 * Copyright (C) 2010-2011 Hector Martin <hector@marcansoft.com>
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

static inline void addr(uint32_t addr)
{
	static uint32_t last = 0xFFFFFFFF;
	static int count = 0;

	if (addr != (last+1)) {
		if (count == 0) {
		} else if (count == 1) {
			printf("+\n");
		} else {
			printf("..%06x\n", (last*2)+1);
		}
		printf("%06x", addr*2);
		fflush(stdout);
		count = 0;
	}
	count++;
	last = addr;
}

int readcb(uint8_t *buffer, int length, FTDIProgressInfo *progress, void *userdata)
{
	static uint32_t buf = 0;
	static int count = 0;
	while (length--) {
		buf <<= 8;
		buf |= *buffer++;
		count++;
		if (count == 3) {
			addr(buf);
			buf = 0;
			count = 0;
		}
	}
	return 0;
}

int main(int argc, char **argv)
{
	FTDIDevice dev;
	int err;

	err = FTDIDevice_Open(&dev);
	if (err) {
		fprintf(stderr, "USB: Error opening device\n");
		return 1;
	}
	err = FTDIDevice_ReadStream(&dev, FTDI_INTERFACE_A, readcb, NULL, 32, 64);

	FTDIDevice_Close(&dev);

	return 0;
}