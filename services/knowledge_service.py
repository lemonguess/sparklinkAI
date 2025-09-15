"""知识库服务"""
import logging
from typing import List, Dict, Any, Optional
import asyncio

from services.embedding_service import EmbeddingService
from services.vector_service import VectorService
from core.config import settings
from core.database import get_db
from models.database import DocumentChunk, Document

logger = logging.getLogger(__name__)

class KnowledgeService:
    """知识库服务类"""
    
    def __init__(self):
        self.embedding_service = EmbeddingService()
        self.vector_service = VectorService()
        self.default_collection = "sparklinkai_knowledge"
    
    async def search(
        self,
        query: str,
        top_k: int = 10,
        similarity_threshold: float = 0.7,
        collection_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """搜索知识库"""
        try:
            if not query or not query.strip():
                return []
            
            collection_name = collection_name or self.default_collection
            
            # 生成查询向量
            query_embedding = await self.embedding_service.generate_embedding(query)
            
            # 向量搜索
            vector_results = await self.vector_service.search_vectors(
                collection_name=collection_name,
                query_embedding=query_embedding,
                top_k=top_k,
                similarity_threshold=similarity_threshold
            )
            
            # 增强结果信息
            enhanced_results = await self._enhance_search_results(vector_results)
            
            logger.info(f"知识库搜索完成: 查询='{query}', 结果数={len(enhanced_results)}")
            
            return enhanced_results
            
        except Exception as e:
            logger.error(f"知识库搜索失败: {e}")
            return []
    
    def search_sync(
        self,
        query: str,
        top_k: int = 10,
        similarity_threshold: float = 0.7,
        collection_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """搜索知识库（同步版本）"""
        try:
            if not query or not query.strip():
                return []
            
            collection_name = collection_name or self.default_collection
            
            # 生成查询向量
            query_embedding = self.embedding_service.generate_embedding_sync(query)
            
            # 向量搜索
            vector_results = self.vector_service.search_vectors_sync(
                collection_name=collection_name,
                query_embedding=query_embedding,
                top_k=top_k,
                similarity_threshold=similarity_threshold
            )
            
            # 增强结果信息（同步版本）
            enhanced_results = self._enhance_search_results_sync(vector_results)
            
            logger.info(f"知识库搜索完成: 查询='{query}', 结果数={len(enhanced_results)}")
            
            return enhanced_results
            
        except Exception as e:
            logger.error(f"知识库搜索失败: {e}")
            return []
    
    async def _enhance_search_results(
        self,
        vector_results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """增强搜索结果信息"""
        if not vector_results:
            return []
        
        try:
            # 获取数据库会话
            from core.database import SessionLocal
            db = SessionLocal()
            
            enhanced_results = []
            
            for result in vector_results:
                chunk_id = result.get("chunk_id")
                
                if chunk_id:
                    # 从数据库获取完整的分块信息
                    chunk = db.query(DocumentChunk).filter(
                        DocumentChunk.id == chunk_id
                    ).first()
                    
                    if chunk:
                        # 获取文档信息
                        document = db.query(Document).filter(
                            Document.id == chunk.document_id
                        ).first()
                        
                        enhanced_result = {
                            "id": result["id"],
                            "score": result["score"],
                            "content": chunk.content,
                            "chunk_id": chunk_id,
                            "chunk_index": chunk.chunk_index,
                            "document_id": chunk.document_id,
                            "document_name": document.original_filename if document else "未知文档",
                            "document_type": document.file_type if document else "unknown",
                            "source": "knowledge_base",
                            "metadata": result.get("metadata", {})
                        }
                        
                        enhanced_results.append(enhanced_result)
                else:
                    # 如果没有chunk_id，使用原始结果
                    enhanced_results.append(result)
            
            db.close()
            return enhanced_results
            
        except Exception as e:
            logger.error(f"增强搜索结果失败: {e}")
            return vector_results
    
    def _enhance_search_results_sync(
        self,
        vector_results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """增强搜索结果信息（同步版本）"""
        if not vector_results:
            return []
        
        try:
            # 获取数据库会话
            from core.database import SessionLocal
            db = SessionLocal()
            
            enhanced_results = []
            
            for result in vector_results:
                chunk_id = result.get("chunk_id")
                
                if chunk_id:
                    # 从数据库获取完整的分块信息
                    chunk = db.query(DocumentChunk).filter(
                        DocumentChunk.id == chunk_id
                    ).first()
                    
                    if chunk:
                        # 获取文档信息
                        document = db.query(Document).filter(
                            Document.id == chunk.document_id
                        ).first()
                        
                        enhanced_result = {
                            "id": result["id"],
                            "score": result["score"],
                            "content": chunk.content,
                            "chunk_id": chunk_id,
                            "chunk_index": chunk.chunk_index,
                            "document_id": chunk.document_id,
                            "document_name": document.original_filename if document else "未知文档",
                            "document_type": document.file_type if document else "unknown",
                            "source": "knowledge_base",
                            "metadata": result.get("metadata", {})
                        }
                        
                        enhanced_results.append(enhanced_result)
                else:
                    # 如果没有chunk_id，使用原始结果
                    enhanced_results.append(result)
            
            db.close()
            return enhanced_results
            
        except Exception as e:
            logger.error(f"增强搜索结果失败: {e}")
            return vector_results
    
    async def add_document_to_knowledge_base(
        self,
        document_id: int,
        collection_name: Optional[str] = None
    ) -> bool:
        """将文档添加到知识库"""
        try:
            collection_name = collection_name or self.default_collection
            
            # 确保集合存在
            await self.vector_service.create_collection(collection_name)
            
            # 获取文档的所有分块
            from core.database import SessionLocal
            db = SessionLocal()
            
            chunks = db.query(DocumentChunk).filter(
                DocumentChunk.document_id == document_id
            ).all()
            
            if not chunks:
                logger.warning(f"文档 {document_id} 没有分块数据")
                db.close()
                return False
            
            success_count = 0
            
            for chunk in chunks:
                try:
                    # 生成嵌入向量
                    embedding = await self.embedding_service.generate_embedding(
                        chunk.content
                    )
                    
                    # 准备元数据
                    metadata = {
                        "chunk_id": chunk.id,
                        "document_id": chunk.document_id,
                        "chunk_index": chunk.chunk_index,
                        "content_preview": chunk.content[:200],
                        "embedding_model": chunk.embedding_model or settings.embedding_model
                    }
                    
                    # 插入向量
                    vector_id = f"chunk_{chunk.id}"
                    success = await self.vector_service.insert_vector(
                        collection_name=collection_name,
                        vector_id=vector_id,
                        embedding=embedding,
                        metadata=metadata
                    )
                    
                    if success:
                        # 更新分块记录
                        chunk.vector_id = vector_id
                        success_count += 1
                    
                except Exception as e:
                    logger.error(f"处理分块 {chunk.id} 失败: {e}")
            
            db.commit()
            db.close()
            
            logger.info(f"文档 {document_id} 添加到知识库完成: {success_count}/{len(chunks)} 个分块成功")
            
            return success_count > 0
            
        except Exception as e:
            logger.error(f"添加文档到知识库失败: {e}")
            return False
    
    async def remove_document_from_knowledge_base(
        self,
        document_id: int,
        collection_name: Optional[str] = None
    ) -> bool:
        """从知识库中移除文档"""
        try:
            collection_name = collection_name or self.default_collection
            
            # 获取文档的所有分块
            from core.database import SessionLocal
            db = SessionLocal()
            
            chunks = db.query(DocumentChunk).filter(
                DocumentChunk.document_id == document_id,
                DocumentChunk.vector_id.isnot(None)
            ).all()
            
            if not chunks:
                logger.warning(f"文档 {document_id} 没有向量数据")
                db.close()
                return True
            
            # 收集向量ID
            vector_ids = [chunk.vector_id for chunk in chunks if chunk.vector_id]
            
            if vector_ids:
                # 从向量数据库删除
                success = await self.vector_service.delete_vectors(
                    collection_name=collection_name,
                    vector_ids=vector_ids
                )
                
                if success:
                    # 清空数据库中的向量ID
                    for chunk in chunks:
                        chunk.vector_id = None
                    
                    db.commit()
            
            db.close()
            
            logger.info(f"文档 {document_id} 从知识库移除完成")
            
            return True
            
        except Exception as e:
            logger.error(f"从知识库移除文档失败: {e}")
            return False
    
    async def delete_document_vectors(self, document_id: int) -> bool:
        """删除文档的向量数据"""
        return await self.remove_document_from_knowledge_base(document_id)
    
    async def create_collection(self, collection_name: str) -> bool:
        """创建知识库集合"""
        return await self.vector_service.create_collection(collection_name)
    
    async def drop_collection(self, collection_name: str) -> bool:
        """删除知识库集合"""
        return await self.vector_service.drop_collection(collection_name)
    
    async def get_knowledge_base_stats(
        self,
        collection_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """获取知识库统计信息"""
        try:
            collection_name = collection_name or self.default_collection
            
            # 获取向量数据库统计
            vector_info = await self.vector_service.get_collection_info(collection_name)
            
            # 获取数据库统计
            from core.database import SessionLocal
            db = SessionLocal()
            
            total_documents = db.query(Document).count()
            processed_documents = db.query(Document).filter(
                Document.status == "completed"
            ).count()
            
            total_chunks = db.query(DocumentChunk).count()
            vectorized_chunks = db.query(DocumentChunk).filter(
                DocumentChunk.vector_id.isnot(None)
            ).count()
            
            db.close()
            
            stats = {
                "collection_name": collection_name,
                "vector_database": vector_info,
                "documents": {
                    "total": total_documents,
                    "processed": processed_documents,
                    "processing_rate": (processed_documents / total_documents * 100) if total_documents > 0 else 0
                },
                "chunks": {
                    "total": total_chunks,
                    "vectorized": vectorized_chunks,
                    "vectorization_rate": (vectorized_chunks / total_chunks * 100) if total_chunks > 0 else 0
                }
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"获取知识库统计失败: {e}")
            return {}
    
    async def test_knowledge_base(self) -> Dict[str, Any]:
        """测试知识库功能"""
        try:
            # 测试嵌入服务
            embedding_ok = await self.embedding_service.test_connection()
            
            # 测试向量数据库
            vector_ok = await self.vector_service.test_connection()
            
            # 测试搜索功能
            search_ok = False
            try:
                results = await self.search("测试查询", top_k=1)
                search_ok = True
            except Exception as e:
                logger.warning(f"搜索测试失败: {e}")
            
            return {
                "embedding_service": embedding_ok,
                "vector_database": vector_ok,
                "search_function": search_ok,
                "overall_status": embedding_ok and vector_ok
            }
            
        except Exception as e:
            logger.error(f"知识库测试失败: {e}")
            return {
                "embedding_service": False,
                "vector_database": False,
                "search_function": False,
                "overall_status": False,
                "error": str(e)
            }