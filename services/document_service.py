"""文档处理服务"""
import os
import logging
from typing import Dict, Any
import mimetypes

logger = logging.getLogger(__name__)

class DocumentService:
    """文档处理服务类"""
    
    def __init__(self):
        pass
    
    def extract_text_from_file(self, file_path: str, file_type: str) -> str:
        """从文件中提取文本内容"""
        try:
            # 需要调用 TextIn API 的文件类型
            textin_types = {'.pdf', '.doc', '.docx', '.ppt', '.pptx', '.jpg', '.jpeg', '.png', '.gif'}
            
            file_ext = os.path.splitext(file_path)[1].lower()
            
            if file_ext in textin_types:
                # 调用 TextIn API 处理
                return self._extract_with_textin(file_path)
            else:
                # 直接读取文件内容
                return self._extract_text_directly(file_path)
                
        except Exception as e:
            logger.error(f"提取文件内容失败 {file_path}: {e}")
            return ""
    
    def _extract_with_textin(self, file_path: str) -> str:
        """使用 TextIn API 提取文本"""
        try:
            # TODO: 实现 TextIn API 调用
            # 这里直接调用 TextIn API，支持 PDF、DOC、DOCX、PPT、PPTX、图片等格式
            return "TextIn API 功能待实现"
        except Exception as e:
            logger.error(f"TextIn API 提取失败 {file_path}: {e}")
            return ""
    
    def _extract_text_directly(self, file_path: str) -> str:
        """直接读取文件内容，处理不同编码格式"""
        try:
            # 尝试不同的编码格式
            encodings = ['utf-8', 'gbk', 'gb2312', 'big5', 'latin1']
            
            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        content = f.read()
                        logger.info(f"成功使用 {encoding} 编码读取文件: {file_path}")
                        return content
                except UnicodeDecodeError:
                    continue
                except Exception as e:
                    logger.warning(f"使用 {encoding} 编码读取文件失败: {e}")
                    continue
            
            # 如果所有编码都失败，尝试二进制读取并忽略错误
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    logger.warning(f"使用 utf-8 忽略错误模式读取文件: {file_path}")
                    return content
            except Exception as e:
                logger.error(f"二进制读取文件也失败: {e}")
                return ""
                
        except Exception as e:
            logger.error(f"直接读取文件失败 {file_path}: {e}")
            return ""
    
    
    def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """获取文件信息"""
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"文件不存在: {file_path}")
            
            file_stat = os.stat(file_path)
            file_type, _ = mimetypes.guess_type(file_path)
            
            return {
                "file_path": file_path,
                "file_name": os.path.basename(file_path),
                "file_size": file_stat.st_size,
                "file_type": file_type,
                "created_time": file_stat.st_ctime,
                "modified_time": file_stat.st_mtime,
                "is_supported": file_type in self.supported_types
            }
            
        except Exception as e:
            logger.error(f"获取文件信息失败: {e}")
            raise
    
    def validate_file(self, file_path: str, max_size: int = 10 * 1024 * 1024) -> bool:
        """验证文件"""
        try:
            file_info = self.get_file_info(file_path)
            
            # 检查文件大小
            if file_info["file_size"] > max_size:
                raise ValueError(f"文件大小超过限制: {file_info['file_size']} > {max_size}")
            
            # 检查文件类型
            if not file_info["is_supported"]:
                raise ValueError(f"不支持的文件类型: {file_info['file_type']}")
            
            return True
            
        except Exception as e:
            logger.error(f"文件验证失败: {e}")
            raise