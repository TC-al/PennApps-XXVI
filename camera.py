import math
from OpenGL.GL import *
from OpenGL.GLU import *
from pygame.locals import *

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