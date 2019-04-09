################################################################################
#+
#  Module:	$KSSDIR/kcwi/scripts/python/Makefile
#
#  Revisions:   
#
#  Author:	Luca Rizzi
#
#  Date:	2015/10/07
#
#  Description:	Top level Makefile for KCWI python Scripts
#-
################################################################################

RELLIB = 

SINFILES = $(wildcard *.sin)
SOUTFILES = $(SINFILES:%.sin=%)


FILES = $(SOUTFILES)
RELBIN = $(FILES)

override SYSNAM = kss/kcwi/scripts/python/
override VERNUM = 1.0.0

#  Include general make rules (use /etc if no environment variable).

include $(KROOT)/etc/config.mk
