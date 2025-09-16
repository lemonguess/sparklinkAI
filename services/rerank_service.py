"""重排序服务"""
import logging
import httpx
from typing import List, Dict, Any, Tuple
import os

from core.config import settings

logger = logging.getLogger(__name__)

class RerankService:
    """重排序服务类"""
    
    def __init__(self):
        self.api_key = settings.SILICONFLOW_API_KEY
        self.base_url = settings.SILICONFLOW_BASE_URL
        self.model_name = settings.rerank_model
        self.rerank_top_k = settings.config.getint('knowledge_base', 'rerank_top_k', fallback=5)
        
        logger.info(f"重排序配置加载成功: 模型={self.model_name}, top_k={self.rerank_top_k}, API可用={'是' if self.api_key else '否'}")
        
    def _load_config(self):
        """加载配置 - 已废弃，现在使用环境变量"""
        pass
    
    async def _call_rerank_api(self, query: str, documents: List[str]) -> List[float]:
        """调用重排序API"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/rerank",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model_name,
                        "query": query,
                        "documents": documents,
                        "top_n": len(documents),  # 修正参数名：top_k -> top_n
                        "return_documents": True  # 添加必要参数
                    },
                    timeout=30.0
                )
                response.raise_for_status()
                result = response.json()
                
                # 根据API文档修正分数提取逻辑
                scores = []
                for item in result["results"]:
                    # API返回的是relevance_score字段
                    scores.append(item.get("relevance_score", 0.0))
                return scores
                
        except Exception as e:
            logger.error(f"调用重排序API失败: {e}")
            return [0.0] * len(documents)
    
    async def rerank(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        top_k: int = None
    ) -> List[Dict[str, Any]]:
        """重排序文档
        
        Args:
            query: 查询文本
            documents: 文档列表，每个文档应包含content字段
            top_k: 返回的文档数量，默认使用配置中的值
            
        Returns:
            重排序后的文档列表，按相关性降序排列
        """
        if not documents:
            return []
            
        if not self.api_key:
            logger.warning("API密钥未配置，返回原始结果")
            return documents
            
        try:
            top_k = top_k or self.rerank_top_k
            
            # 准备文档文本
            doc_texts = []
            for doc in documents:
                content = doc.get('content', '')
                if content:
                    doc_texts.append(content)
                else:
                    doc_texts.append(doc.get('title', ''))
            
            if not doc_texts:
                return documents
            
            # 调用API计算重排序分数
            scores = await self._call_rerank_api(query, doc_texts)
            
            # 将分数与文档配对并排序
            doc_scores = list(zip(documents, scores))
            doc_scores.sort(key=lambda x: x[1], reverse=True)
            
            # 返回top_k个结果
            reranked_docs = []
            for doc, score in doc_scores[:top_k]:
                doc_copy = doc.copy()
                doc_copy['rerank_score'] = float(score)
                reranked_docs.append(doc_copy)
            
            logger.info(f"重排序完成: 输入{len(documents)}个文档，返回{len(reranked_docs)}个文档")
            
            return reranked_docs
            
        except Exception as e:
            logger.error(f"重排序失败: {e}")
            return documents
    
    def is_available(self) -> bool:
        """检查重排序服务是否可用"""
        return bool(self.api_key)
    
    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        return {
            "model_name": self.model_name,
            "rerank_top_k": self.rerank_top_k,
            "available": self.is_available(),
            "api_configured": bool(self.api_key)
        }