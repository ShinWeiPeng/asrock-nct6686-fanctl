# SPDX-License-Identifier: GPL-2.0-or-later
ifneq ($(KERNELRELEASE),)
obj-m := asrock_nct6686.o
asrock_nct6686-y := src/nct6686_hwmon.o src/fan_control.o
else
KERNEL ?= $(shell uname -r)
KDIR ?= /lib/modules/$(KERNEL)/build
CC ?= cc
OUT ?=
.PHONY: all modules clean test
all: modules
modules:
	$(MAKE) -C $(KDIR) M=$(CURDIR) modules
test:
	@set -eu; \
	mkdir -p artifacts/tests; \
	if [ -n "$(OUT)" ]; then mkdir "$(OUT)"; out="$(OUT)"; \
	else out=$$(mktemp -d artifacts/tests/run.XXXXXX); fi; \
	echo "Test run: $$out"; \
	$(CC) -std=c11 -Wall -Wextra -Werror -pedantic -Isrc src/fan_control.c tests/modules/fan-control/test_fan_control.c -o "$$out/test_fan_control"; \
	if "$$out/test_fan_control" > "$$out/test.log" 2>&1; then cat "$$out/test.log"; \
	else cat "$$out/test.log"; exit 1; fi
clean:
	$(MAKE) -C $(KDIR) M=$(CURDIR) clean
endif
