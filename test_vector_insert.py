#!/usr/bin/env python3
"""
测试向量插入功能的简化脚本
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.config import settings
from services.vector_service import VectorService
from services.embedding_service import EmbeddingService

async def test_vector_insert():
    """测试向量插入功能"""
    print("=== 向量插入测试 ===")
    
    # 初始化服务
    vector_service = VectorService()
    embedding_service = EmbeddingService()
    
    try:
        # 1. 测试Milvus连接
        print("1. 测试Milvus连接...")
        connection_result = await vector_service.test_connection()
        print(f"   连接状态: {connection_result}")
        
        if not connection_result:
            print("   ❌ Milvus连接失败")
            return
        
        # 2. 连接到向量数据库
        print("2. 连接到向量数据库...")
        await vector_service.connect()
        
        # 3. 创建集合
        print("3. 创建集合...")
        collection_name = settings.MILVUS_COLLECTION_NAME
        print(f"   集合名称: {collection_name}")
        
        collection_created = await vector_service.create_collection(
            collection_name=collection_name,
            dimension=1024  # BGE模型的维度
        )
        print(f"   创建状态: {collection_created}")
        
        # 4. 获取集合信息
        print("4. 获取集合信息...")
        collection_info = await vector_service.get_collection_info(collection_name)
        print(f"   集合信息: {collection_info}")
        
        # 5. 生成测试嵌入向量
        print("5. 生成测试嵌入向量...")
        test_text = "贾宝玉是《红楼梦》的男主角，性格叛逆，不喜欢读书做官。"
        embedding = await embedding_service.generate_embedding(test_text)
        print(f"   嵌入向量维度: {len(embedding)}")
        print(f"   嵌入向量前5个值: {embedding[:5]}")
        
        # 6. 插入测试向量
        print("6. 插入测试向量...")
        vector_id = "test_001"
        doc_id = "test_doc_001"
        
        # 使用简短的时间戳格式
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        
        insert_result = await vector_service.insert_vector(
            collection_name=collection_name,
            vector_id=vector_id,
            doc_id=doc_id,
            title="测试文档",
            source_path="/test/path",
            chunk_id=0,
            create_at=timestamp,
            update_at=timestamp,
            content=test_text,
            content_vector=embedding,
            type_name="txt",
            auther_name="test",
            user_id=settings.default_user_id
        )
        print(f"   插入结果: {insert_result}")
        
        if insert_result:
            print("   ✅ 向量插入成功")
            
            # 7. 验证数据是否真的插入了
            print("7. 验证数据插入...")
            
            # 等待一下确保数据已经持久化
            await asyncio.sleep(2)
            
            # 尝试搜索刚插入的数据
            search_results = await vector_service.search_vectors(
                collection_name=collection_name,
                query_embedding=embedding,
                top_k=1,
                similarity_threshold=0.1  # 降低阈值确保能找到
            )
            
            print(f"   搜索结果数量: {len(search_results)}")
            if search_results:
                print("   ✅ 数据验证成功，向量已正确插入")
                for i, result in enumerate(search_results):
                    print(f"   结果 {i+1}: ID={result.get('id', 'N/A')}, 相似度={result.get('score', 'N/A')}")
            else:
                print("   ❌ 数据验证失败，未找到插入的向量")
        else:
            print("   ❌ 向量插入失败")
            
    except Exception as e:
        print(f"测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_vector_insert())