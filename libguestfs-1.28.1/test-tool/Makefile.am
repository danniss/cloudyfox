# libguestfs
# Copyright (C) 2009-2014 Red Hat Inc.
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

include $(top_srcdir)/subdir-rules.mk

EXTRA_DIST = libguestfs-test-tool.pod

CLEANFILES = libguestfs-test-tool.1 stamp-libguestfs-test-tool.pod

bin_PROGRAMS = libguestfs-test-tool
man_MANS = libguestfs-test-tool.1

libguestfs_test_tool_SOURCES = test-tool.c

libguestfs_test_tool_CPPFLAGS = \
	-I$(top_srcdir)/src -I$(top_builddir)/src \
	-I$(top_srcdir)/gnulib/lib -I$(top_builddir)/gnulib/lib \
	-DGUESTFS_WARN_DEPRECATED=1 \
	-DLOCALEBASEDIR=\""$(datadir)/locale"\"

libguestfs_test_tool_CFLAGS = \
	$(WARN_CFLAGS) $(WERROR_CFLAGS)

libguestfs_test_tool_LDADD = \
	$(top_builddir)/src/libguestfs.la \
	$(top_builddir)/gnulib/lib/libgnu.la

libguestfs-test-tool.1 $(top_builddir)/html/libguestfs-test-tool.1.html: stamp-libguestfs-test-tool.pod

stamp-libguestfs-test-tool.pod: libguestfs-test-tool.pod
	$(PODWRAPPER) \
	  --man libguestfs-test-tool.1 \
	  --html $(top_builddir)/html/libguestfs-test-tool.1.html \
	  --license GPLv2+ \
	  $<
	touch $@

check-valgrind:
	$(top_builddir)/run --test @VG@ ./libguestfs-test-tool
