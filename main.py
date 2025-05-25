import pygame
import cv2
import numpy as np
import math
import random
import time
from animations import *

# --- 常數 ---
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
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
REVIVAL_RADIUS = CHAIN_MAX_LENGTH  # 復活有效半徑，與鎖鏈長度相同
REVIVE_KEYP1 = pygame.K_f  # 設定復活按鍵為 'F'
REVIVE_KEYP2 = pygame.K_PERIOD

# 協力推箱子常數
COOP_BOX_SIZE = 40
COOP_BOX_SPEED = 2
COOP_BOX_PUSH_RADIUS = 50  # 玩家距離箱子多少以內才可推

# 地刺參數
SAFE_COLOR = (220, 220, 220)  # 縮回(安全) 淺灰色
DANGER_COLOR = (220, 40, 40)  # 伸出(危險) 紅色

# 果實相關常數
FRUIT_RADIUS = 15
FRUIT_EFFECT_DURATION = 30.0  # 30秒效果時間

# 果實顏色
MIRROR_FRUIT_COLOR = (255, 215, 0)     # 金色 - 鏡像操控
INVISIBLE_WALL_COLOR = (138, 43, 226)  # 紫色 - 透明牆壁
VOLCANO_FRUIT_COLOR = (255, 69, 0)     # 橙紅色 - 火山爆發

# 火山效果相關常數
METEOR_WARNING_TIME = 1.5  # 警告時間1.5秒
METEOR_SIZE = 20
METEOR_COLOR = (139, 69, 19)  # 棕色
WARNING_COLOR = (255, 255, 0)  # 黃色警告

# 遊戲狀態
STATE_PLAYING = 0
STATE_GAME_OVER = 1
STATE_LEVEL_COMPLETE = 2
STATE_ALL_LEVELS_COMPLETE = 3

# --- Pygame 初始化 ---
pygame.init()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("雙人合作遊戲 Demo - 雷射關卡與復活系統")
clock = pygame.time.Clock()

#圖片載入
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
    else:
        print("警告：找不到中文字體，遊戲中的中文可能無法正確顯示")
        font_small = pygame.font.Font(None, 36)
        font_large = pygame.font.Font(None, 74)
        font_tiny = pygame.font.Font(None, 24)
except Exception as e:
    print(f"載入字體時出錯：{e}")
    font_small = pygame.font.Font(None, 36)
    font_large = pygame.font.Font(None, 74)
    font_tiny = pygame.font.Font(None, 24)

# --- OpenCV 視窗準備 ---
use_opencv = False
opencv_window_name = "P2 Paint Area (OpenCV)"
paint_surface_width = 400
paint_surface_height = 300
paint_surface = np.zeros((paint_surface_height, paint_surface_width, 3), dtype=np.uint8) + 200

