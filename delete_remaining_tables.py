#!/usr/bin/env python3
"""删除剩余数据库表脚本

安全删除bsh-ai数据库中的所有剩余表
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text, inspect
from core.config import settings

def get_remaining_tables():
    """获取数据库中剩余的所有表"""
    engine = create_engine(settings.database_url, echo=False)
    inspector = inspect(engine)
    return inspector.get_table_names()

def delete_all_remaining_tables():
    """删除所有剩余的表"""
    print("=" * 60)
    print("SparkLinkAI 剩余表删除工具")
    print("=" * 60)
    
    # 获取所有表
    table_names = get_remaining_tables()
    
    if not table_names:
        print("✅ 数据库中没有找到任何表，无需删除")
        return True
    
    print(f"发现 {len(table_names)} 个表需要删除:")
    for i, table_name in enumerate(table_names, 1):
        print(f"  {i}. {table_name}")
    
    print("\n⚠️  警告：此操作将永久删除以下表及其所有数据：")
    print("-" * 60)
    
    # 创建数据库引擎
    engine = create_engine(settings.database_url, echo=True)
    inspector = inspect(engine)
    
    # 显示每个表的详细信息
    for table_name in table_names:
        print(f"📋 表: {table_name}")
        
        # 获取记录数
        try:
            with engine.connect() as conn:
                result = conn.execute(text(f"SELECT COUNT(*) FROM `{table_name}`"))
                row_count = result.scalar()
                print(f"   📊 记录数: {row_count}")
                
                if row_count > 0:
                    print(f"   ⚠️  包含 {row_count} 条数据，删除后将无法恢复！")
        except Exception as e:
            print(f"   ❌ 无法获取记录数: {e}")
        
        print()
    
    # 最终确认
    print("=" * 60)
    confirm1 = input("❓ 确认要删除以上所有表吗？(输入 'DELETE' 确认): ")
    if confirm1 != 'DELETE':
        print("❌ 操作已取消")
        return False
    
    confirm2 = input("❓ 最后确认：真的要永久删除所有数据吗？(输入 'YES' 确认): ")
    if confirm2 != 'YES':
        print("❌ 操作已取消")
        return False
    
    print("\n🗑️  开始删除表...")
    
    try:
        with engine.connect() as conn:
            # 禁用外键检查
            print("🔧 禁用外键检查...")
            conn.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
            conn.commit()
            
            # 删除每个表
            deleted_count = 0
            for table_name in table_names:
                try:
                    print(f"🗑️  删除表: {table_name}")
                    conn.execute(text(f"DROP TABLE IF EXISTS `{table_name}`"))
                    conn.commit()
                    deleted_count += 1
                    print(f"✅ 表 {table_name} 已删除")
                except Exception as e:
                    print(f"❌ 删除表 {table_name} 失败: {e}")
            
            # 启用外键检查
            print("🔧 启用外键检查...")
            conn.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
            conn.commit()
            
            print(f"\n✅ 成功删除 {deleted_count}/{len(table_names)} 个表")
            
            # 验证删除结果
            remaining_tables = get_remaining_tables()
            if remaining_tables:
                print(f"⚠️  仍有 {len(remaining_tables)} 个表未删除: {remaining_tables}")
                return False
            else:
                print("🎉 所有表已成功删除！")
                return True
                
    except Exception as e:
        print(f"❌ 删除操作失败: {e}")
        return False

def main():
    """主函数"""
    try:
        success = delete_all_remaining_tables()
        
        if success:
            print("\n" + "=" * 60)
            print("🎉 数据库清理完成！")
            print("=" * 60)
        else:
            print("\n" + "=" * 60)
            print("❌ 数据库清理未完全成功，请检查错误信息")
            print("=" * 60)
            sys.exit(1)
        
    except Exception as e:
        print(f"\n❌ 操作失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()