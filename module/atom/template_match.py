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
    
    # 确保图像类型一致
    if source.dtype != template.dtype:
        template = template.astype(source.dtype)
    
    # 金字塔参数配置
    pyramid_levels = _calculate_pyramid_levels(source, template)
    
    # 构建自适应金字塔
    source_pyramid = _build_adaptive_pyramid(source, pyramid_levels)
    template_pyramid = _build_adaptive_pyramid(template, pyramid_levels)
    
    # 候选点存储
    candidate_points = []
    
    # 从顶层（低分辨率）到底层（高分辨率）搜索
    for level in range(pyramid_levels-1, -1, -1):
        tpl = template_pyramid[level]
        src = source_pyramid[level]
        
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
    
    # 过滤和融合候选点
    final_matches = _process_candidates(candidate_points, source, template, pyramid_levels)
    
    # 创建结果图
    result_image = _create_result_image(source, template, final_matches, pyramid_levels)
    
    if multi_target:
        return [(score, loc) for score, loc, _ in final_matches], result_image
    else:
        if final_matches:
            best_match = final_matches[0]
            return best_match[0], best_match[1], result_image
        return 0.0, (0, 0), result_image


def _calculate_pyramid_levels(source, template):
    """自动计算最佳金字塔层级（优化版：动态金字塔控制）"""
    min_src_dim = min(source.shape[0], source.shape[1])
    min_tpl_dim = min(template.shape[0], template.shape[1])
    
    # 优化1: 动态金字塔控制
    if min_tpl_dim <= 8:
        return 1  # 禁用金字塔
    elif min_tpl_dim <= 16:
        return 2  # 最多2级
    
    # 计算最大可能层级
    max_levels = 0
    dim = min(min_src_dim, min_tpl_dim)
    while dim >= 16:  # 最小尺寸限制
        max_levels += 1
        dim //= 2
    
    # 根据模板大小调整层级
    if min_tpl_dim < 32:
        max_levels = min(max_levels, 3)
    elif min_tpl_dim < 64:
        max_levels = min(max_levels, 4)
    else:
        max_levels = min(max_levels, 5)
    
    return max(1, max_levels)


