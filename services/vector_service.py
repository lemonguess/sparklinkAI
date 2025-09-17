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
            
            # 定义字段（核心字段在前）
            fields = [
                FieldSchema(
                    name="id",
                    dtype=DataType.VARCHAR,
                    max_length=100,
                    is_primary=True,
                    auto_id=False
                ),
                FieldSchema(
                    name="doc_id",
                    dtype=DataType.VARCHAR,
                    max_length=200
                ),
                FieldSchema(
                    name="doc_name",
                    dtype=DataType.VARCHAR,
                    max_length=500
                ),
                FieldSchema(
                    name="chunk_content",
                    dtype=DataType.VARCHAR,
                    max_length=4000
                ),
                FieldSchema(
                    name="vector",
                    dtype=DataType.FLOAT_VECTOR,
                    dim=dimension
                ),
                FieldSchema(
                    name="source_path",
                    dtype=DataType.VARCHAR,
                    max_length=1000
                ),
                FieldSchema(
                    name="doc_type",
                    dtype=DataType.VARCHAR,
                    max_length=50
                ),
                FieldSchema(
                    name="user_id",
                    dtype=DataType.VARCHAR,
                    max_length=50
                ),
                FieldSchema(
                    name="group_id",
                    dtype=DataType.INT64
                ),
                FieldSchema(
                    name="create_at",
                    dtype=DataType.VARCHAR,
                    max_length=20
                ),
                FieldSchema(
                    name="update_at",
                    dtype=DataType.VARCHAR,
                    max_length=20
                ),


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
                field_name="vector",  # 修正字段名
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
        doc_id: str,
        doc_name: str,
        source_path: str,
        create_at: str,
        update_at: str,
        chunk_content: str,
        vector: List[float],
        doc_type: str,
        auther_name: str,
        user_id: str = None
    ) -> bool:
        """插入向量"""
        # 如果没有提供user_id，使用默认值
        if user_id is None:
            user_id = settings.default_user_id
            
        return await self.insert_vector_async(
            collection_name, vector_id, doc_id, doc_name, source_path,
            create_at, update_at, chunk_content, vector, doc_type,
            auther_name, user_id
        )
    
    async def insert_vector_async(
        self,
        collection_name: str,
        vector_id: str,
        doc_id: str,
        doc_name: str,
        source_path: str,
        create_at: str,
        update_at: str,
        chunk_content: str,
        vector: List[float],
        doc_type: str,
        auther_name: str,
        user_id: str
    ) -> bool:
        """插入向量（异步）"""
        if not self._connected:
            await self.connect()
        
        if not MILVUS_AVAILABLE or not self._connected:
            logger.error("Milvus未连接")
            return False
        
        try:
            # 获取或创建集合
            if collection_name not in self._collections:
                if not utility.has_collection(collection_name):
                    # 集合不存在，创建它
                    await self.create_collection(collection_name)
                    if collection_name not in self._collections:
                        return False
                else:
                    collection = Collection(collection_name)
                    self._collections[collection_name] = collection
            
            collection = self._collections[collection_name]
            
            # 检查是否存在相同doc_id的数据，如果存在则先删除
            if doc_id:
                try:
                    # 查询是否存在相同doc_id的数据
                    expr = f'doc_id == "{doc_id}"'
                    existing_results = collection.query(expr=expr, output_fields=["id"])
                    if existing_results:
                        # 删除现有数据
                        existing_ids = [result["id"] for result in existing_results]
                        collection.delete(expr=f'id in {existing_ids}')
                        logger.info(f"删除了 {len(existing_ids)} 条相同doc_id的数据: {doc_id}")
                except Exception as e:
                    logger.warning(f"删除相同doc_id数据时出错: {e}")
            
            # 准备数据（按字段定义顺序）
            data = [
                [vector_id],  # id
                [doc_id],  # doc_id
                [doc_name[:500]],  # doc_name (截断)
                [chunk_content[:4000]],  # chunk_content (截断)
                [vector],  # vector
                [source_path[:1000]],  # source_path (截断)
                [auther_name[:200]],  # auther_name (截断)
                [user_id],  # user_id
                [doc_type[:50]],  # doc_type (截断)
                [create_at],  # create_at
                [update_at]  # update_at
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
        similarity_threshold: float = 0.7,
        user_id: str = None
    ) -> List[Dict[str, Any]]:
        """搜索向量"""
        # 如果没有提供user_id，使用默认值
        if user_id is None:
            user_id = settings.default_user_id
            
        return await self.search_vectors_async(
            collection_name, query_embedding, top_k, similarity_threshold, user_id
        )
    
    async def search_vectors_async(
        self,
        collection_name: str,
        query_embedding: List[float],
        top_k: int = 10,
        similarity_threshold: float = 0.7,
        user_id: str = None,
        group_id: int = None
    ) -> List[Dict[str, Any]]:
        """搜索向量（异步）"""
        if not self._connected:
            await self.connect()
        
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
            
            # 构建过滤表达式
            filter_conditions = []
            if user_id:
                filter_conditions.append(f'user_id == "{user_id}"')
            if group_id is not None:
                filter_conditions.append(f'group_id == {group_id}')
            
            filter_expr = " and ".join(filter_conditions) if filter_conditions else None
            
            # 执行搜索
            results = collection.search(
                data=[query_embedding],
                anns_field="vector",  # 修正字段名
                param=search_params,
                limit=top_k,
                expr=filter_expr,  # 添加用户和分组过滤
                output_fields=["doc_id", "doc_name", "source_path", "create_at", "update_at", "chunk_content", "doc_type", "auther_name", "user_id", "group_id"]
            )
            
            # 处理结果
            search_results = []
            
            for hits in results:
                for hit in hits:
                    score = float(hit.score)
                    
                    # 过滤低相似度结果
                    if score < similarity_threshold:
                        continue
                    
                    result = {
                        "id": hit.id,
                        "score": score,
                        "doc_id": hit.entity.get("doc_id", ""),
                        "title": hit.entity.get("doc_name", ""),  # 修正字段名
                        "source_path": hit.entity.get("source_path", ""),
                        "create_at": hit.entity.get("create_at", ""),
                        "update_at": hit.entity.get("update_at", ""),
                        "content": hit.entity.get("chunk_content", ""),
                        "doc_type": hit.entity.get("doc_type", ""),
                        "auther_name": hit.entity.get("auther_name", ""),
                        "user_id": hit.entity.get("user_id", ""),
                        "group_id": hit.entity.get("group_id", None)
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

    async def delete_vectors_by_doc_id(
        self,
        collection_name: str,
        doc_id: str
    ) -> bool:
        """根据doc_id删除向量"""
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
            expr = f'doc_id == "{doc_id}"'
            
            # 执行删除
            collection.delete(expr)
            
            # 刷新
            collection.flush()
            
            logger.info(f"根据doc_id删除向量成功: {collection_name}, doc_id: {doc_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"根据doc_id删除向量失败: {e}")
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
            
            # 获取统计信息 - 使用num_entities而不是get_stats()
            try:
                num_entities = collection.num_entities
            except Exception as e:
                logger.warning(f"获取实体数量失败: {e}")
                num_entities = 0
            
            info = {
                "exists": True,
                "name": collection_name,
                "description": getattr(collection, 'description', ''),
                "num_entities": num_entities
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