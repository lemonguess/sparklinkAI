"""聊天服务"""
import logging
from typing import List, Dict, Any, Optional, AsyncGenerator
import json
import time

import openai
from openai import OpenAI

from core.config import settings
from core.database import get_redis

logger = logging.getLogger(__name__)

class ChatService:
    """聊天服务类"""
    
    def __init__(self):
        self.client = OpenAI(
            api_key=settings.SILICONFLOW_API_KEY,
            base_url=settings.SILICONFLOW_BASE_URL
        )
        self.redis_client = get_redis()
    
    async def generate_response(
        self,
        message: str,
        knowledge_sources: List[Dict[str, Any]] = None,
        web_search_results: List[Dict[str, Any]] = None,
        session_id: Optional[int] = None,
        stream: bool = False
    ) -> str:
        """生成聊天回复"""
        try:
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
        session_id: Optional[int] = None
    ) -> AsyncGenerator[str, None]:
        """生成流式聊天回复"""
        try:
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
    
    async def _get_conversation_history(self, session_id: Optional[int]) -> List[Dict[str, str]]:
        """获取对话历史"""
        if not session_id:
            return []
        
        try:
            # 从Redis缓存获取
            cache_key = f"chat_history:{session_id}"
            cached_history = self.redis_client.get(cache_key)
            
            if cached_history:
                return json.loads(cached_history)
            
            # 如果缓存中没有，从数据库获取（这里简化处理）
            # 实际项目中应该从数据库查询最近的对话记录
            return []
            
        except Exception as e:
            logger.warning(f"获取对话历史失败: {e}")
            return []
    
    async def save_conversation_history(
        self,
        session_id: int,
        user_message: str,
        assistant_message: str
    ):
        """保存对话历史到缓存"""
        try:
            cache_key = f"chat_history:{session_id}"
            
            # 获取现有历史
            existing_history = await self._get_conversation_history(session_id)
            
            # 添加新的对话
            existing_history.extend([
                {"role": "user", "content": user_message},
                {"role": "assistant", "content": assistant_message}
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
            
        except Exception as e:
            logger.warning(f"保存对话历史失败: {e}")
    
    async def clear_conversation_history(self, session_id: int):
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
            "base_url": settings.OPENAI_BASE_URL
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