"""PocketFlow框架集成 - 智能搜索策略"""
import logging
from typing import List, Dict, Any, Optional, Tuple
import asyncio
from enum import Enum

from services.knowledge_service import KnowledgeService
from services.search_service import SearchService
from core.config import settings

logger = logging.getLogger(__name__)

class SearchStrategy(Enum):
    """搜索策略枚举"""
    KNOWLEDGE_ONLY = "knowledge_only"
    WEB_ONLY = "web_only"
    HYBRID = "hybrid"
    INTELLIGENT = "intelligent"

class ConfidenceLevel(Enum):
    """置信度级别"""
    HIGH = "high"        # > 0.8
    MEDIUM = "medium"    # 0.5 - 0.8
    LOW = "low"          # < 0.5

class PocketFlow:
    """PocketFlow智能搜索框架
    
    实现智能搜索策略，根据知识库能力动态决定是否进行联网搜索
    """
    
    def __init__(self):
        self.knowledge_service = KnowledgeService()
        self.search_service = SearchService()
        
        # 配置参数
        self.knowledge_threshold = settings.knowledge_confidence_threshold
        self.min_knowledge_results = 3
        self.max_web_results = 5
        self.max_total_results = 10
        
        # 搜索统计
        self.search_stats = {
            "total_searches": 0,
            "knowledge_only": 0,
            "web_only": 0,
            "hybrid": 0,
            "failed": 0
        }
    
    async def intelligent_search(
        self,
        query: str,
        strategy: SearchStrategy = SearchStrategy.INTELLIGENT,
        max_results: int = 10
    ) -> Dict[str, Any]:
        """智能搜索主入口"""
        try:
            self.search_stats["total_searches"] += 1
            
            logger.info(f"开始智能搜索: 查询='{query}', 策略={strategy.value}")
            
            # 根据策略执行搜索
            if strategy == SearchStrategy.KNOWLEDGE_ONLY:
                return await self._knowledge_only_search(query, max_results)
            elif strategy == SearchStrategy.WEB_ONLY:
                return await self._web_only_search(query, max_results)
            elif strategy == SearchStrategy.HYBRID:
                return await self._hybrid_search(query, max_results)
            else:  # INTELLIGENT
                return await self._intelligent_adaptive_search(query, max_results)
                
        except Exception as e:
            logger.error(f"智能搜索失败: {e}")
            self.search_stats["failed"] += 1
            return self._create_error_result(query, str(e))
    
    async def _intelligent_adaptive_search(
        self,
        query: str,
        max_results: int
    ) -> Dict[str, Any]:
        """智能自适应搜索策略"""
        try:
            # 第一阶段：知识库搜索
            knowledge_results = await self._search_knowledge_base(query)
            
            # 分析知识库结果
            analysis = self._analyze_knowledge_results(knowledge_results)
            
            # 决策是否需要联网搜索
            decision = self._make_search_decision(analysis, query)
            
            web_results = []
            final_strategy = "knowledge_only"
            
            # 第二阶段：根据决策执行联网搜索
            if decision["should_web_search"]:
                web_results = await self._search_web(query, decision["web_search_params"])
                
                if web_results:
                    final_strategy = "hybrid" if knowledge_results else "web_only"
                    if not knowledge_results:
                        self.search_stats["web_only"] += 1
                    else:
                        self.search_stats["hybrid"] += 1
                else:
                    final_strategy = "knowledge_only"
                    self.search_stats["knowledge_only"] += 1
            else:
                final_strategy = "knowledge_only"
                self.search_stats["knowledge_only"] += 1
            
            # 第三阶段：结果融合和排序
            final_results = self._merge_and_rank_results(
                knowledge_results,
                web_results,
                max_results
            )
            
            return {
                "query": query,
                "strategy": final_strategy,
                "decision_reasoning": decision["reasoning"],
                "knowledge_analysis": analysis,
                "results": final_results,
                "knowledge_results_count": len(knowledge_results),
                "web_results_count": len(web_results),
                "total_results_count": len(final_results),
                "search_quality": self._evaluate_search_quality(final_results),
                "performance_metrics": {
                    "knowledge_search_time": analysis.get("search_time", 0),
                    "web_search_time": decision.get("web_search_time", 0)
                }
            }
            
        except Exception as e:
            logger.error(f"智能自适应搜索失败: {e}")
            raise
    
    async def _search_knowledge_base(
        self,
        query: str,
        top_k: int = 15
    ) -> List[Dict[str, Any]]:
        """搜索知识库"""
        try:
            import time
            start_time = time.time()
            
            results = await self.knowledge_service.search(
                query=query,
                top_k=top_k,
                similarity_threshold=0.3  # 降低阈值以获取更多候选结果
            )
            
            search_time = time.time() - start_time
            
            # 为结果添加搜索时间信息
            for result in results:
                result["search_time"] = search_time
            
            return results
            
        except Exception as e:
            logger.error(f"知识库搜索失败: {e}")
            return []
    
    async def _search_web(
        self,
        query: str,
        params: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """搜索网络"""
        try:
            import time
            start_time = time.time()
            
            max_results = params.get("max_results", self.max_web_results)
            
            results = await self.search_service.web_search(
                query=query,
                max_results=max_results
            )
            
            search_time = time.time() - start_time
            
            # 为结果添加搜索时间信息
            for result in results:
                result["search_time"] = search_time
            
            return results
            
        except Exception as e:
            logger.error(f"网络搜索失败: {e}")
            return []
    
    def _analyze_knowledge_results(
        self,
        results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """分析知识库搜索结果"""
        if not results:
            return {
                "result_count": 0,
                "max_confidence": 0.0,
                "avg_confidence": 0.0,
                "confidence_level": ConfidenceLevel.LOW,
                "quality_score": 0.0,
                "coverage_assessment": "no_results",
                "search_time": results[0].get("search_time", 0) if results else 0
            }
        
        scores = [r.get("score", 0) for r in results]
        max_confidence = max(scores)
        avg_confidence = sum(scores) / len(scores)
        
        # 确定置信度级别
        if max_confidence >= 0.8:
            confidence_level = ConfidenceLevel.HIGH
        elif max_confidence >= 0.5:
            confidence_level = ConfidenceLevel.MEDIUM
        else:
            confidence_level = ConfidenceLevel.LOW
        
        # 评估覆盖度
        coverage_assessment = self._assess_coverage(results)
        
        # 计算质量分数
        quality_score = self._calculate_quality_score(results)
        
        return {
            "result_count": len(results),
            "max_confidence": max_confidence,
            "avg_confidence": avg_confidence,
            "confidence_level": confidence_level,
            "quality_score": quality_score,
            "coverage_assessment": coverage_assessment,
            "high_confidence_count": len([s for s in scores if s >= 0.8]),
            "medium_confidence_count": len([s for s in scores if 0.5 <= s < 0.8]),
            "low_confidence_count": len([s for s in scores if s < 0.5]),
            "search_time": results[0].get("search_time", 0) if results else 0
        }
    
    def _make_search_decision(
        self,
        analysis: Dict[str, Any],
        query: str
    ) -> Dict[str, Any]:
        """决策是否需要联网搜索"""
        should_web_search = False
        reasoning = []
        web_search_params = {"max_results": self.max_web_results}
        
        # 决策规则1：结果数量不足
        if analysis["result_count"] < self.min_knowledge_results:
            should_web_search = True
            reasoning.append(f"知识库结果不足({analysis['result_count']}个，需要至少{self.min_knowledge_results}个)")
        
        # 决策规则2：最高置信度不足
        if analysis["max_confidence"] < self.knowledge_threshold:
            should_web_search = True
            reasoning.append(f"最高置信度({analysis['max_confidence']:.2f})低于阈值({self.knowledge_threshold})")
        
        # 决策规则3：覆盖度评估
        if analysis["coverage_assessment"] in ["poor", "incomplete"]:
            should_web_search = True
            reasoning.append(f"知识覆盖度评估为{analysis['coverage_assessment']}")
        
        # 决策规则4：查询类型分析
        query_type = self._analyze_query_type(query)
        if query_type in ["current_events", "real_time", "trending"]:
            should_web_search = True
            reasoning.append(f"查询类型({query_type})需要实时信息")
            web_search_params["max_results"] = 8  # 实时信息需要更多结果
        
        # 决策规则5：质量分数
        if analysis["quality_score"] < 0.6:
            should_web_search = True
            reasoning.append(f"知识库结果质量分数({analysis['quality_score']:.2f})较低")
        
        # 如果不需要联网搜索，说明知识库结果充足
        if not should_web_search:
            reasoning.append("知识库结果充足且质量良好，无需联网搜索")
        
        return {
            "should_web_search": should_web_search,
            "reasoning": "; ".join(reasoning),
            "web_search_params": web_search_params,
            "decision_confidence": self._calculate_decision_confidence(analysis)
        }
    
    def _assess_coverage(self, results: List[Dict[str, Any]]) -> str:
        """评估知识覆盖度"""
        if not results:
            return "no_results"
        
        if len(results) >= 8 and results[0].get("score", 0) >= 0.8:
            return "excellent"
        elif len(results) >= 5 and results[0].get("score", 0) >= 0.7:
            return "good"
        elif len(results) >= 3 and results[0].get("score", 0) >= 0.5:
            return "fair"
        elif len(results) >= 1:
            return "poor"
        else:
            return "incomplete"
    
    def _calculate_quality_score(self, results: List[Dict[str, Any]]) -> float:
        """计算结果质量分数"""
        if not results:
            return 0.0
        
        # 综合考虑多个因素
        scores = [r.get("score", 0) for r in results]
        
        # 因子1：最高分数权重40%
        max_score_factor = max(scores) * 0.4
        
        # 因子2：平均分数权重30%
        avg_score_factor = (sum(scores) / len(scores)) * 0.3
        
        # 因子3：结果数量权重20%（归一化到0-1）
        count_factor = min(len(results) / 10, 1.0) * 0.2
        
        # 因子4：分数分布权重10%
        high_quality_ratio = len([s for s in scores if s >= 0.7]) / len(scores)
        distribution_factor = high_quality_ratio * 0.1
        
        quality_score = max_score_factor + avg_score_factor + count_factor + distribution_factor
        
        return min(quality_score, 1.0)
    
    def _analyze_query_type(self, query: str) -> str:
        """分析查询类型"""
        query_lower = query.lower()
        
        # 实时信息关键词
        real_time_keywords = ["最新", "今天", "现在", "当前", "最近", "今年", "2024", "news", "latest", "current"]
        
        # 事实性查询关键词
        factual_keywords = ["什么是", "如何", "为什么", "怎么", "定义", "原理", "方法", "步骤"]
        
        # 技术查询关键词
        technical_keywords = ["代码", "编程", "算法", "技术", "开发", "API", "框架", "库"]
        
        if any(keyword in query_lower for keyword in real_time_keywords):
            return "real_time"
        elif any(keyword in query_lower for keyword in factual_keywords):
            return "factual"
        elif any(keyword in query_lower for keyword in technical_keywords):
            return "technical"
        else:
            return "general"
    
    def _calculate_decision_confidence(self, analysis: Dict[str, Any]) -> float:
        """计算决策置信度"""
        # 基于分析结果计算决策的置信度
        confidence_factors = [
            analysis["max_confidence"],
            analysis["quality_score"],
            min(analysis["result_count"] / 10, 1.0)
        ]
        
        return sum(confidence_factors) / len(confidence_factors)
    
    def _merge_and_rank_results(
        self,
        knowledge_results: List[Dict[str, Any]],
        web_results: List[Dict[str, Any]],
        max_results: int
    ) -> List[Dict[str, Any]]:
        """合并和排序结果"""
        try:
            all_results = []
            
            # 添加知识库结果（提升权重）
            for result in knowledge_results:
                result_copy = result.copy()
                result_copy["final_score"] = result.get("score", 0) * 1.3  # 知识库结果权重提升30%
                result_copy["source_type"] = "knowledge_base"
                all_results.append(result_copy)
            
            # 添加网络搜索结果
            for result in web_results:
                result_copy = result.copy()
                result_copy["final_score"] = result.get("score", 0) * 1.0  # 网络结果保持原权重
                result_copy["source_type"] = "web_search"
                all_results.append(result_copy)
            
            # 按最终得分排序
            all_results.sort(key=lambda x: x.get("final_score", 0), reverse=True)
            
            # 去重和多样性优化
            diverse_results = self._optimize_diversity(all_results)
            
            return diverse_results[:max_results]
            
        except Exception as e:
            logger.error(f"结果合并排序失败: {e}")
            return (knowledge_results + web_results)[:max_results]
    
    def _optimize_diversity(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """优化结果多样性"""
        try:
            if len(results) <= 3:
                return results
            
            diverse_results = []
            used_contents = set()
            
            # 确保至少包含一个高分结果
            if results:
                first_result = results[0]
                diverse_results.append(first_result)
                content_key = self._get_content_key(first_result)
                used_contents.add(content_key)
            
            # 添加其他结果，确保多样性
            for result in results[1:]:
                content_key = self._get_content_key(result)
                
                # 检查内容相似性
                if content_key not in used_contents:
                    diverse_results.append(result)
                    used_contents.add(content_key)
                
                # 限制结果数量
                if len(diverse_results) >= 15:
                    break
            
            return diverse_results
            
        except Exception as e:
            logger.error(f"多样性优化失败: {e}")
            return results
    
    def _get_content_key(self, result: Dict[str, Any]) -> str:
        """获取内容关键字（用于去重）"""
        content = result.get("content", "")
        return content[:100].strip().lower() if content else ""
    
    def _evaluate_search_quality(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """评估搜索质量"""
        if not results:
            return {
                "overall_score": 0.0,
                "relevance_score": 0.0,
                "diversity_score": 0.0,
                "completeness_score": 0.0
            }
        
        scores = [r.get("final_score", 0) for r in results]
        
        # 相关性分数
        relevance_score = sum(scores) / len(scores)
        
        # 多样性分数（基于来源类型）
        source_types = set(r.get("source_type", "unknown") for r in results)
        diversity_score = len(source_types) / 2.0  # 最多2种来源类型
        
        # 完整性分数（基于结果数量）
        completeness_score = min(len(results) / 10, 1.0)
        
        # 综合分数
        overall_score = (relevance_score * 0.5 + diversity_score * 0.3 + completeness_score * 0.2)
        
        return {
            "overall_score": overall_score,
            "relevance_score": relevance_score,
            "diversity_score": diversity_score,
            "completeness_score": completeness_score
        }
    
    async def _knowledge_only_search(self, query: str, max_results: int) -> Dict[str, Any]:
        """仅知识库搜索"""
        knowledge_results = await self._search_knowledge_base(query)
        
        return {
            "query": query,
            "strategy": "knowledge_only",
            "results": knowledge_results[:max_results],
            "knowledge_results_count": len(knowledge_results),
            "web_results_count": 0,
            "total_results_count": len(knowledge_results)
        }
    
    async def _web_only_search(self, query: str, max_results: int) -> Dict[str, Any]:
        """仅网络搜索"""
        web_results = await self._search_web(query, {"max_results": max_results})
        
        return {
            "query": query,
            "strategy": "web_only",
            "results": web_results,
            "knowledge_results_count": 0,
            "web_results_count": len(web_results),
            "total_results_count": len(web_results)
        }
    
    async def _hybrid_search(self, query: str, max_results: int) -> Dict[str, Any]:
        """混合搜索"""
        # 并行执行知识库和网络搜索
        knowledge_task = self._search_knowledge_base(query)
        web_task = self._search_web(query, {"max_results": self.max_web_results})
        
        knowledge_results, web_results = await asyncio.gather(
            knowledge_task, web_task, return_exceptions=True
        )
        
        # 处理异常
        if isinstance(knowledge_results, Exception):
            knowledge_results = []
        if isinstance(web_results, Exception):
            web_results = []
        
        # 合并结果
        final_results = self._merge_and_rank_results(
            knowledge_results, web_results, max_results
        )
        
        return {
            "query": query,
            "strategy": "hybrid",
            "results": final_results,
            "knowledge_results_count": len(knowledge_results),
            "web_results_count": len(web_results),
            "total_results_count": len(final_results)
        }
    
    def _create_error_result(self, query: str, error_message: str) -> Dict[str, Any]:
        """创建错误结果"""
        return {
            "query": query,
            "strategy": "error",
            "results": [],
            "knowledge_results_count": 0,
            "web_results_count": 0,
            "total_results_count": 0,
            "error": error_message
        }
    
    def get_search_stats(self) -> Dict[str, Any]:
        """获取搜索统计信息"""
        return self.search_stats.copy()
    
    def reset_search_stats(self):
        """重置搜索统计"""
        self.search_stats = {
            "total_searches": 0,
            "knowledge_only": 0,
            "web_only": 0,
            "hybrid": 0,
            "failed": 0
        }

# 全局PocketFlow实例
pocket_flow = PocketFlow()