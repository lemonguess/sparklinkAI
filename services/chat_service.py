"""聊天服务"""
import logging
from typing import List, Dict, Any, Optional, AsyncGenerator
import json
import time
import uuid
from enum import Enum

import openai
from openai import OpenAI
from sqlalchemy.orm import Session

from core.config import settings
from core.database import get_redis, get_db
from models.database import ChatMessage as DBChatMessage
from services.knowledge_service import KnowledgeService
from services.search_service import SearchService

logger = logging.getLogger(__name__)


class SearchStrategy(Enum):
    """搜索策略枚举"""
    KNOWLEDGE_FIRST = "knowledge_first"
    WEB_FIRST = "web_first"
    HYBRID = "hybrid"
    AUTO = "auto"


class ChatService:
    """聊天服务类 - 集成智能搜索功能"""
    
    def __init__(self, db: Optional[Session] = None):
        self.client = OpenAI(
            api_key=settings.SILICONFLOW_API_KEY,
            base_url=settings.SILICONFLOW_BASE_URL
        )
        self.redis_client = get_redis()
        self.db = db  # 数据库会话
        
        # 集成搜索服务
        self.knowledge_service = KnowledgeService()
        self.search_service = SearchService()
    
    async def intelligent_search(
        self,
        query: str,
        strategy: SearchStrategy = SearchStrategy.AUTO,
        max_results: int = 5,
        use_knowledge_base: bool = True,
        use_web_search: bool = True
    ) -> Dict[str, Any]:
        """智能搜索 - 整合知识库和网络搜索"""
        logger.info(f"🚀 开始智能搜索: {query}")
        
        knowledge_results = []
        web_results = []
        decision_reasoning = ""
        
        try:
            # 第一步：知识库搜索
            if use_knowledge_base:
                logger.info("🔍 执行知识库搜索")
                knowledge_results = await self.knowledge_service.search(
                    query=query,
                    top_k=10
                )
            
            # 第二步：智能决策是否需要网络搜索
            need_web_search = False
            quality_score = 0.0
            
            if knowledge_results:
                # 计算知识库结果质量
                scores = [r.get('score', 0) for r in knowledge_results]
                quality_score = sum(scores) / len(scores) if scores else 0.0
                max_score = max(scores) if scores else 0.0
                
                # 智能判断逻辑
                if strategy == SearchStrategy.AUTO:
                    need_web_search = (
                        len(knowledge_results) < 3 or  # 结果数量不足
                        max_score < 0.8 or  # 最高相似度不够
                        quality_score < 0.7  # 平均质量不够
                    )
                    decision_reasoning = f"知识库质量评分: {quality_score:.2f}, 最高分: {max_score:.2f}, 结果数: {len(knowledge_results)}"
                elif strategy == SearchStrategy.HYBRID:
                    need_web_search = True
                    decision_reasoning = "混合策略：同时使用知识库和网络搜索"
                elif strategy == SearchStrategy.WEB_FIRST:
                    need_web_search = True
                    decision_reasoning = "网络优先策略"
                else:  # KNOWLEDGE_FIRST
                    need_web_search = quality_score < 0.6  # 只有质量很低时才网络搜索
                    decision_reasoning = f"知识库优先策略，质量评分: {quality_score:.2f}"
            else:
                need_web_search = use_web_search
                decision_reasoning = "知识库无结果，启用网络搜索"
            
            # 第三步：条件性网络搜索
            if need_web_search and use_web_search:
                logger.info("🌐 执行网络搜索")
                web_results = await self.search_service.web_search(
                    query=query,
                    max_results=max_results
                )
            
            # 第四步：结果合并和排序
            logger.info("🔗 合并搜索结果")
            final_results = self.search_service.filter_and_rank_results(
                knowledge_results=knowledge_results,
                web_results=web_results,
                max_results=max_results
            )
            
            logger.info(f"✅ 智能搜索完成: 知识库{len(knowledge_results)}条, 网络{len(web_results)}条, 最终{len(final_results)}条")
            
            return {
                'query': query,
                'results': final_results,
                'knowledge_results': knowledge_results,
                'web_results': web_results,
                'strategy': strategy,
                'success': True,
                'total_results_count': len(final_results),
                'decision_reasoning': decision_reasoning,
                'quality_metrics': {
                    'knowledge_quality': quality_score,
                    'knowledge_count': len(knowledge_results),
                    'web_count': len(web_results),
                    'used_web_search': need_web_search
                },
                'performance_metrics': {
                    'framework': 'Integrated ChatService',
                    'total_time': 0.01
                }
            }
            
        except Exception as e:
            logger.error(f"智能搜索失败: {e}", exc_info=True)
            return {
                'query': query,
                'results': [],
                'success': False,
                'error': str(e),
                'strategy': strategy
            }
    
    async def generate_response(
        self,
        message: str,
        knowledge_sources: List[Dict[str, Any]] = None,
        web_search_results: List[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
        stream: bool = False,
        use_intelligent_search: bool = False,
        search_strategy: SearchStrategy = SearchStrategy.AUTO
    ) -> str:
        """生成聊天回复"""
        try:
            # 如果启用智能搜索，则自动获取搜索结果
            if use_intelligent_search:
                search_result = await self.intelligent_search(
                    query=message,
                    strategy=search_strategy,
                    max_results=5
                )
                
                if search_result.get('success', False):
                    knowledge_sources = search_result.get('knowledge_results', [])
                    web_search_results = search_result.get('web_results', [])
                    logger.info(f"智能搜索获得: 知识库{len(knowledge_sources)}条, 网络{len(web_search_results)}条")
            
            # 构建系统提示词
            system_prompt = self._build_system_prompt(
                knowledge_sources=knowledge_sources,
                web_search_results=web_search_results
            )
            
            # 获取历史对话
            conversation_history = await self._get_conversation_history(session_id)
            
            # 构建消息列表
            messages = [
                {"role": "system", "content": system_prompt}
            ]
            
            # 添加历史对话（最近10轮）
            if conversation_history:
                messages.extend(conversation_history[-20:])  # 最近20条消息（10轮对话）
            
            # 添加当前用户消息
            messages.append({"role": "user", "content": message})
            
            # 调用LLM生成回复
            if stream:
                return await self._generate_stream_response(messages)
            else:
                return await self._generate_single_response(messages)
                
        except Exception as e:
            logger.error(f"生成聊天回复失败: {e}", exc_info=True)
            return "抱歉，我现在无法处理您的请求，请稍后再试。"
    
    async def generate_stream_response(
        self,
        message: str,
        knowledge_sources: List[Dict[str, Any]] = None,
        web_search_results: List[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
        use_intelligent_search: bool = False,
        search_strategy: SearchStrategy = SearchStrategy.AUTO
    ) -> AsyncGenerator[str, None]:
        """生成流式聊天回复"""
        try:
            # 如果启用智能搜索，则自动获取搜索结果
            if use_intelligent_search:
                search_result = await self.intelligent_search(
                    query=message,
                    strategy=search_strategy,
                    max_results=5
                )
                
                if search_result.get('success', False):
                    knowledge_sources = search_result.get('knowledge_results', [])
                    web_search_results = search_result.get('web_results', [])
                    logger.info(f"智能搜索获得: 知识库{len(knowledge_sources)}条, 网络{len(web_search_results)}条")
            
            # 构建系统提示词
            system_prompt = self._build_system_prompt(
                knowledge_sources=knowledge_sources,
                web_search_results=web_search_results
            )
            
            # 获取历史对话
            conversation_history = await self._get_conversation_history(session_id)
            
            # 构建消息列表
            messages = [
                {"role": "system", "content": system_prompt}
            ]
            
            if conversation_history:
                messages.extend(conversation_history[-20:])
            
            messages.append({"role": "user", "content": message})
            
            # 流式生成
            try:
                response = self.client.chat.completions.create(
                    model=settings.chat_model,
                    messages=messages,
                    max_tokens=settings.max_tokens,
                    temperature=settings.temperature,
                    stream=True
                )
                
                for chunk in response:
                    if not chunk.choices:
                        continue
                    if chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content
                    if hasattr(chunk.choices[0].delta, 'reasoning_content') and chunk.choices[0].delta.reasoning_content:
                        yield chunk.choices[0].delta.reasoning_content
                        
            except Exception as e:
                logger.error(f"流式生成失败: {e}")
                yield "抱歉，生成回复时出现错误。"
                
        except Exception as e:
            logger.error(f"流式聊天服务失败: {e}", exc_info=True)
            yield "抱歉，我现在无法处理您的请求。"
    
    async def _generate_single_response(self, messages: List[Dict[str, str]]) -> str:
        """生成单次回复"""
        try:
            response = self.client.chat.completions.create(
                model=settings.chat_model,
                messages=messages,
                max_tokens=settings.max_tokens,
                temperature=settings.temperature
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"调用LLM失败: {e}")
            raise
    
    async def _generate_stream_response(self, messages: List[Dict[str, str]]) -> str:
        """生成流式回复（内部使用）"""
        try:
            response = self.client.chat.completions.create(
                model=settings.chat_model,
                messages=messages,
                max_tokens=settings.max_tokens,
                temperature=settings.temperature,
                stream=True
            )
            
            full_response = ""
            for chunk in response:
                if not chunk.choices:
                    continue
                if chunk.choices[0].delta.content:
                    full_response += chunk.choices[0].delta.content
                if hasattr(chunk.choices[0].delta, 'reasoning_content') and chunk.choices[0].delta.reasoning_content:
                    full_response += chunk.choices[0].delta.reasoning_content
            
            return full_response.strip()
            
        except Exception as e:
            logger.error(f"流式生成失败: {e}")
            raise
    
    def _build_system_prompt(
        self,
        knowledge_sources: List[Dict[str, Any]] = None,
        web_search_results: List[Dict[str, Any]] = None
    ) -> str:
        """构建系统提示词"""
        base_prompt = """你是SparkLink AI，一个智能助手。请根据用户的问题提供准确、有用的回答。

回答要求：
1. 回答要准确、简洁、有条理
2. 如果有相关的知识库内容或搜索结果，请优先参考这些信息
3. 如果信息不足，请诚实说明
4. 保持友好、专业的语调
"""
        
        # 添加知识库信息
        if knowledge_sources:
            base_prompt += "\n\n**相关知识库内容：**\n"
            for i, source in enumerate(knowledge_sources[:5], 1):  # 最多5个来源
                content = source.get('content', '').strip()
                score = source.get('score', 0)
                base_prompt += f"{i}. [相似度: {score:.2f}] {content}\n"
        
        # 添加搜索结果
        if web_search_results:
            base_prompt += "\n\n**相关搜索结果：**\n"
            for i, result in enumerate(web_search_results[:3], 1):  # 最多3个搜索结果
                title = result.get('title', '').strip()
                content = result.get('content', '').strip()
                url = result.get('url', '')
                base_prompt += f"{i}. **{title}**\n{content}\n来源: {url}\n\n"
        
        return base_prompt
    
    async def _get_conversation_history(self, session_id: Optional[str]) -> List[Dict[str, str]]:
        """获取对话历史"""
        if not session_id:
            return []
        
        try:
            cache_key = f"session:{session_id}:messages"
            
            # 从Redis缓存获取
            cached_history = self.redis_client.get(cache_key)
            if cached_history:
                logger.info(f"从Redis缓存获取会话 {session_id} 的聊天历史")
                cached_data = json.loads(cached_history)
                # 转换为简化格式用于对话上下文
                return [{"role": msg["role"], "content": msg["content"]} for msg in cached_data]
            
            # 如果缓存中没有，从MySQL数据库获取
            if self.db:
                logger.info(f"Redis缓存未命中，从MySQL查询会话 {session_id} 的聊天历史")
                messages = self.db.query(DBChatMessage).filter(
                    DBChatMessage.session_id == session_id
                ).order_by(DBChatMessage.created_at.asc()).limit(50).all()
                
                # 转换为完整格式
                full_history = []
                simple_history = []
                for msg in messages:
                    msg_data = {
                        "message_id": msg.message_id,
                        "role": msg.role,
                        "content": msg.content,
                        "created_at": msg.created_at.timestamp() if msg.created_at else time.time()
                    }
                    if msg.knowledge_sources:
                        msg_data["knowledge_sources"] = json.loads(msg.knowledge_sources)
                    if msg.web_search_results:
                        msg_data["web_search_results"] = json.loads(msg.web_search_results)
                    
                    full_history.append(msg_data)
                    simple_history.append({"role": msg.role, "content": msg.content})
                
                # 将完整格式缓存到Redis（24小时过期）
                if full_history:
                    self.redis_client.setex(
                        cache_key,
                        86400,  # 24小时
                        json.dumps(full_history, ensure_ascii=False)
                    )
                    logger.info(f"已将会话 {session_id} 的 {len(full_history)} 条消息缓存到Redis")
                
                return simple_history
            else:
                logger.warning("数据库会话未初始化，无法查询MySQL")
                return []
            
        except Exception as e:
            logger.warning(f"获取对话历史失败: {e}")
            return []
    
    async def save_conversation_history(
        self,
        session_id: str,
        user_message: str,
        assistant_message: str,
        knowledge_sources: Optional[List[Dict[str, Any]]] = None,
        web_search_results: Optional[List[Dict[str, Any]]] = None,
        user_message_id: Optional[str] = None,
        assistant_message_id: Optional[str] = None
    ):
        """保存对话历史到MySQL和Redis缓存"""
        try:
            # 生成消息ID
            user_msg_id = user_message_id or str(uuid.uuid4())
            assistant_msg_id = assistant_message_id or str(uuid.uuid4())
            
            # 1. 保存到MySQL数据库
            if self.db:
                # 保存用户消息
                user_msg = DBChatMessage(
                    session_id=session_id,
                    message_id=user_msg_id,
                    role="user",
                    content=user_message
                )
                self.db.add(user_msg)
                
                # 保存助手消息
                assistant_msg = DBChatMessage(
                    session_id=session_id,
                    message_id=assistant_msg_id,
                    role="assistant",
                    content=assistant_message,
                    knowledge_sources=json.dumps(knowledge_sources, ensure_ascii=False) if knowledge_sources else None,
                    web_search_results=json.dumps(web_search_results, ensure_ascii=False) if web_search_results else None
                )
                self.db.add(assistant_msg)
                self.db.commit()
                logger.info(f"已保存会话 {session_id} 的对话到MySQL数据库")
            else:
                logger.warning("数据库会话未初始化，无法保存到MySQL")
            
            # 2. 更新Redis缓存
            cache_key = f"session:{session_id}:messages"
            
            # 获取现有历史
            existing_history = await self._get_conversation_history(session_id)
            
            # 添加新的对话（包含message_id）
            existing_history.extend([
                {
                    "message_id": user_msg_id,
                    "role": "user", 
                    "content": user_message,
                    "created_at": time.time()
                },
                {
                    "message_id": assistant_msg_id,
                    "role": "assistant", 
                    "content": assistant_message,
                    "created_at": time.time(),
                    "knowledge_sources": knowledge_sources,
                    "web_search_results": web_search_results
                }
            ])
            
            # 保持最近50条消息
            if len(existing_history) > 50:
                existing_history = existing_history[-50:]
            
            # 保存到Redis，过期时间24小时
            self.redis_client.setex(
                cache_key,
                86400,  # 24小时
                json.dumps(existing_history, ensure_ascii=False)
            )
            logger.info(f"已更新会话 {session_id} 的Redis缓存，共 {len(existing_history)} 条消息")
            
        except Exception as e:
            logger.warning(f"保存对话历史失败: {e}")
            if self.db:
                self.db.rollback()
    
    async def intelligent_chat(
        self,
        message: str,
        session_id: Optional[str] = None,
        strategy: SearchStrategy = SearchStrategy.AUTO,
        stream: bool = False
    ) -> str:
        """智能聊天 - 自动搜索并生成回复的便捷接口"""
        if stream:
            return self.generate_stream_response(
                message=message,
                session_id=session_id,
                use_intelligent_search=True,
                search_strategy=strategy
            )
        else:
            return await self.generate_response(
                message=message,
                session_id=session_id,
                use_intelligent_search=True,
                search_strategy=strategy
            )
    
    async def clear_conversation_history(self, session_id: str):
        """清除对话历史"""
        try:
            cache_key = f"chat_history:{session_id}"
            self.redis_client.delete(cache_key)
        except Exception as e:
            logger.warning(f"清除对话历史失败: {e}")
    
    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        return {
            "chat_model": settings.chat_model,
            "max_tokens": settings.max_tokens,
            "temperature": settings.temperature,
            "base_url": settings.SILICONFLOW_BASE_URL
        }
    
    async def test_connection(self) -> bool:
        """测试LLM连接"""
        try:
            response = self.client.chat.completions.create(
                model=settings.chat_model,
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=10
            )
            return True
        except Exception as e:
            logger.error(f"LLM连接测试失败: {e}")
            return False