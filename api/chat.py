"""聊天API路由"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import json
import time
import logging

from core.database import get_db
from models.schemas import (
    ChatRequest, ChatResponse, ChatSessionCreate, ChatSessionResponse,
    ChatMessage, BaseResponse
)
from models.database import ChatSession, ChatMessage as DBChatMessage, User
from services.chat_service import ChatService
from services.knowledge_service import KnowledgeService
from services.search_service import SearchService

router = APIRouter()
logger = logging.getLogger(__name__)

# 服务实例
chat_service = ChatService()
knowledge_service = KnowledgeService()
search_service = SearchService()

@router.post("/sessions", response_model=BaseResponse)
async def create_chat_session(
    session_data: ChatSessionCreate,
    db: Session = Depends(get_db)
):
    """创建聊天会话"""
    try:
        # 检查用户是否存在
        user = db.query(User).filter(User.id == session_data.user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        # 创建会话
        session = ChatSession(
            user_id=session_data.user_id,
            title=session_data.title
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        
        return BaseResponse(
            success=True,
            message="会话创建成功",
            data=ChatSessionResponse.from_orm(session)
        )
    except Exception as e:
        logger.error(f"创建会话失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sessions", response_model=BaseResponse)
async def get_chat_sessions(
    user_id: int,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """获取用户的聊天会话列表"""
    try:
        sessions = db.query(ChatSession).filter(
            ChatSession.user_id == user_id,
            ChatSession.is_active == True
        ).offset(skip).limit(limit).all()
        
        session_responses = []
        for session in sessions:
            message_count = db.query(DBChatMessage).filter(
                DBChatMessage.session_id == session.id
            ).count()
            
            session_data = ChatSessionResponse.from_orm(session)
            session_data.message_count = message_count
            session_responses.append(session_data)
        
        return BaseResponse(
            success=True,
            message="获取会话列表成功",
            data=session_responses
        )
    except Exception as e:
        logger.error(f"获取会话列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sessions/{session_id}/messages", response_model=BaseResponse)
async def get_chat_messages(
    session_id: int,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """获取会话的聊天消息"""
    try:
        # 检查会话是否存在
        session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
        if not session:
            raise HTTPException(status_code=404, detail="会话不存在")
        
        messages = db.query(DBChatMessage).filter(
            DBChatMessage.session_id == session_id
        ).order_by(DBChatMessage.created_at.asc()).offset(skip).limit(limit).all()
        
        message_responses = [ChatMessage.from_orm(msg) for msg in messages]
        
        return BaseResponse(
            success=True,
            message="获取消息列表成功",
            data=message_responses
        )
    except Exception as e:
        logger.error(f"获取消息列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/chat/stream")
async def chat_stream(
    request: ChatRequest,
    db: Session = Depends(get_db)
):
    """流式聊天接口"""
    async def generate():
        try:
            start_time = time.time()
            
            # 如果没有提供session_id，创建新会话
            if not request.session_id:
                user_id = 1  # 临时硬编码
                session = ChatSession(
                    user_id=user_id,
                    title=request.message[:50] + "..." if len(request.message) > 50 else request.message
                )
                db.add(session)
                db.commit()
                db.refresh(session)
                session_id = session.id
            else:
                session_id = request.session_id
                session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
                if not session:
                    yield f"data: {json.dumps({'error': '会话不存在'}, ensure_ascii=False)}\n\n"
                    return
            
            # 保存用户消息
            user_message = DBChatMessage(
                session_id=session_id,
                role="user",
                content=request.message,
                use_knowledge_base=request.use_knowledge_base,
                use_web_search=request.use_web_search
            )
            db.add(user_message)
            db.commit()
            
            # 处理知识库和联网搜索
            knowledge_sources = []
            web_search_results = []
            
            if request.use_knowledge_base:
                try:
                    kb_results = await knowledge_service.search(
                        query=request.message,
                        top_k=10
                    )
                    knowledge_sources = kb_results
                except Exception as e:
                    logger.warning(f"知识库搜索失败: {e}")
            
            if request.use_web_search:
                should_web_search = (
                    len(knowledge_sources) < 3 or
                    (knowledge_sources and max([r.get('score', 0) for r in knowledge_sources]) < 0.8)
                )
                
                if should_web_search:
                    try:
                        web_results = await search_service.web_search(
                            query=request.message,
                            max_results=5
                        )
                        web_search_results = web_results
                    except Exception as e:
                        logger.warning(f"联网搜索失败: {e}")
            
            # 发送开始信号
            yield f"data: {json.dumps({'type': 'start', 'session_id': session_id}, ensure_ascii=False)}\n\n"
            
            # 流式生成回复
            full_response = ""
            async for chunk in chat_service.generate_stream_response(
                message=request.message,
                knowledge_sources=knowledge_sources,
                web_search_results=web_search_results,
                session_id=session_id
            ):
                full_response += chunk
                yield f"data: {json.dumps({'type': 'content', 'content': chunk}, ensure_ascii=False)}\n\n"
            
            # 保存助手消息
            assistant_message = DBChatMessage(
                session_id=session_id,
                role="assistant",
                content=full_response,
                knowledge_sources=json.dumps(knowledge_sources, ensure_ascii=False) if knowledge_sources else None,
                web_search_results=json.dumps(web_search_results, ensure_ascii=False) if web_search_results else None
            )
            db.add(assistant_message)
            db.commit()
            
            # 发送完成信号
            response_time = time.time() - start_time
            yield f"data: {json.dumps({
                'type': 'end',
                'response_time': response_time,
                'knowledge_sources': knowledge_sources,
                'web_search_results': web_search_results
            }, ensure_ascii=False)}\n\n"
            
        except Exception as e:
            logger.error(f"流式聊天失败: {e}")
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)}, ensure_ascii=False)}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream"
        }
    )

@router.post("/chat", response_model=BaseResponse)
async def chat(
    request: ChatRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """聊天接口（非流式）"""
    try:
        start_time = time.time()
        
        # 如果没有提供session_id，创建新会话
        if not request.session_id:
            # 这里简化处理，实际应该从认证中获取用户ID
            user_id = 1  # 临时硬编码
            session = ChatSession(
                user_id=user_id,
                title=request.message[:50] + "..." if len(request.message) > 50 else request.message
            )
            db.add(session)
            db.commit()
            db.refresh(session)
            session_id = session.id
        else:
            session_id = request.session_id
            session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
            if not session:
                raise HTTPException(status_code=404, detail="会话不存在")
        
        # 保存用户消息
        user_message = DBChatMessage(
            session_id=session_id,
            role="user",
            content=request.message,
            use_knowledge_base=request.use_knowledge_base,
            use_web_search=request.use_web_search
        )
        db.add(user_message)
        db.commit()
        
        # 处理聊天请求
        knowledge_sources = []
        web_search_results = []
        
        # 知识库搜索
        if request.use_knowledge_base:
            try:
                kb_results = await knowledge_service.search(
                    query=request.message,
                    top_k=10
                )
                knowledge_sources = kb_results
            except Exception as e:
                logger.warning(f"知识库搜索失败: {e}")
        
        # 联网搜索（智能判断）
        if request.use_web_search:
            # 简单的智能判断逻辑：如果知识库结果不足或置信度低，则进行联网搜索
            should_web_search = (
                len(knowledge_sources) < 3 or
                (knowledge_sources and max([r.get('score', 0) for r in knowledge_sources]) < 0.8)
            )
            
            if should_web_search:
                try:
                    web_results = await search_service.web_search(
                        query=request.message,
                        max_results=5
                    )
                    web_search_results = web_results
                except Exception as e:
                    logger.warning(f"联网搜索失败: {e}")
        
        # 生成回复
        try:
            response_text = await chat_service.generate_response(
                message=request.message,
                knowledge_sources=knowledge_sources,
                web_search_results=web_search_results,
                session_id=session_id
            )
        except Exception as e:
            logger.error(f"生成回复失败: {e}")
            response_text = "抱歉，我现在无法处理您的请求，请稍后再试。"
        
        # 保存助手回复
        assistant_message = DBChatMessage(
            session_id=session_id,
            role="assistant",
            content=response_text,
            knowledge_sources=json.dumps(knowledge_sources, ensure_ascii=False) if knowledge_sources else None,
            web_search_results=json.dumps(web_search_results, ensure_ascii=False) if web_search_results else None
        )
        db.add(assistant_message)
        db.commit()
        
        response_time = time.time() - start_time
        
        return BaseResponse(
            success=True,
            message="聊天成功",
            data=ChatResponse(
                message=response_text,
                session_id=session_id,
                knowledge_sources=knowledge_sources,
                web_search_results=web_search_results,
                response_time=response_time
            )
        )
        
    except Exception as e:
        logger.error(f"聊天处理失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/chat/stream")
async def chat_stream(
    request: ChatRequest,
    db: Session = Depends(get_db)
):
    """流式聊天接口"""
    async def generate_stream():
        try:
            # 类似非流式的处理逻辑，但返回流式响应
            yield f"data: {json.dumps({'type': 'start', 'message': '开始处理您的请求...'}, ensure_ascii=False)}\n\n"
            
            # 这里应该实现真正的流式生成逻辑
            # 暂时返回简单的模拟响应
            response_text = "这是一个模拟的流式响应。在实际实现中，这里会调用真正的LLM API进行流式生成。"
            
            for i, char in enumerate(response_text):
                yield f"data: {json.dumps({'type': 'content', 'content': char}, ensure_ascii=False)}\n\n"
                # 模拟延迟
                import asyncio
                await asyncio.sleep(0.05)
            
            yield f"data: {json.dumps({'type': 'end', 'message': '响应完成'}, ensure_ascii=False)}\n\n"
            
        except Exception as e:
            logger.error(f"流式聊天失败: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )

@router.delete("/sessions/{session_id}", response_model=BaseResponse)
async def delete_chat_session(
    session_id: int,
    db: Session = Depends(get_db)
):
    """删除聊天会话"""
    try:
        session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
        if not session:
            raise HTTPException(status_code=404, detail="会话不存在")
        
        # 软删除
        session.is_active = False
        db.commit()
        
        return BaseResponse(
            success=True,
            message="会话删除成功"
        )
    except Exception as e:
        logger.error(f"删除会话失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))