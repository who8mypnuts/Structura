CC = g++

CFLAGS = $(VOLTA_CFLAGS) -Wno-write-strings

.SUFFIXES: .cpp

.cpp.o:
	$(CC) $(CFLAGS) -c $*.cpp -o $*.o

demo: demo.o
	cc -o demo demo

clean:
	touch dum demo0.kps
	/bin/rm demo?.kps demo??.kps
	/bin/rm *dum*
	touch dum~
	/bin/rm *~
