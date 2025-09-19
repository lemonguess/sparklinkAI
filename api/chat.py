"""聊天API路由"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Body
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import json
import time
import logging
import uuid
from models.enums import SearchStrategy
from core.database import get_db
from core.config import settings
from models.schemas import (
    ChatRequest, ChatResponse, ChatSessionCreate, ChatSessionResponse,
    ChatSessionDelete, ChatSessionUpdateTitle, ChatMessage, BaseResponse,
    ChatMessageDelete
)
from models.database import ChatSession, ChatMessage as DBChatMessage, User
from services.chat_service import ChatService
from services.search_service import SearchService

router = APIRouter()
logger = logging.getLogger(__name__)

from core.shared_state import active_streams

# 服务实例
search_service = SearchService()

@router.post("/create_session", response_model=BaseResponse)
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
    user_id: str = settings.default_user_id,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """获取用户的聊天会话列表"""
    try:
        sessions = db.query(ChatSession).filter(
            ChatSession.user_id == user_id,
            ChatSession.is_active == True
        ).order_by(ChatSession.updated_at.desc()).offset(skip).limit(limit).all()
        
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

@router.post("/sessions/delete", response_model=BaseResponse)
async def delete_chat_session(
    request: ChatSessionDelete,
    db: Session = Depends(get_db)
):
    """删除聊天会话（物理删除）"""
    try:
        # 检查会话是否存在
        session = db.query(ChatSession).filter(ChatSession.id == request.session_id).first()
        if not session:
            raise HTTPException(status_code=404, detail="会话不存在")
        
        # 物理删除：先删除会话相关的消息
        db.query(DBChatMessage).filter(DBChatMessage.session_id == request.session_id).delete()
        
        # 再删除会话本身
        db.delete(session)
        db.commit()
        
        return BaseResponse(
            success=True,
            message="会话删除成功",
            data={"session_id": request.session_id}
        )
    except Exception as e:
        logger.error(f"删除会话失败: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/sessions/update_title", response_model=BaseResponse)
async def update_session_title(
    request: ChatSessionUpdateTitle,
    db: Session = Depends(get_db)
):
    """修改会话标题"""
    try:
        # 查找会话
        session = db.query(ChatSession).filter(ChatSession.id == request.session_id).first()
        if not session:
            raise HTTPException(status_code=404, detail="会话不存在")
        
        # 更新标题
        session.title = request.title
        db.commit()
        
        return BaseResponse(
            success=True,
            message="会话标题修改成功",
            data={
                "session_id": session.id,
                "title": session.title
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"修改会话标题失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/messages/delete", response_model=BaseResponse)
async def delete_chat_message(
    request: ChatMessageDelete,
    db: Session = Depends(get_db)
):
    """删除聊天消息（物理删除）"""
    try:
        # 检查消息是否存在
        message = db.query(DBChatMessage).filter(DBChatMessage.id == request.message_id).first()
        if not message:
            raise HTTPException(status_code=404, detail="消息不存在")
        
        # 物理删除消息
        db.delete(message)
        db.commit()
        
        return BaseResponse(
            success=True,
            message="消息删除成功",
            data={"message_id": request.message_id}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除消息失败: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sessions/{session_id}/messages", response_model=BaseResponse)
async def get_chat_messages(
    session_id: str,
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
        
        # 优化查询：添加索引提示并限制返回字段
        messages = db.query(DBChatMessage).filter(
            DBChatMessage.session_id == session_id
        ).order_by(DBChatMessage.sequence_number.asc()).offset(skip).limit(limit).all()
        
        # 手动构建响应对象，避免ORM的额外开销
        message_responses = []
        for msg in messages:
            message_responses.append(ChatMessage(
                id=msg.id,
                role=msg.role,
                content=msg.content,
                sequence_number=msg.sequence_number,
                created_at=msg.created_at,
                sources={
                    'knowledge_sources': json.loads(msg.knowledge_sources) if msg.knowledge_sources else [],
                    'web_search_results': json.loads(msg.web_search_results) if msg.web_search_results else []
                } if (msg.knowledge_sources or msg.web_search_results) else None,
                thinking_process=msg.thinking_process
            ))
        
        return BaseResponse(
            success=True,
            message="获取消息列表成功",
            data=message_responses
        )
    except Exception as e:
        logger.error(f"获取消息列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/stream")
async def chat_stream(
    request: ChatRequest,
    db: Session = Depends(get_db)
):
    """流式聊天接口"""
    request_id = uuid.uuid4().hex
    active_streams[request_id] = {"cancelled": False}

    async def generate():
        try:
            # 发送请求ID
            yield f"data: {json.dumps({'type': 'request_id', 'request_id': request_id}, ensure_ascii=False)}\n\n"
            # 发送start事件，让前端创建消息元素
            yield f"data: {json.dumps({'type': 'start'}, ensure_ascii=False)}\n\n"
            start_time = time.time()
            # 初始化ChatService
            chat_service = ChatService(db=db)
            # 检查session_id是否提供
            if not request.session_id:
                yield f"data: {json.dumps({'error': '请先创建会话'}, ensure_ascii=False)}\n\n"
                return
            # 处理新会话创建
            if request.is_first:
                user_id = request.user_id or settings.default_user_id
                new_session = ChatSession(
                    id=request.session_id,  # 使用前端传入的UUID
                    user_id=user_id,
                    title="新会话"  # 使用临时标题
                )
                db.add(new_session)
                db.commit()
                db.refresh(new_session)
                session_id = new_session.id
                session = new_session
                
                # 发送会话信息给前端（使用临时标题）
                yield f"data: {json.dumps({'type': 'session_info', 'session_id': session_id, 'session_name': '新会话'}, ensure_ascii=False)}\n\n"
            else:
                session_id = request.session_id
                session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
                if not session:
                    yield f"data: {json.dumps({'error': '会话不存在'}, ensure_ascii=False)}\n\n"
                    return
            # 使用intelligent_chat进行流式生成
            full_response = ""
            thinking_process = ""
            was_cancelled = False
            try:
                search_result = await chat_service.intelligent_search(
                    query=request.message,
                    strategy=SearchStrategy(request.search_strategy),
                )
                yield f"data: {json.dumps({'type': 'source', 'content': search_result}, ensure_ascii=False)}\n\n"
                async for _type, chunk in chat_service.generate_stream_response(
                    message=request.message,
                    knowledge_sources=search_result['knowledge_results'],
                    web_search_results=search_result['web_results'],
                    request_id=request_id,
                    session_id=session_id,
                ):
                    if _type == 'content':
                        full_response += chunk
                    elif _type == 'think':
                        thinking_process += chunk
                    
                    yield f"data: {json.dumps({'type': _type, 'content': chunk}, ensure_ascii=False)}\n\n"
                    # 检查是否被取消
                    if request_id in active_streams and active_streams[request_id].get('cancelled', False):
                        was_cancelled = True
                        logger.info(f"🛑 检测到流式响应被取消，已生成内容长度: {len(full_response)}")
                        break
            except Exception as e:
                logger.error(f"流式生成过程中出错: {e}")
                yield f"data: {json.dumps({'type': 'content', 'content': "抱歉，生成回复时出现错误。"}, ensure_ascii=False)}\n\n"
                if not full_response:
                    full_response = "抱歉，生成回复时出现错误。"
            
            # 处理保存逻辑
            if was_cancelled:
                # 如果被取消，使用ChatService的中断处理方法
                await chat_service.handle_stream_interruption(
                    request_id=request_id,
                    session_id=session_id,
                    user_message=request.message,
                    partial_response=full_response
                )
            elif full_response.strip():  # 正常完成且有内容
                try:
                    await chat_service.save_conversation_history(
                        session_id=session_id,
                        user_message=request.message,
                        assistant_message=full_response,
                        knowledge_sources=search_result['knowledge_results'],
                        web_search_results=search_result['web_results'],
                        thinking_process=thinking_process if thinking_process.strip() else None
                    )
                    logger.info(f"💾 已保存完整的对话记录，内容长度: {len(full_response)}, 思考过程长度: {len(thinking_process)}")
                    
                    # 如果是新会话，异步生成并推送标题
                    if request.is_first:
                        try:
                            session_title = await chat_service.generate_session_title_from_input(request.message)
                            
                            # 更新数据库中的会话标题
                            db.query(ChatSession).filter(ChatSession.id == session_id).update(
                                {"title": session_title}, synchronize_session=False
                            )
                            db.commit()
                            
                            # 推送标题更新给前端
                            yield f"data: {json.dumps({'type': 'title_update', 'session_id': session_id, 'title': session_title}, ensure_ascii=False)}\n\n"
                            
                            logger.info(f"会话标题已生成并推送: {session_id} -> {session_title}")
                            
                        except Exception as e:
                            logger.error(f"异步生成标题失败: {e}")
                            # 如果生成失败，使用用户消息的前几个字符作为标题
                            fallback_title = request.message[:10] + "..." if len(request.message) > 10 else request.message
                            db.query(ChatSession).filter(ChatSession.id == session_id).update(
                                {"title": fallback_title}, synchronize_session=False
                            )
                            db.commit()
                            yield f"data: {json.dumps({'type': 'title_update', 'session_id': session_id, 'title': fallback_title}, ensure_ascii=False)}\n\n"
                    
                except Exception as e:
                    logger.error(f"保存对话历史失败: {e}")
            
            # 发送完成信号
            response_time = time.time() - start_time
            yield f"data: {json.dumps({
                'type': 'end',
                'response_time': response_time
            }, ensure_ascii=False)}\n\n"
            
        except Exception as e:
            logger.error(f"流式聊天失败: {e}")
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)}, ensure_ascii=False)}\n\n"
        finally:
            # 清理
            if request_id in active_streams:
                del active_streams[request_id]
                logger.info(f"Cleaned up active stream for request_id: {request_id}")
    
    return StreamingResponse(
        generate(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream"
        }
    )

@router.post("/stop", summary="停止流式生成")
async def stop_stream(
    request_id: str = Body(..., embed=True),
    db: Session = Depends(get_db)
):
    """停止一个正在进行的流式生成"""
    if request_id not in active_streams:
        raise HTTPException(status_code=404, detail="Request ID not found or stream already completed.")
    
    # 使用ChatService处理停止逻辑
    chat_service = ChatService(db=db)
    success = await chat_service.stop_stream_generation(request_id)
    
    if success:
        return {"status": "stopping"}
    else:
        raise HTTPException(status_code=500, detail="Failed to stop stream generation.")
