"""
大语言模型客户端
提供最基础的带有Tool Call支持的LLM对话补全功能
"""

import asyncio
import os
import json
from typing import Optional, Dict, Any, List
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessage


class LLMClient:
    """大语言模型客户端"""
    
    def __init__(self):
        """初始化LLM客户端"""
        api_key = os.getenv("OPENAI_API_KEY")
        base_url = os.getenv("LLM_URL")
        
        if not api_key:
            raise ValueError("OPENAI_API_KEY环境变量未设置")
        if not base_url:
            raise ValueError("LLM_URL环境变量未设置")
            
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url
        )
        
    async def chat_completion_with_tools(
        self,
        messages: list,
        model: str = "qwen-plus"
    ) -> Optional[ChatCompletionMessage]:
        """
        调用LLM进行对话补全
        """
        try:
            response = await self.client.chat.completions.create(
                model=model,
                messages=messages
            )
            
            if response.choices:
                return response.choices[0].message
            return None
            
        except Exception as e:
            print(f"LLM调用发生异常: {e}")
            return None

    @staticmethod
    def make_tool_result_message(tool_call_id: str, content: str) -> Dict[str, Any]:
        """构造tool result消息字典"""
        return {
            "role": "tool",
            "tool_call_id": tool_call_id,
            "content": content
        }

    @staticmethod
    def make_assistant_tool_call_message(message: ChatCompletionMessage) -> Dict[str, Any]:
        """将带有tool call的message转为可序列化的字典，用于对话历史"""
        msg = {
            "role": "assistant",
            "content": message.content or ""
        }
        if message.tool_calls:
            msg["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments
                    }
                }
                for tc in message.tool_calls
            ]
        return msg


if __name__ == "__main__":
    from dotenv import load_dotenv
    from pathlib import Path
    
    # 根据.env文件加载环境变量 (同级目录或上级目录)
    # 获取脚本同目录下的.env，如果不存在尝试上级目录
    current_dir = Path(__file__).parent
    dotenv_path = current_dir / ".env"
    if not dotenv_path.exists():
        dotenv_path = current_dir.parent / ".env"
        
    load_dotenv(dotenv_path=dotenv_path)
    
    async def test_main():
        try:
            client = LLMClient()
            messages = [{"role": "user", "content": "你好"}]
            print("正在调用LLM...")
            
            response = await client.chat_completion_with_tools(
                messages=messages,
                model="gemini-3.1-pro-preview"
            )
            
            if response:
                print(f" LLM响应成功:\n{response.content}")
            else:
                print("未收到LLM返回内容")
        except Exception as e:
            print(f"运行失败: {e}")

    asyncio.run(test_main())

