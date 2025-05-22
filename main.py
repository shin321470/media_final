import pygame
import cv2
import numpy as np
import math

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

PLAYER_RADIUS = 15
PLAYER_SPEED = 3
CHAIN_MAX_LENGTH = 400
CHAIN_ITERATIONS = 5
REVIVAL_RADIUS = CHAIN_MAX_LENGTH  # 復活有效半徑，與鎖鏈長度相同
REVIVE_KEYP1 = pygame.K_f  # 設定復活按鍵為 'F'
REVIVE_KEYP2 = pygame.K_PERIOD

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

# 加載支持中文的字體
# 嘗試找到系統中可用的中文字體
try:
    # 嘗試使用常見中文字體
    system_fonts = pygame.font.get_fonts()
    chinese_font_name = None

    # 檢查系統中是否有常見的中文字體
    possible_chinese_fonts = [
        'microsoftyahei', 'msyh', 'simsun', 'simhei', 'noto sans cjk tc',
        'noto sans cjk sc', 'microsoft jhenghei', 'pmingliu', 'kaiti', 'heiti tc',
        'heiti sc', 'droid sans fallback'
    ]

    for font in possible_chinese_fonts:
        if font in system_fonts or font.replace(' ', '') in system_fonts:
            chinese_font_name = font
            break

    # 如果找到了中文字體，使用它
    if chinese_font_name:
        font_path = pygame.font.match_font(chinese_font_name)
        font_small = pygame.font.Font(font_path, 36)
        font_large = pygame.font.Font(font_path, 74)
        font_tiny = pygame.font.Font(font_path, 24)
    else:
        # 如果找不到中文字體，使用系統字體並顯示警告
        print("警告：找不到中文字體，遊戲中的中文可能無法正確顯示")
        font_small = pygame.font.Font(None, 36)
        font_large = pygame.font.Font(None, 74)
        font_tiny = pygame.font.Font(None, 24)
except Exception as e:
    print(f"載入字體時出錯：{e}")
    # 使用預設字體作為備用
    font_small = pygame.font.Font(None, 36)
    font_large = pygame.font.Font(None, 74)
    font_tiny = pygame.font.Font(None, 24)

# --- OpenCV 視窗準備 ---
# 由於我們可能不需要OpenCV功能，我將其設為可選
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

        self.image = pygame.Surface([PLAYER_RADIUS * 2, PLAYER_RADIUS * 2], pygame.SRCALPHA)
        self.rect = self.image.get_rect(center=self.pos)

        self.is_alive = True
        self.death_pos = None
        self._update_appearance()

    def _update_appearance(self):
        self.image.fill((0, 0, 0, 0))
        color_to_draw = self.alive_color if self.is_alive else self.dead_color
        pygame.draw.circle(self.image, color_to_draw, (PLAYER_RADIUS, PLAYER_RADIUS), PLAYER_RADIUS)

    def reset(self):
        self.pos = pygame.math.Vector2(self.start_pos.x, self.start_pos.y)
        self.is_alive = True
        self.death_pos = None
        self._update_appearance()
        self.rect.center = self.pos

    def revive(self):
        self.is_alive = True
        if self.death_pos:  # 確保 death_pos 不是 None
            self.pos = pygame.math.Vector2(self.death_pos.x, self.death_pos.y)  # 在死亡地點復活
        self.rect.center = self.pos
        self._update_appearance()

    def update_movement(self, laser_walls):
        if not self.is_alive:
            if self.death_pos:  # 確保死亡後位置固定
                self.pos = self.death_pos
                self.rect.center = self.death_pos
            return

        keys = pygame.key.get_pressed()
        movement_vector = pygame.math.Vector2(0, 0)

        if keys[self.control_keys['up']]: movement_vector.y = -1
        if keys[self.control_keys['down']]: movement_vector.y = 1
        if keys[self.control_keys['left']]: movement_vector.x = -1
        if keys[self.control_keys['right']]: movement_vector.x = 1

        if movement_vector.length_squared() > 0:
            movement_vector.normalize_ip()
            movement_vector *= PLAYER_SPEED

        tentative_pos = self.pos + movement_vector

        # 碰撞檢測 (雷射牆)
        # X方向檢查
        temp_rect_x = self.rect.copy()
        temp_rect_x.centerx = tentative_pos.x
        hit_laser_x = False
        for lw in laser_walls:
            if temp_rect_x.colliderect(lw.rect):
                hit_laser_x = True
                break

        # Y方向檢查
        temp_rect_y = self.rect.copy()
        temp_rect_y.centery = tentative_pos.y
        hit_laser_y = False
        for lw in laser_walls:
            if temp_rect_y.colliderect(lw.rect):
                hit_laser_y = True
                break

        if hit_laser_x or hit_laser_y:  # 任何方向碰到雷射牆
            self.is_alive = False
            self.death_pos = self.pos  # 記錄精確的死亡前位置
            self.pos = self.death_pos  # 設定目前位置為死亡位置
            self._update_appearance()
            self.rect.center = self.pos
            return  # 死亡則不進行後續移動

        # 更新實際位置 (如果沒有碰到雷射)
        self.pos = tentative_pos

        # 畫面邊界限制
        self.pos.x = max(PLAYER_RADIUS, min(self.pos.x, SCREEN_WIDTH - PLAYER_RADIUS))
        self.pos.y = max(PLAYER_RADIUS, min(self.pos.y, SCREEN_HEIGHT - PLAYER_RADIUS))

        self.rect.center = self.pos

    def draw(self, surface):
        surface.blit(self.image, self.rect)


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
        self.image = pygame.Surface([PLAYER_RADIUS * 2.5, PLAYER_RADIUS * 2.5])
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


