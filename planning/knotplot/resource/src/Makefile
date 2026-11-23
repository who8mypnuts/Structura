CC = g++

.SUFFIXES: .cpp

.cpp.o:
	$(CC) $(CFLAGS) -c $*.cpp -o $*.o

all: kpfread2 kpfwrite kpfwritef kpfread kpfsnoop kpfcat write-COMM simple

kpfread2: kpfread2.o kpf_io.o
	$(CC) -o kpfread2 kpfread2.o kpf_io.o
	strip kpfread2

kpfwrite: kpfwrite.o kpf_io.o
	$(CC) -o kpfwrite kpfwrite.o kpf_io.o
	strip kpfwrite

kpfwritef: kpfwritef.o kpf_io.o
	$(CC) -o kpfwritef kpfwritef.o kpf_io.o
	strip kpfwritef

kpfread: kpfread.o kpf_io.o
	$(CC) -o kpfread kpfread.o kpf_io.o
	strip kpfread

kpfsnoop: kpfsnoop.o
	$(CC) -o kpfsnoop kpfsnoop.o
	strip kpfsnoop

kpfcat: kpfcat.o
	$(CC) -o kpfcat kpfcat.o
	strip kpfcat
	chmod ugo+rx kpfcat

simple: simple.o
	$(CC) -o simple simple.o
	strip simple
	chmod ugo+rx simple

multiif: multiif.o
	$(CC) -o multiif multiif.o
	strip multiif
	mv multiif $(BINDIR)

random: random.o
	$(CC) -o random random.o -lm
	strip random
	chmod ugo+rx random

writeFRAC: writeFRAC.o
	$(CC) -o writeFRAC writeFRAC.o -lm
	strip writeFRAC
	chmod ugo+rx writeFRAC

write-COMM: write-COMM.o
	$(CC) -o write-COMM write-COMM.o

eqspace: eqspace.o
	$(CC) -o eqspace eqspace.o -lm
	strip eqspace
	chmod ugo+rx eqspace

ginv: 
	$(CC) -o ginv ginv.c -lfm_s -lgl_s -lc_s
	strip ginv

ppm2cur: ppm2cur.o 
	cc -o ppm2cur ppm2cur.o -lgl_s
	strip ppm2cur
	chmod ugo+rx ppm2cur

showpnm: showpnm.o 
	cc -o showpnm showpnm.o -lgl_s
	strip showpnm
	chmod ugo+rx showpnm

alex: alex.o
	$(CC) -o alex alex.o
	strip alex
	mv alex $(KPBINDIR)
	chmod ugo+rx $(KPBINDIR)/alex

cat4dsurf: cat4dsurf.o
	cc -o cat4dsurf cat4dsurf.o -lm
	strip cat4dsurf
	chmod ugo+rx cat4dsurf


knot-table: knot-table.o
	$(CC) -o knot-table knot-table.o 
	strip knot-table


clean:
	touch dum.o dum.~ x
	/bin/rm *.o *~ ?
	touch kpfread2 kpfwrite kpfwritef kpfread kpfsnoop kpfcat write-COMM simple unknot
	/bin/rm kpfread2 kpfwrite kpfwritef kpfread kpfsnoop kpfcat write-COMM simple unknot

