/* By Bob Jenkins, revamped August 1990, in relation to my masters thesis */

#ifndef STANDARD
#include "standard.h"
#endif
#ifndef POLY
#include "poly.h"
#endif
#ifndef KNOT
#include "knot.h"
#endif
#ifndef ORDER
#include "order.h"
#endif
#ifndef BOUND
#include "bound.h"
#endif
#ifndef MODEL
#include "model.h"
#endif
#ifndef CONTROL
#include "control.h"
#endif

static void c_do_one_weave(/*_ weave *oldweave, weave *newweaves _*/);

int work_quietly = 0;                /* RGS mod */


/* these variables are global, and may be because nobody ever changes them */
void   c_init()
{
  extern poly   llplus;
  extern poly   lplusm;
  extern poly   lminusm;
  extern poly   llminus;
  extern poly   mll;
  extern int    total_weaves_handled;
  poly          blank[1];

  p_init(blank);
  p_term((-1), 0, 2, blank, &llplus);
  p_term((-1), 1, 1, blank, &lplusm);
  p_term((-1), 1, (-1), blank, &lminusm);
  p_term((-1), 0, (-2), blank, &llminus);
  p_init(&mll);
  p_term((-1), (-1), 1, &mll, blank);
  p_kill(&mll);
  p_term((-1), (-1), (-1), blank, &mll);
  p_kill(blank);
  total_weaves_handled = 0;
}


void       c_handle(list, thisweave, newweaves)
int       *list;                  /* matching of inputs/outputs in thisweave */
weave     *thisweave;                             /* the weave to be handled */
weave     *newweaves;                                  /* all the new weaves */
/*  Given a simple weave WEAVE, this figures out what BODY should be,
    and adds the weave to the list NEWWEAVES */
/*  Rather than keeping a heap or tree of new weaves, I have assumed that every
    permutation will probably be used.  I use a total ordering on the
    set of permutations as an index to my array of all possible new weaves. */
/*  This is one of the most used procedures in this program */
{
  poly            temp[1];
  register int    i;
  register int    j;
  register int    k;
  register int    sum;
  register int    prod;
  register int    count;
  register int    boundary;
  int             inputs[BIGWEAVE];

  ++total_weaves_handled;
  boundary = 0;
  /*  Make a list of which inputs go to which outputs; compute *boundary* */
  for (i = newin, j = newcross; --i >= 0;)
  {
    while (!going_in[--j]);
    inputs[i] = list[j];
    boundary = inputs[i]+(boundary << 4);
  }

  /*  Determine this weave's index in the array of newweaves */
  sum  = 0;
  prod = 1;
  for (i = 1; i < newin; ++i)
  {
    prod *= i;
    count = 0;
    for (j = i, k = inputs[i]; --j >= 0;) if (k > inputs[j]) ++count;
    sum += count*prod;
  }

  newweaves[sum].boundary = boundary;
  p_add(&newweaves[sum].tag, &thisweave->tag, temp);
  p_kill(&thisweave->tag);
  p_kill(&newweaves[sum].tag); 
  newweaves[sum].tag = *temp;
}



/*  This does all the weave manipulation associated with adding a single
    crossing to a single weave.                                          */
static void c_do_one_weave(oldweave, newweaves)
weave  *oldweave;           /* the single weave to apply the instructions to */
weave  *newweaves;                            /* the array of all new weaves */
{
  int     one[1];
  int     two[1];
  int     i;
  int     j;
  ub4     boundary;
  weave   other[1];
  poly    temp[1];

  *one   = 0;
  *two   = 0;
  /*================================================== undecode the boundary */
  boundary = oldweave->boundary;
  for (j = 0, i = 0; i < oldin; i++)
  {
    while (!old_going_in[j]) j++;                     /* find the next input */
    list[j]       = boundary & 15;                     /* set boundary input */
    list[list[j]] = j;                                /* set boundary output */
    boundary    >>= 4;
    j++;
  }

  /*=============================================== Try to handle it quickly */
  if (plan.reductions == 0) b_no_pairs(list, list2, one, two);
  else if (plan.which >= 0) b_one_pair(list, list2, one, two);

  /*======================= Is the old weave replaced by only one new weave? */
  if (*one)
  {
    c_handle(list, oldweave, newweaves);
    return;
  }

  /*=========================== Is the old weave replaced by two new weaves? */
  if (*two)
  {
    if (left)
    {
      p_mult(&lplusm, &oldweave->tag, &other->tag);
      p_mult(&llplus, &oldweave->tag, temp);
      p_kill(&oldweave->tag);
      oldweave->tag = *temp;
    }
    else
    {
      p_mult(&lminusm, &oldweave->tag, &other->tag);
      p_mult(&llminus, &oldweave->tag, temp);
      p_kill(&oldweave->tag);
      oldweave->tag = *temp;
    }
    c_handle(list, oldweave, newweaves);
    c_handle(list2, other, newweaves);
    return;
  }

  /*=================== The old weave is replace by up to 2^(n-1) new weaves */
  m_model_weave(list, oldweave, newweaves);
}




