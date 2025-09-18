#!/usr/bin/env python3
"""数据库清理脚本

删除所有表和Milvus集合，不重新创建
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from core.config import settings
from core.database import Base
from services.vector_service import VectorService

def clean_milvus():
    """删除Milvus集合"""
    print("开始删除Milvus集合...")
    
    try:
        vector_service = VectorService()
        
        # 连接到Milvus
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # 连接
        connected = loop.run_until_complete(vector_service.connect())
        if not connected:
            print("无法连接到Milvus，跳过集合删除")
            return
        
        # 删除现有集合
        collection_name = settings.MILVUS_COLLECTION_NAME
        try:
            print(f"正在删除集合: {collection_name}")
            result = loop.run_until_complete(vector_service.drop_collection(collection_name))
            if result:
                print("Milvus集合已删除")
            else:
                print("Milvus集合删除失败或不存在")
        except Exception as e:
            print(f"删除集合时出错: {e}")
        
        loop.close()
        
    except Exception as e:
        print(f"Milvus删除失败: {e}")
        # 不抛出异常，允许继续执行

def clean_database():
    """删除数据库所有表"""
    print("开始删除数据库表...")
    
    # 创建数据库引擎
    engine = create_engine(settings.database_url, echo=True)
    
    try:
        # 禁用外键检查
        print("正在禁用外键检查...")
        with engine.connect() as conn:
            conn.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
            conn.commit()
        
        # 删除所有表
        print("正在删除所有表...")
        Base.metadata.drop_all(bind=engine)
        print("所有表已删除")
        
        # 启用外键检查
        print("正在启用外键检查...")
        with engine.connect() as conn:
            conn.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
            conn.commit()
        
    except Exception as e:
        print(f"数据库删除失败: {e}")
        raise

def main():
    """主函数"""
    try:
        print("=" * 50)
        print("SparkLinkAI 数据库清理工具")
        print("=" * 50)
        
        # 确认操作
        confirm = input("警告：此操作将删除所有数据！是否继续？(y/N): ")
        if confirm.lower() != 'y':
            print("操作已取消")
            return
        
        # 删除数据库表
        clean_database()
        
        # 删除Milvus集合
        clean_milvus()
        
        print("\n" + "=" * 50)
        print("数据库清理完成！")
        print("=" * 50)
        
    except Exception as e:
        print(f"\n操作失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()