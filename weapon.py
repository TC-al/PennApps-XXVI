def shoot(camera, enemies, weapon_system):
    """Handle shooting mechanics - destroy the closest enemy if weapon can shoot"""
    
    # Check if weapon can shoot
    if not weapon_system.shoot():
        return False
    
    # Get camera position and forward direction
    start_pos = [camera.x, camera.y, camera.z]
    direction = camera.get_forward_vector()
    max_distance = 100.0
    
    # Check for enemy intersections and find the closest one
    closest_enemy = None
    closest_distance = float('inf')
    
    for enemy in enemies:
        if not enemy.alive:
            continue
            
        distance = enemy.intersects_ray(start_pos, direction, max_distance)
        if distance is not None and distance < closest_distance:
            closest_distance = distance
            closest_enemy = enemy
    
    # Damage the closest hit enemy
    if closest_enemy is not None:
        damage = 25  # Standard damage per shot
        was_killed = closest_enemy.take_damage(damage)
        
        if was_killed:
            alive_count = sum(1 for enemy in enemies if enemy.alive)
            print(f"Enemy destroyed! {alive_count} enemies remaining.")
        else:
            health_remaining = closest_enemy.current_health
            print(f"Enemy hit! Health: {health_remaining}/{closest_enemy.max_health}")
    
    return True