import pygame
from pygame.locals import *
from OpenGL.GL import *
import random

# Import our modules
from camera import Camera
from enemy import Enemy
from environment import draw_skybox, draw_ground
from ui import draw_crosshair, draw_health_bar, draw_ammo_display
from weapon import shoot
from weapon_system import WeaponSystem
from render import Render
from health import HealthSystem
from collision import CollisionSystem

class Game:
    def __init__(self):
        pygame.init()
        
        # Set up display
        self.display = (800, 600)
        pygame.display.set_mode(self.display, DOUBLEBUF | OPENGL)
        pygame.display.set_caption("3D Shooting Game - AI Enemies")
        
        # Hide cursor and enable relative mouse mode
        pygame.mouse.set_visible(False)
        pygame.event.set_grab(True)
        
        # Initialize OpenGL
        Render.init_opengl()
        
        # Game objects
        self.camera = Camera()
        self.enemies = self.create_enemies()
        self.health_system = HealthSystem(max_health=100)
        self.weapon_system = WeaponSystem(max_ammo=7, reload_time=2.0)
        self.player_radius = 0.5  # Player collision radius
        
        self.clock = pygame.time.Clock()
        self.running = True
        
        self.print_instructions()
    
    def create_enemies(self):
        """Create initial enemy cylinders around the player"""
        enemies = []
        for i in range(8):
            # Spawn enemies in a circle around the player, but at a distance
            angle = (2 * 3.14159 * i) / 8
            distance = random.uniform(15, 25)
            x = distance * random.uniform(-1, 1)
            z = distance * random.uniform(-1, 1)
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
        print("WASD - Move around")
        print("Mouse - Look around")
        print("Left Click - Shoot")
        print("R - Reload weapon (manual)")
        print("ESC - Exit")
        print(f"Survive! Destroy all {len(self.enemies)} AI enemies!")
        print("Watch out - they're coming for you!")
        print("Health: 100/100 - Don't let enemies touch you!")
        print(f"Ammo: {self.weapon_system.max_ammo} rounds per magazine")
    
    def handle_events(self):
        """Handle pygame events"""
        mouse_rel = pygame.mouse.get_rel()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                elif event.key == pygame.K_r:
                    # Manual reload
                    if self.weapon_system.force_reload():
                        print("Manual reload started!")
                    else:
                        print("Cannot reload now (already full or already reloading)")
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left mouse button
                    shoot_result = shoot(self.camera, self.enemies, self.weapon_system)
                    if not shoot_result:
                        # Shooting failed - could be reloading, no ammo, or fire rate
                        if self.weapon_system.is_reloading:
                            print("Cannot shoot - reloading!")
                        elif self.weapon_system.current_ammo <= 0:
                            print("No ammo!")
                        else:
                            print("Weapon cooling down...")
        
        return mouse_rel
    
    def update(self, mouse_rel):
        """Update game state"""
        # Stop updating if player is dead
        if not self.health_system.is_alive:
            return
        
        # Update weapon system
        self.weapon_system.update()
            
        keys = pygame.key.get_pressed()
        self.camera.update(keys, mouse_rel)
        
        # Get player position for collision detection
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
                # Push player away from enemies
                total_push_x = 0
                total_push_z = 0
                for enemy in colliding_enemies:
                    push_x, push_z = CollisionSystem.push_player_away(player_pos, enemy, 0.3)
                    total_push_x += push_x
                    total_push_z += push_z
                
                # Apply push to camera position
                self.camera.x += total_push_x
                self.camera.z += total_push_z
        
        # Remove dead enemies from the list
        self.enemies = [enemy for enemy in self.enemies if enemy.alive]
        
        # Check win condition
        if len(self.enemies) == 0 and self.health_system.is_alive:
            print("Victory! All enemies defeated!")
            print(f"Final Health: {self.health_system.current_health}/{self.health_system.max_health}")
            self.running = False
        elif not self.health_system.is_alive:
            self.running = False
    
    def render(self):
        """Render the game"""
        # Clear screen
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        
        # Apply camera transformation
        self.camera.apply()
        
        # Draw environment
        draw_skybox()
        draw_ground()
        
        # Draw enemies
        for enemy in self.enemies:
            enemy.draw()
        
        # Draw UI
        draw_crosshair()
        draw_health_bar(self.health_system.get_health_percentage())
        draw_ammo_display(self.weapon_system)
        
        pygame.display.flip()
    
    def run(self):
        """Main game loop"""
        while self.running:
            mouse_rel = self.handle_events()
            self.update(mouse_rel)
            self.render()
            self.clock.tick(60)
        
        pygame.quit()

def main():
    game = Game()
    game.run()

if __name__ == "__main__":
    main()