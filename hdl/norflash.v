/*  norflash.v - NOR flasher for PS3

Copyright (C) 2010-2011  Hector Martin "marcan" <hector@marcansoft.com>

This code is licensed to you under the terms of the GNU GPL, version 2;
see file COPYING or http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt
*/

module usbstreamer (
	input mclk, reset,
	inout [7:0] usb_d, input usb_rxf_n, usb_txe_n, output usb_rd_n, output usb_wr_n, output usb_oe_n,
	output out_have_space, input [7:0] out_data, input wr, output reg have_input, output reg [7:0] in_data, input ack
);

	// FIFO configuration
	parameter OUT_FIFO_THRESHOLD = 16;
	parameter OUT_FIFO_LOG_SIZE = 10;
	parameter OUT_FIFO_SIZE = 2**OUT_FIFO_LOG_SIZE;

	parameter IN_FIFO_LOG_SIZE = 10;
	parameter IN_FIFO_SIZE = 2**IN_FIFO_LOG_SIZE;

	// OUT FIFO and pointers
	reg [7:0] out_fifo_mem[OUT_FIFO_SIZE-1:0];

	reg [OUT_FIFO_LOG_SIZE-1:0] out_fifo_read_ptr;
	reg [OUT_FIFO_LOG_SIZE-1:0] out_fifo_write_ptr;

	wire [OUT_FIFO_LOG_SIZE-1:0] out_fifo_write_ptr_next = out_fifo_write_ptr + 1;
	wire [OUT_FIFO_LOG_SIZE-1:0] out_fifo_used_space = out_fifo_write_ptr - out_fifo_read_ptr;

	wire out_fifo_empty = out_fifo_write_ptr == out_fifo_read_ptr;
	wire out_fifo_full = out_fifo_write_ptr_next == out_fifo_read_ptr;
	assign out_have_space = out_fifo_used_space < (OUT_FIFO_SIZE - OUT_FIFO_THRESHOLD);

	// OUT FIFO write process
	always @(posedge mclk or negedge reset) begin
		if (!reset) begin
			out_fifo_write_ptr <= 0;
		end else begin
			if (!out_fifo_full && wr) begin
				out_fifo_mem[out_fifo_write_ptr] <= out_data;
				out_fifo_write_ptr <= out_fifo_write_ptr + 1;
			end
		end
	end

	// IN FIFO and pointers
	reg [7:0] in_fifo_mem[IN_FIFO_SIZE-1:0];

	reg [IN_FIFO_LOG_SIZE-1:0] in_fifo_read_ptr;
	reg [IN_FIFO_LOG_SIZE-1:0] in_fifo_write_ptr;

	wire [IN_FIFO_LOG_SIZE-1:0] in_fifo_write_ptr_next = in_fifo_write_ptr + 1;

	wire in_fifo_empty = in_fifo_write_ptr == in_fifo_read_ptr;
	wire in_fifo_full = in_fifo_write_ptr_next == in_fifo_read_ptr;

	// IN FIFO read process
	always @(posedge mclk or negedge reset) begin
		if (!reset) begin
			in_fifo_read_ptr <= 0;
			have_input <= 0;
		end else begin
			if (in_fifo_empty) begin
				if (ack)
					have_input <= 0;
			end else if (!have_input || ack) begin
				have_input <= 1;
				in_data <= in_fifo_mem[in_fifo_read_ptr];
				in_fifo_read_ptr <= in_fifo_read_ptr + 1;
			end
		end
	end

	parameter S_EVAL = 0;
	parameter S_OUT = 1;
	parameter S_IN = 2;

	reg [1:0] state;

	wire can_write = !out_fifo_empty && !usb_txe_n;
	wire can_read = !in_fifo_full && !usb_rxf_n;

	// write data only during the S_OUT stage
	reg [7:0] out_buf;
	assign usb_d = (state == S_OUT) ? out_buf : 8'hZZ;
	assign usb_wr_n = !(state == S_OUT);
	assign usb_oe_n = !(state == S_IN || (state == S_EVAL && can_read));
	assign usb_rd_n = !(state == S_IN);

	// FIFO read / USB stream process
	always @(posedge mclk or negedge reset) begin
		if (!reset) begin
			state <= S_EVAL;
			out_fifo_read_ptr <= 0;
			// note: no reset of usb_dout because it's really a BRAM output port which is only synchronous
		end else begin
			case (state)
				S_EVAL: begin
					if (can_read) begin
						state <= S_IN;
					end else if (can_write) begin
						out_buf <= out_fifo_mem[out_fifo_read_ptr];
						state <= S_OUT;
					end
				end
				S_OUT: begin
					state <= S_EVAL;
					out_fifo_read_ptr <= out_fifo_read_ptr+1;
				end
				S_IN: begin
					state <= S_EVAL;
					in_fifo_mem[in_fifo_write_ptr] <= usb_d;
					in_fifo_write_ptr <= in_fifo_write_ptr+1;
				end
			endcase
		end
	end
