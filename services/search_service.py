"""搜索服务"""
import logging
from typing import List, Dict, Any, Optional
import asyncio
import httpx
import json
from urllib.parse import quote

from core.config import settings

logger = logging.getLogger(__name__)

class SearchService:
    """搜索服务类"""
    
    def __init__(self):
        self.web_search_api_key = settings.WEB_SEARCH_API_KEY
        self.web_search_enabled = settings.web_search_enabled
        self.timeout = 10  # 搜索超时时间
        
        # HTTP客户端
        self.client = httpx.AsyncClient(
            timeout=self.timeout,
            headers={
                "User-Agent": "SparkLink AI/1.0"
            }
        )
        
        # 同步客户端
        self.sync_client = httpx.Client(
            timeout=self.timeout,
            headers={
                "User-Agent": "SparkLink AI/1.0"
            }
        )
    
    async def web_search(
        self,
        query: str,
        max_results: int = 5,
        language: str = "zh-CN"
    ) -> List[Dict[str, Any]]:
        """联网搜索（异步）"""
        try:
            if not self.web_search_enabled:
                logger.warning("联网搜索功能已禁用")
                return []
            
            if not query or not query.strip():
                return []
            
            # 使用博查API进行搜索
            if self.web_search_api_key:
                return await self._search_with_bocha_api(query, max_results, language)
            else:
                # 如果没有配置API密钥，使用模拟搜索
                logger.warning("未配置搜索API密钥，返回模拟结果")
                return self._get_mock_search_results(query, max_results)
                
        except Exception as e:
            logger.error(f"联网搜索失败: {e}")
            return []
    
    def web_search_sync(
        self,
        query: str,
        max_results: int = 5,
        language: str = "zh-CN"
    ) -> List[Dict[str, Any]]:
        """联网搜索（同步）"""
        try:
            if not self.web_search_enabled:
                logger.warning("联网搜索功能已禁用")
                return []
            
            if not query or not query.strip():
                return []
            
            # 使用博查API进行搜索
            if self.web_search_api_key:
                return self._search_with_bocha_api_sync(query, max_results, language)
            else:
                # 如果没有配置API密钥，使用模拟搜索
                logger.warning("未配置搜索API密钥，返回模拟结果")
                return self._get_mock_search_results(query, max_results)
                
        except Exception as e:
            logger.error(f"联网搜索失败: {e}")
            return []
    
    async def _search_with_bocha_api(
        self,
        query: str,
        max_results: int,
        language: str
    ) -> List[Dict[str, Any]]:
        """使用博查API进行搜索"""
        try:
            # 博查AI搜索API接口
            api_url = "https://api.bochaai.com/v1/web-search"
            
            headers = {
                "Authorization": f"Bearer {self.web_search_api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "query": query,
                "count": min(max_results, 10),  # 博查API最多支持10个结果
                "freshness": "oneYear",  # 搜索时效性：oneYear, oneMonth, oneWeek, oneDay
                "summary": True  # 是否返回摘要
            }
            
            response = await self.client.post(api_url, headers=headers, json=payload)
            
            if response.status_code != 200:
                logger.error(f"博查API调用失败: {response.status_code} - {response.text}")
                return []
            
            data = response.json()
            
            # 解析搜索结果
            results = []
            
            # 根据博查API的实际返回格式进行解析
            # 博查API返回格式: {"code": 200, "data": {"webPages": {"value": [...]}}}
            if "data" in data and "webPages" in data["data"]:
                web_pages = data["data"]["webPages"]
                if "value" in web_pages and web_pages["value"]:
                    for item in web_pages["value"][:max_results]:
                        result = {
                            "title": item.get("name", ""),
                            "content": item.get("snippet", ""),
                            "url": item.get("url", ""),
                            "site_name": item.get("siteName", ""),
                            "site_icon": item.get("siteIcon", ""),
                            "published_date": item.get("datePublished", "")
                        }
                        # 如果有summary字段，添加到结果中
                        if "summary" in item and item["summary"]:
                            result["summary"] = item["summary"]
                        results.append(result)
            
            # 检查是否有全局摘要信息
            if "data" in data and "summary" in data["data"] and data["data"]["summary"] and results:
                results[0]["global_summary"] = data["data"]["summary"]
            
            logger.info(f"博查API搜索完成: 查询='{query}', 结果数={len(results)}")
            
            return results
            
        except Exception as e:
            logger.error(f"博查API搜索失败: {e}")
            return []
    
    def _search_with_bocha_api_sync(
        self,
        query: str,
        max_results: int,
        language: str
    ) -> List[Dict[str, Any]]:
        """使用博查API进行搜索（同步）"""
        try:
            # 博查AI搜索API接口
            api_url = "https://api.bochaai.com/v1/web-search"
            
            headers = {
                "Authorization": f"Bearer {self.web_search_api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "query": query,
                "count": min(max_results, 10),  # 博查API最多支持10个结果
                "freshness": "oneYear",  # 搜索时效性：oneYear, oneMonth, oneWeek, oneDay
                "summary": True  # 是否返回摘要
            }
            
            response = self.sync_client.post(api_url, headers=headers, json=payload)
            
            if response.status_code != 200:
                logger.error(f"博查API调用失败: {response.status_code} - {response.text}")
                return []
            
            data = response.json()
            
            # 解析搜索结果
            results = []
            
            # 根据博查API的实际返回格式进行解析
            # 博查API返回格式: {"code": 200, "data": {"webPages": {"value": [...]}}}
            if "data" in data and "webPages" in data["data"]:
                web_pages = data["data"]["webPages"]
                if "value" in web_pages and web_pages["value"]:
                    for item in web_pages["value"][:max_results]:
                        result = {
                            "title": item.get("name", ""),
                            "content": item.get("snippet", ""),
                            "url": item.get("url", ""),
                            "source": "bocha_search",
                            "score": 0.8,  # 博查API不直接提供相关性分数
                            "site_name": item.get("siteName", ""),
                            "site_icon": item.get("siteIcon", ""),
                            "published_date": item.get("datePublished", "")
                        }
                        # 如果有summary字段，添加到结果中
                        if "summary" in item and item["summary"]:
                            result["summary"] = item["summary"]
                        results.append(result)
            
            # 检查是否有全局摘要信息
            if "data" in data and "summary" in data["data"] and data["data"]["summary"] and results:
                results[0]["global_summary"] = data["data"]["summary"]
            
            logger.info(f"博查API搜索完成: 查询='{query}', 结果数={len(results)}")
            
            return results
            
        except Exception as e:
            logger.error(f"博查API搜索失败: {e}")
            return []
    
    def _get_mock_search_results(
        self,
        query: str,
        max_results: int
    ) -> List[Dict[str, Any]]:
        """获取模拟搜索结果（用于测试）"""
        mock_results = [
            {
                "title": f"关于'{query}'的搜索结果1",
                "content": f"这是关于'{query}'的第一个模拟搜索结果。包含相关信息和详细描述。",
                "url": "https://example.com/result1",
                "source": "web_search",
                "score": 0.9,
                "published_date": "2024-01-01"
            },
            {
                "title": f"'{query}'相关资料",
                "content": f"这里提供了关于'{query}'的详细资料和分析，帮助您更好地理解相关概念。",
                "url": "https://example.com/result2",
                "source": "web_search",
                "score": 0.85,
                "published_date": "2024-01-02"
            },
            {
                "title": f"深入了解{query}",
                "content": f"本文深入探讨了'{query}'的各个方面，提供了全面的信息和见解。",
                "url": "https://example.com/result3",
                "source": "web_search",
                "score": 0.8,
                "published_date": "2024-01-03"
            }
        ]
        
        return mock_results[:max_results]
    
    async def intelligent_search(
        self,
        query: str,
        knowledge_results: List[Dict[str, Any]] = None,
        knowledge_threshold: float = 0.8
    ) -> Dict[str, Any]:
        """智能搜索策略"""
        try:
            search_strategy = "none"
            web_results = []
            
            # 分析知识库结果
            should_web_search = False
            knowledge_confidence = 0.0
            
            if knowledge_results:
                # 计算知识库结果的最高置信度
                knowledge_confidence = max([r.get('score', 0) for r in knowledge_results])
                
                # 智能判断是否需要联网搜索
                if len(knowledge_results) < 3:
                    should_web_search = True
                    logger.info(f"知识库结果不足({len(knowledge_results)}个)，启用联网搜索")
                elif knowledge_confidence < knowledge_threshold:
                    should_web_search = True
                    logger.info(f"知识库置信度({knowledge_confidence:.2f})低于阈值({knowledge_threshold})，启用联网搜索")
                else:
                    logger.info(f"知识库结果充足且置信度高({knowledge_confidence:.2f})，无需联网搜索")
            else:
                should_web_search = True
                logger.info("无知识库结果，启用联网搜索")
            
            # 执行联网搜索
            if should_web_search:
                web_results = await self.web_search(query, max_results=5)
                
                if web_results:
                    if knowledge_results:
                        search_strategy = "hybrid"
                    else:
                        search_strategy = "web_search"
                else:
                    search_strategy = "knowledge_base" if knowledge_results else "none"
            else:
                search_strategy = "knowledge_base"
            
            return {
                "query": query,
                "search_strategy": search_strategy,
                "knowledge_results": knowledge_results or [],
                "web_results": web_results,
                "knowledge_confidence": knowledge_confidence,
                "total_results": len(knowledge_results or []) + len(web_results)
            }
            
        except Exception as e:
            logger.error(f"智能搜索失败: {e}")
            return {
                "query": query,
                "search_strategy": "error",
                "knowledge_results": knowledge_results or [],
                "web_results": [],
                "knowledge_confidence": 0.0,
                "total_results": 0,
                "error": str(e)
            }
    
    def _deduplicate_results(
        self,
        results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """去重搜索结果"""
        try:
            unique_results = []
            seen_contents = set()
            
            for result in results:
                content = result.get("content", "")
                
                # 简单的内容去重（基于前100个字符）
                content_key = content[:100].strip().lower()
                
                if content_key and content_key not in seen_contents:
                    seen_contents.add(content_key)
                    unique_results.append(result)
            
            return unique_results
            
        except Exception as e:
            logger.error(f"结果去重失败: {e}")
            return results
    
    async def test_web_search(self) -> bool:
        """测试联网搜索功能"""
        try:
            if not self.web_search_enabled:
                return False
            
            test_query = "人工智能"
            results = await self.web_search(test_query, max_results=1)
            
            return len(results) > 0
            
        except Exception as e:
            logger.error(f"联网搜索测试失败: {e}")
            return False
    
    def get_search_config(self) -> Dict[str, Any]:
        """获取搜索配置信息"""
        return {
            "web_search_enabled": self.web_search_enabled,
            "api_key_configured": bool(self.web_search_api_key),
            "timeout": self.timeout,
            "knowledge_confidence_threshold": settings.knowledge_confidence_threshold
        }
    
    def __del__(self):
        """清理资源"""
        try:
            if hasattr(self, 'client'):
                asyncio.create_task(self.client.aclose())
            if hasattr(self, 'sync_client'):
                self.sync_client.close()
        except Exception:
            pass