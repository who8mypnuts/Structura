/*  Yet another program by Bob Jenkins.  3/16/88, for 15-451 */

#ifndef STANDARD
#include "standard.h"
#endif
#ifndef POLY
#include "poly.h"
#endif

/* These macros would be different on machines with only unsigned characters */
#define p_sign(m) ((int)(m))
#define p_cast(m) ((char)(m))
#define p_add_pow(m1, m2) ((m1)+(m2))

extern int work_quietly;                /* RGS mod */

void   p_copy(inp, outp)
poly  *inp;
poly  *outp;
/*  This returns a MALLOCed copy of inp.
    It eliminates all terms with coefficients of 0. */
{
  term  *interm;
  term  *outerm;
  term  *endterm;

  if (inp->len)
  {
    outp->term = (term *)malloc((size_t)(inp->len*sizeof(term)));
    for (interm = inp->term, outerm = outp->term,
         endterm = interm+inp->len; interm != endterm; ++interm)
      if (interm->coef) *(outerm++) = *interm;
    outp->len = outerm-outp->term;
  }
  else
  {
    outp->term = (term *)0;
    outp->len  = 0;
  }
}

int num_chars_printed = 0;    /* RGS mod */

print_stuff (s, t) /* new function  RGS mod */
     char *s;
     int t;
{
  num_chars_printed += strlen (s);

  printf (s);

  if (num_chars_printed > 75 && t) {
    num_chars_printed = 0;
    printf ("\n");
  }
}

char buffer [200];   /* RGS mod */

void   p_show(p)                   /* O(|p|). This displays the polynomial p */
poly  *p;
{
  register term  *pt;
  register term  *pend;
  register int    first;
  register int    m;
  register int    l;

  printf("The polynomial is: \n");
  if (!p->len)
    {
    printf("0");
    return;
  }
  for (first = 1, pt = p->term, pend = pt+p->len; pt != pend; ++pt)
  {
    if (!pt->coef) continue;
    m = p_sign(pt->m);
    l = p_sign(pt->l);
    if (pt->coef < 0) print_stuff (" - ", 1);
    else if (!first) print_stuff (" + ", 1);
    if (pt->coef > 1 ) {
      if (pt->m || pt->l)
	sprintf(buffer, "%d*", pt->coef);  /* RGS mod */
      else 
	sprintf(buffer, "%d", pt->coef);  /* RGS mod */
      print_stuff (buffer, 0);
    }
    else if (pt->coef < (-1)) {
      if (pt->m || pt->l) 
	sprintf(buffer, "%d*", -pt->coef); /* RGS mod */
      else
	sprintf(buffer, "%d", -pt->coef); /* RGS mod */
      print_stuff (buffer, 0);
    }
    else if ((!l) && (!m)) {
      sprintf(buffer, "%d", 1);
      print_stuff (buffer, 0);
    }
    if (pt->m)
    {
      printf("M");
      if (m != 1) {
	if (m >= 2 && m <= 9)
	  sprintf(buffer, "^%d", m);   /* RGS mod */
	else
	  sprintf(buffer, "^(%d)", m);   /* RGS mod */
	print_stuff (buffer, 0);
      }
    }
    if (pt->l)
    {
      if (pt->m) printf ("*");    /* RGS mod */
      printf("L");
      if (l != 1) {
	if (l >= 2 && l <= 9)
	  sprintf(buffer, "^%d", l);   /* RGS mod */
	else
	  sprintf(buffer, "^(%d)", l);   /* RGS mod */
	print_stuff (buffer, 0);
      }
    }
    if (first) first = 0;
  }
  printf("\n");
}




void   p_term(coef, m, l, inp, outp)  /* outp = inp + {t.c=c; t.l=l; t.m=m;} */
int    coef;
int    m;
int    l;
poly  *inp;
poly  *outp;
{
  poly   p[1];
  term   t[1];

  t->coef = coef;
  t->m    = p_cast(m);
  t->l    = p_cast(l);
  p->len  = 1;
  p->term = t;
  p_add(p, inp, outp);
}



void   p_add(inp1, inp2, outp)                  /* This is like a merge sort */
poly  *inp1;
poly  *inp2;
poly  *outp;
{
  register term  *t1;
  register term  *t2;
  register term  *tout;
  register term  *end1;
  register term  *end2;
  register int    eq1;

  outp->term = (term *)malloc((size_t)((inp1->len+inp2->len)*sizeof(term)));
  t1         = inp1->term;
  end1       = t1+inp1->len;
  t2         = inp2->term;
  end2       = t2+inp2->len;
  tout       = outp->term;
  if (inp1->len && inp2->len)
  {
    for (;;)
    {
      eq1 = (t1->m == t2->m);
      if ((t1->m < t2->m) || (eq1 && (t1->l < t2->l)))
      {
        *(tout++) = *(t1++);
        if (t1 == end1) break;
      }
      else if ((!eq1) || (eq1 && (t1->l > t2->l)))
      {
        *(tout++) = *(t2++);
        if (t2 == end2) break;
      }
      else
      {
        *(tout)    = *(t1);
        tout->coef = (t1++)->coef+(t2++)->coef;
        if (!(tout++)->coef) --tout;
        if (t1 == end1) break;
        if (t2 == end2) break;
      }
    }
  }
  if (t2 == end2) while (t1 != end1) *(tout++) = *(t1++);
  else while (t2 != end2) *(tout++) = *(t2++);
  outp->len = tout-outp->term;
}



void   p_mult(inp1, inp2, outp)
poly  *inp1;
poly  *inp2;
poly  *outp;                                      /* *outp = (*inp1)*(*inp2) */
/*  Long multiplication.  My apologies, I did not do Fourier transforms. */
/*  It is assumed that inp1, inp2, and outp point to existing poly structs */
{
  poly            xinp2[1];
  poly            temp[1];
  register poly  *blank;
  register term  *t1;
  register term  *t2;
  register term  *end1;
  register term  *end2;
  register term  *tx;

  if (inp1->len > inp2->len)
  {
    blank = inp1;
    inp1  = inp2;
    inp2  = blank;
  }
  p_init(outp);
  xinp2->term = (term *)malloc((size_t)(inp2->len*sizeof(term)));
  xinp2->len  = inp2->len;
  for (t1 = inp1->term, end1 = t1+inp1->len,
       end2 = inp2->term+inp2->len; t1 < end1; ++t1)
  {
    for (t2 = inp2->term, tx = xinp2->term; t2 < end2;)
    {
      tx->m    = p_add_pow(t1->m, t2->m);
      tx->l    = p_add_pow(t1->l, t2->l);
      (tx++)->coef = t1->coef*(t2++)->coef;
    }
    p_add(outp, xinp2, temp);
    p_kill(outp);
    *outp = *temp;
  }
  p_kill(xinp2);
}




