import math
import numpy as np
import pygame
from OpenGL.GL import *

class QuaternionWeapon:
    """Weapon system that tracks ArUco marker position and orientation using geometry calculations"""
    
    def __init__(self, camera_pos=(0, 2, 5)):
        self.camera_pos = camera_pos
        
        # Base weapon offset from camera (will be modified by ArUco position)
        self.base_weapon_offset = np.array([0, -0.4, -0.8])  # Base offset from camera
        self.weapon_offset = self.base_weapon_offset.copy()  # Current actual offset
        
        self.cursor_world_pos = np.array([0, 0, -10])  # Default target position
        
        # Quaternion for weapon rotation (identity quaternion = no rotation)
        self.quaternion = np.array([1.0, 0.0, 0.0, 0.0])  # [w, x, y, z]
        
        # ArUco geometry data
        self.geometry_data = {
            'position_offset': 0.0,    # Horizontal position offset (d value)
            'orientation_alpha': 0.0,  # Orientation angle in radians (alpha)
            'degree': 90.0,           # Original degree value for compatibility
            'rotation_angle': 0.0,    # Left/right rotation of gun
            'distance_to_cam': 1.5    # Distance from camera (default 1.5m)
        }
        
        # Default distance for when ArUco marker not visible
        self.default_distance_to_cam = 1.5
        
        # Target distance for aiming
        self.target_distance = 20.0
        
        # Weapon model specific offsets (based on your pistol GLB model)
        self.barrel_tip_offset = np.array([0.0, 0.2, -1.0])  # Tip is forward from weapon center
        
        # Position sensitivity multiplier
        self.position_sensitivity = 5.0  # How much the weapon position changes with ArUco movement
        
        # Distance-to-camera sensitivity (how much forward/back movement)
        self.distance_sensitivity = 0.3  # Multiplier for distance-based Z offset
        
        # Rotation sensitivity for left/right gun rotation
        self.rotation_sensitivity = 1.0
        
        # Debug flag
        self._debug_counter = 0
        
    def update_full_aruco_data(self, full_data):
        """Update weapon using complete ArUco detection data including rotation and distance"""
        # Update all geometry data except distance_to_cam (handled separately below)
        self.geometry_data['position_offset'] = full_data.get('position_offset', 0.0)
        self.geometry_data['orientation_alpha'] = full_data.get('orientation_alpha', 0.0)
        self.geometry_data['degree'] = full_data.get('degree', 90.0)
        self.geometry_data['rotation_angle'] = full_data.get('rotation_angle', 0.0)
        
        # Only update distance if we have a valid detection (> 0)
        new_distance = full_data.get('distance_to_cam', 0)
        if new_distance > 0:
            self.geometry_data['distance_to_cam'] = new_distance
        
        # Get values with defaults
        position_offset = self.geometry_data['position_offset']
        orientation_alpha = self.geometry_data['orientation_alpha']
        rotation_angle = -self.geometry_data['rotation_angle']  # Invert the angle
        distance_to_cam = self.geometry_data['distance_to_cam']
        
        # If distance is 0 (marker not visible), use default
        if distance_to_cam <= 0.01:
            distance_to_cam = self.default_distance_to_cam
        
        # Calculate weapon offset based on ArUco data
        self.weapon_offset = self.base_weapon_offset.copy()
        
        # Apply horizontal position offset (left-right movement based on d value)
        self.weapon_offset[0] += position_offset * self.position_sensitivity
        
        # Apply distance-based Z offset (forward-back movement)
        # Closer to camera = move weapon forward (more negative Z)
        # Further from camera = move weapon backward (less negative Z)
        distance_offset = (distance_to_cam - self.default_distance_to_cam) * self.distance_sensitivity
        self.weapon_offset[2] -= distance_offset  # Negative because forward is -Z
        
        # Calculate target position based on alpha angle and rotation
        weapon_world_pos = np.array(self.camera_pos) + self.weapon_offset
        
        # Apply rotation angle to target calculation
        # Combine orientation_alpha with rotation_angle for full aiming
        combined_angle = orientation_alpha + math.radians(rotation_angle * self.rotation_sensitivity)
        
        target_x = weapon_world_pos[0] + (math.cos(combined_angle) * self.target_distance)
        target_y = weapon_world_pos[1]  # Keep at same height as weapon
        target_z = weapon_world_pos[2] - (math.sin(combined_angle) * self.target_distance)
        
        self.cursor_world_pos = np.array([target_x, target_y, target_z])
        
        # Debug output
        self._debug_counter += 1
        if self._debug_counter % 30 == 0:  # Print every 0.5 seconds at 60 FPS
            print(f"Alpha: {math.degrees(orientation_alpha):.1f}°, Rotation: {rotation_angle:.1f}°")
            print(f"Distance: {distance_to_cam:.2f}m, Pos offset: {position_offset:.3f}")
            print(f"Target: ({target_x:.1f}, {target_y:.1f}, {target_z:.1f})")
    
    def update_aruco_geometry(self, geometry_data):
        """Update weapon using geometry calculations from ArUco detection"""
        # Use the new full update method
        self.update_full_aruco_data(geometry_data)
    
    def update_aruco_position(self, degree):
        """Legacy method for backward compatibility - converts degree to geometry data"""
        degree = max(0.0, min(180.0, degree))
        horizontal_angle_deg = (degree - 90.0)
        horizontal_angle_rad = math.radians(horizontal_angle_deg)
        
        geometry_data = {
            'position_offset': horizontal_angle_rad * 0.1,
            'orientation_alpha': horizontal_angle_rad,
            'degree': degree,
            'rotation_angle': 0.0,
            'distance_to_cam': self.default_distance_to_cam
        }
        
        self.update_full_aruco_data(geometry_data)
    
    def calculate_weapon_orientation(self):
        """Calculate weapon orientation to point at ArUco target using quaternions"""
        weapon_pos = np.array(self.camera_pos) + self.weapon_offset
        
        direction = self.cursor_world_pos - weapon_pos
        direction_norm = np.linalg.norm(direction)
        
        if direction_norm < 0.001:
            self.quaternion = np.array([1.0, 0.0, 0.0, 0.0])
            return
            
        direction = direction / direction_norm
        
        forward = np.array([0.0, 0.0, -1.0])  # Z-negative is forward
        
        # Include rotation angle in the quaternion calculation
        rotation_angle = self.geometry_data.get('rotation_angle', 0.0)
        
        # Calculate rotation axis and angle
        cross_product = np.cross(forward, direction)
        dot_product = np.dot(forward, direction)
        
        cross_norm = np.linalg.norm(cross_product)
        if cross_norm < 0.001:  # Vectors are parallel
            if dot_product > 0:
                self.quaternion = np.array([1.0, 0.0, 0.0, 0.0])
            else:
                self.quaternion = np.array([0.0, 0.0, 1.0, 0.0])
        else:
            axis = cross_product / cross_norm
            angle = math.acos(np.clip(dot_product, -1.0, 1.0))
            
            # Add Z-axis rotation for left-right gun rotation
            # This creates a combined rotation
            half_angle = angle / 2.0
            sin_half = math.sin(half_angle)
            cos_half = math.cos(half_angle)
            
            base_quat = np.array([
                cos_half,
                axis[0] * sin_half,
                axis[1] * sin_half,
                axis[2] * sin_half
            ])
            
            # Apply additional Z-axis rotation for gun twist
            if abs(rotation_angle) > 0.01:
                twist_angle = math.radians(rotation_angle * self.rotation_sensitivity)
                half_twist = twist_angle / 2.0
                twist_quat = np.array([
                    math.cos(half_twist),
                    0.0,
                    0.0,
                    math.sin(half_twist)
                ])
                # Multiply quaternions to combine rotations
                self.quaternion = self.multiply_quaternions(base_quat, twist_quat)
            else:
                self.quaternion = base_quat
            
            # Normalize quaternion
            quat_norm = np.linalg.norm(self.quaternion)
            if quat_norm > 0:
                self.quaternion = self.quaternion / quat_norm
    
    def multiply_quaternions(self, q1, q2):
        """Multiply two quaternions q1 * q2"""
        w1, x1, y1, z1 = q1
        w2, x2, y2, z2 = q2
        
        return np.array([
            w1*w2 - x1*x2 - y1*y2 - z1*z2,
            w1*x2 + x1*w2 + y1*z2 - z1*y2,
            w1*y2 - x1*z2 + y1*w2 + z1*x2,
            w1*z2 + x1*y2 - y1*x2 + z1*w2
        ])
    
    def quaternion_to_matrix(self, q):
        """Convert quaternion to rotation matrix"""
        w, x, y, z = q
        
        norm = math.sqrt(w*w + x*x + y*y + z*z)
        if norm > 0:
            w, x, y, z = w/norm, x/norm, y/norm, z/norm
        
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
        
        rotation_matrix = self.quaternion_to_matrix(self.quaternion)
        rotated_tip_offset = (rotation_matrix[:3, :3] @ self.barrel_tip_offset)
        
        tip_position = weapon_pos + rotated_tip_offset
        
        if hasattr(self, '_debug_tip_counter'):
            self._debug_tip_counter += 1
        else:
            self._debug_tip_counter = 0
            
        if self._debug_tip_counter % 60 == 0:
            print(f"Weapon tip position: ({tip_position[0]:.2f}, {tip_position[1]:.2f}, {tip_position[2]:.2f})")
            print(f"Distance to cam: {self.geometry_data.get('distance_to_cam', self.default_distance_to_cam):.2f}m")
        
        return tip_position
    
    def get_firing_direction(self):
        """Get the direction from weapon tip to ArUco target"""
        tip_pos = self.get_weapon_tip_position()
        direction = self.cursor_world_pos - tip_pos
        norm = np.linalg.norm(direction)
        if norm > 0:
            return direction / norm
        else:
            return np.array([0, 0, -1])
    
    def apply_weapon_transform(self):
        """Apply the weapon transformation for rendering"""
        glPushMatrix()
        
        weapon_world_pos = np.array(self.camera_pos) + self.weapon_offset
        glTranslatef(weapon_world_pos[0], weapon_world_pos[1], weapon_world_pos[2])
        
        rotation_matrix = self.quaternion_to_matrix(self.quaternion)
        gl_matrix = rotation_matrix.flatten(order='F')
        glMultMatrixf(gl_matrix.astype(np.float32))
        
        return True
    
    def update_with_aruco(self, degree):
        """Legacy update method for backward compatibility"""
        self.update_aruco_position(degree)
        self.calculate_weapon_orientation()
        
    def update_with_aruco_geometry(self, geometry_data):
        """Update method using geometry calculations"""
        self.update_full_aruco_data(geometry_data)
        self.calculate_weapon_orientation()
    
    def update(self):
        """Update weapon orientation - can be called without parameters for compatibility"""
        self.calculate_weapon_orientation()
        
    def get_cursor_world_position(self):
        """Get the current target world position for debugging"""
        return self.cursor_world_pos
    
    def get_aruco_degree(self):
        """Get the current ArUco degree for debugging"""
        return self.geometry_data.get('degree', 90.0)
    
    def get_geometry_data(self):
        """Get current geometry data for debugging"""
        return self.geometry_data.copy()
    
    def calibrate_barrel_tip_offset(self, x_offset, y_offset, z_offset):
        """Allow runtime calibration of barrel tip position"""
        self.barrel_tip_offset = np.array([x_offset, y_offset, z_offset])
        print(f"Barrel tip offset updated to: ({x_offset:.2f}, {y_offset:.2f}, {z_offset:.2f})")
        
    def calibrate_position_sensitivity(self, sensitivity):
        """Allow runtime calibration of position sensitivity"""
        self.position_sensitivity = max(0.1, sensitivity)
        print(f"Position sensitivity updated to: {self.position_sensitivity:.2f}")
    
    def calibrate_distance_sensitivity(self, sensitivity):
        """Allow runtime calibration of distance sensitivity"""
        self.distance_sensitivity = max(0.01, sensitivity)
        print(f"Distance sensitivity updated to: {self.distance_sensitivity:.2f}")
        
    def set_weapon_forward_direction(self, forward_vector):
        """Allow setting the weapon's forward direction for different models"""
        self.weapon_forward = np.array(forward_vector) / np.linalg.norm(forward_vector)
        print(f"Weapon forward direction set to: {self.weapon_forward}")