/*=============================================================================
  NAME:
    C_FOLLOW()
  FUNCTION:
    Given a list of *crossings* instructions *l*, follow them and produce the
    polynomial *answer* which is the HOMFLY polynomial for the original link.
  METHOD:
    For each instruction,
      Break the instruction into (add crossing/remove pair), (remove pair), ...
      (Each operation changes the size of the weave boundary from n inputs
       to either n+2 (add), n (add/remove), or n-2 (remove) crossings)
      For each of the (oldn/2)! old weaves, apply the instruction and merge
       the result into the list of (newn/2)! new weaves.
    At the end (n/2)=1, so there are (n/2)! = 1 final weaves, and the
     tag associated with that weave is *answer* .
  NOTES:
    The tags for the weaves are being freed immediately after they are
    last used by whichever procedure last uses them.  They are not being
    freed in the procedures which MALLOC them.  Before you change where
    things are freed, think.
=============================================================================   */
void       c_follow(l, crossings, answer)
instruct  *l;
int        crossings;
poly     **answer;
{
  int        i,
             j,
             k,
             oldfact,
             newfact;
  weave     *oldweaves,
            *newweaves;
  extern instruct plan;

  /*============================================== Set up the starting weave */
  oldweaves             = (weave *)malloc(sizeof(weave));
  oldweaves[0].boundary = 1;
  oldweaves->tag.len = 0;
  p_term(1, 0, 0, &oldweaves->tag,
         &oldweaves->tag);                      /* tag of original link is 1 */

  /*============== For each crossing, follow the instructions on every weave */
  for (i = 0; i < crossings; i++)
  {
    /*===== Handle adding the crossing, plus the first boundary pair removal */
    plan            = l[i];
    plan.reductions = (plan.reductions > 0);
    plan.newn       = plan.oldn+2-2*plan.reductions;
    b_manip(oldweaves);
    for (j = 2, newfact = 1; j <= newin; newfact *= (j++)) ;
    newweaves = (weave *)malloc((sizeof(weave))*newfact);
    for (j = 0; j < newfact;) newweaves[j++].tag.len = 0;
    for (j = 2, oldfact = 1; j <= oldin; oldfact *= (j++)) ;
    for (j = 0; j < oldfact; j++)
      if (oldweaves[j].tag.len)
      {
        c_do_one_weave((oldweaves+j), newweaves);
      }
    free(oldweaves);
    oldweaves = newweaves;

    /*=========== Remove any other pairs of boundary crossings one at a time */
    for (k = 1; k < l[i].reductions; k++)
    {
      oldfact   = newfact;
      plan.which = (-1);
      plan.r0[0] = l[i].r0[k];
      plan.r1[0] = l[i].r1[k];
      plan.oldn  = plan.newn;
      plan.newn -= 2;
      b_manip(oldweaves);
      newfact   = oldfact/oldin;
      newweaves = (weave *)malloc((sizeof(weave))*newfact);
      for (j = 0; j < newfact;) newweaves[j++].tag.len = 0;
      for (j = 0; j < oldfact; j++)
        if (oldweaves[j].tag.len)
        {
          c_do_one_weave((oldweaves+j), newweaves);
        }
      free(oldweaves);
      oldweaves = newweaves;
    }

    /*======================== Gloat about how little work needed to be done */

    if (!work_quietly)  /* RGS mod */
      printf("strings: %d  max weaves: %d  total weaves handled: %d\n",
	     newin, newfact, total_weaves_handled);
  }
  if (!work_quietly)  /* RGS mod */
    printf("A total of %d weaves were considered\n", total_weaves_handled);
  
  /*=============================== Deposit the final polynomial in *answer* */
  *answer = &oldweaves->tag;
}

#include "normalizations.h"

main(argc, argv)    /* RGS mod */
     int argc;
     char **argv;
{
  crossing  *knot[1];       /* link for which to calculate HOMFLY polynomial */
  instruct  *plan[1];                                /* list of instructions */
  poly      *answer[1];           /* HOMFLY polynomial for the original link */
  int        crossings[1];                    /* number of crossings in link */
  int        common_sense;
  int read_from_stdin = 0, arg;             /* RGS mod */
  int normalization = HOMFLY_LM;            /* RGS mod */

  for (arg = 1; arg < argc; arg++) {                       /* RGS mod */
    if (!strcmp (argv [arg], "-stdin"))
      read_from_stdin = 1;
    else if (!strcmp (argv [arg], "-quiet"))
      work_quietly = 1;
    else if (!strcmp (argv [arg], "-tz"))
      normalization = HOMFLY_TZ;
    else if (!strcmp (argv [arg], "-lm"))
      normalization = HOMFLY_LM;
    else if (!strcmp (argv [arg], "-alex"))
      normalization = HOMFLY_ALEX;
    else if (!strcmp (argv [arg], "-jones"))
      normalization = HOMFLY_JONES;
  }

  c_init();                                          /* initialize variables */
  k_read(crossings, knot, read_from_stdin);              /* read in the link */  /* RGS mod */
  o_make(*knot, *crossings, plan);       /* make plan for attacking the link */
  c_follow(*plan, *crossings, answer);                    /* follow the plan */
  p_show(*answer);                                     /* display the answer */

  free(*knot);
  free(*plan);
  p_kill(*answer);
  /* If you want to be thorough, free the polynomials defined in c_init */
  return 1;
}





