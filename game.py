import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import math
import random
import time

class Camera:
    def __init__(self):
        self.x = 0.0
        self.y = 2.0
        self.z = 5.0
        self.yaw = 0.0
        self.pitch = 0.0
        self.speed = 0.1
        self.sensitivity = 0.1
        
    def update(self, keys, mouse_rel):
        # Mouse look
        self.yaw += mouse_rel[0] * self.sensitivity
        self.pitch -= mouse_rel[1] * self.sensitivity
        
        # Clamp pitch to prevent flipping
        self.pitch = max(-89.0, min(89.0, self.pitch))
        
        # Calculate movement vectors
        yaw_rad = math.radians(self.yaw)
        pitch_rad = math.radians(self.pitch)
        
        front_x = math.cos(yaw_rad) * math.cos(pitch_rad)
        front_y = math.sin(pitch_rad)
        front_z = math.sin(yaw_rad) * math.cos(pitch_rad)
        
        right_x = math.cos(yaw_rad - math.pi/2)
        right_z = math.sin(yaw_rad - math.pi/2)
        
        # WASD movement
        if keys[K_w]:
            self.x += front_x * self.speed
            self.z += front_z * self.speed
        if keys[K_s]:
            self.x -= front_x * self.speed
            self.z -= front_z * self.speed
        if keys[K_a]:
            self.x += right_x * self.speed
            self.z += right_z * self.speed
        if keys[K_d]:
            self.x -= right_x * self.speed
            self.z -= right_z * self.speed
        
        # Keep camera above ground
        self.y = max(2.0, self.y)
        
    def apply(self):
        glLoadIdentity()
        yaw_rad = math.radians(self.yaw)
        pitch_rad = math.radians(self.pitch)
        
        front_x = math.cos(yaw_rad) * math.cos(pitch_rad)
        front_y = math.sin(pitch_rad)
        front_z = math.sin(yaw_rad) * math.cos(pitch_rad)
        
        gluLookAt(self.x, self.y, self.z,
                  self.x + front_x, self.y + front_y, self.z + front_z,
                  0.0, 1.0, 0.0)
    
    def get_forward_vector(self):
        yaw_rad = math.radians(self.yaw)
        pitch_rad = math.radians(self.pitch)
        
        front_x = math.cos(yaw_rad) * math.cos(pitch_rad)
        front_y = math.sin(pitch_rad)
        front_z = math.sin(yaw_rad) * math.cos(pitch_rad)
        
        return front_x, front_y, front_z

class Box:
    def __init__(self, x, y, z, size=1.0):
        self.x = x
        self.y = y
        self.z = z
        self.size = size
        
    def draw(self):
        glPushMatrix()
        glTranslatef(self.x, self.y, self.z)
        
        # Set material properties for the box
        glMaterialfv(GL_FRONT, GL_AMBIENT, [0.8, 0.4, 0.2, 1.0])
        glMaterialfv(GL_FRONT, GL_DIFFUSE, [0.9, 0.5, 0.3, 1.0])
        glMaterialfv(GL_FRONT, GL_SPECULAR, [0.2, 0.2, 0.2, 1.0])
        glMaterialf(GL_FRONT, GL_SHININESS, 20.0)
        
        s = self.size / 2.0
        
        # Draw cube faces
        glBegin(GL_QUADS)
        
        # Front face
        glNormal3f(0, 0, 1)
        glVertex3f(-s, -s, s)
        glVertex3f(s, -s, s)
        glVertex3f(s, s, s)
        glVertex3f(-s, s, s)
        
        # Back face
        glNormal3f(0, 0, -1)
        glVertex3f(-s, -s, -s)
        glVertex3f(-s, s, -s)
        glVertex3f(s, s, -s)
        glVertex3f(s, -s, -s)
        
        # Top face
        glNormal3f(0, 1, 0)
        glVertex3f(-s, s, -s)
        glVertex3f(-s, s, s)
        glVertex3f(s, s, s)
        glVertex3f(s, s, -s)
        
        # Bottom face
        glNormal3f(0, -1, 0)
        glVertex3f(-s, -s, -s)
        glVertex3f(s, -s, -s)
        glVertex3f(s, -s, s)
        glVertex3f(-s, -s, s)
        
        # Right face
        glNormal3f(1, 0, 0)
        glVertex3f(s, -s, -s)
        glVertex3f(s, s, -s)
        glVertex3f(s, s, s)
        glVertex3f(s, -s, s)
        
        # Left face
        glNormal3f(-1, 0, 0)
        glVertex3f(-s, -s, -s)
        glVertex3f(-s, -s, s)
        glVertex3f(-s, s, s)
        glVertex3f(-s, s, -s)
        
        glEnd()
        glPopMatrix()
    
    def intersects_ray(self, ray_start, ray_dir, max_distance):
        # Simple AABB ray intersection
        s = self.size / 2.0
        box_min = [self.x - s, self.y - s, self.z - s]
        box_max = [self.x + s, self.y + s, self.z + s]
        
        t_min = 0.0
        t_max = max_distance
        
        for i in range(3):
            if abs(ray_dir[i]) < 0.0001:  # Ray is parallel to slab
                if ray_start[i] < box_min[i] or ray_start[i] > box_max[i]:
                    return False
            else:
                t1 = (box_min[i] - ray_start[i]) / ray_dir[i]
                t2 = (box_max[i] - ray_start[i]) / ray_dir[i]
                
                if t1 > t2:
                    t1, t2 = t2, t1
                
                t_min = max(t_min, t1)
                t_max = min(t_max, t2)
                
                if t_min > t_max:
                    return False
        
        return t_min <= max_distance

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