def show_opencv_paint_window():
    if use_opencv:
        cv2.imshow(opencv_window_name, paint_surface)
        key = cv2.waitKey(1) & 0xFF

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


        # 載入動畫圖片
        # 根据 player_id 加载不同的动画
        if self.player_id == 0:  # 玩家1
            # 玩家图片放大两倍
            # 我们希望最终图片尺寸是 PLAYER_RADIUS * 6
            self.walk_frames = load_normal_player_walk_animation(target_width=PLAYER_RADIUS * 3,
                                                                 target_height=PLAYER_RADIUS * 3)
            self.is_witch = False  # 确保不是女巫角色
            self.frame_interval = 0.2  # 普通玩家动画速度
        elif self.player_id == 1:
            self.is_witch = True
            self.walk_frames = load_witch_run_animation(target_width=PLAYER_RADIUS * 4, target_height=PLAYER_RADIUS * 4)
            # 加载女巫闲置动画帧
            self.idle_frames = load_witch_idle_animation(target_width=PLAYER_RADIUS * 4, target_height=PLAYER_RADIUS * 4)
            self.frame_interval = 0.15
            self.idle_frame_interval = 0.3  # 女巫动画速度，可能更快

        # 死亡狀態的圖片（黯淡版本）
        self.dead_frames = []
        for frame in self.walk_frames:
            dead_frame = frame.copy()

            # 方法1：使用 set_alpha 讓圖片半透明
            dead_frame.set_alpha(100)  # 100 是透明度，可以調整

            # 方法2：如果想要灰色效果，可以用这个替代上面的 set_alpha
            # dead_frame = self._make_grayscale(dead_frame)
            # dead_frame.set_alpha(150)  # 灰色 + 半透明

            self.dead_frames.append(dead_frame)

        self.current_frame = 0
        self.frame_timer = 0
        self.frame_interval = 0.2  # 每幀的時間間隔

        # 初始化圖片和矩形
        self.image = self.walk_frames[0]
        self.rect = self.image.get_rect(center=self.pos)

        self.is_alive = True
        self.death_pos = None

    def reset(self):
        self.pos = pygame.math.Vector2(self.start_pos.x, self.start_pos.y)
        self.is_alive = True
        self.death_pos = None
        self.image = self.walk_frames[0]
        self.rect = self.image.get_rect(center=self.pos)

    def revive(self):
        self.is_alive = True
        if self.death_pos:
            self.pos = pygame.math.Vector2(self.death_pos.x, self.death_pos.y)
        self.rect.center = self.pos
        self.image = self.walk_frames[0]

    def update_movement(self, laser_walls, coop_boxes=None, spike_trap_group=None, effect_manager=None): # Added effect_manager
        # Update player position
        if not self.is_alive:
            if self.death_pos:
                self.pos = self.death_pos
                self.rect.center = self.death_pos
            self._update_dead_image()
            return

        keys = pygame.key.get_pressed()
        movement_vector = pygame.math.Vector2(0, 0)

        # Check for mirror effect
        mirror_active = effect_manager and effect_manager.is_mirror_active(self.player_id)

        # Determine control keys based on mirror effect
        up_key = self.control_keys['down'] if mirror_active else self.control_keys['up']
        down_key = self.control_keys['up'] if mirror_active else self.control_keys['down']
        left_key = self.control_keys['right'] if mirror_active else self.control_keys['left']
        right_key = self.control_keys['left'] if mirror_active else self.control_keys['right']

        if keys[up_key]: movement_vector.y = -1
        if keys[down_key]: movement_vector.y = 1
        if keys[left_key]: movement_vector.x = -1
        if keys[right_key]: movement_vector.x = 1

        is_moving = movement_vector.length_squared() > 0

        if is_moving:
            movement_vector.normalize_ip()
            movement_vector *= PLAYER_SPEED

        tentative_pos = self.pos + movement_vector
        
        # Store temp_rect_x and temp_rect_y for use in box collision as well
        temp_rect_x = self.rect.copy()
        temp_rect_x.centerx = tentative_pos.x
        
        temp_rect_y = self.rect.copy()
        temp_rect_y.centery = tentative_pos.y

        # Collision check - only if walls are visible
        if not (effect_manager and effect_manager.are_walls_invisible()):
            hit_laser_x = any(temp_rect_x.colliderect(lw.rect) for lw in laser_walls)
            hit_laser_y = any(temp_rect_y.colliderect(lw.rect) for lw in laser_walls)

            if hit_laser_x or hit_laser_y:
                self.is_alive = False
                self.death_pos = self.pos
                # self.pos = self.death_pos # self.pos should remain where death occurred
                self._update_dead_image()
                self.rect = self.image.get_rect(center=self.pos) # Update rect to death_pos
                return

        # Box collision (using the already calculated temp_rect_x and temp_rect_y)
        if coop_boxes:
            for box in coop_boxes:
                # Check collision with the player's intended horizontal move
                test_rect_for_box_x = self.rect.copy()
                test_rect_for_box_x.centerx = tentative_pos.x
                if test_rect_for_box_x.colliderect(box.rect):
                    movement_vector.x = 0
            
            for box in coop_boxes:
                # Check collision with the player's intended vertical move
                test_rect_for_box_y = self.rect.copy()
                test_rect_for_box_y.centery = tentative_pos.y
                if test_rect_for_box_y.colliderect(box.rect):
                    movement_vector.y = 0
        
        # Spike trap collision
        if spike_trap_group:
            for spike in spike_trap_group:
                # Check collision with the player's current rect after potential adjustment from box collision
                current_player_rect_for_spike = pygame.Rect(self.pos.x - self.rect.width / 2 + movement_vector.x, 
                                                             self.pos.y - self.rect.height / 2 + movement_vector.y, 
                                                             self.rect.width, self.rect.height)
                if spike.is_dangerous() and current_player_rect_for_spike.colliderect(spike.rect) and self.is_alive:
                    self.is_alive = False
                    self.death_pos = self.pos # Death at current position before impact
                    self._update_dead_image()
                    self.rect = self.image.get_rect(center=self.pos)
                    return

        # Update position
        self.pos += movement_vector
        self.pos.x = max(self.rect.width / 2, min(self.pos.x, SCREEN_WIDTH - self.rect.width / 2)) # Use rect.width for boundary
        self.pos.y = max(self.rect.height / 2, min(self.pos.y, SCREEN_HEIGHT - self.rect.height / 2)) # Use rect.height for boundary
        self.rect.center = self.pos

        # Update image (alive image)
        self._update_alive_image(is_moving)

    def _update_alive_image(self, is_moving):
        """更新存活狀態的圖片"""
        # 使用存活狀態的圖片
        keys = pygame.key.get_pressed()
        if keys[self.control_keys['left']]:
            self.facing_left = True
        elif keys[self.control_keys['right']]:
            self.facing_left = False

        if is_moving:
            # 播放行走动画
            self.frame_timer += 1 / FPS
            if self.frame_timer >= self.frame_interval:
                self.current_frame = (self.current_frame + 1) % len(self.walk_frames)
                self.frame_timer = 0
            frame = self.walk_frames[self.current_frame]
        else:
            # 播放闲置动画
            # 确保有闲置帧，否则退回到行走的第一帧
            if not self.idle_frames:
                frame = self.walk_frames[0]
                self.current_frame = 0  # 静止时重置帧索引
            else:
                if self.current_frame >= len(self.idle_frames):
                    self.current_frame = 0
                self.frame_timer += 1 / FPS
                # 闲置动画使用自己的帧间隔
                if self.frame_timer >= self.idle_frame_interval:  # 使用 idle_frame_interval
                    self.current_frame = (self.current_frame + 1) % len(self.idle_frames)
                    self.frame_timer = 0
                frame = self.idle_frames[self.current_frame]
        # 根據方向決定是否翻轉圖片
        if self.facing_left:
            frame = pygame.transform.flip(frame, True, False)  # 水平翻转

        self.image = frame

    def _update_dead_image(self):
        """更新死亡狀態的圖片"""
        # 使用死亡狀態的圖片
        frame = self.dead_frames[0]  # 使用第一幀作為死亡狀態的圖片

        # 根據方向決定是否翻轉圖片
        if self.facing_left:
            frame = pygame.transform.flip(frame, True, False)

        self.image = frame

    def draw(self, surface):
        surface.blit(self.image, self.rect)

    def _make_grayscale(self, surface):
        """將圖片轉換為灰度"""
        # 創建一個新的灰度圖片
        grayscale_surface = surface.copy()

        # 獲取像素數組
        arr = pygame.surfarray.pixels3d(grayscale_surface)

        # 計算灰度值
        gray = (arr[:, :, 0] * 0.299 + arr[:, :, 1] * 0.587 + arr[:, :, 2] * 0.114).astype(arr.dtype)

        # 將灰度值應用到所有通道
        arr[:, :, 0] = gray
        arr[:, :, 1] = gray
        arr[:, :, 2] = gray

        del arr  # 釋放像素數組
        return grayscale_surface


