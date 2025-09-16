#!/usr/bin/env python3
"""
测试红楼梦概要.txt文件的嵌入、检索和排序功能
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
from core.database import get_db
from services.vector_service import VectorService
from services.embedding_service import EmbeddingService
from services.rerank_service import RerankService
from services.document_service import DocumentService
from models.database import Document, DocumentChunk


async def test_embedding_process():
    """测试完整的嵌入、检索和排序流程"""
    print("开始测试红楼梦概要.txt的嵌入、检索和排序功能...")
    
    # 初始化服务
    vector_service = VectorService()
    embedding_service = EmbeddingService()
    rerank_service = RerankService()
    document_service = DocumentService()
    
    # 测试Milvus连接
    print("测试Milvus连接...")
    connection_result = await vector_service.test_connection()
    print(f"Milvus连接状态: {connection_result}")
    
    if not connection_result:
        print("Milvus连接失败，跳过向量存储和检索测试")
        return
    
    # 连接到向量数据库
    await vector_service.connect()
    
    # 创建集合（如果不存在）
    collection_created = await vector_service.create_collection(
        collection_name=settings.MILVUS_COLLECTION_NAME,
        dimension=1024  # BGE模型的维度
    )
    print(f"集合创建状态: {collection_created}")
    
    # 获取集合信息
    collection_info = await vector_service.get_collection_info(settings.MILVUS_COLLECTION_NAME)
    print(f"集合信息: {collection_info}")
    
    # 测试文件路径
    test_file_path = "/Users/lixincheng/workspace/sparklinkAI/uploads/红楼梦概要.txt"
    
    if not os.path.exists(test_file_path):
        print(f"测试文件不存在: {test_file_path}")
        return
    
    # 读取文件内容
    with open(test_file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print(f"文件内容长度: {len(content)} 字符")
    
    # 使用默认用户ID
    default_user_id = settings.default_user_id
    print(f"使用默认用户ID: {default_user_id}")
    
    try:
        # 1. 创建文档记录
        db = next(get_db())
        try:
            # 检查是否已存在该文档
            existing_doc = db.query(Document).filter(
                Document.filename == "红楼梦概要.txt",
                Document.user_id == default_user_id
            ).first()
            
            if existing_doc:
                doc_id = existing_doc.id
                print(f"使用已存在的文档记录，doc_id: {doc_id}")
            else:
                # 创建新文档记录
                new_doc = Document(
                    filename="红楼梦概要.txt",
                    original_filename="红楼梦概要.txt",
                    file_path=test_file_path,
                    file_size=len(content.encode('utf-8')),
                    file_type="txt",
                    user_id=default_user_id,
                    status="processed"
                )
                db.add(new_doc)
                db.commit()
                db.refresh(new_doc)
                doc_id = new_doc.id
                print(f"创建新文档记录，doc_id: {doc_id}")
        finally:
            db.close()
        
        # 2. 文档分块
        print("\n开始文档分块...")
        chunk_size = settings.chunk_size
        overlap_size = settings.chunk_overlap
        
        chunks = []
        for i in range(0, len(content), chunk_size - overlap_size):
            chunk_content = content[i:i + chunk_size]
            if chunk_content.strip():
                chunks.append({
                    'content': chunk_content,
                    'start_pos': i,
                    'end_pos': min(i + chunk_size, len(content))
                })
        
        print(f"分块完成，共 {len(chunks)} 个块")
        
        # 3. 生成嵌入向量并存储
        print("\n开始生成嵌入向量...")
        for idx, chunk_data in enumerate(chunks):
            print(f"处理第 {idx + 1}/{len(chunks)} 个块...")
            
            # 生成嵌入向量
            embedding = await embedding_service.generate_embedding(chunk_data['content'])
            
            # 准备元数据
            metadata = {
                'doc_id': str(doc_id),
                'user_id': default_user_id,
                'chunk_index': idx,
                'start_pos': chunk_data['start_pos'],
                'end_pos': chunk_data['end_pos'],
                'file_name': '红楼梦概要.txt'
            }
            
            # 生成向量ID
            vector_id = f"{doc_id}_{idx}"
            
            # 使用简短的时间戳格式
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            
            # 存储到向量数据库
            await vector_service.insert_vector(
                collection_name=settings.MILVUS_COLLECTION_NAME,
                vector_id=vector_id,
                doc_id=str(doc_id),
                title='红楼梦概要.txt',
                source_path=test_file_path,
                chunk_id=idx,
                create_at=timestamp,
                update_at=timestamp,
                content=chunk_data['content'],
                content_vector=embedding,
                type_name='txt',
                auther_name='unknown',
                user_id=default_user_id
            )
            
            # 存储chunk记录到数据库
            db_chunk = next(get_db())
            try:
                chunk_record = DocumentChunk(
                    document_id=doc_id,
                    content=chunk_data['content'],
                    chunk_index=idx,
                    vector_id=vector_id
                )
                db_chunk.add(chunk_record)
                db_chunk.commit()
            finally:
                db_chunk.close()
        
        print("嵌入向量生成和存储完成！")
        
        # 4. 测试检索功能
        print("\n开始测试检索功能...")
        test_queries = [
            "贾宝玉的性格特点",
            "林黛玉和薛宝钗的关系",
            "四大家族的背景",
            "王熙凤的主要事迹"
        ]
        
        for query in test_queries:
            print(f"\n查询: {query}")
            
            # 生成查询向量
            query_embedding = await embedding_service.generate_embedding(query)
            
            # 向量检索
            search_results = await vector_service.search_vectors(
                collection_name=settings.MILVUS_COLLECTION_NAME,
                query_embedding=query_embedding,
                user_id=default_user_id,
                top_k=5,
                similarity_threshold=0.3
            )
            
            print(f"向量检索结果数量: {len(search_results)}")
            
            if search_results:
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
                reranked_results = await rerank_service.rerank(
                    query=query,
                    documents=documents_for_rerank,
                    top_k=3
                )
                
                print(f"重排序后结果数量: {len(reranked_results)}")
                
                # 显示结果
                for i, result in enumerate(reranked_results[:3]):
                    print(f"\n结果 {i+1}:")
                    print(f"相关性分数: {result.get('score', 0.0):.4f}")
                    print(f"内容预览: {result.get('content', '')[:200]}...")
                    print(f"元数据: doc_id={result.get('doc_id')}, chunk_index={result.get('chunk_id')}")
            else:
                print("未找到相关结果")
        
        print("\n测试完成！")
        
    except Exception as e:
        print(f"测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_embedding_process())