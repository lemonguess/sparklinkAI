#!/usr/bin/env python3
"""数据库重置脚本

删除所有表并重新创建，同时添加默认用户
"""

import sys
import os
from datetime import datetime, timezone

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from core.config import settings
from core.database import Base
from models.database import User
from services.vector_service import VectorService

def reset_milvus():
    """重置Milvus集合"""
    print("开始重置Milvus集合...")
    
    try:
        vector_service = VectorService()
        
        # 连接到Milvus
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # 连接
        connected = loop.run_until_complete(vector_service.connect())
        if not connected:
            print("无法连接到Milvus，跳过集合重置")
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
        
        # 重新创建集合
        print("正在创建新的Milvus集合...")
        result = loop.run_until_complete(vector_service.create_collection(collection_name))
        if result:
            print("Milvus集合已创建")
        else:
            print("Milvus集合创建失败")
        
        loop.close()
        
    except Exception as e:
        print(f"Milvus重置失败: {e}")
        # 不抛出异常，允许继续执行

def reset_database():
    """重置数据库：删除所有表并重新创建"""
    print("开始重置数据库...")
    
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
        
        # 重新创建所有表
        print("正在创建所有表...")
        Base.metadata.create_all(bind=engine)
        print("所有表已创建")
        
        return engine
        
    except Exception as e:
        print(f"数据库重置失败: {e}")
        raise

def create_default_user(engine):
    """创建默认用户"""
    print("正在创建默认用户...")
    
    # 创建会话
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        # 检查默认用户是否已存在
        existing_user = db.query(User).filter(User.username == settings.default_username).first()
        if existing_user:
            print(f"默认用户 '{settings.default_username}' 已存在，跳过创建")
            return existing_user
        
        # 创建默认用户
        default_user = User(
            id=settings.default_user_id,
            username=settings.default_username,
            email=settings.default_email,
            is_active=settings.default_user_active,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        db.add(default_user)
        db.commit()
        
        print(f"默认用户创建成功:")
        print(f"  ID: {settings.default_user_id}")
        print(f"  用户名: {settings.default_username}")
        print(f"  邮箱: {settings.default_email}")
        print(f"  激活状态: {settings.default_user_active}")
        
        return default_user
        
    except Exception as e:
        db.rollback()
        print(f"创建默认用户失败: {e}")
        raise
    finally:
        db.close()

def main():
    """主函数"""
    try:
        print("=" * 50)
        print("SparkLinkAI 数据库重置工具")
        print("=" * 50)
        
        # 确认操作
        confirm = input("警告：此操作将删除所有数据！是否继续？(y/N): ")
        if confirm.lower() != 'y':
            print("操作已取消")
            return
        
        # 重置数据库
        engine = reset_database()
        
        # 重置Milvus集合
        reset_milvus()
        
        # 创建默认用户
        create_default_user(engine)
        
        print("\n" + "=" * 50)
        print("数据库重置完成！")
        print("=" * 50)
        
    except Exception as e:
        print(f"\n操作失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()