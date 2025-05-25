import pygame
import cv2
import numpy as np
import math
from animations import *
import random  # Added for fruit/meteor spawning

# --- 常數 ---
SCREEN_WIDTH = 1080
SCREEN_HEIGHT = 720
FPS = 60

# 顏色定義
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
PLAYER1_COLOR = (0, 0, 255)
PLAYER1_DEAD_COLOR = (0, 0, 100)
PLAYER2_COLOR = (255, 0, 0)
PLAYER2_DEAD_COLOR = (100, 0, 0)
CHAIN_COLOR = (150, 150, 150)
LASER_WALL_COLOR = (255, 0, 255)
GOAL_P1_COLOR = (100, 100, 255)
GOAL_P2_COLOR = (255, 100, 100)
TEXT_COLOR = (200, 200, 200)
REVIVE_PROMPT_COLOR = (50, 200, 50)
COOP_BOX_COLOR = (180, 140, 0)

# 玩家參數
PLAYER_RADIUS = 15
PLAYER_SPEED = 3
CHAIN_MAX_LENGTH = 400
CHAIN_ITERATIONS = 5
REVIVAL_RADIUS = CHAIN_MAX_LENGTH
REVIVE_KEYP1 = pygame.K_f
REVIVE_KEYP2 = pygame.K_PERIOD

# 協力推箱子常數
COOP_BOX_SIZE = 40
COOP_BOX_SPEED = 2
COOP_BOX_PUSH_RADIUS = 60

# 地刺參數
SAFE_COLOR = (220, 220, 220)
DANGER_COLOR = (220, 40, 40)

# 遊戲狀態
STATE_START_SCREEN = 4
STATE_PLAYING = 0
STATE_GAME_OVER = 1
STATE_LEVEL_COMPLETE = 2
STATE_ALL_LEVELS_COMPLETE = 3

# --- 果實相關常數 ---
FRUIT_RADIUS = 15
FRUIT_EFFECT_DURATION = 30.0  # 30秒效果時間

# 果實顏色
MIRROR_FRUIT_COLOR = (255, 215, 0)  # 金色 - 鏡像操控
INVISIBLE_WALL_COLOR = (138, 43, 226)  # 紫色 - 透明牆壁
VOLCANO_FRUIT_COLOR = (255, 69, 0)  # 橙紅色 - 火山爆發

# 火山效果相關常數
METEOR_WARNING_TIME = 1.5  # 警告時間1.5秒
METEOR_FALL_TIME = 0.5  # Time the meteor stays on screen after warning
METEOR_SIZE = 50  # Increased size for better visibility
METEOR_COLOR = (139, 69, 19)  # 棕色
WARNING_COLOR = (255, 255, 0)  # 黃色警告

# --- Pygame 初始化 ---
pygame.init()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("雙人合作遊戲 Demo - 果實能力")
clock = pygame.time.Clock()

# 圖片載入
box_img = pygame.image.load("box.png").convert_alpha()
spike_trap_img_out = pygame.image.load("spike_trap_out.png").convert_alpha()
spike_trap_img_in = pygame.image.load("spike_trap_in.png").convert_alpha()

# 加載支持中文的字體
try:
    system_fonts = pygame.font.get_fonts()
    chinese_font_name = None
    possible_chinese_fonts = [
        'microsoftyahei', 'msyh', 'simsun', 'simhei', 'noto sans cjk tc',
        'noto sans cjk sc', 'microsoft jhenghei', 'pmingliu', 'kaiti', 'heiti tc',
        'heiti sc', 'droid sans fallback'
    ]
    for font in possible_chinese_fonts:
        if font in system_fonts or font.replace(' ', '') in system_fonts:
            chinese_font_name = font
            break
    if chinese_font_name:
        font_path = pygame.font.match_font(chinese_font_name)
        font_small = pygame.font.Font(font_path, 36)
        font_large = pygame.font.Font(font_path, 74)
        font_tiny = pygame.font.Font(font_path, 24)
        font_effect = pygame.font.Font(font_path, 18)  # For effect timers
    else:
        print("警告：找不到中文字體，遊戲中的中文可能無法正確顯示")
        font_small = pygame.font.Font(None, 36)
        font_large = pygame.font.Font(None, 74)
        font_tiny = pygame.font.Font(None, 24)
        font_effect = pygame.font.Font(None, 18)
except Exception as e:
    print(f"載入字體時出錯：{e}")
    font_small = pygame.font.Font(None, 36)
    font_large = pygame.font.Font(None, 74)
    font_tiny = pygame.font.Font(None, 24)
    font_effect = pygame.font.Font(None, 18)

# --- OpenCV 視窗準備 (Not used by fruits) ---
use_opencv = False
opencv_window_name = "P2 Paint Area (OpenCV)"
paint_surface_width = 400
paint_surface_height = 300
paint_surface = np.zeros((paint_surface_height, paint_surface_width, 3), dtype=np.uint8) + 200


def show_opencv_paint_window():
    if use_opencv:
        cv2.imshow(opencv_window_name, paint_surface)
        key = cv2.waitKey(1) & 0xFF


# --- 果實類別 ---
class Fruit(pygame.sprite.Sprite):
    def __init__(self, x, y, fruit_type):
        super().__init__()
        self.fruit_type = fruit_type  # "mirror", "invisible_wall", "volcano"
        self.image = pygame.Surface([FRUIT_RADIUS * 2, FRUIT_RADIUS * 2], pygame.SRCALPHA)  # SRCALPHA for transparency
        # self.image.set_colorkey((0,0,0)) # Not needed if using SRCALPHA and drawing transparently

        if fruit_type == "mirror":
            color = MIRROR_FRUIT_COLOR
        elif fruit_type == "invisible_wall":
            color = INVISIBLE_WALL_COLOR
        elif fruit_type == "volcano":
            color = VOLCANO_FRUIT_COLOR
        else:
            color = (255, 255, 255)  # Default white

        pygame.draw.circle(self.image, color, (FRUIT_RADIUS, FRUIT_RADIUS), FRUIT_RADIUS)
        pygame.draw.circle(self.image, WHITE, (FRUIT_RADIUS, FRUIT_RADIUS), FRUIT_RADIUS, 2)  # Outline

        self.rect = self.image.get_rect(center=(x, y))


