
override SYSNAM = kss/kcwi/scripts/python/KCWI_GUIs
override VERNUM = 1.0

SUBST_STRICT = True

RELBIN = KCWI_Exposure KCWI_Offset KCWI_Cal_Gui KCWI_Exposure_Design.py KCWI_Status QLed.py
FILES = $(RELBIN)


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

include $(KROOT)/etc/config.mk
################################################################################


