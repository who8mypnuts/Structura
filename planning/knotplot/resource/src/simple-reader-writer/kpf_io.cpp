#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>

#include "kpf_io.h"

// KnotPlot 1.0 data files are stored using 
// IRIX byte order ("big endian")

// the following are architecture independent subroutines for
// reading and writing

void read_unsigned_short (unsigned short *v, FILE *fp) {
  unsigned char uca, ucb;
  fread (&ucb, 1, 1, fp);
  fread (&uca, 1, 1, fp);
  *v = (ucb << 8) | uca;
}

void read_int (int *v, FILE *fp) {
  unsigned char uc;
  *v = 0;
  for (int shift = 24; shift >= 0; shift -= 8) {
    fread (&uc, 1, 1, fp);
    *v |= uc << shift;
  }
}

void read_float (float *v, FILE *fp) {
  union {
    int lg;
    float flt;
  } x;

  read_int (&x.lg, fp);
  *v = x.flt;
}

int needs_swapping () {
  // returns TRUE on a "little endian" machine (Intel)
  // returns FALSE on a "big endian" machine (PowerPC, IRIX, Solaris)
  
  short super_gumby = 0x0001;
  char *swap_dat_thing = (char *) &super_gumby;
  return (int) *swap_dat_thing;
}

void read_double (double *v, FILE *fp) {
  // for efficiency it is recommended that this function 
  // be written for the computer platform being used,
  // eliminating the need for the needs_swapping() call below
  // (on the other hand, the call is likely to be much 
  // quicker than accessing the file system)

  unsigned char *ucp;
  ucp = (unsigned char *) v;

  if (needs_swapping ()) {
    for (int i = 0; i < 8; i++)
      fread (ucp + 7 - i, 1, 1, fp);
  }
  else {
    for (int i = 0; i < 8; i++)
      fread (ucp++, 1, 1, fp);
  }
}

void read_fvector (fvector v, FILE *fp) {
  read_float (v, fp);
  read_float (v + 1, fp);
  read_float (v + 2, fp);
}


void read_dvector (dvector v, FILE *fp) {
  read_double (v, fp);
  read_double (v + 1, fp);
  read_double (v + 2, fp);
}

void write_int (int *val, FILE *fp) {
  // write a big-endian int to a file
  unsigned char a, b, c, d;
  
  a = (unsigned char) (0xff & (*val) >> 24);
  b = (unsigned char) (0xff & (*val) >> 16);
  c = (unsigned char) (0xff & (*val) >> 8);
  d = (unsigned char) (0xff & (*val));

  fwrite (&a, 1, 1, fp);
  fwrite (&b, 1, 1, fp);
  fwrite (&c, 1, 1, fp);
  fwrite (&d, 1, 1, fp);
}

void write_float (float *val, FILE *fp) {
  union {
    float f;
    int i;
  } x;

  x.f = *val;
  write_int (&x.i, fp);
}

void write_fvector (fvector v, FILE *fp) {
  write_float (v, fp);
  write_float (v + 1, fp);
  write_float (v + 2, fp);
}


void write_double (double *v, FILE *fp) {
  unsigned char *ucp;
  ucp = (unsigned char *) v;

  if (needs_swapping ()) {
    for (int i = 0; i < 8; i++)
      fwrite (ucp + 7 - i, 1, 1, fp);
  }
  else {
    for (int i = 0; i < 8; i++)
      fwrite (ucp++, 1, 1, fp);
  }
}


void write_dvector (dvector v, FILE *fp) {
  write_double (v, fp);
  write_double (v + 1, fp);
  write_double (v + 2, fp);
}

#define is_chunk(x,y) (!strncmp(x,y,4))

void handle_unknown_chunk (FILE *fp, char *chunk_ID) {
  // skips over any unknown chunk
  // http://knotplot.com/manual/FileFormats.html
  // explains the three different types of chunks

  int num_to_skip;
  int data_value;

  if (isupper (chunk_ID [0])) {
    if (isupper (chunk_ID [1])) {
      read_int (&num_to_skip, fp);
      while (num_to_skip--)
	fgetc (fp);
    }
    else {
      read_int (&data_value, fp);
    }
  }
}

