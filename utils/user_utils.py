"""用户相关工具函数"""
import logging
from core.config import settings
from core.database import db_manager
from models.database import User

logger = logging.getLogger(__name__)


def create_default_user():
    """创建默认用户
    
    检查默认用户是否存在，如果不存在则根据配置文件创建默认用户。
    如果用户已存在，则跳过创建过程。
    
    Returns:
        bool: 创建成功或用户已存在返回True，创建失败返回False
    """
    session = db_manager.get_session()
    
    try:
        # 检查默认用户是否存在
        default_user_id = settings.default_user_id
        existing_user = session.query(User).filter(User.id == default_user_id).first()
        
        if existing_user:
            logger.info(f"默认用户已存在: {existing_user.username} (ID: {existing_user.id})")
            return True
        
        # 创建默认用户
        test_user = User(
            id=default_user_id,
            username=settings.default_username,
            email=settings.default_email,
            is_active=settings.default_user_active
        )
        
        session.add(test_user)
        session.commit()
        
        logger.info(f"成功创建默认用户: {test_user.username} (ID: {test_user.id})")
        return True
        
    except Exception as e:
        session.rollback()
        # 如果是主键重复错误，说明用户已存在，这是正常情况
        if "Duplicate entry" in str(e) and "PRIMARY" in str(e):
            logger.info("默认用户已存在（检测到主键重复）")
            return True
        else:
            logger.error(f"创建默认用户失败: {e}")
            return False
    finally:
        session.close()


def get_default_user():
    """获取默认用户信息
    
    Returns:
        User: 默认用户对象，如果不存在返回None
    """
    session = db_manager.get_session()
    
    try:
        default_user_id = settings.default_user_id
        user = session.query(User).filter(User.id == default_user_id).first()
        return user
    except Exception as e:
        logger.error(f"获取默认用户失败: {e}")
        return None
    finally:
        session.close()


def ensure_default_user():
    """确保默认用户存在
    
    这是一个便捷函数，会先尝试创建默认用户，然后返回用户信息。
    
    Returns:
        User: 默认用户对象，如果创建或获取失败返回None
    """
    if create_default_user():
        return get_default_user()
    return None