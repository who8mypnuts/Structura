#include <math.h>
#include <stdio.h>
#include <sys/time.h>

long 
    _Rand__SEED = 1, 	
    _Rand_a = 16807,
    _Rand_m = 2147483647,
    _Rand_q = 127773,
    _Rand_r = 2836,
    _Rand_lo, _Rand_hi, _Rand_test;

long Rand()
{
  _Rand_hi = _Rand__SEED / _Rand_q;
  _Rand_lo = _Rand__SEED % _Rand_q;
  _Rand_test = _Rand_a * _Rand_lo - _Rand_r * _Rand_hi;
  _Rand__SEED = (_Rand_test > 0 ) ? _Rand_test : _Rand_test + _Rand_m;
  return _Rand__SEED;
}

int extra;

void set_sRand_seed_to_clocktime ()
{
  long the_time;
  long pid, newpid;
  void sRand ();
  time (&the_time);

  /* Also XOR with the process ID (this is really sneaky!). */

  pid = (long) getpid ();
  extra = pid % 100;
  newpid = pid << 16;         

  the_time ^= newpid;

  sRand (the_time);
}

void sRand (seed)
     long seed;
{
   int i, ncycles;

   ncycles = 102 + extra;

   if (seed < 0) seed = -seed;
   _Rand__SEED = seed + 2;
   
   /* 
     Cycle the random number generator a few times to get rid of
     any funny business.
     */

   for (i = 0; i < ncycles; i++) Rand ();
}

float rand_uniform ()
{  
  long Rand ();
  return (float) Rand () / 2147483647.0;
}

/* function rand_integer (low, high) returns a random integer 
   >= `low' and < `high'.
   */

rand_integer (low, high)
     int low, high;
{
  extern float rand_uniform ();
  
  return (int) ((float) (high - low) * rand_uniform () + (float) low);
}

main (argc, argv)
     int argc;
     char **argv;
{
  long s, i, number;

  if (argc < 2) {
    fprintf (stderr, "\n");
    fprintf (stderr, "USAGE:  random N [[seed] number]\n");
    fprintf (stderr, "                       \n");
    fprintf (stderr, "   returns a random integer between 0 and N - 1\n");
    fprintf (stderr, 
	     "   inclusive.  If seed is omitted or zero, then the system\n");
    fprintf (stderr, "   clock is used for a seed.\n\n");
    exit (-1);
  }

  if (argc > 2) {
    s = atoi (argv [2]);
    if (s)
      sRand (s);
    else
      set_sRand_seed_to_clocktime ();
  }
  else
    set_sRand_seed_to_clocktime ();

  if (argc > 3)
    number = atoi (argv [3]);
  else 
    number = 1;


  for (i = 0; i < number; i++)
    printf ("%d\n", rand_integer (0, atoi (argv [1])));
}