int handle_LOCC_chunk (FILE *fp, dvector *vertex, int max_num_vert) { // return number of vertices read
  int S, N;
  fvector loc, epsilon;
  float xprev, yprev, zprev;
  float x, y, z;
  signed char xincr, yincr, zincr;

  read_int (&S, fp);
  N = (S - 21) / 3;   // Number of vertices in this section
  if (N > max_num_vert) {
    fprintf (stderr, "too many vertices (%d), can only handle %d!!\n", N, max_num_vert);
    return 0;
  }

  read_fvector (epsilon, fp);  // vector offset
  read_fvector (loc, fp);      // starting coordinate

  for (int i = 0; i < N; i++) {
    if (i == 0) {
      x = loc [0];
      y = loc [1];
      z = loc [2];
    }
    else {
      fread (&xincr, 1, 1, fp);
      fread (&yincr, 1, 1, fp);
      fread (&zincr, 1, 1, fp);

      vertex [i][0] = x = xprev + (float) xincr * epsilon [0];
      vertex [i][1] = y = yprev + (float) yincr * epsilon [1];
      vertex [i][2] = z = zprev + (float) zincr * epsilon [2];
    }

    xprev = x;
    yprev = y;
    zprev = z;
  }
  return N;
}

int handle_LOCS_chunk (FILE *fp, dvector *vertex, int max_num_vert) { // return number of vertices read
  int i, S, N;
  unsigned short usx, usy, usz;
  fvector offset;
  float scale_factor;

  // LOCS files take up about half the space of LOCF files
  // without visible differences (in most cases). 

  read_int (&S, fp);
  N = (S - 16) / 6;    // Number of vertices in this section

  read_float (&scale_factor, fp);
  read_fvector (offset, fp);

  for (i = 0; i < N; i++) {
    read_unsigned_short (&usx, fp);
    read_unsigned_short (&usy, fp);
    read_unsigned_short (&usz, fp);

    vertex [i][0] = scale_factor * ((double) usx) + offset [0];
    vertex [i][1] = scale_factor * ((double) usy) + offset [1];
    vertex [i][2] = scale_factor * ((double) usz) + offset [2];
  }

  return N;
}

int handle_LOCF_chunk (FILE *fp, dvector *vertex, int max_num_vert) { // return number of vertices read
  int S, N, i;
  fvector v;

  read_int (&S, fp);
  N = S / 12;    // Number of vertices in this chunk
  if (N > max_num_vert) {
    fprintf (stderr, "too many vertices (%d), can only handle %d!!\n", N, max_num_vert);
    return 0;
  }

  for (i = 0; i < N; i++) {
    read_fvector (v, fp);
    vertex [i][0] = (double) v [0];
    vertex [i][1] = (double) v [1];
    vertex [i][2] = (double) v [2];
  }

  return N;
}

int handle_LOCD_chunk (FILE *fp, dvector *vertex, int max_num_vert) { // return number of vertices read
  int S, N, i;
  double x, y, z;

  read_int (&S, fp);

  N = S / 24;    // Number of vertices in this chunk
  if (N > max_num_vert) {
    fprintf (stderr, "too many vertices (%d), can only handle %d!!\n", N, max_num_vert);
    return 0;
  }

  for (i = 0; i < N; i++) 
    read_dvector (vertex [i], fp);

  return N;
}

