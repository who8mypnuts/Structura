CC = g++

.SUFFIXES: .cpp

.cpp.o:
	$(CC) $(CFLAGS) -c $*.cpp -o $*.o

all:
	make kpfread2
	make kpfwrite
	make kpfwritef

kpfread2: kpfread2.o kpf_io.o
	$(CC) -o kpfread2 kpfread2.o kpf_io.o
	strip kpfread2

kpfwrite: kpfwrite.o kpf_io.o
	$(CC) -o kpfwrite kpfwrite.o kpf_io.o
	strip kpfwrite

kpfwritef: kpfwritef.o kpf_io.o
	$(CC) -o kpfwritef kpfwritef.o kpf_io.o
	strip kpfwritef

clean:
	touch dum.o dum~
	/bin/rm *.o *~
