import math
import time

class EnemyAI:
    """Handles ghost enemy AI behavior and floating movement logic"""
    
    @staticmethod
    def update_movement(enemy, player_pos):
        """Update ghost AI - float towards player with hovering motion"""
        if not enemy.alive:
            return
            
        # Calculate direction to player
        dx = player_pos[0] - enemy.x
        dz = player_pos[2] - enemy.z
        
        # Calculate distance to player
        distance = math.sqrt(dx * dx + dz * dz)
        
        # Move towards player (more aggressive when close)
        if distance > 0.8:  # Reduced minimum distance for more aggressive behavior
            # Normalize direction vector
            dx /= distance
            dz /= distance
            
            # Increase speed when close to player for more intense combat
            current_speed = enemy.speed
            if distance < 5.0:
                current_speed *= 1.5  # 50% speed boost when close
            
            # Move towards player in X and Z axes
            enemy.x += dx * current_speed
            enemy.z += dz * current_speed
        
        # Add floating motion for ghost behavior
        EnemyAI._update_floating_motion(enemy)
    
    @staticmethod
    def _update_floating_motion(enemy):
        """Add gentle floating up and down motion to the ghost"""
        # Use current time for smooth floating animation
        current_time = time.time()
        
        # Create unique floating pattern for each ghost based on position
        # This prevents all ghosts from floating in sync
        phase_offset = (enemy.x + enemy.z) * 2.0
        
        # Calculate floating height with sine wave
        float_amplitude = 0.3  # How high/low the ghost floats
        float_frequency = 1.5   # How fast the floating motion is
        base_hover_height = 2.0  # Base height above ground
        
        # Create floating motion
        float_offset = float_amplitude * math.sin(current_time * float_frequency + phase_offset)
        target_y = base_hover_height + float_offset
        
        # Smooth interpolation to target height (prevents jerky movement)
        height_difference = target_y - enemy.y
        smoothing_factor = 0.1  # Adjust for smoother/snappier movement
        enemy.y += height_difference * smoothing_factor
        
        # Ensure ghost doesn't go below minimum height
        min_height = enemy.height / 2 + 0.5
        enemy.y = max(min_height, enemy.y)
    
    @staticmethod
    def calculate_direction_to_player(enemy, player_pos):
        """Calculate normalized direction vector from enemy to player"""
        dx = player_pos[0] - enemy.x
        dz = player_pos[2] - enemy.z
        distance = math.sqrt(dx * dx + dz * dz)
        
        if distance > 0:
            return dx / distance, dz / distance, distance
        return 0, 0, 0
    
    @staticmethod
    def should_move_toward_player(enemy, player_pos, min_distance=0.8):
        """Determine if ghost should move toward player based on distance"""
        dx = player_pos[0] - enemy.x
        dz = player_pos[2] - enemy.z
        distance = math.sqrt(dx * dx + dz * dz)
        return distance > min_distance
    
    @staticmethod
    def get_speed_multiplier(enemy, player_pos, close_distance=5.0, speed_boost=1.5):
        """Get speed multiplier based on distance to player"""
        dx = player_pos[0] - enemy.x
        dz = player_pos[2] - enemy.z
        distance = math.sqrt(dx * dx + dz * dz)
        
        if distance < close_distance:
            return speed_boost
        return 1.0
    
    @staticmethod
    def add_ghost_sway(enemy):
        """Add subtle side-to-side swaying motion for more ghostly appearance"""
        current_time = time.time()
        phase_offset = enemy.x * 1.5 + enemy.z * 0.8
        
        # Small sway motion
        sway_amplitude = 0.05
        sway_frequency = 0.8
        
        sway_x = sway_amplitude * math.sin(current_time * sway_frequency + phase_offset)
        sway_z = sway_amplitude * math.cos(current_time * sway_frequency * 1.3 + phase_offset)
        
        # Apply sway (gentle movement)
        enemy.x += sway_x * 0.1
        enemy.z += sway_z * 0.1