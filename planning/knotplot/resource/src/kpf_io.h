#ifndef KPF_IO_H
#define KPF_IO_H

typedef unsigned short usvector [3];
typedef float  fvector [3];
typedef double dvector [3];

void read_unsigned_short (unsigned short *, FILE *);
void read_int (int *, FILE *);
void read_float (float *, FILE *);
void read_double (double *, FILE *);
void read_fvector (fvector, FILE *);
void read_dvector (dvector v, FILE *fp);


void write_int (int *val, FILE *fp);
void write_float (int *val, FILE *fp);
void write_double (double *v, FILE *fp);
void write_fvector (fvector v, FILE *fp);
void write_dvector (dvector v, FILE *fp);

int minimal_read_KnotPlot_file_into_buffer (char *filename, dvector *vertex, int max_num_vert);

bool minimal_write_buffer_to_KnotPlot_file (dvector *vertex, int Nvertices, char *filename); 
bool minimal_write_buffer_to_KnotPlot_file (fvector *vertex, int Nvertices, char *filename); 


#endif

