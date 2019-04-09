# Python module providing a high-level interface to the KCWI instrument.

override SYSNAM = kss/kcwi/scripts/lib/
override VERNUM = 1.0

RELLIB = $(wildcard *.py)
LIBSUB = python/KCWI

################################################################################
# KROOT boilerplate:
# Include general make rules, using default values for the key environment
# variables if they are not already set.

ifndef KROOT
	KROOT = /kroot
endif

ifndef RELNAM
	RELNAM = default
endif

ifndef RELDIR
	RELDIR = $(KROOT)/rel/$(RELNAM)
endif

include $(RELDIR)/etc/defs.mk

ifneq "$(PYTHON3)" ""
	ENABLE_PYTHON3 = True
endif

include $(RELDIR)/etc/rules.mk
################################################################################
