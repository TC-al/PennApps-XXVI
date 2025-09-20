import math
import numpy as np
import pygame
from OpenGL.GL import *

class QuaternionWeapon:
    """Weapon system that tracks ArUco marker position using quaternions and geometry viewer math"""
    
    def __init__(self, camera_pos=(0, 2, 5)):
        self.camera_pos = camera_pos
        self.weapon_offset = np.array([0, -0.4, -0.8])  # Offset from camera
        self.cursor_world_pos = np.array([0, 0, -10])  # Default target position
        
        # Quaternion for weapon rotation (identity quaternion = no rotation)
        self.quaternion = np.array([1.0, 0.0, 0.0, 0.0])  # [w, x, y, z]
        
        # ArUco marker inputs - now using both d and alpha from estimate.py
        self.aruco_d = 0.0      # Position along diameter (-r/2 to +r/2)
        self.aruco_alpha = 0.0  # Aiming angle in radians
        
        # Geometry parameters (matching geometry_viewer.py)
        self.r = 0.4            # Circle radius (same as in estimate.py)
        self.arc_deg = 0.0      # Arc angle (can be calculated or set)
        
        # Target distance for aiming
        self.target_distance = 20.0
        
        # Weapon model specific offsets (based on your pistol GLB model)
        # These values are calibrated for the pistol model's actual barrel position
        self.barrel_tip_offset = np.array([0.0, 0.2, -1.0])  # Tip is forward from weapon center
        
        # Debug counter for output throttling
        self._debug_counter = 0
        
    def update_aruco_position_and_angle(self, d, alpha):
        """Update weapon position and orientation using ArUco d and alpha values"""
        self.aruco_d = d
        self.aruco_alpha = alpha
        
        # Calculate weapon position based on d (position along diameter)
        # d ranges from -r/2 to +r/2, map this to weapon horizontal offset
        camera_pos = np.array(self.camera_pos)
        
        # Scale d to a reasonable weapon position range
        # d = -r/2 (left side) to d = +r/2 (right side)
        position_scale = 3.0  # Scale factor to make position changes more visible
        horizontal_offset = (self.aruco_d / self.r) * position_scale
        
        # Update weapon offset to include horizontal movement
        self.weapon_offset = np.array([horizontal_offset, -0.4, -0.8])
        
        # Calculate target position using the geometry viewer math
        # Following the logic from geometry_viewer.py
        
        # For now, we'll set arc_deg based on alpha or use a default
        # In a full implementation, you might calculate arc_deg from other data
        # Here we'll derive a reasonable arc angle from alpha
        self.arc_deg = math.degrees(self.aruco_alpha) * 2.0  # Simple mapping
        self.arc_deg = max(-90.0, min(90.0, self.arc_deg))  # Clamp to valid range
        
        # Calculate arc end point E using geometry viewer logic
        theta_deg = 90.0 - self.arc_deg  # TOP is 90°, moving CW decreases angle
        theta = math.radians(theta_deg)
        Ex = self.r * math.cos(theta)
        Ey = self.r * math.sin(theta)
        
        # Point P is at (d, 0) on the diameter
        Px, Py = self.aruco_d, 0.0
        
        # Calculate the direction from P to E (this gives us the aiming direction)
        aim_direction_2d = np.array([Ex - Px, Ey - Py])
        aim_direction_2d = aim_direction_2d / np.linalg.norm(aim_direction_2d)  # Normalize
        
        # Convert 2D aiming direction to 3D world coordinates
        # Map the 2D geometry to 3D space in front of the camera
        world_x = camera_pos[0] + horizontal_offset + (aim_direction_2d[0] * self.target_distance)
        world_y = camera_pos[1] + (aim_direction_2d[1] * self.target_distance * 0.5)  # Scale Y for reasonable aiming
        world_z = camera_pos[2] - self.target_distance  # Forward direction
        
        self.cursor_world_pos = np.array([world_x, world_y, world_z])
        
        # Debug output (throttled)
        self._debug_counter += 1
        if self._debug_counter % 60 == 0:  # Every 60 frames (1 second at 60 FPS)
            print(f"ArUco input - d: {d:.3f}, alpha: {alpha:.3f} rad ({math.degrees(alpha):.1f}°)")
            print(f"Geometry - P: ({Px:.3f}, {Py:.3f}), E: ({Ex:.3f}, {Ey:.3f})")
            print(f"Weapon position offset: ({horizontal_offset:.3f}, -0.4, -0.8)")
            print(f"Target position: ({world_x:.2f}, {world_y:.2f}, {world_z:.2f})")
    
    def calculate_weapon_orientation(self):
        """Calculate weapon orientation to point at ArUco target using quaternions"""
        # Get weapon world position (now includes horizontal offset from d)
        weapon_pos = np.array(self.camera_pos) + self.weapon_offset
        
        # Calculate direction from weapon to target
        direction = self.cursor_world_pos - weapon_pos
        if np.linalg.norm(direction) > 0:
            direction = direction / np.linalg.norm(direction)  # Normalize
        else:
            direction = np.array([0.0, 0.0, -1.0])  # Default forward
        
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
        
        return tip_position
    
    def get_firing_direction(self):
        """Get the direction from weapon tip to ArUco target"""
        tip_pos = self.get_weapon_tip_position()
        direction = self.cursor_world_pos - tip_pos
        if np.linalg.norm(direction) > 0:
            return direction / np.linalg.norm(direction)  # Normalize
        else:
            return np.array([0.0, 0.0, -1.0])  # Default forward
    
    def apply_weapon_transform(self):
        """Apply the weapon transformation for rendering"""
        glPushMatrix()
        
        # Position weapon relative to camera (now includes horizontal offset from d)
        weapon_world_pos = np.array(self.camera_pos) + self.weapon_offset
        glTranslatef(weapon_world_pos[0], weapon_world_pos[1], weapon_world_pos[2])
        
        # Apply quaternion rotation
        rotation_matrix = self.quaternion_to_matrix(self.quaternion)
        
        # Convert to OpenGL format (column major) and apply
        gl_matrix = rotation_matrix.flatten(order='F')  # Column major order
        glMultMatrixf(gl_matrix.astype(np.float32))
        
        return True  # Matrix is pushed, caller should pop
    
    def update_with_aruco(self, d, alpha):
        """Update weapon position and orientation based on ArUco marker d and alpha values"""
        self.update_aruco_position_and_angle(d, alpha)
        self.calculate_weapon_orientation()
    
    def update_aruco_position(self, degree):
        """Legacy method for compatibility - converts degree to d value"""
        # Convert degree (0-180) to d value (-r/2 to +r/2)
        degree = max(0.0, min(180.0, degree))
        # 0° -> -r/2, 90° -> 0, 180° -> +r/2
        d = ((degree - 90.0) / 90.0) * (self.r / 2.0)
        alpha = 0.0  # Default alpha when using legacy degree input
        self.update_with_aruco(d, alpha)
    
    def update(self):
        """Update weapon orientation - can be called without parameters for compatibility"""
        # If no ArUco input, maintain current position
        self.calculate_weapon_orientation()
        
    def get_cursor_world_position(self):
        """Get the current target world position for debugging"""
        return self.cursor_world_pos
    
    def get_aruco_values(self):
        """Get the current ArUco d and alpha values for debugging"""
        return self.aruco_d, self.aruco_alpha
    
    def get_aruco_degree(self):
        """Legacy method - convert d back to degree for compatibility"""
        # Convert d value back to degree (0-180)
        degree = ((self.aruco_d / (self.r / 2.0)) * 90.0) + 90.0
        return max(0.0, min(180.0, degree))
    
    def calibrate_barrel_tip_offset(self, x_offset, y_offset, z_offset):
        """Allow runtime calibration of barrel tip position"""
        self.barrel_tip_offset = np.array([x_offset, y_offset, z_offset])
        print(f"Barrel tip offset updated to: ({x_offset:.2f}, {y_offset:.2f}, {z_offset:.2f})")
    
    def get_geometry_debug_info(self):
        """Get geometry information for debugging purposes"""
        # Calculate arc end point for debugging
        theta_deg = 90.0 - self.arc_deg
        theta = math.radians(theta_deg)
        Ex = self.r * math.cos(theta)
        Ey = self.r * math.sin(theta)
        Px, Py = self.aruco_d, 0.0
        
        return {
            'r': self.r,
            'd': self.aruco_d,
            'alpha': self.aruco_alpha,
            'arc_deg': self.arc_deg,
            'point_P': (Px, Py),
            'point_E': (Ex, Ey),
            'weapon_offset': self.weapon_offset,
            'target_world_pos': self.cursor_world_pos
        }