def draw_crosshair():
    # Save current matrices
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    
    # Disable depth testing and lighting for crosshair
    glDisable(GL_DEPTH_TEST)
    glDisable(GL_LIGHTING)
    
    # Draw crosshair
    glColor3f(1.0, 1.0, 1.0)  # White crosshair
    glLineWidth(2.0)
    
    crosshair_size = 0.02
    
    glBegin(GL_LINES)
    # Horizontal line
    glVertex2f(-crosshair_size, 0.0)
    glVertex2f(crosshair_size, 0.0)
    # Vertical line
    glVertex2f(0.0, -crosshair_size)
    glVertex2f(0.0, crosshair_size)
    glEnd()
    
    glLineWidth(1.0)
    
    # Restore settings
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_LIGHTING)
    
    # Restore matrices
    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)

def shoot(camera, boxes):
    # Get camera position and forward direction
    start_pos = [camera.x, camera.y, camera.z]
    direction = camera.get_forward_vector()
    max_distance = 100.0
    
    # Check for box intersections
    boxes_to_remove = []
    for i, box in enumerate(boxes):
        if box.intersects_ray(start_pos, direction, max_distance):
            boxes_to_remove.append(i)
    
    # Remove hit boxes (in reverse order to maintain indices)
    for i in reversed(boxes_to_remove):
        boxes.pop(i)
        print(f"Box destroyed! {len(boxes)} boxes remaining.")

def init_opengl():
    glEnable(GL_DEPTH_TEST)
    glClearColor(0.0, 0.0, 0.0, 1.0)  # Black clear color
    
    # Set up perspective projection
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(60.0, 800.0/600.0, 0.1, 1000.0)
    
    glMatrixMode(GL_MODELVIEW)
    
    # Enable lighting
    glEnable(GL_LIGHTING)
    glEnable(GL_LIGHT0)
    glEnable(GL_COLOR_MATERIAL)
    glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
    
    # Set up a bright point light source
    light_position = [0.0, 20.0, 0.0, 1.0]  # Point light at (0, 20, 0)
    light_ambient = [0.4, 0.4, 0.5, 1.0]    # Soft blue ambient light
    light_diffuse = [1.0, 1.0, 0.9, 1.0]    # Bright white diffuse light
    light_specular = [1.0, 1.0, 1.0, 1.0]   # White specular highlights
    
    glLightfv(GL_LIGHT0, GL_POSITION, light_position)
    glLightfv(GL_LIGHT0, GL_AMBIENT, light_ambient)
    glLightfv(GL_LIGHT0, GL_DIFFUSE, light_diffuse)
    glLightfv(GL_LIGHT0, GL_SPECULAR, light_specular)
    
    # Set light attenuation for point light
    glLightf(GL_LIGHT0, GL_CONSTANT_ATTENUATION, 1.0)
    glLightf(GL_LIGHT0, GL_LINEAR_ATTENUATION, 0.01)
    glLightf(GL_LIGHT0, GL_QUADRATIC_ATTENUATION, 0.001)

def main():
    pygame.init()
    
    # Set up display
    display = (800, 600)
    pygame.display.set_mode(display, DOUBLEBUF | OPENGL)
    pygame.display.set_caption("3D Environment with First Person Movement")
    
    # Hide cursor and enable relative mouse mode
    pygame.mouse.set_visible(False)
    pygame.event.set_grab(True)
    
    init_opengl()
    
    camera = Camera()
    
    # Create target boxes
    boxes = []
    for i in range(10):
        x = random.uniform(-20, 20)
        y = random.uniform(1, 5)
        z = random.uniform(-20, 20)
        size = random.uniform(1.0, 2.5)
        boxes.append(Box(x, y, z, size))
    
    clock = pygame.time.Clock()
    running = True
    
    # Instructions
    print("Controls:")
    print("WASD - Move around")
    print("Mouse - Look around")
    print("Left Click - Shoot")
    print("ESC - Exit")
    print(f"Destroy all {len(boxes)} boxes!")
    
    while running:
        mouse_rel = pygame.mouse.get_rel()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left mouse button
                    shoot(camera, boxes)
        
        keys = pygame.key.get_pressed()
        
        # Update camera
        camera.update(keys, mouse_rel)
        
        # Clear screen
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        
        # Apply camera transformation
        camera.apply()
        
        # Draw skybox first
        draw_skybox()
        
        # Draw ground
        draw_ground()
        
        # Draw boxes
        for box in boxes:
            box.draw()
        
        # Draw crosshair (after 3D scene)
        draw_crosshair()
        
        pygame.display.flip()
        clock.tick(60)
    
    pygame.quit()

if __name__ == "__main__":
    main()