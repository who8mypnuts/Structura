#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <time.h>

#define DEFAULT_DEMOS "demos.txt"

int kount = 0;

#define DISPATCH_PRIORITY 1022  // tfunc priority for <dispatch.kps
#define DISPATCH_CANCEL_PRIORITY (DISPATCH_PRIORITY + 1022) 

#define TRUE  1
#define FALSE 0 

#define TESTDEMOS  "TestDemos.kps"
#define DISPATCH   "dispatch.kps"
#define NDEMOS     "Ndemos.kps"
#define PDEMOS     "Pdemos.kps"
#define ALLDEMOS   "alldemos.kps"
#define NOGO       "kp-nogo.kps"
#define STARTDEMO  "start-demo.kps"
#define STARTBLURB "start-demo2.kps"
#define BLURBTEXT  "To quit the exhibit, hit the ESC key (and wait)."
FILE *fp_pdemos;
FILE *fp_alldemos;
FILE *fp_testdemos;

char *interrupt_action = (char *) NULL;  // what to do when exhibit interrupted
char *restart_action = (char *) NULL;    // what to do when restarting exhibit
double restart_time;

int nap = TRUE;
int minimum_KP_build = 3993;
time_t the_time;

void dateNtime (FILE *fp) {
  fprintf (fp, "%% Script generated at %s\n", ctime (&the_time));
}

void write_knotplotrc () {
  FILE *fp;
  fp = fopen ("knotplotrc.kps", "w");
  if (!fp) {
    fprintf (stderr, "\n\n *** Can't open file `knotplotrc.kps' for output.\n\n");
    exit (1022);
  }
  fprintf (fp, "func 1 <dispatch.kps\n");
  fprintf (fp, "func 9 <alldemos.kps\n");
  fprintf (fp, "func 12 tfunc -1\n");
  
  fprintf (fp, "panic = 0   %% prevents panic exits (not reset with `reset all')\n");
  fprintf (fp, "if par0 == 0 then <start-demo.kps\n");
  fprintf (fp, "par0 = 0\n");
  fclose (fp);
}

void write_start_files () {
  FILE *fp;
  fp = fopen (STARTDEMO, "w");
  if (!fp) {
    fprintf (stderr, "\n\n *** Can't open file `%s' for output.\n\n", STARTDEMO);
    exit (1022);
  }
  dateNtime (fp);

  fprintf (fp, "\n%% The kps files below are read in with a tfunc in order\n");
  fprintf (fp, "%% to allow the chance for windows to open.\n");

  fprintf (fp, "if KPbuild > %d then \"tfunc .4 <%s\" else \"tfunc .4 <%s\"\n", 
    minimum_KP_build - 1, STARTBLURB, NOGO);
  //fprintf (fp, "if KPbuild < %d then <%s else <dispatch.kps\n", minimum_KP_build, NOGO);
  fclose (fp);

  fp = fopen (STARTBLURB, "w");
  if (!fp) {
    fprintf (stderr, "\n\n *** Can't open file `%s' for output.\n\n", STARTBLURB);
    exit (1022);
  }
  
  dateNtime (fp);

  double nap_time;

  if (nap)
    nap_time = 1.0;
  else
    nap_time = 0.0;

  //  fprintf (fp, "if anaglyph then \"anaglyph stayon\"\n");
  fprintf (fp, "reset all\nspe vwt\nfont 4\n");
  fprintf (fp, "%%wlay compact\n<Ndemos.kps\n<Pdemos.kps\n");
  //  fprintf (fp, "nstring cm -40 \"%s\" 0\ndisp t\nnap %.0f\n", BLURBTEXT, nap_time);
  //  fprintf (fp, "nstring cm cm \"%s\" 1\ndisp t\nnap %.0f\n", BLURBTEXT, nap_time);
  //  fprintf (fp, "nstring cm +40 \"%s\" 2\ndisp t\nnap %.0f\n", BLURBTEXT, nap_time);
  //  fprintf (fp, "disp t\nnap %.0f\n", nap_time * 3.0);
  fprintf (fp, "demo closewin\n");
  if (interrupt_action)
    fprintf (fp, "exhibit interrupt %s\n", interrupt_action);
  if (restart_action)
    fprintf (fp, "exhibit restart %s %f\n", restart_action, restart_time);
  fprintf (fp, "<dispatch.kps\n");
  fclose (fp);

  fp = fopen (NOGO, "w");
  if (!fp) {
    fprintf (stderr, "\n\n *** Can't open file `%s' for output.\n\n", NOGO);
    exit (1022);
  }

  dateNtime (fp);

  fprintf (fp, "echo \" \"\n");
  fprintf (fp, "echo \" \"\n");
  fprintf (fp, "echo \"  *** Can't start demo loop!\"\n");
  fprintf (fp, "echo \"  *** KnotPlot build number must be at least %d.\"\n", 
    minimum_KP_build);
  fprintf (fp, "txt init\ntxt font 4\ntxt centre\ntxt c -40 \"Can't start demo loop!\"\n");
  fprintf (fp, "txt c -70  \"KnotPlot build number must be at least %d.\"\n", 
    minimum_KP_build);
  fprintf (fp, "echo \" \"\n");
  fprintf (fp, "txt on\ndisp t\npanel on\n");
  fclose (fp);
}

