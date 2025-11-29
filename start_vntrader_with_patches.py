#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
启动 VN Trader 并自动应用补丁

此脚本会：
1. 自动应用 CTA 回测引擎补丁
2. 启动 VN Trader GUI
3. 确保自定义策略可用
4. 提供流式回测和内存优化功能
"""

import sys
import os
from pathlib import Path

# === 确保项目根目录加入 PYTHONPATH 及 sys.path ===
root_dir = Path(__file__).resolve().parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))
old_pythonpath = os.environ.get("PYTHONPATH", "")
if str(root_dir) not in old_pythonpath.split(os.pathsep):
    os.environ["PYTHONPATH"] = os.pathsep.join([str(root_dir), old_pythonpath]) if old_pythonpath else str(root_dir)


def main():
    print("=== VN Trader 补丁版启动器 ===")
    
    # 确保当前目录在 Python 路径中
    current_dir = Path.cwd()
    if str(current_dir) not in sys.path:
        sys.path.insert(0, str(current_dir))
    
    # 检查补丁文件
    patch_file = current_dir / "patch_ctabacktester.py"
    if not patch_file.exists():
        print("✗ 未找到补丁文件 patch_ctabacktester.py")
        print("请确保在项目根目录运行此脚本")
        return False
    
    # 导入并应用补丁
    try:
        print("正在应用补丁...")
        import patch_ctabacktester
        print("✓ 补丁应用成功")
    except Exception as e:
        print(f"✗ 补丁应用失败: {e}")
        return False
    
    # 检查策略文件
    strategies_dir = current_dir / "strategies"
    if strategies_dir.exists():
        strategy_files = list(strategies_dir.glob("*.py"))
        strategy_files = [f for f in strategy_files if f.name != "__init__.py"]
        print(f"✓ 发现 {len(strategy_files)} 个自定义策略文件")
        for f in strategy_files:
            print(f"  - {f.name}")
    else:
        print("⚠️ 未找到 strategies 目录")
    
    # 启动 VN Trader
    print("\n正在启动 VN Trader...")
    try:
        from vnpy.event import EventEngine
        from vnpy.trader.engine import MainEngine
        from vnpy.trader.ui import MainWindow, create_qapp
        # 新增：导入并注册CTA策略与CTA回测应用，使“功能/应用”菜单出现“CTA策略回测”
        from vnpy_ctastrategy import CtaStrategyApp
        from vnpy_ctabacktester import CtaBacktesterApp
        
        # 创建应用
        qapp = create_qapp()
        
        # 创建引擎
        event_engine = EventEngine()
        main_engine = MainEngine(event_engine)
        
        # 新增：注册应用
        main_engine.add_app(CtaStrategyApp)
        main_engine.add_app(CtaBacktesterApp)
        
        # 创建主窗口
        main_window = MainWindow(main_engine, event_engine)
        main_window.showMaximized()
        
        print("✓ VN Trader 启动成功")
        print("\n=== 使用说明 ===")
        print("1. 在 '功能' 菜单中选择 'CTA策略回测'")
        print("2. 在策略下拉框中应该能看到 'DynamicHedgedRebateGridStrategy'")
        print("3. 在回测参数表单中会有 '内存优化统计' 复选框")
        print("4. 回测将使用流式模式，避免内存暴涨")
        print("5. 勾选内存优化统计可进一步降低内存占用")
        
        # 运行应用
        qapp.exec()
        
    except Exception as e:
        print(f"✗ VN Trader 启动失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    if not success:
        input("按回车键退出...")
        sys.exit(1)
