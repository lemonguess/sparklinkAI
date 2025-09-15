"""向量数据库服务"""
import logging
from typing import List, Dict, Any, Optional, Tuple
import uuid
import json

# Milvus相关导入（如果没有安装会在运行时提示）
try:
    from pymilvus import (
        connections, Collection, CollectionSchema, FieldSchema, DataType,
        utility, MilvusException
    )
    MILVUS_AVAILABLE = True
except ImportError:
    MILVUS_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("Milvus客户端未安装，向量功能将受限")

from core.config import settings

logger = logging.getLogger(__name__)

class VectorService:
    """向量数据库服务类"""
    
    def __init__(self):
        self.host = settings.MILVUS_HOST
        self.port = settings.MILVUS_PORT
        self.user = settings.MILVUS_USER
        self.password = settings.MILVUS_PASSWORD
        self.default_collection = "sparklinkai_knowledge"
        self.dimension = 1024  # 默认向量维度，应该根据嵌入模型调整
        
        self._connected = False
        self._collections = {}
    
    async def connect(self) -> bool:
        """连接到Milvus"""
        if not MILVUS_AVAILABLE:
            logger.error("Milvus客户端未安装")
            return False
        
        try:
            # 连接配置
            connect_params = {
                "host": self.host,
                "port": self.port
            }
            
            if self.user and self.password:
                connect_params.update({
                    "user": self.user,
                    "password": self.password
                })
            
            # 建立连接
            connections.connect(
                alias="default",
                **connect_params
            )
            
            self._connected = True
            logger.info(f"Milvus连接成功: {self.host}:{self.port}")
            
            return True
            
        except Exception as e:
            logger.error(f"Milvus连接失败: {e}")
            self._connected = False
            return False
    
    def connect_sync(self) -> bool:
        """同步连接到Milvus"""
        if not MILVUS_AVAILABLE:
            logger.error("Milvus客户端未安装")
            return False
        
        try:
            # 连接配置
            connect_params = {
                "host": self.host,
                "port": self.port
            }
            
            if self.user and self.password:
                connect_params.update({
                    "user": self.user,
                    "password": self.password
                })
            
            # 建立连接
            connections.connect(
                alias="default",
                **connect_params
            )
            
            self._connected = True
            logger.info(f"Milvus连接成功: {self.host}:{self.port}")
            
            return True
            
        except Exception as e:
            logger.error(f"Milvus连接失败: {e}")
            self._connected = False
            return False
    
    async def create_collection(
        self,
        collection_name: str,
        dimension: int = None,
        description: str = ""
    ) -> bool:
        """创建集合"""
        if not self._connected:
            await self.connect()
        
        if not MILVUS_AVAILABLE or not self._connected:
            logger.error("Milvus未连接")
            return False
        
        try:
            dimension = dimension or self.dimension
            
            # 检查集合是否已存在
            if utility.has_collection(collection_name):
                logger.info(f"集合已存在: {collection_name}")
                return True
            
            # 定义字段
            fields = [
                FieldSchema(
                    name="id",
                    dtype=DataType.VARCHAR,
                    max_length=100,
                    is_primary=True,
                    auto_id=False
                ),
                FieldSchema(
                    name="embedding",
                    dtype=DataType.FLOAT_VECTOR,
                    dim=dimension
                ),
                FieldSchema(
                    name="chunk_id",
                    dtype=DataType.INT64
                ),
                FieldSchema(
                    name="document_id",
                    dtype=DataType.INT64
                ),
                FieldSchema(
                    name="content",
                    dtype=DataType.VARCHAR,
                    max_length=2000
                ),
                FieldSchema(
                    name="metadata",
                    dtype=DataType.VARCHAR,
                    max_length=1000
                )
            ]
            
            # 创建集合schema
            schema = CollectionSchema(
                fields=fields,
                description=description or f"SparkLink AI知识库集合: {collection_name}"
            )
            
            # 创建集合
            collection = Collection(
                name=collection_name,
                schema=schema
            )
            
            # 创建索引
            index_params = {
                "metric_type": "IP",  # 内积（适合归一化向量）
                "index_type": "IVF_FLAT",
                "params": {"nlist": 1024}
            }
            
            collection.create_index(
                field_name="embedding",
                index_params=index_params
            )
            
            # 加载集合
            collection.load()
            
            self._collections[collection_name] = collection
            
            logger.info(f"集合创建成功: {collection_name}, 维度: {dimension}")
            
            return True
            
        except Exception as e:
            logger.error(f"创建集合失败: {e}")
            return False
    
    async def insert_vector(
        self,
        collection_name: str,
        vector_id: str,
        embedding: List[float],
        metadata: Dict[str, Any]
    ) -> bool:
        """插入向量"""
        return self.insert_vector_sync(collection_name, vector_id, embedding, metadata)
    
    def insert_vector_sync(
        self,
        collection_name: str,
        vector_id: str,
        embedding: List[float],
        metadata: Dict[str, Any]
    ) -> bool:
        """插入向量（同步）"""
        if not self._connected:
            self.connect_sync()
        
        if not MILVUS_AVAILABLE or not self._connected:
            logger.error("Milvus未连接")
            return False
        
        try:
            # 获取或创建集合
            if collection_name not in self._collections:
                if not utility.has_collection(collection_name):
                    # 集合不存在，创建它
                    import asyncio
                    asyncio.create_task(self.create_collection(collection_name))
                    return False
                
                collection = Collection(collection_name)
                self._collections[collection_name] = collection
            else:
                collection = self._collections[collection_name]
            
            # 准备数据
            data = [
                [vector_id],  # id
                [embedding],  # embedding
                [metadata.get("chunk_id", 0)],  # chunk_id
                [metadata.get("document_id", 0)],  # document_id
                [metadata.get("content_preview", "")[:2000]],  # content (截断)
                [json.dumps(metadata, ensure_ascii=False)[:1000]]  # metadata (截断)
            ]
            
            # 插入数据
            mr = collection.insert(data)
            
            # 刷新以确保数据持久化
            collection.flush()
            
            logger.debug(f"向量插入成功: {collection_name}, ID: {vector_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"插入向量失败: {e}")
            return False
    
    async def search_vectors(
        self,
        collection_name: str,
        query_embedding: List[float],
        top_k: int = 10,
        similarity_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """搜索向量"""
        return self.search_vectors_sync(collection_name, query_embedding, top_k, similarity_threshold)
    
    def search_vectors_sync(
        self,
        collection_name: str,
        query_embedding: List[float],
        top_k: int = 10,
        similarity_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """搜索向量（同步）"""
        if not self._connected:
            self.connect_sync()
        
        if not MILVUS_AVAILABLE or not self._connected:
            logger.error("Milvus未连接")
            return []
        
        try:
            # 获取集合
            if collection_name not in self._collections:
                if not utility.has_collection(collection_name):
                    logger.warning(f"集合不存在: {collection_name}")
                    return []
                
                collection = Collection(collection_name)
                collection.load()
                self._collections[collection_name] = collection
            else:
                collection = self._collections[collection_name]
            
            # 搜索参数
            search_params = {
                "metric_type": "IP",
                "params": {"nprobe": 10}
            }
            
            # 执行搜索
            results = collection.search(
                data=[query_embedding],
                anns_field="embedding",
                param=search_params,
                limit=top_k,
                output_fields=["chunk_id", "document_id", "content", "metadata"]
            )
            
            # 处理结果
            search_results = []
            
            for hits in results:
                for hit in hits:
                    score = float(hit.score)
                    
                    # 过滤低相似度结果
                    if score < similarity_threshold:
                        continue
                    
                    # 解析元数据
                    try:
                        metadata = json.loads(hit.entity.get("metadata", "{}"))
                    except:
                        metadata = {}
                    
                    result = {
                        "id": hit.id,
                        "score": score,
                        "chunk_id": hit.entity.get("chunk_id"),
                        "document_id": hit.entity.get("document_id"),
                        "content": hit.entity.get("content", ""),
                        "metadata": metadata
                    }
                    
                    search_results.append(result)
            
            # 按相似度排序
            search_results.sort(key=lambda x: x["score"], reverse=True)
            
            logger.debug(f"向量搜索完成: {collection_name}, 找到 {len(search_results)} 个结果")
            
            return search_results
            
        except Exception as e:
            logger.error(f"向量搜索失败: {e}")
            return []
    
    async def delete_vectors(
        self,
        collection_name: str,
        vector_ids: List[str]
    ) -> bool:
        """删除向量"""
        if not self._connected:
            await self.connect()
        
        if not MILVUS_AVAILABLE or not self._connected:
            logger.error("Milvus未连接")
            return False
        
        try:
            # 获取集合
            if collection_name not in self._collections:
                if not utility.has_collection(collection_name):
                    logger.warning(f"集合不存在: {collection_name}")
                    return False
                
                collection = Collection(collection_name)
                self._collections[collection_name] = collection
            else:
                collection = self._collections[collection_name]
            
            # 构建删除表达式
            id_list = "', '".join(vector_ids)
            expr = f"id in ['{id_list}']"
            
            # 执行删除
            collection.delete(expr)
            
            # 刷新
            collection.flush()
            
            logger.info(f"删除向量成功: {collection_name}, 数量: {len(vector_ids)}")
            
            return True
            
        except Exception as e:
            logger.error(f"删除向量失败: {e}")
            return False
    
    async def drop_collection(self, collection_name: str) -> bool:
        """删除集合"""
        if not self._connected:
            await self.connect()
        
        if not MILVUS_AVAILABLE or not self._connected:
            logger.error("Milvus未连接")
            return False
        
        try:
            if utility.has_collection(collection_name):
                utility.drop_collection(collection_name)
                
                # 从缓存中移除
                if collection_name in self._collections:
                    del self._collections[collection_name]
                
                logger.info(f"集合删除成功: {collection_name}")
                return True
            else:
                logger.warning(f"集合不存在: {collection_name}")
                return True
                
        except Exception as e:
            logger.error(f"删除集合失败: {e}")
            return False
    
    async def get_collection_info(self, collection_name: str) -> Dict[str, Any]:
        """获取集合信息"""
        if not self._connected:
            await self.connect()
        
        if not MILVUS_AVAILABLE or not self._connected:
            logger.error("Milvus未连接")
            return {}
        
        try:
            if not utility.has_collection(collection_name):
                return {"exists": False}
            
            collection = Collection(collection_name)
            
            # 获取统计信息
            stats = collection.get_stats()
            
            info = {
                "exists": True,
                "name": collection_name,
                "description": collection.description,
                "num_entities": collection.num_entities,
                "stats": stats
            }
            
            return info
            
        except Exception as e:
            logger.error(f"获取集合信息失败: {e}")
            return {"exists": False, "error": str(e)}
    
    async def test_connection(self) -> bool:
        """测试连接"""
        try:
            if not self._connected:
                success = await self.connect()
                if not success:
                    return False
            
            # 尝试列出集合
            collections = utility.list_collections()
            logger.info(f"Milvus连接测试成功，找到 {len(collections)} 个集合")
            
            return True
            
        except Exception as e:
            logger.error(f"Milvus连接测试失败: {e}")
            return False
    
    def test_connection_sync(self) -> bool:
        """同步测试连接"""
        try:
            if not self._connected:
                success = self.connect_sync()
                if not success:
                    return False
            
            # 尝试列出集合
            collections = utility.list_collections()
            logger.info(f"Milvus连接测试成功，找到 {len(collections)} 个集合")
            
            return True
            
        except Exception as e:
            logger.error(f"Milvus连接测试失败: {e}")
            return False
    
    def get_connection_info(self) -> Dict[str, Any]:
        """获取连接信息"""
        return {
            "host": self.host,
            "port": self.port,
            "connected": self._connected,
            "available": MILVUS_AVAILABLE,
            "default_collection": self.default_collection,
            "dimension": self.dimension
        }