# --- 流星類別 (火山爆發效果) ---
class Meteor(pygame.sprite.Sprite):
    def __init__(self, x, y, lifetime=METEOR_FALL_TIME):
        super().__init__()
        self.image = pygame.Surface([METEOR_SIZE, METEOR_SIZE], pygame.SRCALPHA)
        pygame.draw.circle(self.image, METEOR_COLOR, (METEOR_SIZE // 2, METEOR_SIZE // 2), METEOR_SIZE // 2)
        pygame.draw.ellipse(self.image, (0, 0, 0, 100), [0, 0, METEOR_SIZE, METEOR_SIZE], 2)  # Shadow effect
        self.rect = self.image.get_rect(center=(x, y))
        self.active = True  # Kept for consistency, might not be needed if using lifetime
        self.lifetime = lifetime
        self.timer = 0

    def update(self, dt):
        self.timer += dt
        if self.timer >= self.lifetime:
            self.kill()  # Remove meteor after its lifetime


# --- 警告標記類別 ---
class Warning(pygame.sprite.Sprite):
    def __init__(self, x, y, duration):
        super().__init__()
        self.image = pygame.Surface([METEOR_SIZE * 1.5, METEOR_SIZE * 1.5],
                                    pygame.SRCALPHA)  # Slightly larger than meteor
        self.rect = self.image.get_rect(center=(x, y))
        self.duration = duration
        self.timer = 0
        self.spawn_pos = (x, y)  # Store where the meteor should spawn

    def update(self, dt):
        self.timer += dt
        # Flashing effect
        # Cycle alpha between ~64 and 255 over 0.5 seconds
        flash_speed = 10
        alpha = int(159 + 96 * math.sin(self.timer * flash_speed))
        self.image.fill((0, 0, 0, 0))  # Clear previous frame
        pygame.draw.circle(self.image, WARNING_COLOR + (alpha,), (self.rect.width // 2, self.rect.height // 2),
                           int(METEOR_SIZE * 0.75), 3)

        if self.timer >= self.duration:
            self.kill()  # Remove warning
            return True  # Indicate meteor should spawn
        return False  # Continue updating


# --- 效果管理器 ---
class EffectManager:
    def __init__(self):
        self.default_laser_wall_alpha = 255
        self.effects = {
            "mirror_p1": {"active": False, "timer": 0, "name": "P1 反向"},
            "mirror_p2": {"active": False, "timer": 0, "name": "P2 反向"},
            "invisible_wall": {"active": False, "timer": 0, "flash_timer": 0,
                               "current_alpha": self.default_laser_wall_alpha, "name": "牆壁隱形"},
            # Start showing
            "volcano": {"active": False, "timer": 0, "meteor_timer": 0, "name": "火山爆發"}
        }

    def apply_effect(self, effect_type, player_id=None):
        if effect_type == "mirror":
            if player_id == 0:
                self.effects["mirror_p1"]["active"] = True
                self.effects["mirror_p1"]["timer"] = FRUIT_EFFECT_DURATION
            elif player_id == 1:
                self.effects["mirror_p2"]["active"] = True
                self.effects["mirror_p2"]["timer"] = FRUIT_EFFECT_DURATION
        elif effect_type == "invisible_wall":
            self.effects["invisible_wall"]["active"] = True
            self.effects["invisible_wall"]["timer"] = FRUIT_EFFECT_DURATION
            self.effects["invisible_wall"]["flash_timer"] = 0
            self.effects["invisible_wall"]["current_alpha"] = 0  # Start fully transparent
        elif effect_type == "volcano":
            self.effects["volcano"]["active"] = True
            self.effects["volcano"]["timer"] = FRUIT_EFFECT_DURATION
            self.effects["volcano"]["meteor_timer"] = 0  # Reset meteor timer

    def update(self, dt):
        # Update mirror effects
        for key in ["mirror_p1", "mirror_p2"]:
            if self.effects[key]["active"]:
                self.effects[key]["timer"] -= dt
                if self.effects[key]["timer"] <= 0:
                    self.effects[key]["active"] = False

        # Update invisible wall effect
        if self.effects["invisible_wall"]["active"]:
            self.effects["invisible_wall"]["timer"] -= dt
            self.effects["invisible_wall"]["flash_timer"] += dt

            target_alpha = 0  # Default to transparent during effect

            if self.effects["invisible_wall"]["timer"] <= 0:
                self.effects["invisible_wall"]["active"] = False
                self.effects["invisible_wall"]["current_alpha"] = self.default_laser_wall_alpha  # Reset to default
            else:
                # Cycle logic for alpha: 5s total, 4s transparent, 1s fade in/out
                cycle_duration = 5.0
                hidden_duration = 4.0  # Transparent for 4 seconds
                visible_duration = 1.0  # Visible (fading) for 1 second
                fade_time = visible_duration / 2  # 0.5s for fade-in, 0.5s for fade-out

                current_cycle_time = self.effects["invisible_wall"]["flash_timer"] % cycle_duration

                if current_cycle_time < hidden_duration:  # Hidden phase
                    target_alpha = 0
                else:  # Visible phase (1 second duration)
                    time_in_visible_phase = current_cycle_time - hidden_duration  # Ranges from 0.0 to 1.0

                    if time_in_visible_phase < fade_time:  # Fade-in (e.g., 0 to 0.5s)
                        # Interpolate alpha from 0 to 255
                        target_alpha = int((time_in_visible_phase / fade_time) * 255)
                    else:  # Fade-out (e.g., 0.5s to 1.0s)
                        # Interpolate alpha from 255 to 0
                        time_in_fade_out = time_in_visible_phase - fade_time
                        target_alpha = int((1.0 - (time_in_fade_out / fade_time)) * 255)

                self.effects["invisible_wall"]["current_alpha"] = max(0, min(255, target_alpha))
        else:  # Effect not active
            if self.effects["invisible_wall"]["current_alpha"] != self.default_laser_wall_alpha:
                self.effects["invisible_wall"]["current_alpha"] = self.default_laser_wall_alpha


        # Update volcano effect
        if self.effects["volcano"]["active"]:
            self.effects["volcano"]["timer"] -= dt
            self.effects["volcano"]["meteor_timer"] += dt
            if self.effects["volcano"]["timer"] <= 0:
                self.effects["volcano"]["active"] = False

    def get_laser_wall_alpha(self):
        if self.effects["invisible_wall"]["active"]:
            return self.effects["invisible_wall"]["current_alpha"]
        return self.default_laser_wall_alpha  # Default fully visible

    def is_mirror_active(self, player_id):
        if player_id == 0:
            return self.effects["mirror_p1"]["active"]
        elif player_id == 1:
            return self.effects["mirror_p2"]["active"]
        return False



    def should_spawn_meteor(self):
        # Spawn meteor every 1 to 2 seconds randomly
        return (self.effects["volcano"]["active"] and
                self.effects["volcano"]["meteor_timer"] >= random.uniform(1.0, 2.0))

    def reset_meteor_timer(self):
        self.effects["volcano"]["meteor_timer"] = 0

    def reset_all_effects(self):
        for effect_key in self.effects:
            self.effects[effect_key]["active"] = False
            self.effects[effect_key]["timer"] = 0
            if "flash_timer" in self.effects[effect_key]:
                self.effects[effect_key]["flash_timer"] = 0
            if "showing" in self.effects[effect_key]:  # Ensure walls are visible on reset
                self.effects[effect_key]["showing"] = True
            if "meteor_timer" in self.effects[effect_key]:
                self.effects[effect_key]["meteor_timer"] = 0
            if effect_key == "invisible_wall":
                self.effects[effect_key]["current_alpha"] = self.default_laser_wall_alpha

    def get_active_effects_info(self):
        info = []
        for key, data in self.effects.items():
            if data["active"]:
                timer_str = f"{data['timer']:.1f}s"
                info.append(f"{data['name']}: {timer_str}")
        return info


# --- 玩家類別 ---
class Player(pygame.sprite.Sprite):
    def __init__(self, x, y, alive_color, dead_color, control_keys, player_id):
        super().__init__()
        self.start_pos = pygame.math.Vector2(x, y)
        self.pos = pygame.math.Vector2(x, y)
        self.alive_color = alive_color
        self.dead_color = dead_color
        self.control_keys = control_keys
        self.player_id = player_id
        self.facing_left = False
        self.walk_frames = []
        self.idle_frames = []

        if self.player_id == 0:
            self.walk_frames = load_knight_run_animation(target_width=PLAYER_RADIUS * 8,target_height=PLAYER_RADIUS * 8)
            self.idle_frames = load_knight_idle_animation(target_width=PLAYER_RADIUS * 8,target_height=PLAYER_RADIUS * 8)
            self.is_witch = False
            self.frame_interval = 0.2
            self.idle_frame_interval = 0.3
        elif self.player_id == 1:
            self.is_witch = True
            self.walk_frames = load_witch_run_animation(target_width=PLAYER_RADIUS * 4, target_height=PLAYER_RADIUS * 4)
            self.idle_frames = load_witch_idle_animation(target_width=PLAYER_RADIUS * 4,target_height=PLAYER_RADIUS * 4)
            self.frame_interval = 0.2
            self.idle_frame_interval = 0.3

        self.dead_frames = []
        for frame in self.walk_frames:
            dead_frame = frame.copy()
            dead_frame.set_alpha(100)
            self.dead_frames.append(dead_frame)

        self.current_frame = 0
        self.frame_timer = 0
        # self.frame_interval = 0.2 # This is set above per player_id

        self.image = self.walk_frames[0]
        self.rect = self.image.get_rect(center=self.pos)

        self.is_alive = True
        self.death_pos = None

        # For death shake animation
        self.is_shaking = False
        self.shake_timer = 0.0
        self.shake_duration = 0.2  # seconds for shake
        self.shake_magnitude = 4  # pixels for shake intensity
        self.original_death_pos_for_shake = None  # Stores the position around which to shake

    def reset(self):
        self.pos = pygame.math.Vector2(self.start_pos.x, self.start_pos.y)
        self.is_alive = True
        self.death_pos = None
        self.image = self.walk_frames[0]
        self.rect = self.image.get_rect(center=self.pos)
        self.current_frame = 0

        # Reset shake attributes
        self.is_shaking = False
        self.shake_timer = 0.0
        self.original_death_pos_for_shake = None

    def revive(self):
        self.is_alive = True
        if self.death_pos:
            self.pos = pygame.math.Vector2(self.death_pos.x, self.death_pos.y)  # Revive at final death position
        else:  # Fallback if revived without a specific death_pos (e.g. game reset)
            self.pos = pygame.math.Vector2(self.start_pos.x, self.start_pos.y)

        self.rect.center = self.pos
        self.image = self.walk_frames[0]  # Reset to default alive frame
        self.current_frame = 0  # Reset animation frame

        self.is_shaking = False  # Crucial: stop shaking if revived
        self.shake_timer = 0.0
        self.original_death_pos_for_shake = None  # Clear shake-related temp state
        self.death_pos = None  # Player is no longer considered "at a death position"

    def die(self):
        if self.is_alive:  # Only proceed if player was alive
            self.is_alive = False
            # Guard against re-triggering shake if somehow called multiple times rapidly
            if not self.is_shaking and self.death_pos is None:
                self.death_pos = self.pos.copy()  # Final resting position after shake
                self.original_death_pos_for_shake = self.pos.copy()  # Center of shake
                self.is_shaking = True
                self.shake_timer = self.shake_duration
                self._update_dead_image()  # Set the visual to dead sprite
                # Update rect based on current pos and new dead image
                self.rect = self.image.get_rect(center=self.pos)

    # MODIFIED: update_movement to integrate fruit effects
    def update_movement(self, laser_walls, coop_boxes=None, spike_trap_group=None, meteor_sprites=None,
                        effect_manager=None, dt=0.016):
        if not self.is_alive:
            if self.is_shaking:
                self.shake_timer -= dt
                if self.shake_timer > 0 and self.original_death_pos_for_shake:
                    offset_x = random.uniform(-self.shake_magnitude, self.shake_magnitude)
                    offset_y = random.uniform(-self.shake_magnitude, self.shake_magnitude)
                    self.rect.centerx = self.original_death_pos_for_shake.x + offset_x
                    self.rect.centery = self.original_death_pos_for_shake.y + offset_y
                    # self.pos should remain self.original_death_pos_for_shake
                else:  # Shake ended
                    self.is_shaking = False
                    self.shake_timer = 0.0
                    if self.death_pos:  # Snap to final death position
                        self.pos = self.death_pos
                        self.rect.center = self.death_pos
                    # else: Error case, death_pos should be set
                self._update_dead_image()  # Update visual to dead sprite (especially after shake)
            else:  # Not shaking, just dead and static
                if self.death_pos:
                    self.pos = self.death_pos  # Ensure pos is synced
                    self.rect.center = self.death_pos
                self._update_dead_image()
            return

        keys = pygame.key.get_pressed()
        movement_vector = pygame.math.Vector2(0, 0)

        mirror_active = effect_manager and effect_manager.is_mirror_active(self.player_id)

        up_key_actual = self.control_keys['down'] if mirror_active else self.control_keys['up']
        down_key_actual = self.control_keys['up'] if mirror_active else self.control_keys['down']
        left_key_actual = self.control_keys['right'] if mirror_active else self.control_keys['left']
        right_key_actual = self.control_keys['left'] if mirror_active else self.control_keys['right']

        if keys[up_key_actual]: movement_vector.y = -1
        if keys[down_key_actual]: movement_vector.y = 1
        if keys[left_key_actual]: movement_vector.x = -1
        if keys[right_key_actual]: movement_vector.x = 1

        # Determine facing direction based on NON-MIRRORED input for animation
        if keys[self.control_keys['left']]:
            self.facing_left = True
        elif keys[self.control_keys['right']]:
            self.facing_left = False

        is_moving = movement_vector.length_squared() > 0

        if is_moving:
            movement_vector.normalize_ip()
            movement_vector *= PLAYER_SPEED

        tentative_pos = self.pos + movement_vector

        # Store original rect for collision detection before moving
        original_rect = self.rect.copy()

        # Tentative rects for X and Y movement
        temp_rect_x = original_rect.copy()
        temp_rect_x.centerx = tentative_pos.x

        temp_rect_y = original_rect.copy()
        temp_rect_y.centery = tentative_pos.y

        # Laser Wall Collision
        # Walls are always collidable. Their visual appearance is handled by alpha.
        collided_with_laser = False
        for lw in laser_walls:  # laser_walls is the sprite group
            if temp_rect_x.colliderect(lw.rect):
                movement_vector.x = 0
                if not original_rect.colliderect(lw.rect):
                    collided_with_laser = True;
                    break
            if temp_rect_y.colliderect(lw.rect):  # Check Y collision separately
                movement_vector.y = 0
                if not original_rect.colliderect(lw.rect):
                    collided_with_laser = True;
                    break
        if collided_with_laser:
            self.die()
            return

        # Update tentative_pos based on adjusted movement_vector (if hit laser)
        tentative_pos = self.pos + movement_vector
        temp_rect_x.centerx = tentative_pos.x
        temp_rect_y.centery = tentative_pos.y

        # Coop Box Collision
        if coop_boxes:
            for box in coop_boxes:
                if temp_rect_x.colliderect(box.rect):
                    movement_vector.x = 0
                if temp_rect_y.colliderect(box.rect):  # Check against the original Y rect if X was blocked
                    movement_vector.y = 0

        # Update tentative_pos again
        tentative_pos = self.pos + movement_vector
        # Create a final tentative rect for spike and meteor collision
        final_tentative_rect = self.rect.copy()
        final_tentative_rect.center = tentative_pos

        # Spike Trap Collision
        if spike_trap_group:
            for spike in spike_trap_group:
                # Player attempts to move into the spike's area
                if spike.is_dangerous() and final_tentative_rect.colliderect(spike.rect):
                    # Death should occur at self.pos (position *before* moving into spike)
                    self.die()
                    return  # Exit update_movement

        # Meteor Collision
        if meteor_sprites:
            for meteor in meteor_sprites:
                # Player attempts to move into the meteor's area
                if final_tentative_rect.colliderect(meteor.rect):
                    # Death should occur at self.pos (position *before* moving into meteor)
                    self.die()
                    return  # Exit update_movement

        # Final position update
        self.pos += movement_vector
        self.pos.x = max(self.rect.width // 2, min(self.pos.x, SCREEN_WIDTH - self.rect.width // 2))
        self.pos.y = max(self.rect.height // 2, min(self.pos.y, SCREEN_HEIGHT - self.rect.height // 2))
        self.rect.center = self.pos

        self._update_alive_image(is_moving)

    def _update_alive_image(self, is_moving):
        """更新存活狀態的圖片"""
        # keys = pygame.key.get_pressed() # facing_left is now handled in update_movement
        # if keys[self.control_keys['left']]: self.facing_left = True
        # elif keys[self.control_keys['right']]: self.facing_left = False

        if is_moving:
            self.frame_timer += 1 / FPS
            if self.frame_timer >= self.frame_interval:
                self.current_frame = (self.current_frame + 1) % len(self.walk_frames)
                self.frame_timer = 0
            frame = self.walk_frames[self.current_frame]
        else:
            if not self.idle_frames:
                frame = self.walk_frames[0]
                self.current_frame = 0
            else:
                if self.current_frame >= len(self.idle_frames):  # Reset if switched from walk
                    self.current_frame = 0
                self.frame_timer += 1 / FPS
                # Ensure idle_frame_interval is defined, otherwise use frame_interval
                current_idle_interval = getattr(self, 'idle_frame_interval', self.frame_interval)
                if self.frame_timer >= current_idle_interval:
                    self.current_frame = (self.current_frame + 1) % len(self.idle_frames)
                    self.frame_timer = 0
                frame = self.idle_frames[self.current_frame]

        if self.facing_left:
            frame = pygame.transform.flip(frame, True, False)

        self.image = frame

    def _update_dead_image(self):
        """更新死亡狀態的圖片"""
        # Ensure dead_frames is not empty and current_frame is valid
        if not self.dead_frames:  # Fallback if dead_frames are not loaded
            # Create a simple dead image if needed, or handle error
            # For now, assume dead_frames are always available from walk_frames
            temp_surface = pygame.Surface((PLAYER_RADIUS * 2, PLAYER_RADIUS * 2))
            temp_surface.fill(self.dead_color)  # Use the defined dead_color
            temp_surface.set_alpha(150)  # Make it somewhat transparent
            self.image = temp_surface
            if self.facing_left:  # Still apply flip if necessary
                self.image = pygame.transform.flip(self.image, True, False)
            return

        # Use the first frame of dead_frames for a static dead appearance
        # If you want an animated death (beyond shake), this would be more complex
        frame = self.dead_frames[0]  # Or some other logic for dead sprite
        if self.facing_left:
            frame = pygame.transform.flip(frame, True, False)
        self.image = frame

    def draw(self, surface):
        surface.blit(self.image, self.rect)

    def _make_grayscale(self, surface):  # Keep this utility if needed elsewhere
        grayscale_surface = surface.copy()
        arr = pygame.surfarray.pixels3d(grayscale_surface)
        gray = (arr[:, :, 0] * 0.299 + arr[:, :, 1] * 0.587 + arr[:, :, 2] * 0.114).astype(arr.dtype)
        arr[:, :, 0] = gray
        arr[:, :, 1] = gray
        arr[:, :, 2] = gray
        del arr
        return grayscale_surface


# --- 牆壁類別 (雷射牆壁) ---
class LaserWall(pygame.sprite.Sprite):
    def __init__(self, x, y, width, height):
        super().__init__()
        self.original_color = LASER_WALL_COLOR # Store the base color
        # Create the image that will be drawn. It needs SRCALPHA to support transparency.
        self.image = pygame.Surface([width, height], pygame.SRCALPHA)
        # Fill with opaque color initially (alpha = 255)
        self.image.fill((self.original_color[0], self.original_color[1], self.original_color[2], 255))
        self.rect = self.image.get_rect(topleft=(x, y))
        self._current_alpha = 255

    def update_visuals(self, alpha_value):
        alpha_value = max(0, min(255, int(alpha_value))) # Clamp alpha value
        if self._current_alpha != alpha_value:
            self._current_alpha = alpha_value
            # Re-fill the surface with the original color but new alpha
            self.image.fill((self.original_color[0], self.original_color[1], self.original_color[2], self._current_alpha))


# --- 目標類別 (顏色地板) ---
class Goal(pygame.sprite.Sprite):
    def __init__(self, x, y, color, player_id_target):
        super().__init__()
        self.image = pygame.Surface([int(PLAYER_RADIUS * 2.5), int(PLAYER_RADIUS * 2.5)])
        self.image.fill(color)
        self.rect = self.image.get_rect(center=(x, y))
        self.player_id_target = player_id_target
        self.is_active = False

    def update_status(self, player):
        if player.is_alive and self.rect.colliderect(player.rect) and player.player_id == self.player_id_target:
            self.is_active = True
        else:
            self.is_active = False

    def draw(self, surface):
        surface.blit(self.image, self.rect)
        if self.is_active:
            pygame.draw.rect(surface, WHITE, self.rect, 3)


# --- 協力推箱子類別 ---
class CoopBox(pygame.sprite.Sprite):
    def __init__(self, x, y, img=None):
        super().__init__()
        self.collision_size = COOP_BOX_SIZE
        self.display_size = 60
        self.rect = pygame.Rect(0, 0, self.collision_size, self.collision_size)
        self.rect.center = (x, y)
        self.pos = pygame.math.Vector2(x, y)
        if img:
            self.image = pygame.transform.scale(img, (self.display_size, self.display_size))
        else:
            self.image = pygame.Surface([self.display_size, self.display_size])
            self.image.fill(COOP_BOX_COLOR)

    def move(self, direction, obstacles):
        tentative_pos = self.pos + direction * COOP_BOX_SPEED
        test_rect = self.rect.copy()
        test_rect.center = tentative_pos
        for obs in obstacles:  # obstacles here are laser_walls
            if test_rect.colliderect(obs.rect) and isinstance(obs, LaserWall):  # Ensure it's a LaserWall
                # LaserWalls (even if visually transparent due to fruit) should block the box.
                return  # Blocked by any laser wall
        if not (self.collision_size // 2 <= tentative_pos.x <= SCREEN_WIDTH - self.collision_size // 2 and
                self.collision_size // 2 <= tentative_pos.y <= SCREEN_HEIGHT - self.collision_size // 2):
            return  # Out of bounds
        self.pos = tentative_pos
        self.rect.center = self.pos

    def draw(self, surface):
        img_rect = self.image.get_rect(center=self.rect.center)
        surface.blit(self.image, img_rect)


# ---地刺類別---
class SpikeTrap(pygame.sprite.Sprite):
    def __init__(self, x, y, width=40, height=40, out_time=1.0, in_time=1.5, phase_offset=0.0,
                 img_out=None, img_in=None):
        super().__init__()
        self.rect = pygame.Rect(x, y, width, height)
        self.out_time = out_time
        self.in_time = in_time
        self.cycle_time = self.out_time + self.in_time
        self.timer = phase_offset
        self.active = False
        self.img_out = img_out
        self.img_in = img_in

    def update(self, dt):
        self.timer += dt
        phase = self.timer % self.cycle_time
        self.active = phase < self.out_time

    def is_dangerous(self):
        return self.active

    def draw(self, surface):
        current_img = None
        if self.active and self.img_out:
            current_img = self.img_out
        elif not self.active and self.img_in:
            current_img = self.img_in

        if current_img:
            img_scaled = pygame.transform.scale(current_img, (self.rect.width, self.rect.height))
            surface.blit(img_scaled, self.rect)
        else:
            color = DANGER_COLOR if self.active else SAFE_COLOR
            pygame.draw.rect(surface, color, self.rect)


# --- 關卡資料 ---
levels_data = [
    {
        "player1_start": (100, SCREEN_HEIGHT // 2),
        "player2_start": (150, SCREEN_HEIGHT // 2),
        "goal1_pos": (SCREEN_WIDTH - 50, 100),
        "goal2_pos": (SCREEN_WIDTH - 50, SCREEN_HEIGHT - 100),
        "laser_walls": [
            (SCREEN_WIDTH // 2 - 10, 150, 20, SCREEN_HEIGHT - 300),
            (200, SCREEN_HEIGHT // 2 - 10, SCREEN_WIDTH // 2 - 200 - 10, 10),
            (SCREEN_WIDTH // 2 + 10, SCREEN_HEIGHT // 2 - 10, SCREEN_WIDTH // 2 - 20 - 10, 10),
        ],
        "coop_box_start": [(SCREEN_WIDTH // 4, SCREEN_HEIGHT // 4), (SCREEN_WIDTH // 4 + 50, SCREEN_HEIGHT // 4 + 50)],
        "spike_traps": [
            (40, 40, 40, 40, 1.0, 2.0, 0.0),
            (100, 40, 40, 40, 0.7, 1.5, 0.5),
            (160, 40, 40, 40, 1.2, 1.0, 1.0),
        ],
        "fruits": [  # Added fruits for level 1
            (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 100, "mirror"),
            (200, 100, "invisible_wall"),
            (SCREEN_WIDTH - 200, SCREEN_HEIGHT - 100, "volcano"),
        ]
    },
    {
        "player1_start": (50, 50),
        "player2_start": (100, 50),
        "goal1_pos": (SCREEN_WIDTH - 50, SCREEN_HEIGHT - 50),
        "goal2_pos": (SCREEN_WIDTH - 100, SCREEN_HEIGHT - 50),
        "laser_walls": [
            (0, 0, SCREEN_WIDTH, 20), (0, SCREEN_HEIGHT - 20, SCREEN_WIDTH, 20),
            (0, 0, 20, SCREEN_HEIGHT), (SCREEN_WIDTH - 20, 0, 20, SCREEN_HEIGHT),
            (150, 20, 20, SCREEN_HEIGHT // 2),
            (150, SCREEN_HEIGHT // 2 + 50, 20, SCREEN_HEIGHT // 2 - 70),
            (SCREEN_WIDTH - 150, 20, 20, SCREEN_HEIGHT // 2 - 50),
            (SCREEN_WIDTH - 150, SCREEN_HEIGHT // 2, 20, SCREEN_HEIGHT // 2 - 20),
            (150, SCREEN_HEIGHT // 3, SCREEN_WIDTH - 300, 20),
            (150, SCREEN_HEIGHT * 2 // 3, SCREEN_WIDTH - 300, 20),
        ],
        "coop_box_start": [(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)],  # Ensure this is a list of tuples for consistency
        "fruits": [  # Added fruits for level 2
            (SCREEN_WIDTH // 3, SCREEN_HEIGHT // 3, "volcano"),
            (SCREEN_WIDTH * 2 // 3, SCREEN_HEIGHT * 2 // 3, "mirror"),
            (SCREEN_WIDTH // 2, 100, "invisible_wall"),
        ]
    }
]
current_level_index = 0

# --- 遊戲物件群組 ---
all_sprites = pygame.sprite.Group()  # Not heavily used, but good for organization
laser_wall_sprites = pygame.sprite.Group()
goal_sprites = pygame.sprite.Group()
player_sprites = pygame.sprite.Group()
coop_box_group = pygame.sprite.Group()
spike_trap_group = pygame.sprite.Group()
fruit_sprites = pygame.sprite.Group()  # New group for fruits
meteor_sprites = pygame.sprite.Group()  # New group for meteors
warning_sprites = pygame.sprite.Group()  # New group for warnings

# --- 遊戲物件實體 ---
player1 = Player(0, 0, PLAYER1_COLOR, PLAYER1_DEAD_COLOR,
                 {'up': pygame.K_w, 'down': pygame.K_s, 'left': pygame.K_a, 'right': pygame.K_d}, 0)
player2 = Player(0, 0, PLAYER2_COLOR, PLAYER2_DEAD_COLOR,
                 {'up': pygame.K_UP, 'down': pygame.K_DOWN, 'left': pygame.K_LEFT, 'right': pygame.K_RIGHT}, 1)
player_sprites.add(player1, player2)

goal1 = Goal(0, 0, GOAL_P1_COLOR, 0)
goal2 = Goal(0, 0, GOAL_P2_COLOR, 1)
# coop_box is loaded per level

effect_manager = EffectManager()  # Initialize EffectManager


def load_level(level_idx):
    global game_state
    if level_idx >= len(levels_data):
        game_state = STATE_ALL_LEVELS_COMPLETE
        return

    level = levels_data[level_idx]

    # Clear existing sprites from groups
    laser_wall_sprites.empty()
    goal_sprites.empty()
    coop_box_group.empty()
    spike_trap_group.empty()
    fruit_sprites.empty()
    meteor_sprites.empty()
    warning_sprites.empty()
    effect_manager.reset_all_effects()

    player1.start_pos = pygame.math.Vector2(level["player1_start"])
    player2.start_pos = pygame.math.Vector2(level["player2_start"])
    player1.reset()
    player2.reset()

    for lw_data in level["laser_walls"]:
        laser_wall_sprites.add(LaserWall(*lw_data))

    goal1.rect.center = level["goal1_pos"]
    goal2.rect.center = level["goal2_pos"]
    goal1.is_active = False
    goal2.is_active = False
    goal_sprites.add(goal1, goal2)

    coop_box_starts = level.get("coop_box_start", [])  # Ensure coop_box_start is present
    if coop_box_starts:
        if isinstance(coop_box_starts[0], (list, tuple)) and not isinstance(coop_box_starts[0], int):
            for pos_data in coop_box_starts:
                if len(pos_data) == 2:
                    coop_box_group.add(CoopBox(pos_data[0], pos_data[1], img=box_img))
                # ... (other conditions for coop_box_starts if any)
        elif len(coop_box_starts) == 2 and isinstance(coop_box_starts[0], (int, float)):
            coop_box_group.add(CoopBox(coop_box_starts[0], coop_box_starts[1], img=box_img))

    for spike_data in level.get("spike_traps", []):
        spike_trap_group.add(SpikeTrap(*spike_data, img_out=spike_trap_img_out, img_in=spike_trap_img_in))

    # --- MODIFIED FRUIT SPAWNING LOGIC ---
    obstacle_sprites_for_fruits = pygame.sprite.Group()
    obstacle_sprites_for_fruits.add(laser_wall_sprites.sprites())
    obstacle_sprites_for_fruits.add(spike_trap_group.sprites())
    obstacle_sprites_for_fruits.add(coop_box_group.sprites())
    obstacle_sprites_for_fruits.add(goal_sprites.sprites())
    # Potentially add players' start positions if fruits shouldn't spawn right on them
    # temp_player_rects = [player1.rect.copy(), player2.rect.copy()] # if needed

    for fruit_data in level.get("fruits", []):
        fx, fy, ftype = fruit_data
        original_pos_valid = True
        max_spawn_attempts = 50  # Max attempts to find a new spot
        current_attempts = 0

        # Create a temporary rect for the fruit at its original intended position
        fruit_rect = pygame.Rect(0, 0, FRUIT_RADIUS * 2, FRUIT_RADIUS * 2)
        fruit_rect.center = (fx, fy)

        # Check collision with existing obstacles
        for obs in obstacle_sprites_for_fruits:
            if fruit_rect.colliderect(obs.rect):
                original_pos_valid = False
                break

        # Check if too close to screen edges (already handled by random range if relocated)
        if not (FRUIT_RADIUS <= fruit_rect.centerx <= SCREEN_WIDTH - FRUIT_RADIUS and \
                FRUIT_RADIUS <= fruit_rect.centery <= SCREEN_HEIGHT - FRUIT_RADIUS):
            original_pos_valid = False

        if original_pos_valid:
            fruit_sprites.add(Fruit(fx, fy, ftype))
        else:
            # Try to find a new random valid position
            found_new_spot = False
            for attempt in range(max_spawn_attempts):
                current_attempts += 1
                new_fx = random.randint(FRUIT_RADIUS, SCREEN_WIDTH - FRUIT_RADIUS)
                new_fy = random.randint(FRUIT_RADIUS, SCREEN_HEIGHT - FRUIT_RADIUS)
                fruit_rect.center = (new_fx, new_fy)

                colliding_with_obstacle = False
                for obs in obstacle_sprites_for_fruits:
                    if fruit_rect.colliderect(obs.rect):
                        colliding_with_obstacle = True
                        break

                if not colliding_with_obstacle:
                    fruit_sprites.add(Fruit(new_fx, new_fy, ftype))
                    found_new_spot = True
                    # print(f"Fruit {ftype} relocated to ({new_fx},{new_fy}) after {current_attempts} attempts.")
                    break

            if not found_new_spot:
                print(
                    f"Warning: Could not find a valid spawn location for fruit type '{ftype}' at ({fx},{fy}) after {max_spawn_attempts} attempts. Skipping this fruit.")

    game_state = STATE_PLAYING


# ---遊戲初始化---
game_state = STATE_START_SCREEN
current_level_index = 0
running = True

# --- 閃爍文字相關變數 ---
prompt_blink_timer = 0.0
prompt_blink_interval = 0.5
prompt_text_visible = True

# ---復活設置---
REVIVE_HOLD_TIME = 1.5
revive_progress = 0.0
revive_target = None


def draw_game_state_messages():
    if game_state == STATE_GAME_OVER:
        game_over_text = font_large.render("遊戲結束", True, TEXT_COLOR)
        restart_text = font_small.render("按 R 鍵重新開始", True, TEXT_COLOR)
        screen.blit(game_over_text, (SCREEN_WIDTH // 2 - game_over_text.get_width() // 2, SCREEN_HEIGHT // 2 - 50))
        screen.blit(restart_text, (SCREEN_WIDTH // 2 - restart_text.get_width() // 2, SCREEN_HEIGHT // 2 + 20))
    elif game_state == STATE_ALL_LEVELS_COMPLETE:
        complete_text = font_large.render("所有關卡完成！", True, TEXT_COLOR)
        restart_text = font_small.render("按 R 鍵重新開始", True, TEXT_COLOR)
        screen.blit(complete_text, (SCREEN_WIDTH // 2 - complete_text.get_width() // 2, SCREEN_HEIGHT // 2 - 50))
        screen.blit(restart_text, (SCREEN_WIDTH // 2 - restart_text.get_width() // 2, SCREEN_HEIGHT // 2 + 20))

    if game_state == STATE_PLAYING:
        level_text = font_small.render(f"關卡 {current_level_index + 1}", True, TEXT_COLOR)
        screen.blit(level_text, (10, 10))

        p1_status_text = "存活" if player1.is_alive else "死亡"
        p2_status_text = "存活" if player2.is_alive else "死亡"
        p1_text = font_tiny.render(f"玩家1: {p1_status_text}", True, PLAYER1_COLOR)
        p2_text = font_tiny.render(f"玩家2: {p2_status_text}", True, PLAYER2_COLOR)
        screen.blit(p1_text, (10, 50))
        screen.blit(p2_text, (10, 75))

        if (player1.is_alive and not player2.is_alive) or \
                (player2.is_alive and not player1.is_alive):
            revive_hint = font_tiny.render("靠近隊友按住 F/. 復活", True, REVIVE_PROMPT_COLOR)
            screen.blit(revive_hint, (SCREEN_WIDTH // 2 - revive_hint.get_width() // 2, 10))

        # Display active effects
        active_effects = effect_manager.get_active_effects_info()
        y_offset = 100
        for effect_str in active_effects:
            effect_surf = font_effect.render(effect_str, True, TEXT_COLOR)
            screen.blit(effect_surf, (10, y_offset))
            y_offset += 20

        # Push hint (simplified as there can be multiple boxes)
        # This needs to be smarter if there are multiple boxes. For now, it checks the first one if any.
        if player1.is_alive and player2.is_alive and coop_box_group:
            first_box = next(iter(coop_box_group))  # Get the first box
            p1_near = player1.pos.distance_to(first_box.pos) < COOP_BOX_PUSH_RADIUS
            p2_near = player2.pos.distance_to(first_box.pos) < COOP_BOX_PUSH_RADIUS
            if p1_near and p2_near:
                push_hint = font_tiny.render("兩人靠近可推箱", True, (225, 210, 80))
                screen.blit(push_hint, (SCREEN_WIDTH // 2 - push_hint.get_width() // 2, 40))


# ---遊戲主程式循環---
while running:
    dt = clock.tick(FPS) / 1000.0
    keys = pygame.key.get_pressed()  # Get keys once per frame

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        # --- 開始畫面事件處理 ---
        if game_state == STATE_START_SCREEN:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    current_level_index = 0
                    load_level(current_level_index)
                    game_state = STATE_PLAYING
        if event.type == pygame.KEYDOWN:
            if (game_state == STATE_GAME_OVER or game_state == STATE_ALL_LEVELS_COMPLETE) and event.key == pygame.K_r:
                if game_state == STATE_ALL_LEVELS_COMPLETE:
                    current_level_index = 0
                load_level(current_level_index)  # This will reset effects

    if game_state == STATE_START_SCREEN:
        prompt_blink_timer += dt
        if prompt_blink_timer >= prompt_blink_interval:
            prompt_blink_timer = 0.0  # 重置計時器
            prompt_text_visible = not prompt_text_visible
    # ---遊戲狀態_遊玩中---
    elif game_state == STATE_PLAYING:
        effect_manager.update(dt)  # Update effects first

        # Update player movement (pass effect_manager and meteor_sprites)
        player1.update_movement(laser_wall_sprites, coop_box_group, spike_trap_group, meteor_sprites, effect_manager,
                                dt)
        player2.update_movement(laser_wall_sprites, coop_box_group, spike_trap_group, meteor_sprites, effect_manager,
                                dt)

        # Player-Fruit collision
        for player in player_sprites:
            if player.is_alive:
                collided_fruits = pygame.sprite.spritecollide(player, fruit_sprites,
                                                              True)  # True to remove fruit on collision
                for fruit in collided_fruits:
                    effect_manager.apply_effect(fruit.fruit_type, player.player_id)
                    # Add sound effect or visual feedback for fruit pickup here if desired

        # Volcano effect: Spawn warnings and meteors
        if effect_manager.should_spawn_meteor():
            spawn_x = random.randint(METEOR_SIZE, SCREEN_WIDTH - METEOR_SIZE)
            spawn_y = random.randint(METEOR_SIZE, SCREEN_HEIGHT - METEOR_SIZE)
            warning_sprites.add(Warning(spawn_x, spawn_y, METEOR_WARNING_TIME))
            effect_manager.reset_meteor_timer()

        # Update warnings and spawn meteors
        for warning in list(warning_sprites):  # Iterate over a copy for safe removal
            if warning.update(dt):  # True if warning expired and meteor should spawn
                meteor_sprites.add(Meteor(warning.spawn_pos[0], warning.spawn_pos[1]))

        warning_sprites.update(dt)  # Ensure this is called if not done inside loop
        meteor_sprites.update(dt)  # Update meteors (e.g., for lifetime)

        # --- 推箱判斷 ---
        if player1.is_alive and player2.is_alive:
            for coop_box in coop_box_group:
                p1_near = player1.pos.distance_to(coop_box.pos) < COOP_BOX_PUSH_RADIUS
                p2_near = player2.pos.distance_to(coop_box.pos) < COOP_BOX_PUSH_RADIUS
                if p1_near and p2_near:
                    # Determine push direction from player inputs relative to the box
                    # This logic might need refinement if players push in opposite directions
                    # For simplicity, let's combine their intended directions
                    dir_p1 = pygame.math.Vector2(0, 0)
                    if keys[player1.control_keys['right']]: dir_p1.x += 1
                    if keys[player1.control_keys['left']]: dir_p1.x -= 1
                    if keys[player1.control_keys['down']]: dir_p1.y += 1
                    if keys[player1.control_keys['up']]: dir_p1.y -= 1

                    dir_p2 = pygame.math.Vector2(0, 0)
                    if keys[player2.control_keys['right']]: dir_p2.x += 1
                    if keys[player2.control_keys['left']]: dir_p2.x -= 1
                    if keys[player2.control_keys['down']]: dir_p2.y += 1
                    if keys[player2.control_keys['up']]: dir_p2.y -= 1

                    # If players are trying to push, average their direction or use the dominant one
                    # A more robust system would check if they are on opposite sides pushing towards each other
                    # For now, if either is pushing, and they are both near, the box moves.
                    # The direction can be tricky. A simple approach: if P1 pushes right, and P2 is also near, box moves right.
                    # Let's use the combined direction from player inputs

                    # Consider movement based on player positions relative to box and their input
                    # A simpler model: if both near and any player is pushing towards the box's direction
                    # For now, using combined normalized input:
                    total_dir = pygame.math.Vector2(0, 0)
                    # P1 movement input
                    if keys[player1.control_keys['right']]: total_dir.x += 1
                    if keys[player1.control_keys['left']]:  total_dir.x -= 1
                    if keys[player1.control_keys['down']]:  total_dir.y += 1
                    if keys[player1.control_keys['up']]:    total_dir.y -= 1
                    # P2 movement input
                    if keys[player2.control_keys['right']]: total_dir.x += 1
                    if keys[player2.control_keys['left']]:  total_dir.x -= 1
                    if keys[player2.control_keys['down']]:  total_dir.y += 1
                    if keys[player2.control_keys['up']]:    total_dir.y -= 1

                    if total_dir.length_squared() > 0:
                        total_dir.normalize_ip()
                        # Pass only laser_wall_sprites as obstacles for boxes
                        coop_box.move(total_dir, laser_wall_sprites)

        # --- 鎖鏈物理 ---
        # (Chain physics code remains largely the same)
        for _ in range(CHAIN_ITERATIONS):
            if player1.is_alive and player2.is_alive:
                p1_pos_vec = player1.pos
                p2_pos_vec = player2.pos
                delta = p2_pos_vec - p1_pos_vec
                distance = delta.length()
                if distance > CHAIN_MAX_LENGTH and distance != 0:
                    diff = (distance - CHAIN_MAX_LENGTH) / distance
                    # Correct for collision with walls/boxes after chain pull
                    p1_new_pos = player1.pos + delta * 0.5 * diff
                    p2_new_pos = player2.pos - delta * 0.5 * diff

                    # Basic boundary check for chain pull (can be more sophisticated)
                    player1.pos.x = max(player1.rect.width // 2,
                                        min(p1_new_pos.x, SCREEN_WIDTH - player1.rect.width // 2))
                    player1.pos.y = max(player1.rect.height // 2,
                                        min(p1_new_pos.y, SCREEN_HEIGHT - player1.rect.height // 2))
                    player2.pos.x = max(player2.rect.width // 2,
                                        min(p2_new_pos.x, SCREEN_WIDTH - player2.rect.width // 2))
                    player2.pos.y = max(player2.rect.height // 2,
                                        min(p2_new_pos.y, SCREEN_HEIGHT - player2.rect.height // 2))

                    player1.rect.center = player1.pos
                    player2.rect.center = player2.pos

            elif player1.is_alive and not player2.is_alive and player2.death_pos:
                delta = player2.death_pos - player1.pos
                distance = delta.length()
                if distance > CHAIN_MAX_LENGTH and distance != 0:
                    diff_factor = (distance - CHAIN_MAX_LENGTH) / distance
                    p1_new_pos = player1.pos + delta * diff_factor
                    player1.pos.x = max(player1.rect.width // 2,
                                        min(p1_new_pos.x, SCREEN_WIDTH - player1.rect.width // 2))
                    player1.pos.y = max(player1.rect.height // 2,
                                        min(p1_new_pos.y, SCREEN_HEIGHT - player1.rect.height // 2))
                    player1.rect.center = player1.pos
            elif player2.is_alive and not player1.is_alive and player1.death_pos:
                delta = player1.death_pos - player2.pos
                distance = delta.length()
                if distance > CHAIN_MAX_LENGTH and distance != 0:
                    diff_factor = (distance - CHAIN_MAX_LENGTH) / distance
                    p2_new_pos = player2.pos + delta * diff_factor
                    player2.pos.x = max(player2.rect.width // 2,
                                        min(p2_new_pos.x, SCREEN_WIDTH - player2.rect.width // 2))
                    player2.pos.y = max(player2.rect.height // 2,
                                        min(p2_new_pos.y, SCREEN_HEIGHT - player2.rect.height // 2))
                    player2.rect.center = player2.pos

        # ----是否過關---
        goal1.update_status(player1)
        goal2.update_status(player2)
        if goal1.is_active and goal2.is_active and player1.is_alive and player2.is_alive:
            current_level_index += 1
            if current_level_index < len(levels_data):
                load_level(current_level_index)
            else:
                game_state = STATE_ALL_LEVELS_COMPLETE
        if not player1.is_alive and not player2.is_alive:
            game_state = STATE_GAME_OVER


    # ---遊戲畫面繪製---
    screen.fill(BLACK)

    if game_state == STATE_START_SCREEN:
        title_text = font_large.render("雙人合作遊戲 Demo", True, TEXT_COLOR)
        screen.blit(title_text, (SCREEN_WIDTH // 2 - title_text.get_width() // 2, SCREEN_HEIGHT // 3))

        if prompt_text_visible:  # 只有當 prompt_text_visible 為 True 時才繪製
            start_prompt_text = font_small.render("按 Enter 開始遊戲", True, TEXT_COLOR)
            screen.blit(start_prompt_text, (SCREEN_WIDTH // 2 - start_prompt_text.get_width() // 2, SCREEN_HEIGHT // 2))

    elif game_state == STATE_PLAYING:
        # ... 您現有的遊戲畫面繪製 ...
        draw_game_state_messages()  # UI 文字等
    elif game_state == STATE_GAME_OVER or game_state == STATE_ALL_LEVELS_COMPLETE:
        draw_game_state_messages()  # 遊戲結束/完成訊息

    show_opencv_paint_window()  # If used

    # Update laser wall visuals based on effect manager
    current_lw_alpha = effect_manager.get_laser_wall_alpha()
    for wall_sprite in laser_wall_sprites:  # Use a different variable name if 'wall' is used elsewhere
        if hasattr(wall_sprite, 'update_visuals'):  # Check if it's a LaserWall with the method
            wall_sprite.update_visuals(current_lw_alpha)

    laser_wall_sprites.draw(screen)  # Always draw; their alpha determines visibility

    goal_sprites.draw(screen)  # Draw goals first
    for goal_sprite in goal_sprites:  # Custom draw for active state highlight
        goal_sprite.draw(screen)

    for coop_box_item in coop_box_group:  # Renamed to avoid conflict
        coop_box_item.draw(screen)
        # Number display on boxes
        p1_on_box = player1.is_alive and player1.pos.distance_to(coop_box_item.pos) < COOP_BOX_PUSH_RADIUS
        p2_on_box = player2.is_alive and player2.pos.distance_to(coop_box_item.pos) < COOP_BOX_PUSH_RADIUS
        num_on_box = int(p1_on_box) + int(p2_on_box)
        if num_on_box < 2:  # Show remaining needed
            box_text_val = 2 - num_on_box
            if box_text_val > 0:
                box_text = font_small.render(str(box_text_val), True, WHITE)
                box_cx, box_cy = int(coop_box_item.rect.centerx), int(coop_box_item.rect.centery)
                screen.blit(box_text, (box_cx - box_text.get_width() // 2, box_cy - box_text.get_height() // 2))

    for spike in spike_trap_group:
        spike.update(dt)  # Update spike state
        spike.draw(screen)

    fruit_sprites.draw(screen)  # Draw fruits
    warning_sprites.draw(screen)  # Draw warnings
    meteor_sprites.draw(screen)  # Draw meteors

    # 繪製鎖鏈
    chain_start_pos = None
    chain_end_pos = None
    can_draw_chain = False
    if player1.is_alive and player2.is_alive:
        chain_start_pos = player1.rect.center
        chain_end_pos = player2.rect.center
        can_draw_chain = True
    elif player1.is_alive and not player2.is_alive and player2.death_pos:
        chain_start_pos = player1.rect.center
        chain_end_pos = player2.death_pos
        can_draw_chain = True
    elif player2.is_alive and not player1.is_alive and player1.death_pos:
        chain_start_pos = player2.rect.center
        chain_end_pos = player1.death_pos
        can_draw_chain = True
    if can_draw_chain:
        pygame.draw.line(screen, CHAIN_COLOR, chain_start_pos, chain_end_pos, 3)

    player_sprites.draw(screen)  # Draw players on top of most things

    draw_game_state_messages()  # Draw UI text last

    # 判斷復活條件
    # keys already gotten at top of loop
    if game_state == STATE_PLAYING:
        # Reset revive_target and progress if conditions change
        current_revive_initiator = None
        potential_target_player = None

        if player1.is_alive and not player2.is_alive and player2.death_pos:
            if player1.pos.distance_to(player2.death_pos) <= REVIVAL_RADIUS:
                if keys[REVIVE_KEYP1]:
                    current_revive_initiator = player1
                    potential_target_player = player2
                    if revive_target != player2:  # New target or first press
                        revive_target = player2
                        revive_progress = 0
                    revive_progress += dt
                else:  # Key not held for P1
                    if revive_target == player2:  # Was P1 reviving P2?
                        revive_progress = 0
                        # revive_target = None # Keep target to draw incomplete circle maybe
            # else: # P1 too far from P2's body
            #     if revive_target == player2:
            #         revive_progress = 0
            #         # revive_target = None

        elif player2.is_alive and not player1.is_alive and player1.death_pos:
            if player2.pos.distance_to(player1.death_pos) <= REVIVAL_RADIUS:
                if keys[REVIVE_KEYP2]:
                    current_revive_initiator = player2
                    potential_target_player = player1
                    if revive_target != player1:
                        revive_target = player1
                        revive_progress = 0
                    revive_progress += dt
                else:  # Key not held for P2
                    if revive_target == player1:
                        revive_progress = 0
                        # revive_target = None
            # else: # P2 too far from P1's body
            #     if revive_target == player1:
            #         revive_progress = 0
            #         # revive_target = None

        # If no one is actively reviving, or conditions are not met, reset progress
        if not (keys[REVIVE_KEYP1] and revive_target == player2 and player1.pos.distance_to(
                player2.death_pos) <= REVIVAL_RADIUS) and \
                not (keys[REVIVE_KEYP2] and revive_target == player1 and player2.pos.distance_to(
                    player1.death_pos) <= REVIVAL_RADIUS):
            if revive_target is not None and revive_progress < REVIVE_HOLD_TIME:  # Only reset if not completed
                pass  # keep partial progress visible if key released momentarily
            if not ((player1.is_alive and not player2.is_alive and player2.death_pos and player1.pos.distance_to(
                    player2.death_pos) <= REVIVAL_RADIUS and keys[REVIVE_KEYP1]) or \
                    (player2.is_alive and not player1.is_alive and player1.death_pos and player2.pos.distance_to(
                        player1.death_pos) <= REVIVAL_RADIUS and keys[REVIVE_KEYP2])):
                revive_progress = 0  # Full reset if conditions are not met at all
                # revive_target = None # Could also reset target here

        if revive_progress >= REVIVE_HOLD_TIME and revive_target is not None:
            if revive_target == player2:  # P1 revived P2
                player2.revive()
            elif revive_target == player1:  # P2 revived P1
                player1.revive()
            revive_progress = 0
            revive_target = None

    # --- 繪製復活進度圈 ---
    if revive_target is not None and revive_progress > 0:
        percentage = min(revive_progress / REVIVE_HOLD_TIME, 1.0)
        # angle = percentage * 360 # For pygame.draw.arc, angle is in radians

        # Find the center for the circle (death position of the target)
        center_pos_death = None
        if revive_target == player1 and player1.death_pos:
            center_pos_death = player1.death_pos
        elif revive_target == player2 and player2.death_pos:
            center_pos_death = player2.death_pos

        if center_pos_death:
            radius = 20
            # rect for arc needs to be top-left, width, height
            arc_rect = pygame.Rect(int(center_pos_death.x) - radius,
                                   int(center_pos_death.y - PLAYER_RADIUS - radius * 1.5) - radius,
                                   # Position above player's head
                                   radius * 2, radius * 2)

            # Draw background circle (slightly transparent or darker)
            pygame.draw.circle(screen, (80, 80, 80, 150) if pygame.SRCALPHA else (80, 80, 80), arc_rect.center, radius,
                               2)

            # Draw reviving progress arc
            start_angle_rad = -math.pi / 2  # Start at the top (12 o'clock)
            end_angle_rad = start_angle_rad + (percentage * 2 * math.pi)  # Full circle is 2*pi

            if percentage > 0.01:  # Draw only if there's some progress
                pygame.draw.arc(screen, REVIVE_PROMPT_COLOR, arc_rect, start_angle_rad, end_angle_rad, 4)

    pygame.display.flip()

pygame.quit()
if use_opencv:
    cv2.destroyAllWindows()