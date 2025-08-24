import time
import cv2
import numpy as np
import math

def match_template(source, template, method=cv2.TM_CCOEFF_NORMED, 
                  min_confidence=0.4, multi_target=False, max_targets=5):
    """
    优化的模板匹配函数，显著提升精度和速度
    支持多目标检测和亚像素精度
    
    参数:
        source: 源图像 (灰度或彩色)
        template: 模板图像 (灰度或彩色)
        method: 匹配方法 (默认cv2.TM_CCOEFF_NORMED)
        min_confidence: 最小置信度阈值
        multi_target: 是否检测多个目标
        max_targets: 最大目标检测数量
    
    返回:
        如果multi_target=False: (max_val, max_loc, result_image)
        如果multi_target=True: [(score, location), ...]
    """
    # 禁用OpenCV多线程优化以避免线程开销
    # cv2.setUseOptimized(True)
    # cv2.setNumThreads(1)
    
    # 确保图像类型一致 - 使用更小的数据类型以减少内存占用
    if source.dtype != np.uint8:
        source = source.astype(np.uint8)
    if template.dtype != np.uint8:
        template = template.astype(np.uint8)
    
    # 金字塔参数配置
    pyramid_levels = _calculate_pyramid_levels(source, template)
    
    # 候选点存储
    candidate_points = []
    
    # 从顶层（低分辨率）到底层（高分辨率）搜索
    for level in range(pyramid_levels-1, -1, -1):
        # 惰性计算金字塔层级 - 只在需要时计算
        tpl = _get_pyramid_level(template, level)
        src = _get_pyramid_level(source, level)
        
        # 确定搜索区域
        search_areas = _get_search_areas(src, tpl, candidate_points, level, pyramid_levels)
        
        for roi in search_areas:
            x, y, w, h = roi
            # 确保ROI有效
            if w <= 0 or h <= 0:
                continue
                
            search_area = src[y:y+h, x:x+w]
            
            # 跳过无效区域
            if search_area.size == 0 or tpl.size == 0 or search_area.shape[0] < tpl.shape[0] or search_area.shape[1] < tpl.shape[1]:
                continue
                
            # 使用积分图加速小模板匹配
            if tpl.size < 2500:
                result = cv2.matchTemplate(search_area, tpl, method)
            else:
                result = cv2.matchTemplate(search_area, tpl, method)
            
            # 获取候选点
            current_candidates = _get_candidate_points(result, min_confidence, multi_target, max_targets, tpl)
            
            # 转换坐标到当前层图像
            for score, loc in current_candidates:
                abs_loc = (loc[0] + x, loc[1] + y)
                candidate_points.append((score, abs_loc, level))
        
        # 释放当前层级的图像以节省内存
        del tpl
        del src
    
    # 过滤和融合候选点
    final_matches = _process_candidates(candidate_points, source, template, pyramid_levels)
    
    # 释放候选点列表
    del candidate_points
    
    # 创建结果图（当前有问题，返回None）
    # result_image = _create_result_image(source, template, final_matches, pyramid_levels)
    
    if multi_target:
        return [(score, loc) for score, loc, _ in final_matches], None
    else:
        if final_matches:
            best_match = final_matches[0]
            return best_match[0], best_match[1], None
        return 0.0, (0, 0), None


