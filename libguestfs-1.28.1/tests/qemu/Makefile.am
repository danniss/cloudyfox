# libguestfs
# Copyright (C) 2011 Red Hat Inc.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

# Safety and liveness tests of components that libguestfs depends upon
# (not of libguestfs itself).  Mainly this is for qemu and the kernel.
# This test is the first to run.

include $(top_srcdir)/subdir-rules.mk

TESTS = \
	qemu-liveness.sh \
	qemu-snapshot-isolation.sh \
	qemu-force-tcg.sh

TESTS_ENVIRONMENT = $(top_builddir)/run --test

EXTRA_DIST = \
	$(TESTS) \
	qemu-boot.c \
	qemu-speed-test.c

# qemu-boot & qemu-speed-test are built but not run by default as they
# are mainly qemu & kernel diagnostic tools.

check_PROGRAMS = qemu-boot qemu-speed-test

qemu_boot_SOURCES = \
	../../df/estimate-max-threads.c \
	../../df/estimate-max-threads.h \
	qemu-boot.c
qemu_boot_CPPFLAGS = \
	-DGUESTFS_PRIVATE=1 \
	-I$(top_srcdir)/gnulib/lib -I$(top_builddir)/gnulib/lib \
	-I$(top_srcdir)/src -I$(top_builddir)/src \
	-I$(top_srcdir)/df
qemu_boot_CFLAGS = \
	-pthread \
	$(WARN_CFLAGS) $(WERROR_CFLAGS)
qemu_boot_LDADD = \
	$(top_builddir)/src/libutils.la \
	$(top_builddir)/src/libguestfs.la \
	$(LIBXML2_LIBS) \
	$(LIBVIRT_LIBS) \
	$(top_builddir)/gnulib/lib/libgnu.la

qemu_speed_test_SOURCES = \
	qemu-speed-test.c
qemu_speed_test_CPPFLAGS = \
	-DGUESTFS_PRIVATE=1 \
	-I$(top_srcdir)/gnulib/lib -I$(top_builddir)/gnulib/lib \
	-I$(top_srcdir)/src -I$(top_builddir)/src \
	-I$(top_srcdir)/df
qemu_speed_test_CFLAGS = \
	$(WARN_CFLAGS) $(WERROR_CFLAGS)
qemu_speed_test_LDADD = \
	$(top_builddir)/src/libutils.la \
	$(top_builddir)/src/libguestfs.la \
	$(LIBXML2_LIBS) \
	$(LIBVIRT_LIBS) \
	$(top_builddir)/gnulib/lib/libgnu.la
