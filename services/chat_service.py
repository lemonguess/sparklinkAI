"""聊天服务"""
import logging
from typing import List, Dict, Any, Optional, AsyncGenerator
import json
import time
import uuid
from openai import OpenAI
from sqlalchemy.orm import Session
from core.config import settings
from core.database import get_redis, get_db
from core.shared_state import active_streams
from models.database import ChatMessage as DBChatMessage
from services.knowledge_service import KnowledgeService
from services.search_service import SearchService
from models.enums import SearchStrategy
logger = logging.getLogger(__name__)





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
            logger.info(f"✅ 智能搜索完成: 知识库{len(knowledge_results)}条, 网络{len(web_results)}条")
            
            return {
                'knowledge_results': knowledge_results,
                'web_results': web_results,
                'decision_reasoning': decision_reasoning
            }
        except Exception as e:
            logger.error(f"智能搜索失败: {e}", exc_info=True)
            return {
                'knowledge_results': [],
                'web_results': [],
                'decision_reasoning': f"智能搜索失败: {e}"
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
        request_id: Optional[str] = None,  # 添加 request_id
        use_intelligent_search: bool = False,
        search_strategy: SearchStrategy = SearchStrategy.AUTO
    ) -> AsyncGenerator[str, None]:
        """生成流式聊天回复"""
        try:
            # # 如果启用智能搜索，则自动获取搜索结果
            if use_intelligent_search:
                search_result = await self.intelligent_search(
                    query=message,
                    strategy=search_strategy,
                    max_results=10
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
                    # 检查是否被取消
                    if request_id and request_id in active_streams:
                        if active_streams[request_id].get('cancelled', False):
                            logger.info(f"🛑 流式响应被用户取消: {request_id}")
                            break
                    
                    if not chunk.choices:
                        continue
                    
                    if chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        logger.info(f"📤 流式输出: '{content}' (request_id: {request_id})")
                        yield content
                        
                    if hasattr(chunk.choices[0].delta, 'reasoning_content') and chunk.choices[0].delta.reasoning_content:
                        reasoning = chunk.choices[0].delta.reasoning_content
                        logger.info(f"🧠 推理内容: '{reasoning}' (request_id: {request_id})")
                        yield reasoning
                        
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
        user_request_id: Optional[str] = None,
        assistant_request_id: Optional[str] = None
    ):
        """保存对话历史到MySQL和Redis缓存"""
        try:
            # 生成请求ID
            user_req_id = user_request_id or uuid.uuid4().hex
            assistant_req_id = assistant_request_id or uuid.uuid4().hex
            
            # 1. 保存到MySQL数据库
            if self.db:
                # 获取当前会话的最大序号
                max_sequence = self.db.query(DBChatMessage.sequence_number).filter(
                    DBChatMessage.session_id == session_id
                ).order_by(DBChatMessage.sequence_number.desc()).first()
                
                next_sequence = (max_sequence[0] + 1) if max_sequence and max_sequence[0] is not None else 1
                
                # 保存用户消息
                user_msg = DBChatMessage(
                    session_id=session_id,
                    request_id=user_req_id,
                    role="user",
                    content=user_message,
                    sequence_number=next_sequence
                )
                self.db.add(user_msg)
                
                # 保存助手消息
                assistant_msg = DBChatMessage(
                    session_id=session_id,
                    request_id=assistant_req_id,
                    role="assistant",
                    content=assistant_message,
                    sequence_number=next_sequence + 1,
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
            
            # 添加新的对话
            existing_history.extend([
                {
                    "role": "user", 
                    "content": user_message,
                    "created_at": time.time()
                },
                {
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
    
    async def handle_stream_interruption(
        self,
        request_id: str,
        session_id: str,
        user_message: str,
        partial_response: str,
        knowledge_sources: Optional[List[Dict[str, Any]]] = None,
        web_search_results: Optional[List[Dict[str, Any]]] = None
    ):
        """处理流式响应中断，保存已生成的内容"""
        try:
            if partial_response.strip():  # 只有当有实际内容时才保存
                # 在消息末尾添加中断标记
                final_message = partial_response + "\n\n[此消息已被用户中断]"
                
                await self.save_conversation_history(
                    session_id=session_id,
                    user_message=user_message,
                    assistant_message=final_message,
                    knowledge_sources=knowledge_sources,
                    web_search_results=web_search_results
                )
                logger.info(f"💾 已保存被中断的对话记录，request_id: {request_id}, 内容长度: {len(final_message)}")
            else:
                logger.info(f"⚠️ 中断时无内容可保存，request_id: {request_id}")
        except Exception as e:
            logger.error(f"处理流式中断时保存对话历史失败: {e}")
    
    async def stop_stream_generation(self, request_id: str) -> bool:
        """停止流式生成并标记为已取消"""
        try:
            if request_id not in active_streams:
                logger.warning(f"尝试停止不存在的流式请求: {request_id}")
                return False
            
            active_streams[request_id]["cancelled"] = True
            logger.info(f"🛑 已标记流式请求为取消状态: {request_id}")
            return True
        except Exception as e:
            logger.error(f"停止流式生成失败: {e}")
            return False
    
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
    
    async def generate_session_title_from_input(self, user_message: str) -> str:
        """根据用户输入快速生成会话标题"""
        try:
            # 构建生成标题的提示
            prompt = f"""请根据用户的问题或需求，生成一个简洁、准确的会话标题（不超过15个字符）：

用户输入：{user_message[:100]}

要求：
1. 标题要简洁明了，能概括用户的问题或需求
2. 不超过15个字符
3. 不要包含标点符号
4. 直接返回标题，不要其他内容"""
            
            response = self.client.chat.completions.create(
                model=settings.chat_model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                max_tokens=30,
                temperature=0.5
            )
            
            title = response.choices[0].message.content.strip()
            # 确保标题长度不超过15个字符
            if len(title) > 15:
                title = title[:15]
            
            return title
            
        except Exception as e:
            logger.error(f"快速生成会话标题失败: {e}")
            # 如果生成失败，返回基于用户消息的简单标题
            return user_message[:12] + "..." if len(user_message) > 12 else user_message
    
    async def generate_session_title(self, user_message: str, assistant_message: str) -> str:
        """根据对话内容生成会话标题"""
        try:
            # 构建生成标题的提示
            prompt = f"""请根据以下对话内容，生成一个简洁、准确的会话标题（不超过20个字符）：

用户：{user_message[:200]}
助手：{assistant_message[:200]}

要求：
1. 标题要简洁明了，能概括对话主题
2. 不超过20个字符
3. 不要包含标点符号
4. 直接返回标题，不要其他内容"""
            
            response = self.client.chat.completions.create(
                model=settings.chat_model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                max_tokens=50,
                temperature=0.7
            )
            
            title = response.choices[0].message.content.strip()
            # 确保标题长度不超过20个字符
            if len(title) > 20:
                title = title[:20]
            
            return title
            
        except Exception as e:
            logger.error(f"生成会话标题失败: {e}")
            # 如果生成失败，返回基于用户消息的简单标题
            return user_message[:15] + "..." if len(user_message) > 15 else user_message
    
    async def test_connection(self) -> bool:
        """测试连接"""
        try:
            response = self.client.chat.completions.create(
                model=settings.chat_model,
                messages=[
                    {"role": "user", "content": "Hello"}
                ],
                max_tokens=10
            )
            return True
        except Exception as e:
            logger.error(f"连接测试失败: {e}")
            return False