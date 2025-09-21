import pygame
from pygame.locals import *
from OpenGL.GL import *
import random
import cv2
import threading
import time

# Import our modules
from src.core.camera import Camera  # Now fixed position camera
from src.entities.enemy.enemy import Enemy
from src.rendering.environment import draw_skybox, draw_ground, draw_weapon_model, draw_cursor_target
from src.rendering.ui import draw_crosshair, draw_health_bar, draw_ammo_display  # Crosshair is now empty
from src.weapons.weapon import shoot  # Updated to use cursor tracking
from src.weapons.weapon_system import WeaponSystem
from src.systems.particles import ShootingEffects  # New visual effects system
from src.core.render import Render
from src.entities.player.health import HealthSystem
from src.systems.collision import CollisionSystem
from src.weapons.cursor_weapon import QuaternionWeapon  # New cursor tracking weapon
from src.vision.estimate import Estimate  # ArUco marker detection
from src.audio.sound_system import initialize_sound_system, cleanup_sound_system  # Sound system

class Game:
    def __init__(self):
        pygame.init()
        
        # Set up display
        self.display = (800, 600)
        pygame.display.set_mode(self.display, DOUBLEBUF | OPENGL)
        pygame.display.set_caption("3D Shooting Game - ArUco Position & Orientation")
        
        # Initialize OpenGL
        Render.init_opengl()
        
        # Initialize sound system
        self.sound_system = initialize_sound_system()
        
        # Initialize shooting effects system
        self.shooting_effects = ShootingEffects()
        
        # ArUco marker detection system
        self.estimator = Estimate()
        self.aruco_thread = None
        self.aruco_running = False
        
        # Store full geometry data instead of just degree
        self.current_geometry_data = {
            'position_offset': 0.0,    # Horizontal position offset (d value)
            'orientation_alpha': 0.0,  # Orientation angle in radians (alpha)
            'degree': 90.0            # Original degree value for compatibility
        }
        self.aruco_lock = threading.Lock()
        
        # Start ArUco detection in separate thread
        self.start_aruco_detection()
        
        # Game objects
        self.camera = Camera()  # Fixed position camera
        self.quaternion_weapon = QuaternionWeapon(self.camera.get_position())
        self.enemies = self.create_enemies()
        self.health_system = HealthSystem(max_health=100)
        self.weapon_system = WeaponSystem(max_ammo=7, reload_time=2.0)
        self.player_radius = 0.5  # Player collision radius
        
        self.clock = pygame.time.Clock()
        self.running = True
        
        self.print_instructions()
    
    def start_aruco_detection(self):
        """Start ArUco marker detection in a separate thread"""
        self.aruco_running = True
        self.aruco_thread = threading.Thread(target=self.aruco_detection_loop, daemon=True)
        self.aruco_thread.start()
        print("ArUco detection started...")
    
    def aruco_detection_loop(self):
        """ArUco detection loop running in separate thread"""
        cap = None
        try:
            # Test if estimator is properly initialized
            if not hasattr(self.estimator, 'K') or not hasattr(self.estimator, 'dist'):
                print("Error: ArUco estimator not properly initialized")
                return
                
            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                print("Warning: Could not open camera for ArUco detection")
                return
                
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            
            print("ArUco camera initialized successfully")
            print("Camera matrix shape:", self.estimator.K.shape)
            print("Distortion coefficients shape:", self.estimator.dist.shape)
            
            while self.aruco_running:
                ret, frame = cap.read()
                if not ret:
                    print("Failed to read frame from camera")
                    continue
                
                try:
                    frame = cv2.flip(frame, 1)
                    frame = cv2.convertScaleAbs(frame, alpha=1.2, beta=20)
                    
                    # Process frame for ArUco markers
                    frame = self.estimator.get_measurements(frame)
                    
                    # Update geometry data thread-safely (NEW!)
                    with self.aruco_lock:
                        self.current_geometry_data = self.estimator.get_weapon_transform_data()
                    
                    # Show ArUco detection window (optional - can be disabled for production)
                    cv2.imshow("ArUco Detection", frame)
                    
                    # Break if 'q' is pressed in the ArUco window
                    key = cv2.waitKey(1) & 0xFF
                    if key == ord('q'):
                        break
                        
                except Exception as frame_error:
                    print(f"Error processing frame: {frame_error}")
                    continue
                
                time.sleep(0.016)  # ~60 FPS
                
        except Exception as e:
            print(f"ArUco detection error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            if cap is not None:
                cap.release()
            cv2.destroyAllWindows()
            print("ArUco detection stopped")
    
    def stop_aruco_detection(self):
        """Stop ArUco detection thread"""
        self.aruco_running = False
        if self.aruco_thread and self.aruco_thread.is_alive():
            self.aruco_thread.join(timeout=1.0)
    
    def create_enemies(self):
        """Create initial enemy cylinders in front of the camera"""
        enemies = []
        for i in range(4):
            # Spawn enemies only in front of camera (negative Z direction)
            # Camera is at (0, 2, 5) looking toward negative Z
            distance = random.uniform(15, 25)
            spread = 10.0  # How wide the spawn area is
            
            x = random.uniform(-spread, spread)  # Left to right spread
            z = -distance + random.uniform(-5, 5)  # In front, with some depth variation
            y = 1.5  # Half the height so they sit on the ground
            
            # Vary the enemy sizes slightly
            height = random.uniform(2.5, 3.5)
            radius = random.uniform(0.6, 1.0)
            
            enemy = Enemy(x, y, z, height, radius)
            enemies.append(enemy)
            print(f"Enemy {i+1} spawned with {enemy.max_health} HP")
        
        return enemies
    
    def print_instructions(self):
        print("Controls:")
        print("ArUco Marker - Aim weapon (POSITION AND ORIENTATION)")
        print("Left Click - Shoot (with muzzle flash, smoke, and screen shake!)")
        print("R - Reload weapon (manual)")
        print("S - Toggle sound on/off")
        print("- / + - Decrease / Increase volume")
        print("ESC - Exit")
        print("Q - Close ArUco detection window")
        print()
        print("Barrel Position Calibration:")
        print("1 - Move barrel tip forward")
        print("2 - Move barrel tip backward")
        print("3 - Move barrel tip up")
        print("4 - Move barrel tip down")
        print("5 - Move barrel tip right") 
        print("6 - Move barrel tip left")
        print("7 - Decrease position sensitivity")
        print("8 - Increase position sensitivity")
        print()
        print("NEW: Enhanced ArUco Controls!")
        print("- ArUco marker now controls BOTH weapon position AND orientation")
        print("- Position follows the 'd' value from geometry calculations")
        print("- Orientation follows the 'alpha' angle from geometry calculations")
        print("- Use keys 7/8 to adjust how much the weapon position moves")
        print("- Watch the weapon move left/right as you move the marker!")
        print()
        print(f"Survive! Destroy all {len(self.enemies)} AI enemies!")
        print("Watch out - they're coming for you!")
        print("Health: 100/100 - Don't let enemies touch you!")
        print(f"Ammo: {self.weapon_system.max_ammo} rounds per magazine")
        print("Watch the beige arm perform the reload animation!")
        print("Sound effects: gun.mp3 for shooting, reload.mp3 for reloading")
        print("Visual effects: muzzle flash, smoke particles, and screen shake!")
        print("Use calibration keys 1-6 to adjust barrel tip position for perfect effects alignment!")
        print("The weapon now physically moves with your ArUco marker - feel the immersion!")
    
    def handle_events(self):
        """Handle pygame events"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                elif event.key == pygame.K_r:
                    # Manual reload with weapon transition
                    if self.weapon_system.force_reload(self.quaternion_weapon.quaternion):
                        print("Manual reload started! Watch the weapon transition and arm animation!")
                    else:
                        print("Cannot reload now (already full or already reloading)")
                elif event.key == pygame.K_q:
                    # Close ArUco window
                    cv2.destroyWindow("ArUco Detection")
                elif event.key == pygame.K_s:
                    # Toggle sound on/off
                    sound_enabled = self.sound_system.toggle_sound()
                    print(f"Sound system {'enabled' if sound_enabled else 'disabled'}")
                elif event.key == pygame.K_MINUS or event.key == pygame.K_KP_MINUS:
                    # Decrease volume
                    current_volume = self.sound_system.volume
                    new_volume = max(0.0, current_volume - 0.1)
                    self.sound_system.set_volume(new_volume)
                    print(f"Volume: {int(new_volume * 100)}%")
                elif event.key == pygame.K_EQUALS or event.key == pygame.K_KP_PLUS:
                    # Increase volume (= key is usually + without shift)
                    current_volume = self.sound_system.volume
                    new_volume = min(1.0, current_volume + 0.1)
                    self.sound_system.set_volume(new_volume)
                    print(f"Volume: {int(new_volume * 100)}%")
                # Calibration controls for barrel tip position
                elif event.key == pygame.K_1:
                    # Move barrel tip forward (negative Z)
                    current_offset = self.quaternion_weapon.barrel_tip_offset
                    self.quaternion_weapon.calibrate_barrel_tip_offset(
                        current_offset[0], current_offset[1], current_offset[2] - 0.1)
                elif event.key == pygame.K_2:
                    # Move barrel tip backward (positive Z)
                    current_offset = self.quaternion_weapon.barrel_tip_offset
                    self.quaternion_weapon.calibrate_barrel_tip_offset(
                        current_offset[0], current_offset[1], current_offset[2] + 0.1)
                elif event.key == pygame.K_3:
                    # Move barrel tip up (positive Y)
                    current_offset = self.quaternion_weapon.barrel_tip_offset
                    self.quaternion_weapon.calibrate_barrel_tip_offset(
                        current_offset[0], current_offset[1] + 0.1, current_offset[2])
                elif event.key == pygame.K_4:
                    # Move barrel tip down (negative Y)
                    current_offset = self.quaternion_weapon.barrel_tip_offset
                    self.quaternion_weapon.calibrate_barrel_tip_offset(
                        current_offset[0], current_offset[1] - 0.1, current_offset[2])
                elif event.key == pygame.K_5:
                    # Move barrel tip right (positive X)
                    current_offset = self.quaternion_weapon.barrel_tip_offset
                    self.quaternion_weapon.calibrate_barrel_tip_offset(
                        current_offset[0] + 0.1, current_offset[1], current_offset[2])
                elif event.key == pygame.K_6:
                    # Move barrel tip left (negative X)
                    current_offset = self.quaternion_weapon.barrel_tip_offset
                    self.quaternion_weapon.calibrate_barrel_tip_offset(
                        current_offset[0] - 0.1, current_offset[1], current_offset[2])
                elif event.key == pygame.K_7:
                    # NEW: Decrease position sensitivity
                    current_sensitivity = self.quaternion_weapon.position_sensitivity
                    new_sensitivity = max(0.5, current_sensitivity - 0.5)
                    self.quaternion_weapon.calibrate_position_sensitivity(new_sensitivity)
                elif event.key == pygame.K_8:
                    # NEW: Increase position sensitivity
                    current_sensitivity = self.quaternion_weapon.position_sensitivity
                    new_sensitivity = min(20.0, current_sensitivity + 0.5)
                    self.quaternion_weapon.calibrate_position_sensitivity(new_sensitivity)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left mouse button
                    # Use ArUco-controlled weapon for shooting with visual effects
                    shoot_result = shoot(self.camera, self.enemies, self.weapon_system, 
                                       self.quaternion_weapon, self.shooting_effects)
                    if not shoot_result:
                        # Shooting failed - could be reloading, no ammo, or fire rate
                        if self.weapon_system.is_reloading:
                            print("Cannot shoot - reloading!")
                        elif self.weapon_system.current_ammo <= 0:
                            print("No ammo!")
                        else:
                            print("Weapon cooling down...")
    
    def update(self, mouse_rel=None):
        """Update game state"""
        # Stop updating if player is dead
        if not self.health_system.is_alive:
            return
        
        # Update weapon system
        self.weapon_system.update()
        
        # Update shooting effects (muzzle flash, smoke, screen shake)
        self.shooting_effects.update()
        
        # Update quaternion weapon with ArUco geometry data (NEW APPROACH!)
        if not self.weapon_system.is_reloading:
            # Get current ArUco geometry data thread-safely
            with self.aruco_lock:
                current_geometry_data = self.current_geometry_data.copy()
            
            # Update weapon using both position and orientation from geometry calculations
            self.quaternion_weapon.update_with_aruco_geometry(current_geometry_data)
            
        # Get player position for collision detection (camera position since camera is fixed)
        player_pos = [self.camera.x, self.camera.y, self.camera.z]
        
        # Update AI enemies
        for enemy in self.enemies:
            enemy.update(player_pos)
        
        # Check for collisions with enemies
        colliding_enemies = CollisionSystem.check_multiple_collisions(
            player_pos, self.player_radius, self.enemies
        )
        
        # Handle collisions
        if colliding_enemies:
            # Take damage from collision
            if self.health_system.take_damage():
                print("Enemy collision! Cannot move to avoid damage - defend yourself!")
        
        # Remove dead enemies from the list
        self.enemies = [enemy for enemy in self.enemies if enemy.alive]
        
        # Check win condition
        if len(self.enemies) == 0 and self.health_system.is_alive:
            print("Victory! All enemies defeated!")
            print(f"Final Health: {self.health_system.current_health}/{self.health_system.max_health}")
            
            # Print final statistics about ArUco geometry usage
            with self.aruco_lock:
                final_geometry = self.current_geometry_data.copy()
            print(f"Final ArUco Position: {final_geometry['position_offset']:.3f}")
            print(f"Final ArUco Orientation: {final_geometry['orientation_alpha']:.3f} rad")
            print("You mastered the geometry-based aiming system!")
            
            self.running = False
        elif not self.health_system.is_alive:
            print("Game Over! You were overwhelmed by enemies.")
            print("The enhanced ArUco system couldn't save you this time!")
            self.running = False
    
    def render(self):
        """Render the game"""
        # Clear screen
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        
        # Apply screen shake BEFORE camera transformation
        self.shooting_effects.apply_screen_shake()
        
        # Apply camera transformation (fixed position)
        self.camera.apply()
        
        # Draw environment
        draw_skybox()
        draw_ground()
        
        # Draw cursor target for visualization (shows where ArUco is pointing)
        draw_cursor_target(self.quaternion_weapon)
        
        # Draw weapon using ArUco tracking with reload transitions
        # The weapon now moves both position and orientation based on geometry calculations
        draw_weapon_model(self.quaternion_weapon, self.weapon_system)
        
        # Render muzzle flash (uses stored position from when effect was triggered)
        self.shooting_effects.render_muzzle_flash()
        
        # Render smoke effects
        self.shooting_effects.render_smoke_effects()
        
        # Draw enemies
        for enemy in self.enemies:
            enemy.draw()
        
        # Draw UI (render after 3D scene to ensure it's on top)
        draw_crosshair()  # This might be empty or show ArUco status
        draw_health_bar(self.health_system.get_health_percentage())
        draw_ammo_display(self.weapon_system)
        
        # Show enhanced effects debug info (optional)
        if self.shooting_effects.is_any_effect_active():
            effects_info = self.shooting_effects.get_effects_info()
            if effects_info['muzzle_flash'] or effects_info['screen_shake']:
                # Could display debug info showing both position and orientation here if needed
                pass
        
        pygame.display.flip()
    
    def run(self):
        """Main game loop"""
        try:
            print("Starting enhanced ArUco position and orientation tracking...")
            print("Move your ArUco marker to see the weapon move AND rotate!")
            
            while self.running:
                self.handle_events()
                self.update()
                self.render()
                self.clock.tick(60)
        finally:
            # Clean up ArUco detection
            print("Stopping ArUco detection...")
            self.stop_aruco_detection()
            # Clean up sound system
            cleanup_sound_system()
            print("Game cleanup complete.")
        
        pygame.quit()

def main():
    print("3D Shooting Game - Enhanced ArUco Position & Orientation Control")
    print("="*60)
    game = Game()
    game.run()

if __name__ == "__main__":
    main()