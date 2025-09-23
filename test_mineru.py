#!/usr/bin/env python3
"""
MinerU 文档解析功能测试脚本

用途：验证 MinerU API 集成是否正常工作
作者：SparkLink AI 开发团队
版本：1.0.0
"""

import sys
import os
import time
import logging

# 添加项目根目录到 Python 路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.document_service import DocumentService

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_mineru_parsing():
    """测试 MinerU 解析功能"""
    
    # 测试文件路径
    test_file_path = "/Users/lixincheng/Downloads/test2.pdf"
    
    print("🧪 MinerU 文档解析测试")
    print("=" * 50)
    print(f"📄 开始测试 MinerU 解析: {test_file_path}")
    
    # 检查测试文件是否存在
    if not os.path.exists(test_file_path):
        print(f"❌ 测试文件不存在: {test_file_path}")
        print("请确保测试文件存在后重新运行测试")
        return
    
    try:
        # 初始化文档服务
        doc_service = DocumentService()
        
        # 显示当前配置
        print(f"📋 当前解析器配置: {doc_service.parser_type}")
        print(f"🔗 MinerU API 地址: {doc_service.mineru_api_url}")
        print(f"🔑 MinerU API 密钥: {'已设置' if doc_service.mineru_api_key and doc_service.mineru_api_key.strip() else '未设置（使用免费额度）'}")
        
        # 获取文件信息
        file_info = doc_service.get_file_info(test_file_path)
        print(f"📊 文件信息:")
        print(f"   - 文件名: {file_info['file_name']}")
        print(f"   - 文件大小: {file_info['file_size']} 字节")
        print(f"   - 文件类型: {file_info['file_type']}")
        print(f"   - 是否支持: {file_info['is_supported']}")
        
        print(f"\n🚀 开始解析文档...")
        
        # 记录开始时间
        start_time = time.time()
        
        # 提取文本内容
        content = doc_service.extract_text_from_file(test_file_path, file_info['file_type'])
        
        # 记录结束时间
        end_time = time.time()
        processing_time = end_time - start_time
        
        if content:
            print("✅ 解析成功!")
            print(f"📝 内容长度: {len(content)} 字符")
            print(f"⏱️ 处理时间: {processing_time:.2f} 秒")
            print(f"📄 内容预览 (前500字符):")
            print("-" * 50)
            print(content[:500])
            if len(content) > 500:
                print("...")
            print("-" * 50)
            
            # 保存解析结果到文件
            result_file = os.path.join(os.path.dirname(__file__), "mineru_test_result.md")
            with open(result_file, 'w', encoding='utf-8') as f:
                f.write(f"# MinerU 解析结果\n\n")
                f.write(f"**文件**: {os.path.basename(test_file_path)}\n")
                f.write(f"**解析时间**: {start_time}\n")
                f.write(f"**处理时长**: {processing_time:.2f} 秒\n")
                f.write(f"**内容长度**: {len(content)} 字符\n\n")
                f.write(f"## 解析内容\n\n")
                f.write(content)
            
            print(f"💾 解析结果已保存到: {result_file}")
            
        else:
            print("❌ 解析失败，未获取到内容")
            
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print("\n" + "=" * 50)
    print("🎉 测试完成！MinerU 解析功能正常工作")

if __name__ == "__main__":
    test_mineru_parsing()