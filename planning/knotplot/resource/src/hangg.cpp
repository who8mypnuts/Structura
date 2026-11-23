// this is a test program for one specific hardware installation

// if you are a general KnotPlot user, just ignore this file

#include <GL/glut.h> 
#include <stdlib.h>
#include <stdio.h>
#include <ctype.h>
#include <string.h>

#define ESCAPE     27
 

#ifndef TRUE
#define TRUE  1
#define FALSE 0
#endif

double angle = 0.0;

void ifunc () {
  static int last_call = 0;
  int t = glutGet (GLUT_ELAPSED_TIME);
  int dt = t - last_call;
  last_call = t;
  angle += 40.0 * (double) dt / 1000.0; // 40 degrees per second
  if (angle > 360.0)
    angle -= 360.0;
  glutPostRedisplay ();
}

void draw_prop_text (void *font, double x, double y, double z, char *s) {
  int len, i;

  glRasterPos3f ((GLfloat) x, (GLfloat) y, (GLfloat) z);
  len = (int) strlen (s);
  for (i = 0; i < len; i++) 
    glutBitmapCharacter (font, s [i]);
}

void initialize_graphics (void) {
  
  glEnable (GL_DEPTH_TEST);     

  glMatrixMode (GL_PROJECTION); 
  glLoadIdentity ();
  gluPerspective (45.0,         
                  1.0,          
                  0.2,          
                                
                  102.2);       
                                

  glMatrixMode (GL_MODELVIEW);  
  glLoadIdentity ();
  gluLookAt (0.0, 0.0, 5.0,    
             0.0, 0.0, 0.0,    
             0.0, 1.0, 0.0);   

  glEnable (GL_LIGHTING);
  glEnable (GL_LIGHT0);

}


void paint (void) {   
 
  glClear (GL_COLOR_BUFFER_BIT | 
           GL_DEPTH_BUFFER_BIT); 

  glPushMatrix ();         
 
  glRotated (angle, 1.0, 0.0, 0.0);
  glutSolidIcosahedron ();
        
  glPopMatrix ();      
                       
  glDisable (GL_LIGHTING);
  glColor3d (1.0, 1.0, 1.0);

  double offset = 3.5, xpos = -3.5;

  draw_prop_text (GLUT_BITMAP_HELVETICA_18, xpos, offset - 1.8, 0.0, 
		  "After the icosahedron starts rotating");
  draw_prop_text (GLUT_BITMAP_HELVETICA_18, xpos, offset - 2.0, 0.0, 
		  "press one of the following keys");
  draw_prop_text (GLUT_BITMAP_HELVETICA_18, xpos, offset - 2.2, 0.0, 
		  "to perform the indicated system() call:");
  draw_prop_text (GLUT_BITMAP_HELVETICA_18, xpos, offset - 2.4, 0.0, 
		  "spacebar --- system (\"ls\")");
  draw_prop_text (GLUT_BITMAP_HELVETICA_18, xpos, offset - 2.6, 0.0, 
		  "p --- system (\"ps\")");
  draw_prop_text (GLUT_BITMAP_HELVETICA_18, xpos, offset - 2.8, 0.0, 
		  "/ --- system (\"ls /\")");
  draw_prop_text (GLUT_BITMAP_HELVETICA_18, xpos, offset - 3.0, 0.0, 
		  "w --- system (\"who\")");
  glEnable (GL_LIGHTING);

  glutSwapBuffers ();  
}

void reshape_viewport (int width, int height) {
  float aspect = (float) width / (float) height;
  glMatrixMode (GL_PROJECTION); 
  glLoadIdentity ();
  gluPerspective (45.0,         
                  aspect,       
                  0.2,          
                  102.2);       
                                
  glMatrixMode (GL_MODELVIEW); 
  glViewport (0, 0, width, height);
}

void keyboard_function (unsigned char key, 
			int x, int y) { 
 
  switch (key) {
    
  case ESCAPE:
    exit (1);
    break;
    
  case ' ':
    system ("ls");
    break;

  case '/':
    system ("ls /");
    break;

  case 'p':
    system ("ps");
    break;

  case 'w':
    system ("who");
    break;
  }
}




int main (int argc, char **argv) {
  glutInit (&argc, argv);
  glutInitDisplayMode (GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH);
  

  glutInitWindowSize (800, 450);
  glutCreateWindow ("Test");


  glutDisplayFunc (paint);
  glutReshapeFunc (reshape_viewport);
  glutKeyboardFunc (keyboard_function);
  initialize_graphics ();    

  glutIdleFunc (ifunc);

  glutMainLoop (); 

  return 1;        
}


