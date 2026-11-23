#include <gl/gl.h>
#include <device.h>
#include <sys/time.h>
#include <math.h>
#include <stdio.h> 

#define PBM '4'
#define PGM '5'
#define PPM '6'

main (argc, argv)
  int argc;
  char **argv;
{
  FILE *fp;
  long xsize, ysize;
  long xorig, yorig;
  long pix_count;
  int x, y, index = 1, i;
  char file_type;
  unsigned char r, g, b;
  unsigned long *data;
  Screencoord x1, x2, y1, y2;
  int looping = TRUE, noborder_flag = FALSE, pref_pos_flag = FALSE;
  int show_n_go = FALSE, give_info = FALSE, keep_data = FALSE;
  int keep_foreground = FALSE;
  long event;
  short val;
  unsigned long *frame;

  if (argc < 2) {
    fprintf (stderr, "\n\nUSAGE: %s [options] PNMfile\n\n", argv [0]);
    fprintf (stderr, "   Options:\n\n");
    fprintf (stderr, "          -pos xloc yloc     (window origin)\n");
    fprintf (stderr, "          -noborder          (borderless window)\n");
    fprintf (stderr, "          -foreground        (keep process in foreground)\n\n");
    exit (102);
  }


  for (i = 1; i < argc - 1; i++) {
    if (!strcmp (argv [i], "-noborder")) 
      noborder_flag = TRUE;
    else if (!strcmp (argv [i], "-pos")) {
      xorig = atoi (argv [i + 1]);
      yorig = atoi (argv [i + 2]);
      i += 2;
      pref_pos_flag = TRUE;
    }
    else if (!strcmp (argv [i], "-showngo"))
      show_n_go = TRUE;
    else if (!strcmp (argv [i], "-foreground"))
      keep_foreground = TRUE;
    else if (!strcmp (argv [i], "-info"))
      give_info = TRUE;
    else if (!strcmp (argv [i], "-keep"))
      keep_data = TRUE;
  }
    

  if (!open_pnm (&fp, argv [argc - 1], &xsize, &ysize, &file_type)) exit (-1);

  if (keep_data) {
    fprintf (stderr, "Attempting to allocate %d bytes ... ",
	     xsize * ysize * sizeof (unsigned long));
    fflush (stderr);
    frame = (unsigned long *) calloc (xsize * ysize, sizeof (unsigned long));
    if (frame == (unsigned long *) NULL) {
      fprintf (stderr, "\n\nCouldn't get memory, exiting.\n\n");
      exit (1022);
    }
  }

#ifdef IBM
  if (show_n_go) 
    foreground ();
#endif

  if (keep_foreground)
    foreground ();

  if (noborder_flag)
    noborder ();
  if (pref_pos_flag) 
    prefposition (xorig, xorig + xsize - 1,
		  yorig, yorig + ysize - 1);
  else
    prefsize (xsize, ysize);
  winopen (argv [1]);

  if (give_info) {
    getorigin (&xorig, &yorig);
    fprintf (stderr, "-pos %d %d\n", xorig, yorig);
  }
  x1 = 0;
  x2 = xsize - 1;
  RGBmode ();
  singlebuffer ();
  gconfig ();
  zbuffer (FALSE);
  cpack (0x00);
  clear ();
  cursoff ();
  data = (unsigned long *) calloc (xsize, sizeof (unsigned long));
  
  switch (file_type) {
  case PPM:
    for (y = 0, y1 = ysize - 1; y < ysize; y++, y1--) {
      for (x = 0; x < xsize; x++) {
	fread (&r, 1, sizeof (unsigned char), fp);
	fread (&g, 1, sizeof (unsigned char), fp);
	fread (&b, 1, sizeof (unsigned char), fp);
	data [x] = (b << 16) | (g << 8) | r;
      }
      lrectwrite (x1, y1, x2, y1, data);
    }
    break;
  case PGM:
    for (y = 0, y1 = ysize - 1; y < ysize; y++, y1--) {
      for (x = 0; x < xsize; x++) {
	fread (&r, 1, sizeof (unsigned char), fp);
	g = b = r;
	data [x] = (b << 16) | (g << 8) | r;
      }
      lrectwrite (x1, y1, x2, y1, data);
    }
    break;
  case PBM:
    for (y = 0, y1 = ysize - 1; y < ysize; y++, y1--) {
      for (x = 0, pix_count = 0; x < xsize; x++, pix_count++) {
	if (pix_count % 8 == 0)
	  fread (&r, 1, sizeof (unsigned char), fp);
	if (r & 0x80)
	  b = 0;
	else 
	  b = 255;
	r <<= 1;
	data [x] = (b << 16) | (b << 8) | b;
      }
      lrectwrite (x1, y1, x2, y1, data);
    }
    break;
  }

  if (show_n_go) 
    exit (1);

  qdevice (ESCKEY);
  while (looping) {
    switch (event = qread (&val)) {
    case ESCKEY:
      if (!val)
	looping = FALSE;
      break;
    }
  }
}

open_pnm (pfp, file_name, pxs, pys, ftype)
     FILE **pfp;
     char *file_name;
     long *pxs, *pys;
     char *ftype;
{
  char in_line [300];
  FILE *fp;

  fp = fopen (file_name, "r");
  if (fp == (FILE *) NULL) {
    fprintf (stderr, "Can't open file `%s'.\n", file_name);
    return FALSE;
  }
  *pfp = fp;
  
  fgets (in_line, 30, fp);
  *ftype = in_line [1];
  if (in_line [0] != 'P' || !(*ftype == PGM || 
			      *ftype == PBM ||
			      *ftype == PPM)) {
    fprintf (stderr, "File `%s' not a PBM, PGM, or PPM file.\n", file_name);
    return FALSE;
  }
  get_a_line (in_line, 300, fp);
  sscanf (in_line, "%d%d", pxs, pys);

  if (*ftype != PBM)
    get_a_line (in_line, 300, fp);

  return TRUE;
}


get_a_line (in_line, s, fp)
     char *in_line;
     int s;
     FILE *fp;
{
  int looping = TRUE;
  do {
    fgets (in_line, 300, fp);
    if (!(in_line [0] == '\n' || in_line [0] == '#'))
      looping = FALSE;
  } while (looping);
}




