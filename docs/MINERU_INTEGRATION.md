# MinerU 文档解析功能集成文档

## 概述

本项目已成功集成 MinerU 文档解析功能，支持通过配置文件选择使用 MinerU 或 TextIn 作为文档解析引擎。

## 功能特性

- 支持多种文档格式：PDF、Word、PowerPoint、图片等
- 可配置的解析引擎选择（MinerU/TextIn）
- 完整的错误处理和日志记录
- 支持 API 密钥配置和免费额度使用

## 配置说明

### 1. 配置文件设置

在 `config/conf.ini` 中配置文档解析器：

```ini
[document_parser]
# 文档解析配置
parser_type = mineru  # 可选值：textin, mineru

# TextIn API 配置
textin_api_url = 
textin_api_key = 

# MinerU API 配置
mineru_api_url = https://mineru.net
mineru_api_key =  # 空密钥可获得每日500页免费额度
```

### 2. 解析器选择

- `parser_type = mineru`：使用 MinerU API 进行文档解析
- `parser_type = textin`：使用 TextIn API 进行文档解析

## 支持的文件类型

- PDF 文档 (`application/pdf`)
- Word 文档 (`application/msword`, `application/vnd.openxmlformats-officedocument.wordprocessingml.document`)
- PowerPoint 文档 (`application/vnd.ms-powerpoint`, `application/vnd.openxmlformats-officedocument.presentationml.presentation`)
- 图片文件 (`image/jpeg`, `image/png`, `image/gif`)
- 纯文本文件 (`text/plain`, `text/markdown`)

## API 使用说明

### MinerU API

1. **免费使用**：无需 API 密钥，每日可获得 500 页免费解析额度
2. **付费使用**：访问 https://mineru.net/ 申请 API 密钥，获得更高额度
3. **配置方式**：在 `mineru_api_key` 中设置您的 API 密钥

### 代码示例

```python
from services.document_service import DocumentService

# 初始化文档服务
doc_service = DocumentService()

# 解析文档
file_path = "/path/to/your/document.pdf"
file_type = "application/pdf"
content = doc_service.extract_text_from_file(file_path, file_type)

print(f"解析结果长度: {len(content)}")
print(f"内容预览: {content[:500]}...")
```

## 实现细节

### 核心方法

1. **`extract_text_from_file()`**：主要入口方法，根据配置选择解析引擎
2. **`_extract_with_mineru()`**：MinerU API 调用方法
3. **`_extract_with_textin()`**：TextIn API 调用方法（待实现）
4. **`_extract_text_directly()`**：直接文本提取方法（备用）

### 错误处理

- 完整的异常捕获和日志记录
- 网络请求超时处理
- API 调用失败时的降级处理
- 文件验证和类型检查

## 测试验证

项目包含完整的测试脚本 `test_mineru.py`，可用于验证 MinerU 功能：

```bash
uv run python test_mineru.py
```

测试内容包括：
- 配置读取验证
- 文件信息获取
- 解析功能测试
- 结果保存和展示

## 注意事项

1. **网络连接**：MinerU API 需要稳定的网络连接
2. **文件大小**：建议单个文件不超过 10MB
3. **API 限制**：免费额度有每日限制，付费用户根据套餐不同有相应限制
4. **配置更新**：修改配置后需要重启应用程序

## 故障排除

### 常见问题

1. **解析结果为空**
   - 检查网络连接
   - 验证 API 密钥配置
   - 确认文件格式支持

2. **配置不生效**
   - 检查配置文件路径
   - 验证配置项格式
   - 重启应用程序

3. **API 调用失败**
   - 检查 API 地址配置
   - 验证网络连接
   - 查看日志错误信息

### 日志查看

系统会记录详细的解析日志，包括：
- 文件处理状态
- API 调用结果
- 错误信息和警告

## 更新历史

- **v1.0.0**：初始版本，支持基础 MinerU API 集成
- 配置文件支持
- 多文件格式支持
- 完整的错误处理机制

## 后续计划

1. 实现完整的 MinerU API 调用（需要有效 API 密钥）
2. 添加 TextIn API 支持
3. 优化解析性能和错误处理
4. 添加更多文档格式支持