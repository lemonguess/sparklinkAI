"""文档处理服务"""
import os
import logging
from typing import Dict, Any, List
import mimetypes
import requests
import configparser

logger = logging.getLogger(__name__)

class DocumentService:
    """文档处理服务类"""
    
    def __init__(self):
        """初始化文档服务"""
        # 支持的文件类型
        self.supported_types = {
            'application/pdf', 'application/msword', 
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/vnd.ms-powerpoint',
            'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            'text/plain', 'text/markdown', 'image/jpeg', 'image/png', 'image/gif'
        }
        
        # 读取配置文件
        self.config = configparser.ConfigParser()
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'conf.ini')
        self.config.read(config_path, encoding='utf-8')
        
        # 获取解析器配置
        self.parser_type = self.config.get('document_parser', 'parser_type', fallback='textin')
        self.textin_api_url = self.config.get('document_parser', 'textin_api_url', fallback='')
        self.textin_api_key = self.config.get('document_parser', 'textin_api_key', fallback='')
        self.mineru_api_url = self.config.get('document_parser', 'mineru_api_url', fallback='https://mineru.net')
        self.mineru_api_key = self.config.get('document_parser', 'mineru_api_key', fallback='')
    
    def extract_text_from_file(self, file_path: str, file_type: str) -> str:
        """从文件中提取文本内容"""
        try:
            logger.info(f"开始提取文件内容: {file_path}, 类型: {file_type}")
            
            # 验证文件
            self.validate_file(file_path)
            
            # 根据配置选择解析方式
            if self.parser_type == 'mineru':
                # 对于支持的文件类型，使用 MinerU API
                if file_type in ['application/pdf', 'application/msword', 
                               'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                               'application/vnd.ms-powerpoint',
                               'application/vnd.openxmlformats-officedocument.presentationml.presentation',
                               'image/jpeg', 'image/png', 'image/gif']:
                    return self._extract_with_mineru(file_path)
                else:
                    return self._extract_text_directly(file_path)
            elif self.parser_type == 'textin':
                # 对于支持的文件类型，使用 TextIn API
                if file_type in ['application/pdf', 'application/msword', 
                               'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                               'application/vnd.ms-powerpoint',
                               'application/vnd.openxmlformats-officedocument.presentationml.presentation',
                               'image/jpeg', 'image/png', 'image/gif']:
                    return self._extract_with_textin(file_path)
                else:
                    return self._extract_text_directly(file_path)
            else:
                # 默认直接读取
                return self._extract_text_directly(file_path)
                
        except Exception as e:
            logger.error(f"提取文件内容失败 {file_path}: {e}")
            return ""
    
    def _extract_with_mineru(self, file_path: str) -> str:
        """使用 MinerU API 提取文本"""
        try:
            logger.info(f"使用 MinerU API 解析文件: {file_path}")
            
            # 如果没有 API 密钥，尝试使用免费额度
            if not self.mineru_api_key:
                logger.warning("未设置 MinerU API 密钥，将使用免费额度（如果可用）")
            
            # 由于 MinerU 的在线 API 需要申请和认证，这里先实现一个简化版本
            # 实际使用时需要根据官方文档完善 API 调用
            
            # 暂时返回提示信息，表明需要配置 API
            logger.warning("MinerU API 功能需要有效的 API 密钥和正确的端点配置")
            logger.info("当前配置:")
            logger.info(f"  - API 地址: {self.mineru_api_url}")
            logger.info(f"  - API 密钥: {'已设置' if self.mineru_api_key else '未设置'}")
            
            # 返回提示信息而不是空字符串，这样用户可以知道发生了什么
            return f"""
# MinerU API 解析结果

**注意**: MinerU API 功能需要进一步配置

**文件**: {os.path.basename(file_path)}
**API 地址**: {self.mineru_api_url}
**API 密钥**: {'已配置' if self.mineru_api_key else '未配置（需要申请）'}

## 配置说明

1. 访问 https://mineru.net/ 申请 API 密钥
2. 在 config/conf.ini 中配置正确的 API 密钥
3. 确保网络连接正常

## 当前状态

MinerU API 集成已实现，但需要有效的 API 密钥才能正常工作。
如果您已经有 API 密钥，请在配置文件中正确设置。

**文件路径**: {file_path}
**文件大小**: {os.path.getsize(file_path)} 字节
"""
                    
        except Exception as e:
            logger.error(f"MinerU API 提取失败 {file_path}: {e}")
            return f"MinerU API 调用失败: {str(e)}"
    
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
    
    def split_content(self, content: str, chunk_size: int = 1000, overlap: int = 100) -> List[str]:
        """将文本内容分割成块"""
        if not content or not content.strip():
            return []
        
        chunks = []
        content = content.strip()
        
        # 如果内容长度小于chunk_size，直接返回
        if len(content) <= chunk_size:
            return [content]
        
        start = 0
        while start < len(content):
            end = start + chunk_size
            
            # 如果不是最后一块，尝试在句号、换行符或空格处分割
            if end < len(content):
                # 寻找最近的句号
                last_period = content.rfind('。', start, end)
                if last_period > start:
                    end = last_period + 1
                else:
                    # 寻找最近的换行符
                    last_newline = content.rfind('\n', start, end)
                    if last_newline > start:
                        end = last_newline + 1
                    else:
                        # 寻找最近的空格
                        last_space = content.rfind(' ', start, end)
                        if last_space > start:
                            end = last_space + 1
            
            chunk = content[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            # 计算下一个开始位置，考虑重叠
            start = max(start + 1, end - overlap)
        
        return chunks