# --- 牆壁類別 (雷射牆壁) ---
class LaserWall(pygame.sprite.Sprite):
    def __init__(self, x, y, width, height):
        super().__init__()
        self.image = pygame.Surface([width, height])
        self.image.fill(LASER_WALL_COLOR)
        self.rect = self.image.get_rect(topleft=(x, y))

# --- 目標類別 (顏色地板) ---
class Goal(pygame.sprite.Sprite):
    def __init__(self, x, y, color, player_id_target):
        super().__init__()
        self.image = pygame.Surface([int(PLAYER_RADIUS * 2.5), int(PLAYER_RADIUS * 2.5)])
        self.image.fill(color)
        self.rect = self.image.get_rect(center=(x, y))
        self.player_id_target = player_id_target
        self.is_active = False

    #--- 地板被踩下狀態更新 ---
    def update_status(self, player):
        if player.is_alive and self.rect.colliderect(player.rect) and player.player_id == self.player_id_target:
            self.is_active = True
        else:
            self.is_active = False
    #--- 繪製通關地板 ---
    def draw(self, surface):
        surface.blit(self.image, self.rect)
        if self.is_active:
            pygame.draw.rect(surface, WHITE, self.rect, 3)

# --- 協力推箱子類別 ---
class CoopBox(pygame.sprite.Sprite):
    def __init__(self, x, y, img=None):
        super().__init__()
        # 碰撞體積尺寸（例如 40）
        self.collision_size = COOP_BOX_SIZE  # 例如 40
        # 圖片顯示尺寸（例如 80）
        self.display_size = 60  # 你想要的更大尺寸

        # 碰撞體積
        self.rect = pygame.Rect(0, 0, self.collision_size, self.collision_size)
        self.rect.center = (x, y)
        self.pos = pygame.math.Vector2(x, y)

        # 繪圖用圖片
        if img:
            self.image = pygame.transform.scale(img, (self.display_size, self.display_size))
        else:
            self.image = pygame.Surface([self.display_size, self.display_size])
            self.image.fill(COOP_BOX_COLOR)

    def move(self, direction, obstacles):
        tentative_pos = self.pos + direction * COOP_BOX_SPEED
        test_rect = self.rect.copy()
        test_rect.center = tentative_pos
        for obs in obstacles:
            if test_rect.colliderect(obs.rect):
                return
        if not (self.collision_size//2 <= tentative_pos.x <= SCREEN_WIDTH - self.collision_size//2 and
                self.collision_size//2 <= tentative_pos.y <= SCREEN_HEIGHT - self.collision_size//2):
            return
        self.pos = tentative_pos
        self.rect.center = self.pos

    def draw(self, surface):
        # 圖片中心要對齊碰撞rect中心
        img_rect = self.image.get_rect(center=self.rect.center)
        surface.blit(self.image, img_rect)
#---地刺類別---
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

        # 圖片讀取，地刺有無伸出狀態的圖片
        self.img_out = img_out
        self.img_in = img_in

    #--- 讀取時間更新地刺狀態 ---
    def update(self, dt):
        self.timer += dt
        phase = self.timer % self.cycle_time
        self.active = phase < self.out_time

    #回傳地刺狀態
    def is_dangerous(self):
        return self.active

    #--- 繪製地刺 ---
    def draw(self, surface):
        if self.active and self.img_out:
            img = pygame.transform.scale(self.img_out, (self.rect.width, self.rect.height))
            surface.blit(img, self.rect)
        elif not self.active and self.img_in:
            img = pygame.transform.scale(self.img_in, (self.rect.width, self.rect.height))
            surface.blit(img, self.rect)
        else:
            # 後備畫法
            color = (220, 220, 220) if not self.active else (220, 40, 40)
            pygame.draw.rect(surface, color, self.rect)

# --- 果實類別 ---
class Fruit(pygame.sprite.Sprite):
    def __init__(self, x, y, fruit_type):
        super().__init__()
        self.fruit_type = fruit_type  # "mirror", "invisible_wall", "volcano"
        self.image = pygame.Surface([FRUIT_RADIUS * 2, FRUIT_RADIUS * 2])
        self.image.set_colorkey((0, 0, 0))  # 設置透明色

        # 根據果實類型設置顏色
        if fruit_type == "mirror":
            color = MIRROR_FRUIT_COLOR
        elif fruit_type == "invisible_wall":
            color = INVISIBLE_WALL_COLOR
        elif fruit_type == "volcano":
            color = VOLCANO_FRUIT_COLOR
        else:
            color = (255, 255, 255) # Default color if type is unknown

        # 畫一個圓形果實
        pygame.draw.circle(self.image, color, (FRUIT_RADIUS, FRUIT_RADIUS), FRUIT_RADIUS)
        pygame.draw.circle(self.image, (255, 255, 255), (FRUIT_RADIUS, FRUIT_RADIUS), FRUIT_RADIUS, 2) # Outline

        self.rect = self.image.get_rect(center=(x, y))

# --- 流星類別 (火山爆發效果) ---
class Meteor(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.Surface([METEOR_SIZE, METEOR_SIZE])
        self.image.set_colorkey((0, 0, 0))
        pygame.draw.circle(self.image, METEOR_COLOR, (METEOR_SIZE//2, METEOR_SIZE//2), METEOR_SIZE//2)
        self.rect = self.image.get_rect(center=(x, y))
        self.active = True # Might be useful later for animation or effects

# --- 警告標記類別 ---
class Warning(pygame.sprite.Sprite):
    def __init__(self, x, y, duration): # duration is METEOR_WARNING_TIME
        super().__init__()
        self.image = pygame.Surface([METEOR_SIZE * 2, METEOR_SIZE * 2]) # Warning larger than meteor
        self.image.set_colorkey((0, 0, 0)) # Transparent background
        self.image.set_alpha(200) # Slightly transparent warning
        
        # Draw a circle for the warning sign
        pygame.draw.circle(self.image, WARNING_COLOR, (METEOR_SIZE, METEOR_SIZE), METEOR_SIZE, 3) # Yellow circle, width 3
        
        self.rect = self.image.get_rect(center=(x, y))
        self.duration = duration
        self.timer = 0

    def update(self, dt):
        self.timer += dt
        # Simple fade out or blink effect could be added here if desired
        # For now, it just tracks time. The example had a math.sin for alpha, ensure math is imported if used.
        # The user's code:
        # alpha = int(128 + 127 * math.sin(self.timer * 10))
        # self.image.set_alpha(alpha)
        # Ensure math is imported if this is used. For simplicity, I'll keep the user's version.
        # Make sure `import math` is at the top of main.py.
        alpha = int(128 + 127 * math.sin(self.timer * 10)) # Requires math import
        self.image.set_alpha(alpha)
        return self.timer < self.duration

# --- 效果管理器 ---
class EffectManager:
    def __init__(self):
        self.effects = {
            "mirror_p1": {"active": False, "timer": 0},
            "mirror_p2": {"active": False, "timer": 0},
            "invisible_wall": {"active": False, "timer": 0, "flash_timer": 0, "showing": False},
            "volcano": {"active": False, "timer": 0, "meteor_timer": 0}
        }

    def apply_effect(self, effect_type, player_id=None):
        if effect_type == "mirror":
            if player_id == 0: # Assuming player_id 0 is P1
                self.effects["mirror_p1"]["active"] = True
                self.effects["mirror_p1"]["timer"] = FRUIT_EFFECT_DURATION
            elif player_id == 1: # Assuming player_id 1 is P2
                self.effects["mirror_p2"]["active"] = True
                self.effects["mirror_p2"]["timer"] = FRUIT_EFFECT_DURATION
        elif effect_type == "invisible_wall":
            self.effects["invisible_wall"]["active"] = True
            self.effects["invisible_wall"]["timer"] = FRUIT_EFFECT_DURATION
            self.effects["invisible_wall"]["flash_timer"] = 0 # Time until next flash state change
            self.effects["invisible_wall"]["showing"] = False # Currently not showing
        elif effect_type == "volcano":
            self.effects["volcano"]["active"] = True
            self.effects["volcano"]["timer"] = FRUIT_EFFECT_DURATION
            self.effects["volcano"]["meteor_timer"] = 0 # Time until next meteor spawn check

    def update(self, dt):
        # Update mirror effect
        for key in ["mirror_p1", "mirror_p2"]:
            if self.effects[key]["active"]:
                self.effects[key]["timer"] -= dt
                if self.effects[key]["timer"] <= 0:
                    self.effects[key]["active"] = False

        # Update invisible wall effect
        if self.effects["invisible_wall"]["active"]:
            self.effects["invisible_wall"]["timer"] -= dt
            self.effects["invisible_wall"]["flash_timer"] += dt

            # Wall flashes visible for 1s every 5s (4s invisible, 1s visible cycle)
            if self.effects["invisible_wall"]["flash_timer"] >= 5.0: # End of 5s cycle
                self.effects["invisible_wall"]["showing"] = True # Start showing
                self.effects["invisible_wall"]["flash_timer"] = 0 # Reset cycle timer
            elif self.effects["invisible_wall"]["flash_timer"] >= 1.0 and self.effects["invisible_wall"]["showing"]:
                self.effects["invisible_wall"]["showing"] = False # Stop showing after 1s

            if self.effects["invisible_wall"]["timer"] <= 0: # Effect duration ended
                self.effects["invisible_wall"]["active"] = False
                self.effects["invisible_wall"]["showing"] = False # Ensure it's not stuck showing

        # Update volcano effect
        if self.effects["volcano"]["active"]:
            self.effects["volcano"]["timer"] -= dt
            self.effects["volcano"]["meteor_timer"] += dt # Time accumulating for meteor spawn
            if self.effects["volcano"]["timer"] <= 0:
                self.effects["volcano"]["active"] = False

    def is_mirror_active(self, player_id):
        if player_id == 0:
            return self.effects["mirror_p1"]["active"]
        elif player_id == 1:
            return self.effects["mirror_p2"]["active"]
        return False

    def are_walls_invisible(self):
        # Walls are invisible if effect is active AND they are not in their "showing" phase
        return self.effects["invisible_wall"]["active"] and not self.effects["invisible_wall"]["showing"]

    def should_spawn_meteor(self):
        # Spawn meteor if volcano effect is active and meteor_timer has exceeded a random interval
        # The random interval was given as random.uniform(1.0, 3.0) in user's text.
        # This check should ideally be done in the main game loop, and then reset_meteor_timer called.
        if self.effects["volcano"]["active"]:
            # The actual check for meteor_timer >= random.uniform(1.0, 3.0) will be done in the main loop.
            # This method just indicates if the volcano effect is generally active for spawning.
            return self.effects["volcano"]["active"] 
        return False

    def reset_meteor_timer(self):
        # Reset after a meteor spawn decision has been made
        self.effects["volcano"]["meteor_timer"] = 0
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
        "coop_box_start": [(SCREEN_WIDTH // 4, SCREEN_HEIGHT // 4),(SCREEN_WIDTH // 4+50, SCREEN_HEIGHT // 4+50)],
        "spike_traps": [
                            (40, 40, 40, 40, 1.0, 2.0, 0.0),     # 1秒伸出/2秒縮回，立即開始
                            (100, 40, 40, 40, 0.7, 1.5, 0.5),    # 0.7秒伸出/1.5秒縮回，起始延遲0.5秒
                            (160, 40, 40, 40, 1.2, 1.0, 1.0),    # 1.2秒伸出/1秒縮回，起始延遲1秒
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
        "coop_box_start": (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
    }
]

# 在關卡資料中添加果實位置
def add_fruits_to_levels():
    # 為第一關添加果實
    if len(levels_data) > 0:
        levels_data[0]["fruits"] = [
            (300, 300, "mirror"),
            (500, 200, "invisible_wall"),
            (400, 400, "volcano")
        ]
    else:
        print("Warning: levels_data is empty or too short to add fruits to level 0.")

    # 為第二關添加果實
    if len(levels_data) > 1:
        levels_data[1]["fruits"] = [
            (200, 300, "mirror"),
            (600, 400, "volcano"),
            (400, 150, "invisible_wall")
        ]
    else:
        print("Warning: levels_data does not have a level 1 to add fruits to.")

add_fruits_to_levels()
current_level_index = 0

# --- 遊戲物件群組 ---
all_sprites = pygame.sprite.Group()
laser_wall_sprites = pygame.sprite.Group()
goal_sprites = pygame.sprite.Group()
player_sprites = pygame.sprite.Group()
coop_box_group = pygame.sprite.Group()
spike_trap_group = pygame.sprite.Group()
fruit_sprites = pygame.sprite.Group()
meteor_sprites = pygame.sprite.Group()
warning_sprites = pygame.sprite.Group()

# --- 遊戲物件實體 ---
player1 = Player(0, 0, PLAYER1_COLOR, PLAYER1_DEAD_COLOR,
                 {'up': pygame.K_w, 'down': pygame.K_s, 'left': pygame.K_a, 'right': pygame.K_d}, 0)
player2 = Player(0, 0, PLAYER2_COLOR, PLAYER2_DEAD_COLOR,
                 {'up': pygame.K_UP, 'down': pygame.K_DOWN, 'left': pygame.K_LEFT, 'right': pygame.K_RIGHT}, 1)
player_sprites.add(player1, player2)

goal1 = Goal(0, 0, GOAL_P1_COLOR, 0)
goal2 = Goal(0, 0, GOAL_P2_COLOR, 1)

coop_box = CoopBox(0, 0)
coop_box_group.add(coop_box)

effect_manager = EffectManager()

# 將所有物件加入群組
def load_level(level_idx):
    global game_state
    if level_idx >= len(levels_data):
        game_state = STATE_ALL_LEVELS_COMPLETE
        return
    level = levels_data[level_idx]
    laser_wall_sprites.empty()
    goal_sprites.empty()
    fruit_sprites.empty()
    meteor_sprites.empty()
    warning_sprites.empty()
    player1.start_pos = pygame.math.Vector2(level["player1_start"])
    player2.start_pos = pygame.math.Vector2(level["player2_start"])
    player1.reset()
    player2.reset()
    for lw_data in level["laser_walls"]:
        lw = LaserWall(*lw_data)
        laser_wall_sprites.add(lw)
    goal1.rect.center = level["goal1_pos"]
    goal2.rect.center = level["goal2_pos"]
    goal1.is_active = False
    goal2.is_active = False
    goal_sprites.add(goal1, goal2)
    # 箱子
    coop_box_group.empty()
    coop_box_starts = level["coop_box_start"]
    if isinstance(coop_box_starts[0], (list, tuple)):
        for pos in coop_box_starts:
            box = CoopBox(*pos, img=box_img)
            coop_box_group.add(box)
    else:
        box = CoopBox(*coop_box_starts, img=box_img)
        coop_box_group.add(box)
    game_state = STATE_PLAYING
    # 清空地刺群
    spike_trap_group.empty()
    # 依據關卡資料加入地刺
    for spike_data in level.get("spike_traps", []):
        # spike_data 只要是 (x, y, ...) tuple
        spike_trap_group.add(
            SpikeTrap(*spike_data, img_out=spike_trap_img_out, img_in=spike_trap_img_in)
        )
    # Load fruits for the level
    if "fruits" in level: # Check if fruit data exists for this level
        for fruit_data in level["fruits"]:
            fx, fy, ftype = fruit_data
            new_fruit = Fruit(fx, fy, ftype)
            fruit_sprites.add(new_fruit)
            # If you have a main 'all_sprites' group that's used for drawing everything, add to it too:
            # all_sprites.add(new_fruit) 
            # For now, assuming fruit_sprites will be drawn independently.

#---遊戲初始化---
game_state = STATE_PLAYING
load_level(current_level_index)
running = True

#---復活設置---
REVIVE_HOLD_TIME = 1.5
revive_progress = 0.0
revive_target = None

#---遊戲提示或公告訊息---
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
        p1_status = "存活" if player1.is_alive else "死亡"
        p2_status = "存活" if player2.is_alive else "死亡"
        p1_text = font_tiny.render(f"玩家1: {p1_status}", True, PLAYER1_COLOR)
        p2_text = font_tiny.render(f"玩家2: {p2_status}", True, PLAYER2_COLOR)
        screen.blit(p1_text, (10, 50))
        screen.blit(p2_text, (10, 75))
        if (player1.is_alive and not player2.is_alive) or (player2.is_alive and not player1.is_alive):
            revive_hint = font_tiny.render("靠近死亡位置並按住 F 鍵或 . 以復活隊友", True, REVIVE_PROMPT_COLOR)
            screen.blit(revive_hint, (SCREEN_WIDTH // 2 - revive_hint.get_width() // 2, 10))
        # 提示推箱
        if player1.is_alive and player2.is_alive:
            p1_near = player1.pos.distance_to(coop_box.pos) < COOP_BOX_PUSH_RADIUS
            p2_near = player2.pos.distance_to(coop_box.pos) < COOP_BOX_PUSH_RADIUS
            if p1_near and p2_near:
                push_hint = font_tiny.render("兩人靠近箱子時可推動箱子", True, (225, 210, 80))
                screen.blit(push_hint, (SCREEN_WIDTH//2 - push_hint.get_width()//2, 40))

#---遊戲主程式循環---
while running:
    dt = clock.tick(FPS) / 1000.0
    effect_manager.update(dt) # Update effect manager each frame
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN:
            if game_state == STATE_GAME_OVER and event.key == pygame.K_r:
                load_level(current_level_index)
            if game_state == STATE_ALL_LEVELS_COMPLETE and event.key == pygame.K_r:
                current_level_index = 0
                load_level(current_level_index)
    #---遊戲狀態_遊玩中---
    if game_state == STATE_PLAYING:
        # 更新玩家位置
        player1.update_movement(laser_wall_sprites, coop_box_group, spike_trap_group, effect_manager)
        player2.update_movement(laser_wall_sprites, coop_box_group, spike_trap_group, effect_manager)
        
        # --- Fruit Collection ---
        for fruit in list(fruit_sprites): # Iterate over a copy if modifying the group
            # Check collision with Player 1
            if player1.is_alive and pygame.sprite.collide_rect(player1, fruit): # Or use collide_mask if more precise
                effect_manager.apply_effect(fruit.fruit_type, player1.player_id)
                fruit.kill() # Remove fruit from all groups
                # Potentially add a sound effect or visual feedback here

            # Check collision with Player 2 (only if not already collected by P1)
            elif player2.is_alive and pygame.sprite.collide_rect(player2, fruit): # Or use collide_mask
                effect_manager.apply_effect(fruit.fruit_type, player2.player_id)
                fruit.kill() # Remove fruit
                # Potentially add a sound effect or visual feedback here

        # --- 推箱判斷 ---
        if player1.is_alive and player2.is_alive:
            for coop_box in coop_box_group:
                p1_near = player1.pos.distance_to(coop_box.pos) < COOP_BOX_PUSH_RADIUS
                p2_near = player2.pos.distance_to(coop_box.pos) < COOP_BOX_PUSH_RADIUS
                if p1_near and p2_near:
                    dir_p1 = pygame.math.Vector2(
                        keys[player1.control_keys['right']] - keys[player1.control_keys['left']],
                        keys[player1.control_keys['down']] - keys[player1.control_keys['up']]
                    )
                    dir_p2 = pygame.math.Vector2(
                        keys[player2.control_keys['right']] - keys[player2.control_keys['left']],
                        keys[player2.control_keys['down']] - keys[player2.control_keys['up']]
                    )
                    total_dir = dir_p1 + dir_p2
                    if total_dir.length_squared() > 0:
                        total_dir.normalize_ip()
                        coop_box.move(total_dir, laser_wall_sprites)

        # --- 鎖鏈物理 ---
        for _ in range(CHAIN_ITERATIONS):
            if player1.is_alive and player2.is_alive:
                p1_pos_vec = player1.pos
                p2_pos_vec = player2.pos
                delta = p2_pos_vec - p1_pos_vec
                distance = delta.length()
                if distance > CHAIN_MAX_LENGTH and distance != 0:
                    diff = (distance - CHAIN_MAX_LENGTH) / distance
                    player1.pos += delta * 0.5 * diff
                    player2.pos -= delta * 0.5 * diff
                    player1.rect.center = player1.pos
                    player2.rect.center = player2.pos
            elif player1.is_alive and not player2.is_alive and player2.death_pos:
                delta = player2.death_pos - player1.pos
                distance = delta.length()
                if distance > CHAIN_MAX_LENGTH and distance != 0:
                    diff_factor = (distance - CHAIN_MAX_LENGTH) / distance
                    player1.pos += delta * diff_factor
                    player1.rect.center = player1.pos
            elif player2.is_alive and not player1.is_alive and player1.death_pos:
                delta = player1.death_pos - player2.pos
                distance = delta.length()
                if distance > CHAIN_MAX_LENGTH and distance != 0:
                    diff_factor = (distance - CHAIN_MAX_LENGTH) / distance
                    player2.pos += delta * diff_factor
                    player2.rect.center = player2.pos
        #----是否過關---
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

        # --- Volcano Effect: Meteor Spawning and Warnings ---
        # Check if volcano effect is active and it's time to spawn a new meteor warning
        if effect_manager.effects["volcano"]["active"] and \
           effect_manager.effects["volcano"]["meteor_timer"] >= random.uniform(1.5, 3.5): # Random spawn interval (e.g. 1.5-3.5s)
            
            # Determine meteor landing position (random X, bottom of screen)
            meteor_target_x = random.randint(METEOR_SIZE // 2, SCREEN_WIDTH - METEOR_SIZE // 2)
            meteor_target_y = SCREEN_HEIGHT - METEOR_SIZE // 2 # Land at the very bottom

            # Create a warning at the target location
            # The Warning class's duration argument is METEOR_WARNING_TIME
            new_warning = Warning(meteor_target_x, meteor_target_y, METEOR_WARNING_TIME)
            warning_sprites.add(new_warning)
            # all_sprites.add(new_warning) # If all_sprites is used for drawing everything

            effect_manager.reset_meteor_timer() # Reset timer for next spawn

        # Update warnings
        for warning in list(warning_sprites): # Iterate over a copy
            if not warning.update(dt): # update returns False if duration is over
                # Warning time is over, spawn meteor
                # Meteor appears at the same spot the warning was
                meteor_x, meteor_y = warning.rect.centerx, warning.rect.centery 
                new_meteor = Meteor(meteor_x, meteor_y)
                meteor_sprites.add(new_meteor)
                # all_sprites.add(new_meteor) # If all_sprites is used for drawing

                warning.kill() # Remove the warning

        # Update meteors and check for player collisions
        for meteor in list(meteor_sprites): # Iterate over a copy
            # Meteors are currently static once they appear.
            player1_hit_by_meteor = False
            player2_hit_by_meteor = False

            # Check collision with Player 1
            if player1.is_alive and pygame.sprite.collide_rect(player1, meteor):
                player1.is_alive = False
                player1.death_pos = pygame.math.Vector2(player1.pos.x, player1.pos.y) # Store current pos as death_pos
                player1.pos = player1.death_pos # Ensure player pos is fixed at death_pos
                player1._update_dead_image()
                player1.rect.center = player1.pos # Update rect to death_pos
                player1_hit_by_meteor = True

            # Check collision with Player 2
            if player2.is_alive and pygame.sprite.collide_rect(player2, meteor):
                player2.is_alive = False
                player2.death_pos = pygame.math.Vector2(player2.pos.x, player2.pos.y)
                player2.pos = player2.death_pos
                player2._update_dead_image()
                player2.rect.center = player2.pos
                player2_hit_by_meteor = True
            
            if player1_hit_by_meteor or player2_hit_by_meteor:
                 if meteor.active: # meteor.active is True by default in its constructor
                    meteor.kill() # Remove meteor after impact

    #---遊戲畫面繪製---
    show_opencv_paint_window()
    screen.fill(BLACK)

    # Conditionally draw laser walls
    if not effect_manager.are_walls_invisible():
        laser_wall_sprites.draw(screen)
        
    goal_sprites.draw(screen)
    for coop_box in coop_box_group:
        coop_box.draw(screen)

    # 算有幾個角色在推範圍內，並在箱子顯示數字
    # This logic seems fine, it's UI related to coop_box, not drawing the box itself again.
    for coop_box in coop_box_group:
        p1_on_box = player1.pos.distance_to(coop_box.pos) < COOP_BOX_PUSH_RADIUS
        p2_on_box = player2.pos.distance_to(coop_box.pos) < COOP_BOX_PUSH_RADIUS
        num_on_box = int(p1_on_box) + int(p2_on_box)
        if num_on_box < 2: # Only draw if less than 2 players are on the box
            box_text = font_small.render(str(2 - num_on_box), True, (255, 255, 255))
            box_cx, box_cy = int(coop_box.rect.centerx), int(coop_box.rect.centery)
            screen.blit(box_text, (box_cx - box_text.get_width() // 2, box_cy - box_text.get_height() // 2))
            
    # 更新地刺狀態和繪製地刺 (SpikeTrap.update is called in game logic section, draw is here)
    for spike in spike_trap_group:
        # spike.update(dt) # This call is in the game logic section now.
        spike.draw(screen)

    # --- Add drawing for new elements ---
    fruit_sprites.draw(screen)
    warning_sprites.draw(screen) 
    meteor_sprites.draw(screen)
    # --- End of new element drawing ---

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
    # 繪製玩家
    player_sprites.draw(screen)
    # 繪製遊戲提示或公告
    draw_game_state_messages()
    # 判斷復活條件
    keys = pygame.key.get_pressed()
    if game_state == STATE_PLAYING:
        if player1.is_alive and not player2.is_alive and player2.death_pos:
            if player1.pos.distance_to(player2.death_pos) <= REVIVAL_RADIUS:
                if keys[REVIVE_KEYP1]:
                    revive_target = 1
                    revive_progress += dt
                else:
                    revive_progress = 0
                    revive_target = None
            else:
                revive_progress = 0
                revive_target = None
        elif player2.is_alive and not player1.is_alive and player1.death_pos:
            if player2.pos.distance_to(player1.death_pos) <= REVIVAL_RADIUS:
                if keys[REVIVE_KEYP2]:
                    revive_target = 0
                    revive_progress += dt
                else:
                    revive_progress = 0
                    revive_target = None
            else:
                revive_progress = 0
                revive_target = None
        else:
            revive_progress = 0
            revive_target = None
        if revive_progress >= REVIVE_HOLD_TIME and revive_target is not None:
            if revive_target == 1:
                player2.revive()
            elif revive_target == 0:
                player1.revive()
            revive_progress = 0
            revive_target = None
    # 繪製復活進度條
    # --- 繪製復活進度圈 ---
    if revive_target is not None:
        percentage = min(revive_progress / REVIVE_HOLD_TIME, 1.0)
        angle = percentage * 360

        # 找到死亡角色的位置
        if revive_target == 0 and player1.death_pos:
            center = player1.death_pos
        elif revive_target == 1 and player2.death_pos:
            center = player2.death_pos
        else:
            center = None

        if center:
            radius = 20
            rect = pygame.Rect(0, 0, radius * 2, radius * 2)
            rect.center = (int(center.x), int(center.y - 40))  # 圓圈畫在角色上方一點

            # 畫背景圓圈
            pygame.draw.circle(screen, (80, 80, 80), rect.center, radius, 2)

            # 畫復活進度（弧線）
            start_angle = -math.pi / 2  # 從上方開始畫
            end_angle = start_angle + percentage * 2 * math.pi
            pygame.draw.arc(screen, REVIVE_PROMPT_COLOR, rect, start_angle, end_angle, 4)

    #畫面展示
    pygame.display.flip()

pygame.quit()
if use_opencv:
    cv2.destroyAllWindows()