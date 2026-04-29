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

async def test_long_context_models():
    """测试模型长上下文提取能力并导出Markdown报告"""
    
    models = [
        "deepseek-v4-pro",
        "gpt-5.4",
        "kimi-k2.6",
        "claude-opus-4-7",
        "claude-sonnet-4-6",
        "gemini-3.1-pro-preview",
        "glm-5.1"
    ]
    
    question = "在小说《全职高手》中，撕裂末日的重量是多少？"
    
    result_dir = current_dir / "test_results" / "长上下文测试"
    result_dir.mkdir(parents=True, exist_ok=True)
    
    txt_path = current_dir / "全职高手.txt"
    
    try:
        try:
            with open(txt_path, "r", encoding="utf-8") as f:
                novel_text = f.read()
        except UnicodeDecodeError:
            with open(txt_path, "r", encoding="gb18030") as f:
                novel_text = f.read()
        print(f"成功读取文本，长度: {len(novel_text)} 字符")
    except FileNotFoundError:
        print(f"找不到文件: {txt_path}，请确保文本文件存在。")
        return
    except Exception as e:
        print(f"读取文本失败: {e}")
        return

    try:
        client = LLMClient()
    except Exception as e:
        print(f"初始化 LLM 客户端失败: {e}")
        return

    print("开始长上下文测试...\n")
    
    for model_name in models:
        print(f"[{model_name}] 正在测试...")
        
        # 第一阶段：无文本测试
        print(f"  - 阶段一：无上下文作答...")
        prompt_no_ctx = (
            f"【注意：禁止使用任何网络搜索工具或联网能力，请仅凭你的已有知识直接回答。】\n\n"
            f"问题：{question}"
        )
        
        try:
            resp1 = await client.chat_completion_with_tools(
                messages=[{"role": "user", "content": prompt_no_ctx}],
                model=model_name
            )
            answer_no_ctx = resp1.content.strip() if resp1 and resp1.content else "无返回"
        except Exception as e:
            import traceback
            answer_no_ctx = f"**ERROR:**\n```text\n{str(e)}\n```\n\n**Traceback:**\n```python\n{traceback.format_exc()}\n```"
            print(f"    无上下文测试报错: {e}")

        # 第二阶段：带全文本测试
        print(f"  - 阶段二：长上下文作答...")
        prompt_with_ctx = (
            f"【注意：请根据以下小说文本内容，回答我的问题。】\n\n"
            f"问题：{question}\n\n"
            f"以下为小说文本内容：\n{novel_text}"
        )
        
        try:
            resp2 = await client.chat_completion_with_tools(
                messages=[{"role": "user", "content": prompt_with_ctx}],
                model=model_name
            )
            answer_with_ctx = resp2.content.strip() if resp2 and resp2.content else "无返回"
        except Exception as e:
            import traceback
            answer_with_ctx = f"**ERROR:**\n```text\n{str(e)}\n```\n\n**Traceback:**\n```python\n{traceback.format_exc()}\n```"
            print(f"    长上下文测试报错: {e}")
        
        # 生成Markdown报告
        md_content = f"# {model_name} 长上下文测试报告\n\n"
        md_content += f"## 测试问题\n\n{question}\n\n"
        md_content += f"## 阶段一：无上下文作答结果\n\n*（用于验证模型是否自带该精确记忆）*\n\n{answer_no_ctx}\n\n"
        md_content += f"## 阶段二：包含全文本作答结果\n\n*（用于测试长文本提取能力及报错情况）*\n\n{answer_with_ctx}\n\n"
        
        report_file = result_dir / f"{model_name}.md"
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(md_content)
            
        print(f"[{model_name}] 测试完成! 结果已保存至 {report_file}")
        
    print("\n✅ 所有模型长上下文测试保存完毕！")

if __name__ == "__main__":
    asyncio.run(test_long_context_models())
