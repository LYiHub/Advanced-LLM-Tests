import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
from llm_client import LLMClient

# 加载环境变量
current_dir = Path(__file__).parent
dotenv_path = current_dir / ".env"
if not dotenv_path.exists():
    dotenv_path = current_dir.parent / ".env"
load_dotenv(dotenv_path=dotenv_path)

async def test_writing_models_2():
    """测试模型创意写作并导出Markdown报告"""
    
    models = [
        "deepseek-v4-pro",
        "gpt-5.4",
        "kimi-k2.6",
        "claude-opus-4-7",
        "claude-opus-4-6",
        "claude-sonnet-4-6",
        "gemini-3.1-pro-preview",
        "glm-5.1"
    ]
    
    prompt = "写一段带有“俗世奇人”、“扫地僧”、“大隐隐于市”意境的武侠小说片段。"
    
    result_dir = current_dir / "test_results" / "模型写作测试2"
    result_dir.mkdir(parents=True, exist_ok=True)

    try:
        client = LLMClient()
    except Exception as e:
        print(f"初始化 LLM 客户端失败: {e}")
        return

    print("开始模型写作能力测试2...\n")
    
    for model_name in models:
        print(f"[{model_name}] 正在创作...")
        
        messages = [{"role": "user", "content": prompt}]
        
        try:
            response = await client.chat_completion_with_tools(
                messages=messages,
                model=model_name
            )
            
            model_answer = response.content.strip() if response and response.content else "无返回"
            
        except Exception as e:
            print(f"    请求出现异常: {e}")
            model_answer = f"ERROR: {str(e)}"
        
        # 生成Markdown报告
        md_content = f"# {model_name} 写作测试报告2\n\n"
        md_content += f"## 创作主题\n\n{prompt}\n\n"
        md_content += f"## 小说正文\n\n{model_answer}\n\n"
        
        report_file = result_dir / f"{model_name}.md"
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(md_content)
            
        print(f"[{model_name}] 创作完成! 结果已保存至 {report_file}")
        
    print("\n✅ 所有模型写作测试2并保存完毕！")

if __name__ == "__main__":
    asyncio.run(test_writing_models_2())