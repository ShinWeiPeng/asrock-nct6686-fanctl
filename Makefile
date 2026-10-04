# SPDX-License-Identifier: GPL-2.0-or-later
ifneq ($(KERNELRELEASE),)
obj-m := asrock_nct6686.o
asrock_nct6686-y := src/nct6686_hwmon.o src/fan_control.o
else
KERNEL ?= $(shell uname -r)
KDIR ?= /lib/modules/$(KERNEL)/build
CC ?= cc
.PHONY: all modules clean
all: modules
modules:
	$(MAKE) -C $(KDIR) M=$(CURDIR) modules
clean:
	$(MAKE) -C $(KDIR) M=$(CURDIR) clean
endif
