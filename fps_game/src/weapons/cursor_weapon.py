import math
import numpy as np
import pygame
from OpenGL.GL import *

class QuaternionWeapon:
    """Weapon system that tracks ArUco marker position using quaternions"""
    
    def __init__(self, camera_pos=(0, 2, 5)):
        self.camera_pos = camera_pos
        self.weapon_offset = np.array([0, -0.4, -0.8])  # Offset from camera
        self.cursor_world_pos = np.array([0, 0, -10])  # Default target position
        
        # Quaternion for weapon rotation (identity quaternion = no rotation)
        self.quaternion = np.array([1.0, 0.0, 0.0, 0.0])  # [w, x, y, z]
        
        # ArUco marker degree input (0-180)
        self.aruco_degree = 90.0  # Default to center (90 degrees)
        
        # Target distance for aiming
        self.target_distance = 20.0
        
        # Weapon model specific offsets (based on your pistol GLB model)
        # These values are calibrated for the pistol model's actual barrel position
        self.barrel_tip_offset = np.array([0.0, 0.2, -1.0])  # Tip is forward from weapon center
        
    def update_aruco_position(self, degree):
        """Convert ArUco degree (0-180) to 3D world coordinates"""
        # Clamp degree to valid range
        self.aruco_degree = max(0.0, min(180.0, degree))
        
        # Convert degree to horizontal angle
        # 0 degrees = far left, 90 degrees = center, 180 degrees = far right
        # Map to angle range: 0° -> -90°, 90° -> 0°, 180° -> +90°
        horizontal_angle_deg = (self.aruco_degree - 90.0)  # -90 to +90 range
        horizontal_angle_rad = math.radians(horizontal_angle_deg)
        
        # Calculate world coordinates based on camera position and angle
        camera_pos = np.array(self.camera_pos)
        
        # Calculate target position at fixed distance in front of camera
        world_x = camera_pos[0] + (math.sin(horizontal_angle_rad) * self.target_distance)
        world_y = camera_pos[1]  # Keep at same height as camera
        world_z = camera_pos[2] - (math.cos(horizontal_angle_rad) * self.target_distance)
        
        self.cursor_world_pos = np.array([world_x, world_y, world_z])
    
    def calculate_weapon_orientation(self):
        """Calculate weapon orientation to point at ArUco target using quaternions"""
        # Get weapon world position
        weapon_pos = np.array(self.camera_pos) + self.weapon_offset
        
        # Calculate direction from weapon to target
        direction = self.cursor_world_pos - weapon_pos
        direction = direction / np.linalg.norm(direction)  # Normalize
        
        # Calculate quaternion to rotate weapon toward target
        # Default weapon forward direction is (0, 0, -1)
        forward = np.array([0.0, 0.0, -1.0])
        
        # Calculate rotation axis and angle
        cross_product = np.cross(forward, direction)
        dot_product = np.dot(forward, direction)
        
        # Handle edge cases
        if np.allclose(cross_product, 0):
            if dot_product > 0:
                # Same direction
                self.quaternion = np.array([1.0, 0.0, 0.0, 0.0])
            else:
                # Opposite direction
                self.quaternion = np.array([0.0, 1.0, 0.0, 0.0])
        else:
            # Calculate quaternion from axis and angle
            axis = cross_product / np.linalg.norm(cross_product)
            angle = math.acos(max(-1.0, min(1.0, dot_product)))
            
            half_angle = angle / 2.0
            sin_half = math.sin(half_angle)
            cos_half = math.cos(half_angle)
            
            self.quaternion = np.array([
                cos_half,
                axis[0] * sin_half,
                axis[1] * sin_half,
                axis[2] * sin_half
            ])
    
    def quaternion_to_matrix(self, q):
        """Convert quaternion to rotation matrix"""
        w, x, y, z = q
        
        # Rotation matrix from quaternion
        matrix = np.array([
            [1 - 2*y*y - 2*z*z, 2*x*y - 2*w*z,     2*x*z + 2*w*y,     0],
            [2*x*y + 2*w*z,     1 - 2*x*x - 2*z*z, 2*y*z - 2*w*x,     0],
            [2*x*z - 2*w*y,     2*y*z + 2*w*x,     1 - 2*x*x - 2*y*y, 0],
            [0,                 0,                 0,                 1]
        ])
        
        return matrix
    
    def get_weapon_tip_position(self):
        """Get the position of the weapon tip (barrel end) in world coordinates"""
        weapon_pos = np.array(self.camera_pos) + self.weapon_offset
        
        # Apply rotation to the barrel tip offset
        rotation_matrix = self.quaternion_to_matrix(self.quaternion)
        rotated_tip_offset = (rotation_matrix[:3, :3] @ self.barrel_tip_offset)
        
        # Return weapon center position + rotated tip offset
        tip_position = weapon_pos + rotated_tip_offset
        
        # Debug output to help calibrate
        if hasattr(self, '_debug_tip_counter'):
            self._debug_tip_counter += 1
        else:
            self._debug_tip_counter = 0
            
        # Print debug info every 60 frames (1 second at 60 FPS)
        if self._debug_tip_counter % 60 == 0:
            print(f"Weapon tip position: ({tip_position[0]:.2f}, {tip_position[1]:.2f}, {tip_position[2]:.2f})")
            print(f"Weapon center: ({weapon_pos[0]:.2f}, {weapon_pos[1]:.2f}, {weapon_pos[2]:.2f})")
        
        return tip_position
    
    def get_firing_direction(self):
        """Get the direction from weapon tip to ArUco target"""
        tip_pos = self.get_weapon_tip_position()
        direction = self.cursor_world_pos - tip_pos
        return direction / np.linalg.norm(direction)  # Normalize
    
    def apply_weapon_transform(self):
        """Apply the weapon transformation for rendering"""
        glPushMatrix()
        
        # Position weapon relative to camera
        weapon_world_pos = np.array(self.camera_pos) + self.weapon_offset
        glTranslatef(weapon_world_pos[0], weapon_world_pos[1], weapon_world_pos[2])
        
        # Apply quaternion rotation
        rotation_matrix = self.quaternion_to_matrix(self.quaternion)
        
        # Convert to OpenGL format (column major) and apply
        gl_matrix = rotation_matrix.flatten(order='F')  # Column major order
        glMultMatrixf(gl_matrix.astype(np.float32))
        
        return True  # Matrix is pushed, caller should pop
    
    def update_with_aruco(self, degree):
        """Update weapon orientation based on ArUco marker degree"""
        self.update_aruco_position(degree)
        self.calculate_weapon_orientation()
    
    def update(self):
        """Update weapon orientation - can be called without parameters for compatibility"""
        # If no ArUco input, maintain current position
        self.calculate_weapon_orientation()
        
    def get_cursor_world_position(self):
        """Get the current target world position for debugging"""
        return self.cursor_world_pos
    
    def get_aruco_degree(self):
        """Get the current ArUco degree for debugging"""
        return self.aruco_degree
    
    def calibrate_barrel_tip_offset(self, x_offset, y_offset, z_offset):
        """Allow runtime calibration of barrel tip position"""
        self.barrel_tip_offset = np.array([x_offset, y_offset, z_offset])
        print(f"Barrel tip offset updated to: ({x_offset:.2f}, {y_offset:.2f}, {z_offset:.2f})")