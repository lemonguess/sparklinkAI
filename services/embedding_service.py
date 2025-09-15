"""嵌入向量服务"""
import logging
from typing import List, Dict, Any, Optional
import asyncio
import httpx
import numpy as np

from core.config import settings

logger = logging.getLogger(__name__)

class EmbeddingService:
    """嵌入向量服务类"""
    
    def __init__(self):
        self.api_key = settings.SILICONFLOW_API_KEY
        self.base_url = settings.SILICONFLOW_BASE_URL
        self.default_model = settings.embedding_model
        
        # HTTP客户端配置
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
        )
        
        # 同步客户端
        self.sync_client = httpx.Client(
            timeout=30.0,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
        )
    
    async def generate_embedding(
        self,
        text: str,
        model: Optional[str] = None
    ) -> List[float]:
        """生成文本的嵌入向量（异步）"""
        try:
            if not text or not text.strip():
                raise ValueError("文本内容不能为空")
            
            model = model or self.default_model
            
            # 准备请求数据
            data = {
                "model": model,
                "input": text.strip(),
                "encoding_format": "float"
            }
            
            # 调用API
            response = await self.client.post(
                f"{self.base_url}/embeddings",
                json=data
            )
            
            if response.status_code != 200:
                error_msg = f"嵌入API调用失败: {response.status_code} - {response.text}"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            result = response.json()
            
            # 提取嵌入向量
            if "data" not in result or not result["data"]:
                raise Exception("API返回数据格式错误")
            
            embedding = result["data"][0]["embedding"]
            
            logger.debug(f"生成嵌入向量成功: 模型={model}, 维度={len(embedding)}")
            
            return embedding
            
        except Exception as e:
            logger.error(f"生成嵌入向量失败: {e}")
            raise
    
    def generate_embedding_sync(
        self,
        text: str,
        model: Optional[str] = None
    ) -> List[float]:
        """生成文本的嵌入向量（同步）"""
        try:
            if not text or not text.strip():
                raise ValueError("文本内容不能为空")
            
            model = model or self.default_model
            
            # 准备请求数据
            data = {
                "model": model,
                "input": text.strip(),
                "encoding_format": "float"
            }
            
            # 调用API
            response = self.sync_client.post(
                f"{self.base_url}/embeddings",
                json=data
            )
            
            if response.status_code != 200:
                error_msg = f"嵌入API调用失败: {response.status_code} - {response.text}"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            result = response.json()
            
            # 提取嵌入向量
            if "data" not in result or not result["data"]:
                raise Exception("API返回数据格式错误")
            
            embedding = result["data"][0]["embedding"]
            
            logger.debug(f"生成嵌入向量成功: 模型={model}, 维度={len(embedding)}")
            
            return embedding
            
        except Exception as e:
            logger.error(f"生成嵌入向量失败: {e}")
            raise
    
    async def generate_batch_embeddings(
        self,
        texts: List[str],
        model: Optional[str] = None,
        batch_size: int = 10
    ) -> List[List[float]]:
        """批量生成嵌入向量"""
        try:
            if not texts:
                return []
            
            model = model or self.default_model
            embeddings = []
            
            # 分批处理
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i:i + batch_size]
                
                # 准备批量请求数据
                data = {
                    "model": model,
                    "input": batch_texts,
                    "encoding_format": "float"
                }
                
                # 调用API
                response = await self.client.post(
                    f"{self.base_url}/embeddings",
                    json=data
                )
                
                if response.status_code != 200:
                    error_msg = f"批量嵌入API调用失败: {response.status_code} - {response.text}"
                    logger.error(error_msg)
                    raise Exception(error_msg)
                
                result = response.json()
                
                # 提取嵌入向量
                if "data" not in result:
                    raise Exception("批量API返回数据格式错误")
                
                batch_embeddings = [item["embedding"] for item in result["data"]]
                embeddings.extend(batch_embeddings)
                
                # 避免API限流
                if i + batch_size < len(texts):
                    await asyncio.sleep(0.1)
            
            logger.info(f"批量生成嵌入向量完成: {len(texts)} 个文本, 模型={model}")
            
            return embeddings
            
        except Exception as e:
            logger.error(f"批量生成嵌入向量失败: {e}")
            raise
    
    def calculate_similarity(
        self,
        embedding1: List[float],
        embedding2: List[float],
        method: str = "cosine"
    ) -> float:
        """计算两个向量的相似度"""
        try:
            vec1 = np.array(embedding1)
            vec2 = np.array(embedding2)
            
            if method == "cosine":
                # 余弦相似度
                dot_product = np.dot(vec1, vec2)
                norm1 = np.linalg.norm(vec1)
                norm2 = np.linalg.norm(vec2)
                
                if norm1 == 0 or norm2 == 0:
                    return 0.0
                
                similarity = dot_product / (norm1 * norm2)
                return float(similarity)
            
            elif method == "euclidean":
                # 欧几里得距离（转换为相似度）
                distance = np.linalg.norm(vec1 - vec2)
                similarity = 1 / (1 + distance)
                return float(similarity)
            
            elif method == "dot_product":
                # 点积
                similarity = np.dot(vec1, vec2)
                return float(similarity)
            
            else:
                raise ValueError(f"不支持的相似度计算方法: {method}")
                
        except Exception as e:
            logger.error(f"计算向量相似度失败: {e}")
            raise
    
    def calculate_batch_similarity(
        self,
        query_embedding: List[float],
        embeddings: List[List[float]],
        method: str = "cosine"
    ) -> List[float]:
        """批量计算相似度"""
        try:
            query_vec = np.array(query_embedding)
            embedding_matrix = np.array(embeddings)
            
            if method == "cosine":
                # 批量余弦相似度计算
                dot_products = np.dot(embedding_matrix, query_vec)
                query_norm = np.linalg.norm(query_vec)
                embedding_norms = np.linalg.norm(embedding_matrix, axis=1)
                
                # 避免除零
                norms_product = embedding_norms * query_norm
                norms_product[norms_product == 0] = 1e-8
                
                similarities = dot_products / norms_product
                return similarities.tolist()
            
            elif method == "dot_product":
                # 批量点积
                similarities = np.dot(embedding_matrix, query_vec)
                return similarities.tolist()
            
            else:
                # 逐个计算（较慢但支持更多方法）
                similarities = []
                for embedding in embeddings:
                    sim = self.calculate_similarity(query_embedding, embedding, method)
                    similarities.append(sim)
                return similarities
                
        except Exception as e:
            logger.error(f"批量计算相似度失败: {e}")
            raise
    
    async def test_connection(self) -> bool:
        """测试嵌入服务连接"""
        try:
            test_text = "Hello, world!"
            embedding = await self.generate_embedding(test_text)
            return len(embedding) > 0
        except Exception as e:
            logger.error(f"嵌入服务连接测试失败: {e}")
            return False
    
    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        return {
            "default_model": self.default_model,
            "base_url": self.base_url,
            "api_configured": bool(self.api_key)
        }
    
    async def get_available_models(self) -> List[str]:
        """获取可用的嵌入模型列表"""
        try:
            # 这里应该调用API获取模型列表
            # 暂时返回常用的模型
            return [
                "BAAI/bge-large-zh-v1.5",
                "BAAI/bge-m3",
                "BAAI/bge-small-zh-v1.5",
                "text-embedding-ada-002"
            ]
        except Exception as e:
            logger.error(f"获取可用模型列表失败: {e}")
            return [self.default_model]
    
    def __del__(self):
        """清理资源"""
        try:
            if hasattr(self, 'client'):
                asyncio.create_task(self.client.aclose())
            if hasattr(self, 'sync_client'):
                self.sync_client.close()
        except Exception:
            pass