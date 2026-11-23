CC	= gcc
CFLAGS	= -O2 -fsigned-char
LD	= gcc
LDFLAGS	= -s
LIBS	= 

all:	homfly

install:
	make homfly
	mv homfly ../../$(MACHINE)/homfly
	chmod ugo+rx ../../$(MACHINE)/homfly

homfly: poly.o link.o knot.o order.o bound.o model.o control.o
	$(LD) $(LDFLAGS) -o homfly poly.o link.o knot.o order.o \
		bound.o model.o control.o $(LIBS)
	strip homfly

.c.o:
	$(CC) -c $(CFLAGS) -o $@ $*.c

poly.o: standard.h order.h control.h bound.h poly.c

link.o: link.h link.c

knot.o: standard.h link.h knot.h knot.c

order.o: knot.h order.h order.c

bound.o: standard.h order.h control.h bound.h bound.c

model.o: poly.h order.h bound.h control.h model.h model.c

control.o: standard.h poly.h knot.h order.h bound.h model.h control.h control.c

clean:
	rm -f *.o *~ core a.out

clobber: clean
	rm -f homfly