def _build_adaptive_pyramid(image, levels, min_size=16):
    """构建自适应图像金字塔"""
    pyramid = [image]
    current = image
    
    # 确保构建指定数量的层级，即使图像尺寸接近最小限制
    for i in range(1, levels):
        # 检查降采样后的尺寸是否仍然大于最小尺寸
        new_shape = ((current.shape[1] + 1) // 2, (current.shape[0] + 1) // 2)
        if min(new_shape) < min_size:
            break
            
        # 直接降采样，不使用内存池
        current = cv2.resize(current, new_shape, interpolation=cv2.INTER_AREA)
        pyramid.append(current)
    
    return pyramid


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

        # 计算搜索区域大小 (模板尺寸的3倍)
        search_w = min(tpl.shape[1] * 3, src.shape[1])
        search_h = min(tpl.shape[0] * 3, src.shape[0])

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
            new_x_end = max(x1_end, x2_end)
            new_y_end = max(y1_end, y2_end)
            
            new_w = new_x_end - new_x
            new_h = new_y_end - new_y
            
            # 替换原有区域
            merged[i] = (new_x, new_y, new_w, new_h)
            return merged
    
    # 无重叠，添加新区域
    merged.append(new_area)
    return merged


def _get_candidate_points(result, min_confidence, multi_target, max_targets, template):
    """从匹配结果中获取候选点"""
    candidates = []
    
    # 单目标模式
    if not multi_target:
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
        if max_val >= min_confidence:
            candidates.append((max_val, max_loc))
        return candidates
    
    # 多目标模式
    _, max_val, _, max_loc = cv2.minMaxLoc(result)
    threshold = max(min_confidence, max_val * 0.8)
    
    # 查找所有超过阈值的点
    locs = np.where(result >= threshold)
    
    # 非极大值抑制
    points = []
    for pt in zip(*locs[::-1]):
        points.append(pt)
    
    # 按置信度排序
    points.sort(key=lambda pt: result[pt[1], pt[0]], reverse=True)
    
    # 应用非极大值抑制 - 调整动态阈值逻辑
    selected = []
    for i, pt in enumerate(points):
        x, y = pt
        confidence = result[y, x]
        
        # 使用固定NMS阈值以提高性能
        dynamic_dist = min(template.shape[0], template.shape[1]) * 0.5
        
        # 检查是否与已选点太近
        too_close = False
        for sx, sy in selected:
            dist = math.sqrt((x - sx)**2 + (y - sy)**2)
            if dist < dynamic_dist:
                too_close = True
                break
        
        if not too_close and confidence >= min_confidence:
            selected.append((x, y))
            candidates.append((confidence, (x, y)))
            
            if len(candidates) >= max_targets:
                break
    
    return candidates


def _process_candidates(candidates, source, template, pyramid_levels):
    """处理和过滤候选点"""
    if not candidates:
        return []
    
    # 按置信度排序
    candidates.sort(key=lambda x: x[0], reverse=True)
    
    # 非极大值抑制
    filtered = []
    for score, loc, level in candidates:
        # 计算原始图像位置
        scale_factor = 2 ** level
        orig_loc = (int(loc[0] * scale_factor), int(loc[1] * scale_factor))
        
        # 使用固定NMS阈值以提高性能
        dynamic_dist = min(template.shape[0], template.shape[1]) * 0.8
        
        # 检查是否与已选点太近
        too_close = False
        for _, floc, _ in filtered:
            dist = math.sqrt((orig_loc[0] - floc[0])**2 + (orig_loc[1] - floc[1])**2)
            if dist < dynamic_dist:
                too_close = True
                break
        
        if not too_close:
            # 在原始层进行精确匹配
            refined_score, refined_loc = _refine_match(source, template, orig_loc, method=cv2.TM_CCOEFF_NORMED)
            filtered.append((refined_score, refined_loc, level))
    
    # 返回前N个结果
    return filtered[:10]



def _refine_match(source, template, approx_loc, method=cv2.TM_CCOEFF_NORMED):
    # 计算搜索区域
    tpl_h, tpl_w = template.shape[:2]
    src_h, src_w = source.shape[:2]
    
    # 特殊处理：当模板和源图像大小相同时
    if tpl_h == src_h and tpl_w == src_w:
        # 直接在整个图像上执行匹配
        result = cv2.matchTemplate(source, template, method)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
        abs_loc = max_loc
        
        # 亚像素优化 - 放宽条件
        if max_val > 0.7:  # 降低阈值
            # 在匹配结果周围提取小区域
            sub_x = max(0, max_loc[0] - 2)
            sub_y = max(0, max_loc[1] - 2)
            sub_w = min(5, result.shape[1] - sub_x)
            sub_h = min(5, result.shape[0] - sub_y)
            
            if sub_w > 0 and sub_h > 0:
                sub_region = result[sub_y:sub_y+sub_h, sub_x:sub_x+sub_w]
                
                # 亚像素优化
                refined_loc = _subpixel_accuracy(sub_region)
                
                # 调整到原始坐标
                refined_x = refined_loc[0] + sub_x
                refined_y = refined_loc[1] + sub_y
                abs_loc = (refined_x, refined_y)
        
        return max_val, abs_loc
    
    # 搜索区域为模板尺寸的2倍
    search_size = max(tpl_w, tpl_h) * 2
    x = max(0, approx_loc[0] - search_size // 2)
    y = max(0, approx_loc[1] - search_size // 2)
    w = min(search_size, src_w - x)
    h = min(search_size, src_h - y)
    
    # 确保搜索区域有效
    if w <= 0 or h <= 0:
        # 如果搜索区域无效，返回默认值
        return 0.0, approx_loc
    
    # 裁剪搜索区域
    search_area = source[y:y+h, x:x+w]
    
    # 执行匹配
    result = cv2.matchTemplate(search_area, template, method)
    
    # 获取最佳匹配位置
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
    
    # 转换为原始图像坐标
    abs_loc = (max_loc[0] + x, max_loc[1] + y)
    
    # 亚像素优化 - 放宽条件
    if max_val > 0.7:  # 降低阈值
        # 在匹配结果周围提取小区域
        sub_x = max(0, max_loc[0] - 2)
        sub_y = max(0, max_loc[1] - 2)
        sub_w = min(5, result.shape[1] - sub_x)
        sub_h = min(5, result.shape[0] - sub_y)
        
        if sub_w > 0 and sub_h > 0:
            sub_region = result[sub_y:sub_y+sub_h, sub_x:sub_x+sub_w]
            
            # 亚像素优化
            refined_loc = _subpixel_accuracy(sub_region)
            
            # 调整到原始坐标
            refined_x = refined_loc[0] + sub_x + x
            refined_y = refined_loc[1] + sub_y + y
            abs_loc = (refined_x, refined_y)
    
    return max_val, abs_loc


def _subpixel_accuracy(result):
    """亚像素精度优化"""
    # 找到整数最大值位置
    max_pos = np.unravel_index(np.argmax(result), result.shape)
    y, x = max_pos
    
    # 检查边界
    if 0 < y < result.shape[0]-1 and 0 < x < result.shape[1]-1:
        # 二次曲面拟合
        dx = (result[y, x+1] - result[y, x-1]) / 2.0
        dy = (result[y+1, x] - result[y-1, x]) / 2.0
        dxx = result[y, x+1] - 2*result[y, x] + result[y, x-1]
        dyy = result[y+1, x] - 2*result[y, x] + result[y-1, x]
        dxy = (result[y+1, x+1] - result[y+1, x-1] - result[y-1, x+1] + result[y-1, x-1]) / 4.0
        
        # 构建Hessian矩阵
        A = np.array([[dxx, dxy], [dxy, dyy]])
        b = np.array([-dx, -dy])
        
        try:
            # 求解亚像素偏移
            offset = np.linalg.solve(A, b)
            return (x + offset[0], y + offset[1])
        except np.linalg.LinAlgError:
            # 矩阵奇异，退回整数位置
            return (x, y)
    
    return (x, y)


def _create_result_image(source, template, matches, pyramid_levels):
    """创建结果图像"""
    h, w = source.shape[:2]
    t_h, t_w = template.shape[:2]
    result_h = h - t_h + 1
    result_w = w - t_w + 1
    
    # 创建全尺寸结果图
    result_image = np.full((result_h, result_w), -1.0, dtype=np.float32)
    
    # 标记匹配位置
    for score, loc, level in matches:
        x, y = loc
        # 将浮点数坐标转换为整数
        x_int, y_int = int(round(x)), int(round(y))
        if 0 <= x_int < result_w and 0 <= y_int < result_h:
            # 在结果图上标记匹配点
            result_image[y_int, x_int] = score
    
    return result_image


def visualize_matches(source, template, matches):
    """可视化匹配结果"""
    # 创建彩色可视化图像
    if len(source.shape) == 2:
        vis = cv2.cvtColor(source, cv2.COLOR_GRAY2BGR)
    else:
        vis = source.copy()
    
    t_h, t_w = template.shape[:2]
    
    for i, (score, loc) in enumerate(matches):
        x, y = loc
        top_left = (x, y)
        bottom_right = (x + t_w, y + t_h)
        
        # 绘制矩形
        color = (0, 255, 0) if i == 0 else (0, 0, 255)  # 最佳匹配绿色，其他红色
        cv2.rectangle(vis, top_left, bottom_right, color, 2)
        
        # 显示置信度
        text = f"{score:.4f}"
        cv2.putText(vis, text, (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 
                   0.5, color, 1, cv2.LINE_AA)
    
    return vis

# 使用示例
if __name__ == "__main__":
    # 加载图像
    template = cv2.imread(r'H:\game\yys\OnmyojiAutoScript-easy-install\OnmyojiAutoScript-easy-install\test_shape_match\template_draw.png')  # 150x150模板
    source = cv2.imread(r'H:\game\yys\OnmyojiAutoScript-easy-install\OnmyojiAutoScript-easy-install\test_shape_match\source.png')      # 1280x1024搜索图
    
    # 转换为灰度
    template_img = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
    source_img = cv2.cvtColor(source, cv2.COLOR_BGR2GRAY)
    
    start_time = time.time()
    res = cv2.matchTemplate(source_img, template_img, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)  # 最小匹配度，最大匹配度，最小匹配度的坐标，最大匹配度的坐标
    print(f"opencv matching score: {max_val} Matching time: {1000*(time.time()-start_time):.2f}ms")


    # 测试优化后的匹配
    start_time = time.time()
    
    # 单目标匹配
    score, location, result_map = match_template(source_img, template_img)
    print("单目标匹配结果:")
    print(f"匹配度: {score:.4f}, 位置: {location}")
    print(f"耗时: {(time.time() - start_time)*1000:.2f} ms")
    
    # 可视化
    vis_single = visualize_matches(source, template_img, [(score, location)])
    cv2.imwrite('single_match_result.jpg', vis_single)
    
    # 多目标匹配
    start_time = time.time()
    matches, result_map = match_template(source_img, template_img, multi_target=True)
    print("\n多目标匹配结果:")
    for i, (score, loc) in enumerate(matches):
        print(f"目标 {i+1}: 匹配度={score:.4f}, 位置={loc}")
    print(f"耗时: {(time.time() - start_time)*1000:.2f} ms")
    
    # 可视化多目标
    vis_multi = visualize_matches(source, template_img, matches)
    # cv2.imwrite('multi_match_result.jpg', vis_multi)
    
    # 保存结果图
    # cv2.imwrite('result_map.jpg', (result_map * 255).astype(np.uint8))