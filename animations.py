import pygame
import os

# 定义一个函数来加载并切割女巫的奔跑精灵图集
def load_witch_run_animation(target_width, target_height):
    """
    加载女巫奔跑动画的精灵图集，并将其切割为单独的帧。
    Args:
        target_width (int): 最终缩放后的图片宽度。
        target_height (int): 最终缩放后的图片高度。
    Returns:
        list: 包含所有缩放后动画帧的列表。
    """
    witch_sprite_sheet_path = "./plays_animation_art/B_witch_run.png"
    if not os.path.exists(witch_sprite_sheet_path):
        # 尝试从当前目录加载，以防路径问题
        witch_sprite_sheet_path = "B_witch_run.png"
        if not os.path.exists(witch_sprite_sheet_path):
            raise FileNotFoundError(f"女巫奔跑动画图片未找到: {witch_sprite_sheet_path} 或 ./plays_animation_art/B_witch_run.png")


    witch_sprite_sheet = pygame.image.load(witch_sprite_sheet_path).convert_alpha()

    # 假设女巫精灵图每帧宽度和高度 (B_witch_run.png 通常是 8 帧，垂直排列，每帧宽度是图片宽度，高度是图片高度/8)
    witch_frame_width = witch_sprite_sheet.get_width()
    witch_frame_height = witch_sprite_sheet.get_height() // 8 # 假设有8帧

    if witch_sprite_sheet.get_height() % 8 != 0:
        print(f"警告：B_witch_run.png 的高度 {witch_sprite_sheet.get_height()} 不是帧数 8 的整数倍，可能导致切割不准确！")

    frames = []
    for i in range(8): # B_witch_run.png 有 8 帧，垂直排列
        frame = witch_sprite_sheet.subsurface((0, i * witch_frame_height, witch_frame_width, witch_frame_height))
        # 根据传入的 target_width 和 target_height 进行缩放
        frames.append(pygame.transform.smoothscale(frame, (target_width, target_height)))
    return frames

def load_witch_idle_animation(target_width, target_height):
    """
    加载女巫闲置动画的精灵图集，并将其切割为单独的帧。
    Args:
        target_width (int): 最终缩放后的图片宽度。
        target_height (int): 最终缩放后的图片高度。
    Returns:
        list: 包含所有缩放后动画帧的列表。
    """
    idle_sprite_sheet_path = "./plays_animation_art/B_witch_idle.png"

    if not os.path.exists(idle_sprite_sheet_path):
        # 尝试从当前目录加载，以防路径问题
        idle_sprite_sheet_path = "B_witch_idle.png"
        if not os.path.exists(idle_sprite_sheet_path):
            raise FileNotFoundError(f"女巫闲置动画图片未找到: {idle_sprite_sheet_path} 或 ./plays_animation_art/B_witch_idle.png")

    idle_sprite_sheet = pygame.image.load(idle_sprite_sheet_path).convert_alpha()

    # 根据您提供的 B_witch_idle.png 图片，它有 6 帧，而不是 8 帧。
    # 每帧等高，并且图中的角色是完整的。
    num_idle_frames = 6 # 修正：根据 B_witch_idle.png 实际帧数
    idle_frame_width = idle_sprite_sheet.get_width()
    # 每帧的高度是整个图集的高度除以帧数
    idle_frame_height = idle_sprite_sheet.get_height() // num_idle_frames

    if idle_sprite_sheet.get_height() % num_idle_frames != 0:
        print(f"警告：B_witch_idle.png 的高度 {idle_sprite_sheet.get_height()} 不是帧数 {num_idle_frames} 的整数倍，可能导致切割不准确！")
        # 考虑到可能存在轻微的误差，我们可以尝试向下取整，但这通常表示图片切割有问题
        # 或者帧数设置不正确。如果这里有警告，请仔细检查图片。

    frames = []
    for i in range(num_idle_frames):
        # subsurface 的参数是 (left, top, width, height)
        # left: 总是 0，因为帧是垂直排列的
        # top: i * idle_frame_height，这是当前帧的起始y坐标
        # width: idle_frame_width，当前帧的宽度
        # height: idle_frame_height，当前帧的高度
        frame = idle_sprite_sheet.subsurface((0, i * idle_frame_height, idle_frame_width, idle_frame_height))
        # 使用 smoothscale 进行高质量缩放
        scaled_frame = pygame.transform.smoothscale(frame, (target_width, target_height))
        frames.append(scaled_frame)
    return frames

