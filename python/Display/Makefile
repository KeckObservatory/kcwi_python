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

DATFILES = kcwi-ds9-b1.reg kcwi-ds9-b2.reg

FILES = $(SOUTFILES)
RELBIN = $(FILES) $(DATFILES)

override SYSNAM = kss/kcwi/scripts/python/
override VERNUM = 1.0.0

#  Include general make rules (use /etc if no environment variable).

include $(KROOT)/etc/config.mk
