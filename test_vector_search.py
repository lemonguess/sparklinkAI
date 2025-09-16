#!/usr/bin/env python3
"""
向量检索功能测试脚本
专门测试向量检索和重排序功能
"""

import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.config import settings
from services.vector_service import VectorService
from services.embedding_service import EmbeddingService
from services.rerank_service import RerankService


async def test_vector_search():
    """测试向量检索功能"""
    print("=== 向量检索功能测试 ===")
    
    # 初始化服务
    vector_service = VectorService()
    embedding_service = EmbeddingService()
    rerank_service = RerankService()
    
    try:
        # 测试连接
        print("1. 测试Milvus连接...")
        connected = await vector_service.test_connection()
        if not connected:
            print("❌ Milvus连接失败")
            return
        print("✅ Milvus连接成功")
        
        # 获取集合信息
        print("\n2. 获取集合信息...")
        collection_info = await vector_service.get_collection_info(settings.MILVUS_COLLECTION_NAME)
        if collection_info:
            print(f"✅ 集合信息: {collection_info}")
        else:
            print("❌ 获取集合信息失败")
            return
        
        # 测试查询列表
        test_queries = [
            "贾宝玉的性格特点是什么？",
            "王熙凤有哪些主要事迹？",
            "林黛玉和薛宝钗的关系如何？",
            "大观园的象征意义是什么？",
            "红楼梦的主要主题有哪些？"
        ]
        
        print(f"\n3. 开始向量检索测试...")
        
        for i, query in enumerate(test_queries, 1):
            print(f"\n--- 测试查询 {i} ---")
            print(f"查询: {query}")
            
            try:
                # 生成查询向量
                query_embedding = await embedding_service.generate_embedding(query)
                print(f"✅ 查询向量生成成功，维度: {len(query_embedding)}")
                
                # 向量检索
                search_results = await vector_service.search_vectors(
                    collection_name=settings.MILVUS_COLLECTION_NAME,
                    query_embedding=query_embedding,
                    top_k=5,
                    similarity_threshold=0.3
                )
                
                print(f"📊 向量检索结果数量: {len(search_results)}")
                
                if search_results:
                    # 显示原始检索结果
                    print("\n🔍 原始检索结果:")
                    for j, result in enumerate(search_results[:3], 1):
                        print(f"  结果 {j}:")
                        print(f"    相关性分数: {result.get('score', 0.0):.4f}")
                        print(f"    文档ID: {result.get('doc_id', 'N/A')}")
                        print(f"    块ID: {result.get('chunk_id', 'N/A')}")
                        print(f"    标题: {result.get('title', 'N/A')}")
                        print(f"    内容预览: {result.get('content', '')[:100]}...")
                        print(f"    创建时间: {result.get('create_at', 'N/A')}")
                        print(f"    作者: {result.get('auther_name', 'N/A')}")
                        print()
                    
                    # 准备重排序数据
                    documents_for_rerank = []
                    for result in search_results:
                        documents_for_rerank.append({
                            'content': result.get('content', ''),
                            'score': result.get('score', 0.0),
                            'doc_id': result.get('doc_id'),
                            'chunk_id': result.get('chunk_id'),
                            'title': result.get('title', ''),
                            'source_path': result.get('source_path', ''),
                            'create_at': result.get('create_at', ''),
                            'update_at': result.get('update_at', ''),
                            'type_name': result.get('type_name', ''),
                            'auther_name': result.get('auther_name', ''),
                            'user_id': result.get('user_id', '')
                        })
                    
                    # 重排序
                    try:
                        reranked_results = await rerank_service.rerank(
                            query=query,
                            documents=documents_for_rerank,
                            top_k=3
                        )
                        
                        print(f"🎯 重排序后结果数量: {len(reranked_results)}")
                        
                        # 显示重排序结果
                        print("\n📈 重排序结果:")
                        for j, result in enumerate(reranked_results[:3], 1):
                            print(f"  结果 {j}:")
                            print(f"    重排序分数: {result.get('score', 0.0):.4f}")
                            print(f"    文档ID: {result.get('doc_id', 'N/A')}")
                            print(f"    块ID: {result.get('chunk_id', 'N/A')}")
                            print(f"    标题: {result.get('title', 'N/A')}")
                            print(f"    内容预览: {result.get('content', '')[:100]}...")
                            print()
                            
                    except Exception as rerank_error:
                        print(f"⚠️ 重排序失败: {rerank_error}")
                        print("使用原始检索结果")
                        
                else:
                    print("❌ 未找到相关结果")
                    
            except Exception as query_error:
                print(f"❌ 查询处理失败: {query_error}")
                continue
        
        print("\n=== 测试完成 ===")
        
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_vector_search())