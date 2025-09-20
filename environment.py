import math
from OpenGL.GL import *

def draw_skybox():
    # Disable depth testing for skybox
    glDisable(GL_DEPTH_TEST)
    glDisable(GL_LIGHTING)  # Disable lighting for skybox
    glDepthMask(GL_FALSE)
    
    # Sky gradient
    glBegin(GL_QUADS)
    
    # Top (lighter blue)
    glColor3f(0.5, 0.7, 1.0)
    glVertex3f(-100, 50, -100)
    glVertex3f(100, 50, -100)
    glVertex3f(100, 50, 100)
    glVertex3f(-100, 50, 100)
    
    # Sides with gradient
    for i in range(4):
        angle = i * math.pi / 2
        x1, z1 = 100 * math.cos(angle), 100 * math.sin(angle)
        x2, z2 = 100 * math.cos(angle + math.pi/2), 100 * math.sin(angle + math.pi/2)
        
        # Top of side (sky blue)
        glColor3f(0.5, 0.7, 1.0)
        glVertex3f(x1, 50, z1)
        glVertex3f(x2, 50, z2)
        
        # Bottom of side (horizon blue)
        glColor3f(0.7, 0.8, 1.0)
        glVertex3f(x2, 0, z2)
        glVertex3f(x1, 0, z1)
    
    glEnd()
    
    # Re-enable depth testing and lighting
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_LIGHTING)
    glDepthMask(GL_TRUE)

def draw_ground():
    # Set material properties for the ground
    glMaterialfv(GL_FRONT, GL_AMBIENT, [0.3, 0.3, 0.3, 1.0])
    glMaterialfv(GL_FRONT, GL_DIFFUSE, [0.5, 0.5, 0.5, 1.0])
    glMaterialfv(GL_FRONT, GL_SPECULAR, [0.1, 0.1, 0.1, 1.0])
    glMaterialf(GL_FRONT, GL_SHININESS, 10.0)
    
    # Draw large platform
    glBegin(GL_QUADS)
    glNormal3f(0, 1, 0)
    glVertex3f(-50, 0, -50)
    glVertex3f(50, 0, -50)
    glVertex3f(50, 0, 50)
    glVertex3f(-50, 0, 50)
    glEnd()
    
    # Add some grid lines for depth perception
    glDisable(GL_LIGHTING)  # Disable lighting for grid lines
    glColor3f(0.3, 0.3, 0.3)
    glBegin(GL_LINES)
    for i in range(-50, 51, 5):
        glVertex3f(i, 0.01, -50)
        glVertex3f(i, 0.01, 50)
        glVertex3f(-50, 0.01, i)
        glVertex3f(50, 0.01, i)
    glEnd()
    glEnable(GL_LIGHTING)  # Re-enable lighting