endmodule

module norflash (
	input mclk,
	output [3:0] led,
	inout [7:0] usb_d, input usb_rxf_n, usb_txe_n, output usb_rd_n, usb_wr_n, usb_oe_n,

	inout [22:0] nor_a, inout [15:0] nor_d, inout nor_we_n, inout nor_ce_n, inout nor_oe_n,
	inout nor_reset_n, input nor_ready, input nor_vcc, inout nor_trist_n
);

	reg out_trist = 0;
	assign nor_trist_n = (nor_vcc && out_trist) ? 1'b0 : 1'bZ;

	reg drive;
	wire really_drive = drive && nor_vcc && out_trist;

	reg drive_d;
	wire really_drive_d = really_drive && drive_d && nor_oe_n;

	reg out_we, out_ce, out_oe;
	reg out_reset;
	reg [22:0] out_a;
	reg [15:0] out_d;

	assign nor_a = really_drive ? out_a : 23'hZZZZZZ;
	assign nor_d = really_drive_d ? out_d : 16'hZZZZ;
	assign nor_we_n = really_drive ? !out_we : 1'bZ;
	assign nor_oe_n = really_drive ? !out_oe : 1'bZ;
	assign nor_ce_n = really_drive ? !out_ce : 1'bZ;
	assign nor_reset_n = really_drive ? !out_reset : 1'bZ;

	// FPGA reset generator
	reg reset = 0;
	always @(posedge mclk) begin
		reset <= 1;
	end

	// Blinky LED counter
	reg [23:0] led_div;
	always @(posedge mclk or negedge reset) begin
		if (!reset) begin
			led_div <= 0;
		end else begin
			led_div <= led_div + 24'b1;
		end
	end


	// USB streamer lines
	wire can_write;
	reg [7:0] tx_data;
	reg tx_wr;
	wire can_read;
	wire [7:0] in_data;
	wire in_ack;

	// instantiate USB streamer
	usbstreamer ustm (
		mclk, reset,
		usb_d, usb_rxf_n, usb_txe_n, usb_rd_n, usb_wr_n, usb_oe_n,
		can_write, tx_data, tx_wr, can_read, in_data, in_ack
	);

	// assign some leds
	assign led[0] = !can_read;
	assign led[1] = !can_write;
	assign led[2] = usb_rxf_n;
	assign led[3] = led_div[23];

	parameter S_IDLE = 0;
	parameter S_DELAY = 1;
	parameter S_ADDR2 = 2;
	parameter S_ADDR3 = 3;
	parameter S_READING = 4;
	parameter S_WDATA1 = 5;
	parameter S_WDATA2 = 6;
	parameter S_WRITING = 7;
	parameter S_WAITING = 8;
	reg [3:0] state;

	wire ack_cmd = state == S_IDLE;
	wire ack_addr = state == S_ADDR2 || state == S_ADDR3;
	wire ack_data = state == S_WDATA1 || state == S_WDATA2;
	assign in_ack = (ack_cmd || ack_addr || ack_data) && can_write && can_read;

	wire [7:0] state_byte = {drive, nor_vcc, nor_trist_n, nor_reset_n, nor_ready, nor_ce_n, nor_we_n, nor_oe_n};

	reg [5:0] cycle;
	reg [7:0] hold_buf;

	reg do_increment;

	always @(posedge mclk or negedge reset) begin
		if (!reset) begin
			state <= S_IDLE;
			tx_wr <= 0;
			drive <= 0;
			drive_d <= 0;
			out_trist <= 0;
			out_we <= 0;
			out_ce <= 1;
			out_oe <= 0;
			out_reset <= 0;
		end else if (can_write) begin
			tx_wr <= 0;
			case (state)
			S_IDLE: begin
				if (can_read) begin
					casez (in_data) // command
					8'b00000000: begin // NOP
					end
					8'b00000001: begin // READSTATE
						tx_data <= state_byte;
						tx_wr <= 1;
					end
					8'b00000010: begin // PING1
						tx_data <= 8'h42;
						tx_wr <= 1;
					end
					8'b00000011: begin // PING2
						tx_data <= 8'hbd;
						tx_wr <= 1;
					end
					8'b0000010z: begin // DRIVE
						drive <= in_data[0];
					end
					8'b0000011z: begin // TRISTATE
						out_trist <= in_data[0];
					end
					8'b0000100z: begin // RESET
						out_reset <= in_data[0];
					end
					8'b0000111z: begin // WAIT
						do_increment <= in_data[0];
						state <= S_WAITING;
					end
					8'b000100zz: begin // READ
						do_increment <= in_data[0];
						if (in_data[1])
							cycle <= 12;
						else begin
							cycle <= 4;
							out_oe <= 1;
						end
						state <= S_READING;
					end
					8'b0001100z: begin // WRITE
						do_increment <= in_data[0];
						state <= S_WDATA1;
					end
					8'b01zzzzzz: begin // DELAY
						cycle <= in_data[5:0];
						state <= S_DELAY;
					end
					8'b1zzzzzzz: begin // ADDR
						out_a[22:16] <= in_data[6:0];
						state <= S_ADDR2;
					end
					endcase
				end
			end
			S_DELAY: begin
				if (cycle == 0)
					state <= S_IDLE;
				else
					cycle <= cycle - 1;
			end
			S_ADDR2: begin
				if (can_read) begin
					out_a[15:8] <= in_data;
					state <= S_ADDR3;
				end
			end
			S_ADDR3: begin
				if (can_read) begin
					out_a[7:0] <= in_data;
					state <= S_IDLE;
				end
			end
			S_READING: begin
				if (cycle == 4)
					out_oe <= 1;
				if (cycle == 1) begin
					tx_data <= nor_d[15:8];
					hold_buf <= nor_d[7:0];
					tx_wr <= 1;
					out_oe <= 0;
					if (do_increment)
						out_a <= out_a + 1;
				end
				if (cycle == 0) begin
					tx_data <= hold_buf;
					tx_wr <= 1;
					state <= S_IDLE;
				end else
					cycle <= cycle - 1;
			end
			S_WDATA1: begin
				if (can_read) begin
					out_d[15:8] <= in_data;
					state <= S_WDATA2;
				end
			end
			S_WDATA2: begin
				if (can_read) begin
					out_d[7:0] <= in_data;
					drive_d <= 1;
					cycle <= 14;
					state <= S_WRITING;
				end
			end
			S_WRITING: begin
				if (cycle == 12)
					out_we <= 1;
				if (cycle == 8) begin
					out_we <= 0;
					drive_d <= 0;
				end
				if (cycle == 0) begin
					if (do_increment)
						out_a <= out_a + 1;
					state <= S_IDLE;
				end else
					cycle <= cycle - 1;
			end
			S_WAITING: begin
				if (nor_ready == 1) begin
					if (do_increment)
						out_a <= out_a + 1;
					state <= S_IDLE;
				end
			end
			endcase
		end
	end

/*
	always @(posedge mclk or negedge reset) begin
		if (!reset) begin
			tx_wr <= 0;
		end else begin
			if (can_read && can_write) begin
				tx_data <= in_data;
				tx_wr <= 1;
			end else begin
				tx_wr <= 0;
			end
		end
	end
*/

/*
	always @(posedge mclk or negedge reset) begin
		if (!reset) begin
			tog <= 0;
			tx_wr <= 0;
			last_addr <= 0;
			pend <= 0;
		end else begin
			high_addr <= nor_a[22:15];
			if (pend) begin
				tog <= !tog;
				tx_data <= high_addr;
				tx_wr <= 1;
				last_addr <= high_addr;
				pend <= 0;
			end else if (last_addr != high_addr) begin
				tx_wr <= 0;
				pend <= 1;
			end else begin
				tx_wr <= 0;
			end
		end
	end
*/

endmodule
