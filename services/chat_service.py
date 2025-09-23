"""聊天服务"""
import logging
from typing import List, Dict, Any, Optional, AsyncGenerator
import json
import time
import uuid
from openai import AsyncOpenAI
from sqlalchemy.orm import Session
from core.config import settings
from core.database import get_db
from core import active_streams
from models.database import ChatMessage as DBChatMessage
from services.search_service import SearchService
from models.enums import SearchStrategy
from utils.extract_keyword import extract_keywords, need_web_search
logger = logging.getLogger(__name__)





class ChatService:
    """聊天服务类 - 集成智能搜索功能"""
    
    def __init__(self, db: Optional[Session] = None):
        self.client = AsyncOpenAI(
            api_key=settings.SILICONFLOW_API_KEY,
            base_url=settings.SILICONFLOW_BASE_URL
        )
        self.db = db  # 数据库会话
        
        # 集成搜索服务
        # 使用SearchService替代KnowledgeService
        self.knowledge_service = SearchService()
        self.search_service = SearchService()
    
    async def intelligent_search(
        self,
        query: str,
        strategy: SearchStrategy = SearchStrategy.AUTO,
        kg_max_results: int = 5,
        web_max_results: int = 10,
        similarity_threshold: float = settings.knowledge_confidence_threshold,
        group_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """智能搜索 - 整合知识库和网络搜索"""
        logger.info(f"🚀 开始智能搜索: {query}")
        
        knowledge_results = []
        web_results = []
        decision_reasoning = ""
        
        try:
            if strategy != SearchStrategy.NONE:
                logger.info("🔍 执行知识库搜索")
                knowledge_results = await self.knowledge_service.knowledge_search(
                    query=query,
                    group_id=group_id,
                    top_k=kg_max_results,
                    similarity_threshold=similarity_threshold,
                )
            # 第三步：判断是否需要网络搜索
            if strategy == SearchStrategy.WEB_ONLY:
                decision_reasoning = "仅需网络搜索"
                query_string = extract_keywords(query)
                web_results = await self.search_service.web_search(
                    query=query_string,
                    max_results=web_max_results
                )
            elif strategy == SearchStrategy.KNOWLEDGE_ONLY:
                decision_reasoning = "仅需知识库搜索"
                pass
            elif strategy == SearchStrategy.HYBRID:
                decision_reasoning = "混合检索--知识库+网络搜索"
                query_string = extract_keywords(query)
                web_results = await self.search_service.web_search(
                    query=query_string,
                    max_results=web_max_results
                )
            elif strategy == SearchStrategy.AUTO:
                if need_web_search(query):
                    decision_reasoning = "根据关键词判断需要网络搜索"
                    logger.info("🌐 执行网络搜索")
                    query_string = extract_keywords(query)
                    web_results = await self.search_service.web_search(
                        query=query_string,
                        max_results=web_max_results
                    )
                else:
                    decision_reasoning = "根据关键词判断不需要网络搜索"
            logger.info(f"✅ 智能搜索完成: 知识库{len(knowledge_results)}条, 网络{len(web_results)}条")
            logger.info(f"决策依据: {decision_reasoning}")
            return {
                'success': True,
                'knowledge_results': knowledge_results,
                'web_results': web_results
            }
        except Exception as e:
            logger.error(f"智能搜索失败: {e}", exc_info=True)
            return {
                'success': False,
                'knowledge_results': [],
                'web_results': []
            }
    
    async def generate_response(
        self,
        message: str,
        knowledge_sources: List[Dict[str, Any]] = None,
        web_search_results: List[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
        stream: bool = False,
    ) -> str:
        """生成聊天回复"""
        try:
            # # 如果启用智能搜索，则自动获取搜索结果
            # if use_intelligent_search:
            #     search_result = await self.intelligent_search(
            #         query=message,
            #         strategy=search_strategy,
            #         max_results=5
            #     )
                
            #     if search_result.get('success', False):
            #         knowledge_sources = search_result.get('knowledge_results', [])
            #         web_search_results = search_result.get('web_results', [])
            #         logger.info(f"智能搜索获得: 知识库{len(knowledge_sources)}条, 网络{len(web_search_results)}条")
            
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
                messages.extend(conversation_history[-settings.conversation_history_limit:])  # 最近20条消息（10轮对话）
            
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
        knowledge_sources: List = None,
        web_search_results: List = None,
        session_id: Optional[str] = None,
        request_id: Optional[str] = None,
        max_tokens: Optional[int] = settings.max_tokens,
        temperature: Optional[float] = settings.temperature,
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
                messages.extend(conversation_history[-settings.conversation_history_limit:])
            
            messages.append({"role": "user", "content": message})
            
            # 流式生成
            try:
                response = await self.client.chat.completions.create(
                    model=settings.chat_model,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    stream=True
                )
                
                async for chunk in response:
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
                        yield 'content', content
                        
                    if hasattr(chunk.choices[0].delta, 'reasoning_content') and chunk.choices[0].delta.reasoning_content:
                        reasoning = chunk.choices[0].delta.reasoning_content
                        logger.info(f"🧠 推理内容: '{reasoning}' (request_id: {request_id})")
                        yield 'think', reasoning
                        
            except Exception as e:
                logger.error(f"流式生成失败: {e}")
                yield "抱歉，生成回复时出现错误。"
                
        except Exception as e:
            logger.error(f"流式聊天服务失败: {e}", exc_info=True)
            yield "抱歉，我现在无法处理您的请求。"
    
    async def _generate_single_response(self, messages: List[Dict[str, str]]) -> str:
        """生成单次回复"""
        try:
            response = await self.client.chat.completions.create(
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
        base_prompt = settings.base_prompt
        
        # 添加知识库信息
        if knowledge_sources:
            base_prompt += "\n\n**相关知识库内容：**\n"
            context_parts = []
            for i, source in enumerate(knowledge_sources, 1):
                context_parts.append(
                    f"[知识库片段{i}]\n"
                    f"标题: {source['title']}\n"
                    f"内容: {source['content']}\n"
                    f"来源: {source['source_path'] if source['doc_type'] != 'file' else '暂无'}\n"
                )
            context_text = "\n".join(context_parts)
            base_prompt += context_text
        
        # 添加搜索结果
        if web_search_results:
            context_parts = []
            base_prompt += "\n\n**相关联网搜索结果：**\n"
            for i, result in enumerate(web_search_results, 1):
                context_parts.append(
                    f"[网络搜索结果{i}]\n"
                    f"标题: {result['title']}\n"
                    f"内容: {result['content']}\n"
                    f"来源: {result['url']}\n"
                )
            context_text = "\n".join(context_parts)
            base_prompt += context_text
        
        return base_prompt.strip()
    
    async def _get_conversation_history(self, session_id: Optional[str]) -> List[Dict[str, str]]:
        """获取会话的对话历史（仅从MySQL获取）"""
        if not session_id:
            return []
        
        try:
            # 直接从MySQL数据库获取
            if self.db:
                logger.info(f"从MySQL查询会话 {session_id} 的聊天历史")
                messages = self.db.query(DBChatMessage).filter(
                    DBChatMessage.session_id == session_id
                ).order_by(DBChatMessage.created_at.asc()).limit(50).all()
                
                # 转换为简化格式用于对话上下文
                simple_history = []
                for msg in messages:
                    # 对于助手消息，如果有思考过程，只使用content部分（不包含thinking_process）
                    # 对于用户消息，直接使用content
                    content = msg.content
                    if msg.role == "assistant" and msg.thinking_process:
                        # 助手消息只使用答案部分，不包含思考过程
                        content = msg.content
                    
                    simple_history.append({"role": msg.role, "content": content})
                
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
        assistant_request_id: Optional[str] = None,
        thinking_process: Optional[str] = None
    ):
        """保存对话历史到MySQL数据库"""
        try:
            # 生成请求ID
            user_req_id = user_request_id or uuid.uuid4().hex
            assistant_req_id = assistant_request_id or uuid.uuid4().hex
            
            # 保存到MySQL数据库
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
                    web_search_results=json.dumps(web_search_results, ensure_ascii=False) if web_search_results else None,
                    thinking_process=thinking_process
                )
                self.db.add(assistant_msg)
                self.db.commit()
                logger.info(f"已保存会话 {session_id} 的对话到MySQL数据库")
            else:
                logger.warning("数据库会话未初始化，无法保存到MySQL")
            
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
        """清除对话历史（仅从MySQL删除）"""
        try:
            if self.db:
                # 从MySQL删除会话的所有消息
                self.db.query(DBChatMessage).filter(
                    DBChatMessage.session_id == session_id
                ).delete()
                self.db.commit()
                logger.info(f"已从MySQL删除会话 {session_id} 的所有消息")
        except Exception as e:
            logger.warning(f"清除对话历史失败: {e}")
            if self.db:
                self.db.rollback()
    
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
            
            response = await self.client.chat.completions.create(
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
            
            response = await self.client.chat.completions.create(
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
            response = await self.client.chat.completions.create(
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