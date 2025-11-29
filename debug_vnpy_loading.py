#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
调试VN.PY策略加载过程
"""

import sys
import importlib
import traceback
from pathlib import Path
from glob import glob
from vnpy_ctastrategy.template import CtaTemplate, TargetPosTemplate

# 确保当前目录在Python路径中
current_dir = Path.cwd()
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

print("=== 调试VN.PY策略加载过程 ===")

# 模拟VN.PY的load_strategy_class_from_folder方法

def debug_load_strategy_class_from_folder(path: Path, module_name: str = ""):
    print(f"\n调试加载目录: {path}")
    print(f"模块名前缀: {module_name}")
    print(f"目录存在: {path.exists()}")
    
    if not path.exists():
        print("目录不存在，跳过")
        return
    
    classes = {}
    
    for suffix in ["py", "pyd", "so"]:
        pathname: str = str(path.joinpath(f"*.{suffix}"))
        print(f"\n搜索模式: {pathname}")
        
        glob_results = glob(pathname)
        print(f"glob结果: {glob_results}")
        
        for filepath in glob_results:
            filename = Path(filepath).stem
            print(f"\n处理文件: {filepath}")
            print(f"文件名(stem): {filename}")
            
            if filename == "__init__":
                print("跳过__init__文件")
                continue
                
            name: str = f"{module_name}.{filename}"
            print(f"模块名: {name}")
            
            # 调用load_strategy_class_from_module
            try:
                print(f"尝试导入模块: {name}")
                module = importlib.import_module(name)
                print(f"模块导入成功: {module}")
                
                # 重载模块
                importlib.reload(module)
                print(f"模块重载成功")
                
                # 查找策略类
                found_classes = []
                for attr_name in dir(module):
                    value = getattr(module, attr_name)
                    if (
                        isinstance(value, type)
                        and issubclass(value, CtaTemplate)
                        and value not in {CtaTemplate, TargetPosTemplate}
                    ):
                        print(f"找到策略类: {attr_name} = {value}")
                        classes[value.__name__] = value
                        found_classes.append(attr_name)
                        
                if not found_classes:
                    print("未找到策略类")
                    
            except Exception as e:
                print(f"导入失败: {e}")
                print(f"异常详情: {traceback.format_exc()}")
    
    return classes

# 测试VN.PY内置策略目录
print("\n=== 测试VN.PY内置策略目录 ===")
from vnpy_ctastrategy import engine
path1 = Path(engine.__file__).parent.joinpath("strategies")
classes1 = debug_load_strategy_class_from_folder(path1, "vnpy_ctastrategy.strategies")
print(f"内置策略类: {list(classes1.keys())}")

# 测试项目策略目录
print("\n=== 测试项目策略目录 ===")
path2 = Path.cwd().joinpath("strategies")
classes2 = debug_load_strategy_class_from_folder(path2, "strategies")
print(f"项目策略类: {list(classes2.keys())}")

# 合并结果
all_classes = {**classes1, **classes2}
print(f"\n=== 总结 ===")
print(f"总策略类数量: {len(all_classes)}")
print(f"所有策略类: {list(all_classes.keys())}")
print(f"包含DynamicHedgedRebateGridStrategy: {'DynamicHedgedRebateGridStrategy' in all_classes}")
