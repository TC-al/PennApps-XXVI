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
            'degree': 90.0            # Original degree value for compatibility
        }
        
        # Target distance for aiming
        self.target_distance = 20.0
        
        # Weapon model specific offsets (based on your pistol GLB model)
        # These values are calibrated for the pistol model's actual barrel position
        self.barrel_tip_offset = np.array([0.0, 0.2, -1.0])  # Tip is forward from weapon center
        
        # Position sensitivity multiplier (adjust this to control how much the weapon moves)
        self.position_sensitivity = 5.0  # How much the weapon position changes with ArUco movement
        
        # Debug flag
        self._debug_counter = 0
        
    def update_aruco_geometry(self, geometry_data):
        """Update weapon using geometry calculations from ArUco detection"""
        self.geometry_data = geometry_data
        
        # Update weapon position based on the 'd' value from geometry calculations
        position_offset = geometry_data['position_offset']
        
        # Apply horizontal position offset to weapon (left-right movement)
        # The 'd' value represents horizontal displacement from center
        self.weapon_offset = self.base_weapon_offset.copy()
        self.weapon_offset[0] += position_offset * self.position_sensitivity  # Apply to X axis
        
        # Update weapon orientation based on the 'alpha' value (angle in radians)
        orientation_alpha = geometry_data['orientation_alpha']
        
        # Calculate target position based on the alpha angle
        # The alpha angle is the angle from point P to the arc end E
        # We need to transform this into world coordinates for aiming
        
        # Get weapon position (includes the horizontal offset)
        weapon_world_pos = np.array(self.camera_pos) + self.weapon_offset
        
        # Calculate target position using the alpha angle
        # Alpha is angle from horizontal, so we use it to determine target direction
        # The target should be at distance from the weapon position, not camera position
        target_x = weapon_world_pos[0] + (math.cos(orientation_alpha) * self.target_distance)
        target_y = weapon_world_pos[1]  # Keep at same height as weapon
        target_z = weapon_world_pos[2] - (math.sin(orientation_alpha) * self.target_distance)
        
        self.cursor_world_pos = np.array([target_x, target_y, target_z])
        
        # Debug output
        self._debug_counter += 1
        if self._debug_counter % 30 == 0:  # Print every 0.5 seconds at 60 FPS
            print(f"Alpha: {math.degrees(orientation_alpha):.1f}°, Pos offset: {position_offset:.3f}")
            print(f"Target: ({target_x:.1f}, {target_y:.1f}, {target_z:.1f})")
    
    def update_aruco_position(self, degree):
        """Legacy method for backward compatibility - converts degree to geometry data"""
        # Convert degree to position and orientation for compatibility
        # This is a simplified conversion - ideally use update_aruco_geometry instead
        
        # Clamp degree to valid range
        degree = max(0.0, min(180.0, degree))
        
        # Convert degree to horizontal angle
        horizontal_angle_deg = (degree - 90.0)  # -90 to +90 range
        horizontal_angle_rad = math.radians(horizontal_angle_deg)
        
        # Simple conversion to geometry data format
        geometry_data = {
            'position_offset': horizontal_angle_rad * 0.1,  # Simple mapping
            'orientation_alpha': horizontal_angle_rad,
            'degree': degree
        }
        
        self.update_aruco_geometry(geometry_data)
    
    def calculate_weapon_orientation(self):
        """Calculate weapon orientation to point at ArUco target using quaternions"""
        # Get weapon world position (now includes position offset from ArUco)
        weapon_pos = np.array(self.camera_pos) + self.weapon_offset
        
        # Calculate direction from weapon to target
        direction = self.cursor_world_pos - weapon_pos
        direction_norm = np.linalg.norm(direction)
        
        if direction_norm < 0.001:  # Avoid division by zero
            self.quaternion = np.array([1.0, 0.0, 0.0, 0.0])
            return
            
        direction = direction / direction_norm  # Normalize
        
        # The weapon's forward direction depends on your GLB model
        # Common possibilities: [0,0,-1], [0,0,1], [1,0,0], [-1,0,0]
        # Try different ones based on how your model is oriented
        
        # Most common for gun models pointing forward
        forward = np.array([0.0, 0.0, -1.0])  # Z-negative is forward (most common)
        
        # If the gun points sideways in the model, try:
        # forward = np.array([1.0, 0.0, 0.0])  # X-positive is forward
        # forward = np.array([-1.0, 0.0, 0.0]) # X-negative is forward
        
        # Calculate rotation axis and angle
        cross_product = np.cross(forward, direction)
        dot_product = np.dot(forward, direction)
        
        # Handle edge cases
        cross_norm = np.linalg.norm(cross_product)
        if cross_norm < 0.001:  # Vectors are parallel
            if dot_product > 0:
                # Same direction - no rotation needed
                self.quaternion = np.array([1.0, 0.0, 0.0, 0.0])
            else:
                # Opposite direction - 180 degree rotation around Y axis
                self.quaternion = np.array([0.0, 0.0, 1.0, 0.0])
        else:
            # Calculate quaternion from axis and angle
            axis = cross_product / cross_norm
            angle = math.acos(np.clip(dot_product, -1.0, 1.0))
            
            # Create quaternion from axis-angle representation
            half_angle = angle / 2.0
            sin_half = math.sin(half_angle)
            cos_half = math.cos(half_angle)
            
            self.quaternion = np.array([
                cos_half,
                axis[0] * sin_half,
                axis[1] * sin_half,
                axis[2] * sin_half
            ])
            
            # Normalize quaternion to avoid numerical drift
            quat_norm = np.linalg.norm(self.quaternion)
            if quat_norm > 0:
                self.quaternion = self.quaternion / quat_norm
    
    def quaternion_to_matrix(self, q):
        """Convert quaternion to rotation matrix"""
        w, x, y, z = q
        
        # Ensure quaternion is normalized
        norm = math.sqrt(w*w + x*x + y*y + z*z)
        if norm > 0:
            w, x, y, z = w/norm, x/norm, y/norm, z/norm
        
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
        # Use the current weapon offset (which includes ArUco position adjustments)
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
            print(f"Position offset: {self.geometry_data['position_offset']:.3f}, Alpha: {math.degrees(self.geometry_data['orientation_alpha']):.1f}°")
        
        return tip_position
    
    def get_firing_direction(self):
        """Get the direction from weapon tip to ArUco target"""
        tip_pos = self.get_weapon_tip_position()
        direction = self.cursor_world_pos - tip_pos
        norm = np.linalg.norm(direction)
        if norm > 0:
            return direction / norm  # Normalize
        else:
            return np.array([0, 0, -1])  # Default forward
    
    def apply_weapon_transform(self):
        """Apply the weapon transformation for rendering"""
        glPushMatrix()
        
        # Position weapon relative to camera (now includes ArUco position offset)
        weapon_world_pos = np.array(self.camera_pos) + self.weapon_offset
        glTranslatef(weapon_world_pos[0], weapon_world_pos[1], weapon_world_pos[2])
        
        # Apply quaternion rotation
        rotation_matrix = self.quaternion_to_matrix(self.quaternion)
        
        # Convert to OpenGL format (column major) and apply
        gl_matrix = rotation_matrix.flatten(order='F')  # Column major order
        glMultMatrixf(gl_matrix.astype(np.float32))
        
        return True  # Matrix is pushed, caller should pop
    
    def update_with_aruco(self, degree):
        """Legacy update method for backward compatibility"""
        self.update_aruco_position(degree)
        self.calculate_weapon_orientation()
        
    def update_with_aruco_geometry(self, geometry_data):
        """New update method using geometry calculations"""
        self.update_aruco_geometry(geometry_data)
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
        return self.geometry_data['degree']
    
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
        
    def set_weapon_forward_direction(self, forward_vector):
        """Allow setting the weapon's forward direction for different models"""
        # This can be called if your weapon model has a different forward direction
        # Common values: [0,0,-1], [0,0,1], [1,0,0], [-1,0,0], [0,1,0], [0,-1,0]
        self.weapon_forward = np.array(forward_vector) / np.linalg.norm(forward_vector)
        print(f"Weapon forward direction set to: {self.weapon_forward}")