# --- 關卡資料 ---
levels_data = [
    {  # Level 1
        "player1_start": (100, SCREEN_HEIGHT // 2),
        "player2_start": (150, SCREEN_HEIGHT // 2),
        "goal1_pos": (SCREEN_WIDTH - 50, 100),
        "goal2_pos": (SCREEN_WIDTH - 50, SCREEN_HEIGHT - 100),
        "laser_walls": [
            (SCREEN_WIDTH // 2 - 10, 150, 20, SCREEN_HEIGHT - 300),
            (200, SCREEN_HEIGHT // 2 - 10, SCREEN_WIDTH // 2 - 200 - 10, 10),
            (SCREEN_WIDTH // 2 + 10, SCREEN_HEIGHT // 2 - 10, SCREEN_WIDTH // 2 - 20 - 10, 10),
        ]
    },
    {  # Level 2
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
        ]
    }
]
current_level_index = 0

# --- 遊戲物件群組 ---
all_sprites = pygame.sprite.Group()  # Not used for drawing all, but for general management if needed
laser_wall_sprites = pygame.sprite.Group()
goal_sprites = pygame.sprite.Group()
player_sprites = pygame.sprite.Group()

# --- 遊戲物件實體 ---
player1 = Player(0, 0, PLAYER1_COLOR, PLAYER1_DEAD_COLOR,
                 {'up': pygame.K_w, 'down': pygame.K_s, 'left': pygame.K_a, 'right': pygame.K_d}, 0)
player2 = Player(0, 0, PLAYER2_COLOR, PLAYER2_DEAD_COLOR,
                 {'up': pygame.K_UP, 'down': pygame.K_DOWN, 'left': pygame.K_LEFT, 'right': pygame.K_RIGHT}, 1)

player_sprites.add(player1, player2)

goal1 = Goal(0, 0, GOAL_P1_COLOR, 0)
goal2 = Goal(0, 0, GOAL_P2_COLOR, 1)


# --- 函式：載入關卡 ---
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

    game_state = STATE_PLAYING

# --- 主遊戲迴圈 ---
game_state = STATE_PLAYING
load_level(current_level_index)
running = True
# --- 新增復活進度相關常數與變數 ---
REVIVE_HOLD_TIME = 1.5  # 按住F鍵1.5秒復活
revive_progress = 0.0
revive_target = None  # 0: P1, 1: P2, None: 無


# 繫結遊戲狀態訊息
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

    # 遊戲中的資訊顯示
    if game_state == STATE_PLAYING:
        level_text = font_small.render(f"關卡 {current_level_index + 1}", True, TEXT_COLOR)
        screen.blit(level_text, (10, 10))

        # 顯示玩家狀態
        p1_status = "存活" if player1.is_alive else "死亡"
        p2_status = "存活" if player2.is_alive else "死亡"
        p1_text = font_tiny.render(f"玩家1: {p1_status}", True, PLAYER1_COLOR)
        p2_text = font_tiny.render(f"玩家2: {p2_status}", True, PLAYER2_COLOR)
        screen.blit(p1_text, (10, 50))
        screen.blit(p2_text, (10, 75))

        # 提示如何復活
        if (player1.is_alive and not player2.is_alive) or (player2.is_alive and not player1.is_alive):
            revive_hint = font_tiny.render("靠近死亡位置並按住 F 鍵或 . 以復活隊友", True, REVIVE_PROMPT_COLOR)
            screen.blit(revive_hint, (SCREEN_WIDTH // 2 - revive_hint.get_width() // 2, 10))


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

            # 復活鍵處理(立即復活，暫時不用，取消才會有按住復活5/22)
            '''
            if event.key == REVIVE_KEY and game_state == STATE_PLAYING:
                if player1.is_alive and not player2.is_alive:
                    if player1.pos.distance_to(player2.death_pos) <= REVIVAL_RADIUS:
                        player2.revive()
                elif player2.is_alive and not player1.is_alive:
                    if player2.pos.distance_to(player1.death_pos) <= REVIVAL_RADIUS:
                        player1.revive()
            '''

    # --- 更新 ---
    if game_state == STATE_PLAYING:
        player1.update_movement(laser_wall_sprites)
        player2.update_movement(laser_wall_sprites)

        # 鎖鏈物理約束
        for _ in range(CHAIN_ITERATIONS):
            # 情況1: 兩者皆存活
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
            # 情況2: P1存活, P2死亡 (P2為錨點)
            elif player1.is_alive and not player2.is_alive and player2.death_pos:
                delta = player2.death_pos - player1.pos
                distance = delta.length()
                if distance > CHAIN_MAX_LENGTH and distance != 0:
                    diff_factor = (distance - CHAIN_MAX_LENGTH) / distance
                    player1.pos += delta * diff_factor
                    player1.rect.center = player1.pos
            # 情況3: P2存活, P1死亡 (P1為錨點)
            elif player2.is_alive and not player1.is_alive and player1.death_pos:
                delta = player1.death_pos - player2.pos  # 注意方向
                distance = delta.length()
                if distance > CHAIN_MAX_LENGTH and distance != 0:
                    diff_factor = (distance - CHAIN_MAX_LENGTH) / distance
                    player2.pos += delta * diff_factor  # player2 被拉向 player1.death_pos
                    player2.rect.center = player2.pos

        #----是否過關---
        goal1.update_status(player1)
        goal2.update_status(player2)

        if goal1.is_active and goal2.is_active and player1.is_alive and player2.is_alive:  # 過關條件
            current_level_index += 1
            if current_level_index < len(levels_data):
                load_level(current_level_index)
            else:
                game_state = STATE_ALL_LEVELS_COMPLETE

        if not player1.is_alive and not player2.is_alive:
            game_state = STATE_GAME_OVER

    # --- OpenCV 視窗顯示 ---
    show_opencv_paint_window()

    # --- 繪製 ---
    screen.fill(BLACK)

    laser_wall_sprites.draw(screen)
    goal_sprites.draw(screen)

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
        chain_end_pos = player2.death_pos  # 連接到死亡位置
        can_draw_chain = True
    elif player2.is_alive and not player1.is_alive and player1.death_pos:
        chain_start_pos = player2.rect.center
        chain_end_pos = player1.death_pos  # 連接到死亡位置
        can_draw_chain = True

    if can_draw_chain:
        pygame.draw.line(screen, CHAIN_COLOR, chain_start_pos, chain_end_pos, 3)

    player_sprites.draw(screen)  # 用 Group 繪製玩家

    # 繪製遊戲狀態訊息
    draw_game_state_messages()

    # 在主遊戲迴圈 while running: 內，更新事件處理
    keys = pygame.key.get_pressed()
    if game_state == STATE_PLAYING:
        # 判斷是否有一人生一人死且在範圍內
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

        # 判斷是否完成復活
        if revive_progress >= REVIVE_HOLD_TIME and revive_target is not None:
            if revive_target == 1:
                player2.revive()
            elif revive_target == 0:
                player1.revive()
            revive_progress = 0
            revive_target = None

    # 顯示復活進度
    if revive_target is not None:
        print("!!復活進度:", revive_progress)
        revive_percentage = int((revive_progress / REVIVE_HOLD_TIME) * 100)
        revive_text = font_tiny.render(f"復活進度: {revive_percentage}%", True, REVIVE_PROMPT_COLOR)
        screen.blit(revive_text, (10, SCREEN_HEIGHT - 30))

    # 更新畫面
    pygame.display.flip()

# 遊戲結束清理
pygame.quit()
if use_opencv:
    cv2.destroyAllWindows()