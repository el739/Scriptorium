import os
import hashlib
import sys
from colorama import init, Fore, Style

def calculate_md5(file_path):
    """计算文件的MD5哈希值"""
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def compare_folders(dir1, dir2):
    """比较两个文件夹中的文件"""
    # 检查目录是否存在
    if not os.path.exists(dir1):
        print(f"错误: 目录 '{dir1}' 不存在")
        return
    if not os.path.exists(dir2):
        print(f"错误: 目录 '{dir2}' 不存在")
        return
    
    # 初始化计数器
    only_in_dir1 = []
    only_in_dir2 = []
    diff_files = []
    
    # 获取两个目录中的所有文件(包括子目录)
    files1 = {os.path.relpath(os.path.join(root, file), dir1): os.path.join(root, file)
              for root, _, files in os.walk(dir1)
              for file in files}
    
    files2 = {os.path.relpath(os.path.join(root, file), dir2): os.path.join(root, file)
              for root, _, files in os.walk(dir2)
              for file in files}
    
    # 找出只在dir1中的文件
    for rel_path in sorted(files1.keys()):
        if rel_path not in files2:
            only_in_dir1.append(rel_path)
    
    # 找出只在dir2中的文件
    for rel_path in sorted(files2.keys()):
        if rel_path not in files1:
            only_in_dir2.append(rel_path)
    
    # 比较两个目录中都有的文件
    common_files = set(files1.keys()) & set(files2.keys())
    for rel_path in sorted(common_files):
        # 比较文件内容（使用MD5哈希）
        if calculate_md5(files1[rel_path]) != calculate_md5(files2[rel_path]):
            diff_files.append(rel_path)
    
    # 显示结果
    print(f"\n{Fore.CYAN}比较结果:{Style.RESET_ALL}")
    print(f"{Fore.CYAN}==========={Style.RESET_ALL}\n")
    
    if not (only_in_dir1 or only_in_dir2 or diff_files):
        print(f"{Fore.GREEN}两个文件夹内容完全相同!{Style.RESET_ALL}")
        return
    
    if only_in_dir1:
        print(f"{Fore.YELLOW}只在 '{dir1}' 中存在的文件:{Style.RESET_ALL}")
        for file in only_in_dir1:
            print(f"  {file}")
        print()
    
    if only_in_dir2:
        print(f"{Fore.YELLOW}只在 '{dir2}' 中存在的文件:{Style.RESET_ALL}")
        for file in only_in_dir2:
            print(f"  {file}")
        print()
    
    if diff_files:
        print(f"{Fore.RED}内容不同的文件:{Style.RESET_ALL}")
        for file in diff_files:
            print(f"  {file}")
        print()
    
    # 总结
    total_files = len(set(files1.keys()) | set(files2.keys()))
    different_files = len(only_in_dir1) + len(only_in_dir2) + len(diff_files)
    print(f"{Fore.CYAN}总结:{Style.RESET_ALL}")
    print(f"  总文件数: {total_files}")
    print(f"  不同文件数: {different_files}")
    print(f"  相同文件数: {total_files - different_files}")

if __name__ == "__main__":
    # 初始化colorama
    init()
    
    if len(sys.argv) == 3:
        dir1 = sys.argv[1]
        dir2 = sys.argv[2]
    else:
        # 用户输入目录路径
        dir1 = input("请输入第一个文件夹路径: ").strip()
        dir2 = input("请输入第二个文件夹路径: ").strip()
    
    # 转换为绝对路径
    dir1 = os.path.abspath(dir1)
    dir2 = os.path.abspath(dir2)
    
    print(f"\n比较文件夹:")
    print(f"  目录1: {dir1}")
    print(f"  目录2: {dir2}")
    
    compare_folders(dir1, dir2)