void write_dispatch_script () {
  FILE *fp;
  fp = fopen (DISPATCH, "w");
  if (!fp) {
    fprintf (stderr, "\n\n *** Can't open file `%s' for output.\n\n", DISPATCH);
    exit (1022);
  }


  fprintf (fp, "tfunc reset %d\n", DISPATCH_CANCEL_PRIORITY);  // cancel any other pending dispatches, is this needed?  can't hurt!

  fprintf (fp, "curs 1\nif exists exhibit_config.kps then <exhibit_config.kps else \"exhibit fullscreen go\"\ndemo\n");
  fclose (fp);

  fp = fopen (NDEMOS, "w");
  if (!fp) {
    fprintf (stderr, "\n\n *** Can't open file `%s' for output.\n\n", NDEMOS);
    exit (1022);
  }

  fprintf (fp, "demo Ndemos %d %d\n", kount, kount / 2);
  fclose (fp);

}


void create_demo (char *s, float min, float max, int flag, float prob) {
  char filename [102];
  static int ipos = -2;
  sprintf (filename, "demo%d.kps", kount);
  FILE *fout;

  fout = fopen (filename, "w");
  if (!fout) {
    fprintf (stderr, "\n\n *** Can't open file `%s' for output.\n\n", filename);
    exit (1022);
  }

  switch (flag) {
  default:
  case 0:
    if (min == max) 
      fprintf (fout, "tmax %.2f\n", min);
    else 
      fprintf (fout, "tmax \\rr[%.2f/%.2f]\n", min, max);
    if (prob >= 1.0)
      fprintf (fout, "<%s.kps\n", s);
    else 
      fprintf (fout, "if \\rr1 < %f then <%s.kps else <dispatch.kps\n", prob, s);
    fprintf (stderr, "\n *** Type #%d sequences not implemented yet!\n\n", flag);
    exit (102);
    break;
  case 1:
    fprintf (fout, "<%s.kps\n<dispatch.kps\n", s);
    break;
  case 2:
    fprintf (fout, "<%s.kps\ntfunc \\rr[%.2f/%.2f] <dispatch.kps %d\n", s, min, max, DISPATCH_PRIORITY);
    break;
  }

  fprintf (fp_pdemos, "demo p %d %f %s\n", kount, prob, s);

  fprintf (fp_alldemos, "echo \" \"\n");
  fprintf (fp_alldemos, "echo \" \"\n");
  fprintf (fp_alldemos, "echo Demo `%s'\n", s);
  fprintf (fp_alldemos, "<%s.kps\n", s);

  if (ipos == -2)
    fprintf (fp_testdemos, "\nbutton Nbuttons 3\nbutton pos 1\n");
  fprintf (fp_testdemos, "button DemoA %s <%s.kps %d -1 0 10 0 10\n", s, s, ipos);
  ipos = -1;


  fclose (fout);
  kount++;
}

#define MAX(X, Y)  ((X) > (Y) ? (X) : (Y))

int main (int argc, char **argv) {
  FILE *fp = stdin;
  char input_line [300];
  int index;

  time (&the_time);

  for (index = 1; index < argc; index++) {
    if (argv [index][0] != '-') break;
    if (!strcmp (argv [index], "-nonap")) nap = FALSE;
    else if (!strcmp (argv [index], "-int")) {
      index++;
      interrupt_action = (char *) calloc (strlen (argv [index]) + 2, 
					  sizeof (char));
      strcpy (interrupt_action, argv [index]);
    }
    else if (!strcmp (argv [index], "-restart")) {
      index++;
      restart_action = (char *) calloc (strlen (argv [index]) + 2, 
					sizeof (char));
      strcpy (restart_action, argv [index]);
      index++;
      restart_time = atof (argv [index]);
    }
    else {
      fprintf (stderr, "\n *** Unknown argument `%s'.\n", argv [index]);
      exit (1022);
    }
  }

  if (index < argc) {
    fp = fopen (argv [index], "r");
    if (!fp) {
      fprintf (stderr, "\n\n *** Can't open file `%s' for input.\n", argv [index]);
      exit (1022);
    }
  }
  else {
    fp = fopen (DEFAULT_DEMOS, "r");
    if (!fp) {
      fprintf (stderr, "\n\n *** Can't open file `%s' for input.\n", DEFAULT_DEMOS);
      exit (1022);
    }
  }

  int npar, flag;
  char script [60];
  float max, min, prob;

  fp_pdemos = fopen (PDEMOS, "w");
  fp_alldemos = fopen (ALLDEMOS, "w");
  fp_testdemos = fopen (TESTDEMOS, "w");

  while (fgets (input_line, 99, fp)) {
    npar = sscanf (input_line, "%s%f%f%d%f", script, &min, &max, &flag, &prob);
    if (input_line [0] == '%') {
      if (input_line [1] == '!' && input_line [2] == ' ') {
        int value;
        sscanf (input_line + 3, "%d", &value);
        minimum_KP_build = MAX (minimum_KP_build, value);
        printf ("Minimum KnotPlot build required set to %d.\n", minimum_KP_build);
      }
      else 
        printf ("skipping: %s\n", script + 1);
      continue;
    }
    if (npar < 3) continue;
    if (npar < 4) flag = 0;
    if (npar < 5) prob = 1.0001f;
    printf ("demo%d: %d %s %f %f %d %f\n", kount, npar, script, min, max, flag, prob);
    create_demo (script, min, max, flag, prob);
  }

  if (fp != stdin) fclose (fp);

  write_dispatch_script ();
  write_start_files ();
  write_knotplotrc ();

  fprintf (fp_pdemos, "\ndemo probs\n");
  fclose (fp_pdemos);

  fprintf (fp_alldemos, "echo \" \"\necho \" \"\necho \" \"\necho All done!\necho \" \"\n\n");
  fclose (fp_alldemos);
  fclose (fp_testdemos);
  printf ("This exhibit needs KnotPlot build #%d.\n", minimum_KP_build);
  printf ("Number of demo sequences is %d.\n", kount);
  //exit (1022);
  return 0;
}

