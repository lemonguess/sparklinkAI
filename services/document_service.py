"""文档处理服务"""
import os
import logging
from typing import Dict, Any, List
import mimetypes
import requests

from core.config import settings

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
        
        # 从统一配置获取文档解析配置
        self.parser_type = settings.parser_type
        self.textin_api_url = settings.textin_api_url
        self.textin_api_key = settings.TEXTIN_API_KEY
        self.textin_api_secret = settings.TEXTIN_API_SECRET
        self.mineru_api_url = settings.mineru_api_url
        self.mineru_api_key = settings.mineru_api_key
    
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
            
            # 检查文件是否存在
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"文件不存在: {file_path}")
            
            # 准备文件上传 - 使用 files 数组格式
            with open(file_path, 'rb') as f:
                files = {
                    'files': (os.path.basename(file_path), f, 'application/octet-stream')
                }
                
                # 准备请求数据，包含 MinerU API 的参数
                data = {
                    'output_dir': './output',
                    'lang_list': ['ch'],  # 中文
                    'backend': 'pipeline',
                    'parse_method': 'auto',
                    'formula_enable': True,
                    'table_enable': True,
                    'return_md': True,
                    'return_middle_json': False,
                    'return_model_output': False,
                    'return_content_list': False,
                    'return_images': False,
                    'response_format_zip': False,
                    'start_page_id': 0,
                    'end_page_id': 99999
                }
                
                # 发送 POST 请求到本地 MinerU 服务
                response = requests.post(
                    self.mineru_api_url,
                    files=files,
                    data=data,
                    timeout=120  # 120秒超时，文档解析可能需要较长时间
                )
            
            # 检查响应状态
            if response.status_code == 200:
                result = response.json()
                
                # 根据 MinerU API 响应格式提取文本内容
                if isinstance(result, dict):
                    # 首先检查是否有 results 字段（MinerU 的标准响应格式）
                    if 'results' in result and isinstance(result['results'], dict):
                        # 获取第一个文件的解析结果
                        for filename, file_result in result['results'].items():
                            if isinstance(file_result, dict) and 'md_content' in file_result:
                                content = file_result['md_content']
                                logger.info(f"MinerU API 解析成功，内容长度: {len(content)} 字符")
                                return content
                    
                    # 尝试其他可能的字段
                    content = None
                    for field in ['content', 'text', 'markdown', 'md_content', 'data']:
                        if field in result and result[field]:
                            content = result[field]
                            break
                    
                    # 如果是列表格式，尝试提取第一个元素
                    if not content and isinstance(result, dict):
                        for key, value in result.items():
                            if isinstance(value, list) and len(value) > 0:
                                if isinstance(value[0], dict) and 'content' in value[0]:
                                    content = value[0]['content']
                                    break
                                elif isinstance(value[0], str):
                                    content = '\n'.join(value)
                                    break
                    
                    if content:
                        logger.info(f"MinerU API 解析成功，内容长度: {len(content)} 字符")
                        return content
                    else:
                        # 如果没有找到预期字段，返回整个响应用于调试
                        logger.warning(f"未找到预期的内容字段，返回原始响应: {result}")
                        return str(result)
                        
                elif isinstance(result, str):
                    # 如果直接返回字符串
                    logger.info(f"MinerU API 解析成功，内容长度: {len(result)} 字符")
                    return result
                else:
                    # 其他格式，转换为字符串
                    content = str(result)
                    logger.info(f"MinerU API 解析成功，内容长度: {len(content)} 字符")
                    return content
                
            else:
                error_msg = f"MinerU API 请求失败，状态码: {response.status_code}"
                if response.text:
                    error_msg += f"，错误信息: {response.text}"
                logger.error(error_msg)
                raise Exception(error_msg)
                    
        except requests.exceptions.Timeout:
            error_msg = "MinerU API 请求超时"
            logger.error(error_msg)
            raise Exception(error_msg)
        except requests.exceptions.ConnectionError:
            error_msg = f"无法连接到 MinerU API 服务: {self.mineru_api_url}"
            logger.error(error_msg)
            raise Exception(error_msg)
        except Exception as e:
            logger.error(f"MinerU API 提取失败 {file_path}: {e}")
            raise Exception(f"MinerU API 调用失败: {str(e)}")
    
    
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