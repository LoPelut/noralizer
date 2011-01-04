# Base name of the project file.
PROJECT=norflash

# Part name
PART=xc3s500epq208-4

# Implementation option file
# Pick one: fast_runtime balanced high_effort overnight weekend exhaustive
IMPLEMENT=fast_runtime

# Synthesis option file
SYNTH=xst_verilog

# Working directory name
WORK=work

BITFILE=work/$(PROJECT).bit

UCF=$(PROJECT).ucf

.PHONY: all clean project

all: $(BITFILE)

$(BITFILE): *.v $(UCF)
	@mkdir -p $(WORK)
	cp $(UCF) work/$(UCF)
	xflow -wd $(WORK) -p $(PART) -synth $(SYNTH) -implement $(IMPLEMENT) -config ../bitgen.opt $(PROJECT)

run: $(BITFILE) ../loader/loadbit
	../loader/loadbit $(BITFILE)

clean:
	rm -rf $(WORK)/

project:
	@rm -f $(PROJECT).prj
	#@echo VHDL:
	#@for i in $$(ls *.vhd 2> /dev/null); do echo "    " $$i; echo vhdl work $$i >> $(PROJECT).prj; done
	@echo Verilog:
	@for i in $$(ls *.v 2> /dev/null); do echo "    " $$i; echo verilog work $$i >> $(PROJECT).prj; done
	echo "    " $$i; echo verilog work $$i >> $(PROJECT).prj; done
