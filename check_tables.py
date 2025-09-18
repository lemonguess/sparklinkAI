#!/usr/bin/env python3
"""数据库表检查脚本

检查bsh-ai数据库中的所有表
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text, inspect
from core.config import settings

def check_database_tables():
    """检查数据库中的所有表"""
    print("=" * 60)
    print("SparkLinkAI 数据库表检查工具")
    print("=" * 60)
    
    # 创建数据库引擎
    engine = create_engine(settings.database_url, echo=False)
    
    try:
        # 使用inspector检查数据库结构
        inspector = inspect(engine)
        
        # 获取所有表名
        table_names = inspector.get_table_names()
        
        if not table_names:
            print("数据库中没有找到任何表")
            return []
        
        print(f"在数据库 'bsh-ai' 中找到 {len(table_names)} 个表:")
        print("-" * 60)
        
        table_info = []
        
        for i, table_name in enumerate(table_names, 1):
            print(f"{i}. 表名: {table_name}")
            
            # 获取表的列信息
            columns = inspector.get_columns(table_name)
            print(f"   列数: {len(columns)}")
            
            # 获取表中的记录数
            try:
                with engine.connect() as conn:
                    result = conn.execute(text(f"SELECT COUNT(*) FROM `{table_name}`"))
                    row_count = result.scalar()
                    print(f"   记录数: {row_count}")
            except Exception as e:
                print(f"   记录数: 无法获取 ({e})")
                row_count = "未知"
            
            # 显示主要列信息
            print("   主要列:")
            for col in columns[:5]:  # 只显示前5列
                print(f"     - {col['name']} ({col['type']})")
            if len(columns) > 5:
                print(f"     ... 还有 {len(columns) - 5} 列")
            
            table_info.append({
                'name': table_name,
                'columns': len(columns),
                'rows': row_count
            })
            
            print("-" * 60)
        
        return table_info
        
    except Exception as e:
        print(f"检查数据库失败: {e}")
        return []

def main():
    """主函数"""
    try:
        table_info = check_database_tables()
        
        if table_info:
            print("\n" + "=" * 60)
            print("表汇总信息:")
            print("=" * 60)
            for info in table_info:
                print(f"- {info['name']}: {info['columns']} 列, {info['rows']} 行")
            
            print(f"\n总计: {len(table_info)} 个表")
        
    except Exception as e:
        print(f"\n操作失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()