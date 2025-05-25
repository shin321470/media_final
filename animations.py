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
        raise FileNotFoundError(f"女巫奔跑动画图片未找到: {witch_sprite_sheet_path}")

    witch_sprite_sheet = pygame.image.load(witch_sprite_sheet_path).convert_alpha()

    # 假设女巫精灵图每帧宽度和高度 (B_witch_run.png 通常是 8 帧，每帧等高)
    witch_frame_width = witch_sprite_sheet.get_width()
    witch_frame_height = witch_sprite_sheet.get_height() // 8 # 假设有8帧

    if witch_sprite_sheet.get_height() % 8 != 0:
        print(f"警告：B_witch_run.png 的高度 {witch_sprite_sheet.get_height()} 不是帧数 8 的整数倍，可能导致切割不准确！")

    frames = []
    for i in range(8): # B_witch_run.png 有 8 帧
        frame = witch_sprite_sheet.subsurface((0, i * witch_frame_height, witch_frame_width, witch_frame_height))
        # 根据传入的 target_width 和 target_height 进行缩放
        frames.append(pygame.transform.smoothscale(frame, (target_width, target_height)))
    return frames

# 定义一个函数来加载并缩放普通玩家的行走动画
def load_normal_player_walk_animation(target_width, target_height):
    """
    加载普通玩家的行走动画图片（walk1.png, walk2.png），并进行缩放。
    Args:
        target_width (int): 最终缩放后的图片宽度。
        target_height (int): 最终缩放后的图片高度。
    Returns:
        list: 包含所有缩放后动画帧的列表。
    """
    walk1_path = "walk1.png"
    walk2_path = "walk2.png"
    if not os.path.exists(walk1_path) or not os.path.exists(walk2_path):
        raise FileNotFoundError(f"普通玩家行走动画图片未找到: {walk1_path} 或 {walk2_path}")

    original_frames = [
        pygame.image.load(walk1_path).convert_alpha(),
        pygame.image.load(walk2_path).convert_alpha()
    ]

    scaled_frames = [
        pygame.transform.smoothscale(frame, (target_width, target_height))
        for frame in original_frames
    ]
    return scaled_frames

def load_witch_idle_animation(target_width, target_height):
    """
    加载女巫闲置动画的精灵图集，并将其切割为单独的帧。
    Args:
        target_width (int): 最终缩放后的图片宽度。
        target_height (int): 最终缩放后的图片高度。
    Returns:
        list: 包含所有缩放后动画帧的列表。
    """
    # 假设 B_witch_idle.png 也是一个垂直排列的精灵图集
    # 请根据实际图片中帧的数量和排列方式调整以下参数
    idle_sprite_sheet_path = "B_witch_idle.png"
    if not os.path.exists(idle_sprite_sheet_path):
        raise FileNotFoundError(f"女巫闲置动画图片未找到: {idle_sprite_sheet_path}")

    idle_sprite_sheet = pygame.image.load(idle_sprite_sheet_path).convert_alpha()

    # 假设 B_witch_idle.png 有 8 帧，每帧等高
    # 如果你的图片有不同数量的帧，请修改这里的 8
    num_idle_frames = 8
    idle_frame_width = idle_sprite_sheet.get_width()
    idle_frame_height = idle_sprite_sheet.get_height() // num_idle_frames

    if idle_sprite_sheet.get_height() % num_idle_frames != 0:
        print(f"警告：B_witch_idle.png 的高度 {idle_sprite_sheet.get_height()} 不是帧数 {num_idle_frames} 的整数倍，可能导致切割不准确！")

    frames = []
    for i in range(num_idle_frames):
        frame = idle_sprite_sheet.subsurface((0, i * idle_frame_height, idle_frame_width, idle_frame_height))
        frames.append(pygame.transform.smoothscale(frame, (target_width, target_height)))
    return frames
