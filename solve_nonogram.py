def solve_nonogram(row_clues, col_clues):
    rows = len(row_clues)
    cols = len(col_clues)
    
    # 初始化网格: 0=未知, 1=填充, -1=空白
    grid = [[0 for _ in range(cols)] for _ in range(rows)]
    
    # 迭代直到没有变化
    changed = True
    while changed:
        changed = False
        
        # 处理每一行
        for i in range(rows):
            row_changed = solve_line(grid[i], row_clues[i])
            changed = changed or row_changed
        
        # 处理每一列
        for j in range(cols):
            col = [grid[i][j] for i in range(rows)]
            col_changed = solve_line(col, col_clues[j])
            if col_changed:
                changed = True
                for i in range(rows):
                    grid[i][j] = col[i]
    
    return grid

def solve_line(line, clues):
    """解决一行或一列，返回是否有变化"""
    length = len(line)
    old_line = line.copy()
    
    # 特殊情况：没有提示，整行/列都是空白
    if not clues:
        for i in range(length):
            line[i] = -1
        return line != old_line
    
    # 生成所有可能的填充方案
    all_arrangements = []
    
    def generate_arrangements(arrangement, pos, clue_idx):
        # 所有提示都已使用
        if clue_idx == len(clues):
            # 剩余位置填充为空白
            full_arrangement = arrangement + [-1] * (length - pos)
            
            # 检查方案是否与当前状态兼容
            if all(line[i] == 0 or line[i] == full_arrangement[i] for i in range(length)):
                all_arrangements.append(full_arrangement)
            return
        
        block_size = clues[clue_idx]
        
        # 尝试在不同位置放置当前块
        max_pos = length - sum(clues[clue_idx:]) - (len(clues) - clue_idx - 1)
        for i in range(pos, max_pos + 1):
            # 检查是否可以在位置i放置块
            can_place = True
            
            # 检查块之前的位置
            for j in range(pos, i):
                if line[j] == 1:
                    can_place = False
                    break
            
            if not can_place:
                continue
            
            # 检查块内的位置
            for j in range(i, i + block_size):
                if j >= length or line[j] == -1:
                    can_place = False
                    break
            
            if not can_place:
                continue
            
            # 检查块之后的位置
            if i + block_size < length and line[i + block_size] == 1:
                continue
            
            # 创建新的填充方案
            new_arrangement = arrangement.copy()
            
            # 填充块之前的空白
            for j in range(pos, i):
                new_arrangement.append(-1)
            
            # 填充块
            for j in range(i, i + block_size):
                new_arrangement.append(1)
            
            # 填充块之后的空白分隔符
            if i + block_size < length:
                new_arrangement.append(-1)
                generate_arrangements(new_arrangement, i + block_size + 1, clue_idx + 1)
            else:
                generate_arrangements(new_arrangement, i + block_size, clue_idx + 1)
    
    # 生成所有可能的填充方案
    generate_arrangements([], 0, 0)
    
    # 无解情况
    if not all_arrangements:
        return False
    
    # 根据所有可能方案确定格子状态
    for i in range(length):
        if line[i] == 0:  # 只处理未确定的格子
            all_black = True
            all_white = True
            
            for arrangement in all_arrangements:
                if arrangement[i] == -1:
                    all_black = False
                elif arrangement[i] == 1:
                    all_white = False
            
            if all_black:
                line[i] = 1
            elif all_white:
                line[i] = -1
    
    return line != old_line

# 使用给定的提示解决nonogram
row_clues = [[6], [1, 1], [1, 1, 1], [6, 1, 1], [1, 1], [1, 7], [4, 2], [1, 3, 3], 
             [1, 1, 1, 1, 1], [4, 1, 2, 3], [1, 1], [1, 3, 2], [3, 2, 1, 1], [1, 1, 1, 1], [5, 4]]
col_clues = [[4,1],[1,1,1],[1,1,1],[1,4,3],[1,1,1],[4,6,1],[1,1,1],[1,3,3],
             [1,4,4],[1,1,1],[4,5,4],[3,1,1],[1,3,1],[1,4],[1,1]]

# 求解nonogram
solution = solve_nonogram(row_clues, col_clues)

# 打印结果
def print_solution(grid):
    for row in grid:
        print(''.join(['█' if cell == 1 else '·' if cell == -1 else '?' for cell in row]))

print_solution(solution)