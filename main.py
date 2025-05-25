import pygame
import cv2
import numpy as np
import math
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

    def update_movement(self, laser_walls, coop_boxes=None,spike_trap_group=None):
        # 更新玩家位置
        if not self.is_alive:
            if self.death_pos:
                self.pos = self.death_pos
                self.rect.center = self.death_pos

            # 如果玩家死亡，則使用死亡狀態的圖片
            self._update_dead_image()
            return

        keys = pygame.key.get_pressed()
        movement_vector = pygame.math.Vector2(0, 0)
        if keys[self.control_keys['up']]: movement_vector.y = -1
        if keys[self.control_keys['down']]: movement_vector.y = 1
        if keys[self.control_keys['left']]: movement_vector.x = -1
        if keys[self.control_keys['right']]: movement_vector.x = 1

        is_moving = movement_vector.length_squared() > 0

        if is_moving:
            movement_vector.normalize_ip()
            movement_vector *= PLAYER_SPEED

        tentative_pos = self.pos + movement_vector

        # 碰撞檢查
        temp_rect_x = self.rect.copy()
        temp_rect_x.centerx = tentative_pos.x
        hit_laser_x = any(temp_rect_x.colliderect(lw.rect) for lw in laser_walls)

        temp_rect_y = self.rect.copy()
        temp_rect_y.centery = tentative_pos.y
        hit_laser_y = any(temp_rect_y.colliderect(lw.rect) for lw in laser_walls)

        if hit_laser_x or hit_laser_y:
            self.is_alive = False
            self.death_pos = self.pos
            self.pos = self.death_pos
            # 立即更新死亡狀態的圖片
            self._update_dead_image()
            self.rect = self.image.get_rect(center=self.pos)
            return

        # 箱子碰撞
        if coop_boxes:
            for box in coop_boxes:
                if temp_rect_x.colliderect(box.rect):
                    movement_vector.x = 0
            for box in coop_boxes:
                if temp_rect_y.colliderect(box.rect):
                    movement_vector.y = 0
        #地刺碰撞
        if spike_trap_group:
            for spike in spike_trap_group:
                if spike.is_dangerous() and self.rect.colliderect(spike.rect) and self.is_alive:
                    self.is_alive = False
                    self.death_pos = self.pos
                    self._update_dead_image()
                    self.rect = self.image.get_rect(center=self.pos)
                    return  # 死掉就直接跳出

        # 更新位置
        self.pos += movement_vector
        self.pos.x = max(PLAYER_RADIUS, min(self.pos.x, SCREEN_WIDTH - PLAYER_RADIUS))
        self.pos.y = max(PLAYER_RADIUS, min(self.pos.y, SCREEN_HEIGHT - PLAYER_RADIUS))
        self.rect.center = self.pos

        # 更新復活後圖片
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
current_level_index = 0

# --- 遊戲物件群組 ---
all_sprites = pygame.sprite.Group()
laser_wall_sprites = pygame.sprite.Group()
goal_sprites = pygame.sprite.Group()
player_sprites = pygame.sprite.Group()
coop_box_group = pygame.sprite.Group()
spike_trap_group = pygame.sprite.Group()

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

# 將所有物件加入群組
def load_level(level_idx):
    global game_state
    if level_idx >= len(levels_data):
        game_state = STATE_ALL_LEVELS_COMPLETE
        return
    level = levels_data[level_idx]
    laser_wall_sprites.empty()
    goal_sprites.empty()
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
        player1.update_movement(laser_wall_sprites, coop_box_group, spike_trap_group)
        player2.update_movement(laser_wall_sprites, coop_box_group, spike_trap_group)
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

    #---遊戲畫面繪製---
    show_opencv_paint_window()
    screen.fill(BLACK)
    laser_wall_sprites.draw(screen)
    goal_sprites.draw(screen)
    for coop_box in coop_box_group:
        coop_box.draw(screen)

    # 算有幾個角色在推範圍內，並在箱子顯示數字
    for coop_box in coop_box_group:
        p1_on_box = player1.pos.distance_to(coop_box.pos) < COOP_BOX_PUSH_RADIUS
        p2_on_box = player2.pos.distance_to(coop_box.pos) < COOP_BOX_PUSH_RADIUS
        num_on_box = int(p1_on_box) + int(p2_on_box)
        if num_on_box < 2:
            box_text = font_small.render(str(2 - num_on_box), True, (255, 255, 255))
            box_cx, box_cy = int(coop_box.rect.centerx), int(coop_box.rect.centery)
            screen.blit(box_text, (box_cx - box_text.get_width() // 2, box_cy - box_text.get_height() // 2))

    # 更新地刺狀態和繪製地刺
    for spike in spike_trap_group:
        spike.update(dt)
        spike.draw(screen)

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