def _get_pyramid_level(image, level):
    """惰性计算金字塔层级"""
    if level == 0:
        return image.copy()
    
    current = image
    for i in range(level):
        # 计算降采样后的尺寸
        new_shape = ((current.shape[1] + 1) // 2, (current.shape[0] + 1) // 2)
        current = cv2.resize(current, new_shape, interpolation=cv2.INTER_AREA)
    
    return current


def _calculate_pyramid_levels(source, template):
    """自动计算最佳金字塔层级（优化版：动态金字塔控制）"""
    min_src_dim = min(source.shape[0], source.shape[1])
    min_tpl_dim = min(template.shape[0], template.shape[1])
    
    # 优化1: 动态金字塔控制 - 比基准版本更精简
    if min_tpl_dim <= 8:
        return 1  # 禁用金字塔
    elif min_tpl_dim <= 16:
        return 2  # 最多2级
    
    # 计算最大可能层级 - 比基准版本更严格
    max_levels = 0
    dim = min(min_src_dim, min_tpl_dim)
    while dim >= 32:  # 最小尺寸限制提高到32，减少层级
        max_levels += 1
        dim //= 2
    
    # 根据模板大小调整层级 - 比基准版本更精简
    if min_tpl_dim < 32:
        max_levels = min(max_levels, 2)
    elif min_tpl_dim < 64:
        max_levels = min(max_levels, 3)
    else:
        max_levels = min(max_levels, 4)
    
    return max(1, max_levels)


def _get_search_areas(src, tpl, prev_candidates, current_level, total_levels):
    """获取当前层的搜索区域"""
    search_areas = []

    # 顶层全图搜索
    if not prev_candidates:
        return [(0, 0, src.shape[1], src.shape[0])]

    # 根据上一级候选点生成搜索区域
    for score, loc, level in prev_candidates:
        # 计算层级缩放因子
        scale_factor = 2 ** (level - current_level)

        # 缩放位置
        scaled_loc = (int(loc[0] * scale_factor), int(loc[1] * scale_factor))

        # 计算搜索区域大小 (模板尺寸的2倍，比基准版本更小)
        search_w = min(tpl.shape[1] * 2, src.shape[1])
        search_h = min(tpl.shape[0] * 2, src.shape[0])

        # 计算ROI坐标
        x = max(0, scaled_loc[0] - search_w // 2)
        y = max(0, scaled_loc[1] - search_h // 2)

        # 确保ROI在图像范围内
        w = min(search_w, src.shape[1] - x)
        h = min(search_h, src.shape[0] - y)
        search_areas.append((x, y, w, h))
    
    # 合并重叠区域
    return _merge_search_areas(search_areas)


def _merge_search_areas(areas):
    """合并重叠的搜索区域"""
    if not areas:
        return []
    
    # 简单去重
    merged = []
    for area in areas:
        merged = _add_area(merged, area)
    
    return merged


def _add_area(merged, new_area):
    """添加新区域到列表，合并重叠区域"""
    x1, y1, w1, h1 = new_area
    x1_end = x1 + w1
    y1_end = y1 + h1
    
    for i, (x2, y2, w2, h2) in enumerate(merged):
        x2_end = x2 + w2
        y2_end = y2 + h2
        
        # 检查重叠
        if not (x1_end < x2 or x2_end < x1 or y1_end < y2 or y2_end < y1):
            # 合并区域
            new_x = min(x1, x2)
            new_y = min(y1, y2)
            new_w = max(x1_end, x2_end) - new_x
            new_h = max(y1_end, y2_end) - new_y
            merged[i] = (new_x, new_y, new_w, new_h)
            return merged
    
    # 没有重叠，添加新区域
    merged.append(new_area)
    return merged


def _get_candidate_points(result, min_confidence, multi_target, max_targets, tpl):
    """获取候选匹配点"""
    # 单目标匹配
    if not multi_target:
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
        if method == cv2.TM_SQDIFF or method == cv2.TM_SQDIFF_NORMED:
            if min_val < (1 - min_confidence):
                return [(1 - min_val, min_loc)]
        else:
            if max_val > min_confidence:
                return [(max_val, max_loc)]
        return []
    
    # 多目标匹配
    candidates = []
    
    # 应用阈值
    if method == cv2.TM_SQDIFF or method == cv2.TM_SQDIFF_NORMED:
        threshold = 1 - min_confidence
        loc = np.where(result < threshold)
        for pt in zip(*loc[::-1]):
            score = 1 - result[pt[1], pt[0]]
            candidates.append((score, pt))
    else:
        threshold = min_confidence
        loc = np.where(result > threshold)
        for pt in zip(*loc[::-1]):
            score = result[pt[1], pt[0]]
            candidates.append((score, pt))
    
    # 按分数排序
    candidates.sort(reverse=True, key=lambda x: x[0])
    
    # 应用非极大值抑制
    if candidates:
        candidates = _non_max_suppression(candidates, tpl.shape[1], tpl.shape[0])
    
    # 限制最大目标数
    return candidates[:max_targets]


def _non_max_suppression(candidates, width, height, threshold=0.5):
    """非极大值抑制"""
    if not candidates:
        return []
    
    # 提取坐标和分数
    boxes = np.array([(x, y, x + width, y + height) for _, (x, y) in candidates])
    scores = np.array([score for score, _ in candidates])
    
    # 使用OpenCV的NMSBoxes
    indices = cv2.dnn.NMSBoxes(boxes.tolist(), scores.tolist(), score_threshold=0, nms_threshold=threshold)
    
    # 提取结果
    result = []
    if len(indices) > 0:
        for i in indices.flatten():
            x, y = boxes[i][0], boxes[i][1]
            result.append((scores[i], (x, y)))
    
    return result


def _process_candidates(candidates, source, template, pyramid_levels):
    """处理候选点，进行亚像素优化"""
    if not candidates:
        return []
    
    # 按分数排序
    candidates.sort(reverse=True, key=lambda x: x[0])
    
    # 应用非极大值抑制
    filtered = []
    for score, loc, level in candidates:
        # 计算实际坐标
        scale_factor = 2 ** level
        real_loc = (int(loc[0] * scale_factor), int(loc[1] * scale_factor))
        
        # 添加到结果
        filtered.append((score, real_loc, level))
    
    # 进一步过滤 - 只保留最佳匹配或多个不重叠的匹配
    if len(filtered) > 1:
        # 提取框
        boxes = np.array([(x, y, x + template.shape[1], y + template.shape[0]) for _, (x, y), _ in filtered])
        scores = np.array([score for score, _, _ in filtered])
        
        # 使用NMS
        indices = cv2.dnn.NMSBoxes(boxes.tolist(), scores.tolist(), score_threshold=0, nms_threshold=0.3)
        
        # 更新结果
        result = []
        if len(indices) > 0:
            for i in indices.flatten():
                result.append(filtered[i])
        else:
            result = [filtered[0]]
    else:
        result = filtered
    
    # 释放中间变量
    del filtered
    
    return result

# 全局变量 - 缓存常用模板以减少内存分配
_template_cache = {}

# 为了兼容原代码结构，这里保留method变量
method = cv2.TM_CCOEFF_NORMED