# 加载骑士的奔跑动画 (保持不变)
def load_knight_run_animation(target_width, target_height):
    """
    加载骑士奔跑动画的精灵图集，并将其切割为单独的帧。
    Args:
        target_width (int): 最终缩放后的图片宽度。
        target_height (int): 最终缩放后的图片高度。
    Returns:
        list: 包含所有缩放后动画帧的列表。
    """
    knight_sprite_sheet_path = "./plays_animation_art/Knight_WALK.png" # 假设您将图片保存为这个名字

    if not os.path.exists(knight_sprite_sheet_path):
        raise FileNotFoundError(f"骑士奔跑动画图片未找到: {knight_sprite_sheet_path}")

    knight_sprite_sheet = pygame.image.load(knight_sprite_sheet_path).convert_alpha()

    # 根据提供的 Knight_WALK.png 图片，它有 8 帧，水平排列。
    # 每帧的宽度是整个图片宽度除以帧数，高度是整个图片高度。
    num_knight_frames = 8
    knight_frame_width = knight_sprite_sheet.get_width() // num_knight_frames
    knight_frame_height = knight_sprite_sheet.get_height()

    if knight_sprite_sheet.get_width() % num_knight_frames != 0:
        print(f"警告：Knight_WALK.png 的宽度 {knight_sprite_sheet.get_width()} 不是帧数 {num_knight_frames} 的整数倍，可能导致切割不准确！")

    frames = []
    for i in range(num_knight_frames):
        # subsurface 的参数是 (left, top, width, height)
        # left: i * knight_frame_width，这是当前帧的起始x坐标
        # top: 总是 0，因为帧是水平排列的
        # width: knight_frame_width，当前帧的宽度
        # height: knight_frame_height，当前帧的高度
        frame = knight_sprite_sheet.subsurface((i * knight_frame_width, 0, knight_frame_width, knight_frame_height))
        # 使用 smoothscale 进行高质量缩放
        scaled_frame = pygame.transform.smoothscale(frame, (target_width, target_height))
        frames.append(scaled_frame)
    return frames

# 新增的函数：加载骑士的闲置动画
def load_knight_idle_animation(target_width, target_height):
    """
    加载骑士闲置动画的精灵图集，并将其切割为单独的帧。
    Args:
        target_width (int): 最终缩放后的图片宽度。
        target_height (int): 最终缩放后的图片高度。
    Returns:
        list: 包含所有缩放后动画帧的列表。
    """
    knight_idle_sprite_sheet_path = "./plays_animation_art/Knight_IDLE.png" # 假设您将图片保存为这个名字

    if not os.path.exists(knight_idle_sprite_sheet_path):
        raise FileNotFoundError(f"骑士闲置动画图片未找到: {knight_idle_sprite_sheet_path}")

    knight_idle_sprite_sheet = pygame.image.load(knight_idle_sprite_sheet_path).convert_alpha()

    # 根据提供的 Knight_IDLE.png 图片，它有 8 帧，水平排列。
    # 每帧的宽度是整个图片宽度除以帧数，高度是整个图片高度。
    num_knight_idle_frames = 7
    knight_idle_frame_width = knight_idle_sprite_sheet.get_width() // num_knight_idle_frames
    knight_idle_frame_height = knight_idle_sprite_sheet.get_height()

    if knight_idle_sprite_sheet.get_width() % num_knight_idle_frames != 0:
        print(f"警告：Knight_IDLE.png 的宽度 {knight_idle_sprite_sheet.get_width()} 不是帧数 {num_knight_idle_frames} 的整数倍，可能导致切割不准确！")

    frames = []
    for i in range(num_knight_idle_frames):
        # subsurface 的参数是 (left, top, width, height)
        # left: i * knight_idle_frame_width，这是当前帧的起始x坐标
        # top: 总是 0，因为帧是水平排列的
        # width: knight_idle_frame_width，当前帧的宽度
        # height: knight_idle_frame_height，当前帧的高度
        frame = knight_idle_sprite_sheet.subsurface((i * knight_idle_frame_width, 0, knight_idle_frame_width, knight_idle_frame_height))
        # 使用 smoothscale 进行高质量缩放
        scaled_frame = pygame.transform.smoothscale(frame, (target_width, target_height))
        frames.append(scaled_frame)
    return frames