int minimal_read_KnotPlot_file_into_buffer (char *filename,       // file with knot coordinate data
					    dvector *vertex,      // array of vertices
					    int max_num_vert) {   // maximum number of vertices allowed

  // returns number of vertices successfully read

  /*
    
    NOTE: This is the simplest possible reader for KnotPlot 1.0 binary files. 
    It has the following limitations:
    
    Only works for single component knots that are not open-ended. 

    Only handles LOCC, LOCS, LOCF and LOCD vertex chunks.
    Ignores (skips) most data chunks, including Attr and comp.
    
    Only supports one vertex chunk.

    For more information on the KnotPlot 1.0 file format, see http://knotplot.com/manual/FileFormats.html

  */

  char chunk_ID [5];
  FILE *fp;
  
  fp = fopen (filename, "rb");
  
  if (!fp) {
    fprintf (stderr, "Can't open file `%s'!\n", filename);
    return 0;
  }

  // determine what kind of file it is

  char comment [20];
  fread (comment, 12, 1, fp);

  if (strncmp (comment, "KnotPlot 1.0", 12)) {
    fclose (fp);
    fprintf (stderr, "File `%s' is not a KnotPlot file!\n", 
	     filename);
    return 0;
  }

  // If we get this far, then we have a KnotPlot 1.0 format file
  // Scan to control L and then read one extra character

  while (fgetc (fp) != 12);  // Empty loop to scan to control-L
  fgetc (fp);                // This character is arbitrary, read it and ignore

  int N_vert_read = 0;
  bool looping = true;

  do {
    if (fread (chunk_ID, 1, 4, fp) != 4) {
      fprintf (stderr, " *** End of data before end of file `%s'\n",
	       filename);
      fclose (fp);
      return 0;
    }
    chunk_ID [4] = '\0';

    // note that comp and Attr chunks will be ignored by this function

    if (is_chunk (chunk_ID, "endf")) {  // end of file chunk
      fclose (fp); 
      looping = false;
    }
    if (is_chunk (chunk_ID, "LOCF"))
      N_vert_read = handle_LOCF_chunk (fp, vertex, max_num_vert);
    else if (is_chunk (chunk_ID, "LOCS"))
      N_vert_read = handle_LOCS_chunk (fp, vertex, max_num_vert);
    else if (is_chunk (chunk_ID, "LOCC"))
      N_vert_read = handle_LOCC_chunk (fp, vertex, max_num_vert);
    else if (is_chunk (chunk_ID, "LOCD"))
      N_vert_read = handle_LOCD_chunk (fp, vertex, max_num_vert);
    else 
      handle_unknown_chunk (fp, chunk_ID);
    
  } while (looping);
  
  return N_vert_read;  
}

bool minimal_write_buffer_to_KnotPlot_file (dvector *vertex,      // vertex array
					    int Nvertices,        // number of vertices in vertex array
					    char *filename) {     // file to contain knot coordinate data
  // write a KnotPlot file in LOCD format (all coordinates stored as 8-byte doubles)
  // return true if file successfully written, false otherwise

  FILE *fp = fopen (filename, "wb");
  if (!fp) {
    fprintf (stderr, "can't open file `%s' for output\n", filename);
    return false;
  }

  fprintf (fp, "KnotPlot 1.0  %c\n", (char) 12);  // KnotPlot file header followed by a Control-L

  fprintf (fp, "comp");     // signals start of a new component

    /* The data will be written using a `LOCD' (location double) field
       of size 24 * Nvertices (8 is sizeof (double) 
       and each bead has 3 coords).

       Note that this 24 * Nvertices bytes does not include the four byte field
       name LOCD and the four bytes used to store the value of num_bytes.

       Total size of the field is therefore 24 * Nvertices + 8 bytes. */

  int num_bytes = 24 * Nvertices;
  
  fprintf (fp, "LOCD");        // beginning of vertex chunk
  write_int (&num_bytes, fp);
  
  for (int i = 0; i < Nvertices; i++) 
    write_dvector (vertex [i], fp);
  
  // write an `endf' chunk to indicate end of file
  
  fprintf (fp, "endf");
  fclose (fp);

  return true;
}

bool minimal_write_buffer_to_KnotPlot_file (fvector *vertex,      // vertex array
					    int Nvertices,        // number of vertices in vertex array
					    char *filename) {     // file to contain knot coordinate data
  // write a KnotPlot file in LOCF format (all coordinates stored as 4-byte floats)
  // return true if file successfully written, false otherwise

  FILE *fp = fopen (filename, "wb");
  if (!fp) {
    fprintf (stderr, "can't open file `%s' for output\n", filename);
    return false;
  }

  fprintf (fp, "KnotPlot 1.0  %c\n", (char) 12);  // KnotPlot file header followed by a Control-L

  fprintf (fp, "comp");     // signals start of a new component

    /* The data will be written using a `LOCF' (location float) field
       of size 12 * Nvertices (4 is sizeof (float) 
       and each bead has 3 coords).

       Note that this 12 * Nvertices bytes does not include the four byte field
       name LOCD and the four bytes used to store the value of num_bytes.

       Total size of the field is therefore 12 * Nvertices + 8 bytes. */

  int num_bytes = 12 * Nvertices;
  
  fprintf (fp, "LOCF");        // beginning of vertex chunk
  write_int (&num_bytes, fp);
  
  for (int i = 0; i < Nvertices; i++) 
    write_fvector (vertex [i], fp);
  
  // write an `endf' chunk to indicate end of file
  
  fprintf (fp, "endf");
  fclose (fp);

  return true;
}
