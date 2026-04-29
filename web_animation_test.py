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

async def test_web_animation_models():
    """测试模型生成网页动画代码并导出HTML文件"""
    
    models = [
        "deepseek-v4-pro",
        "gpt-5.4",
        "kimi-k2.6",
        "claude-opus-4-7",
        "claude-sonnet-4-6",
        "gemini-3.1-pro-preview",
        "glm-5.1"
    ]
    
    # 这里设置想要显示的时间，例如 10:10
    time_to_show = "10:10"
    
    prompt = f"Create HTML/CSS of an analog clock showing {time_to_show}. Include numbers (or numerals) if you wish, and have a CSS animated second hand. Make it responsive and use a white background. Return ONLY the HTML/CSS code with no markdown formatting."
    
    result_dir = current_dir / "test_results" / "模型网页动画测试"
    result_dir.mkdir(parents=True, exist_ok=True)

    try:
        client = LLMClient()
    except Exception as e:
        print(f"初始化 LLM 客户端失败: {e}")
        return

    print("开始模型网页动画生成能力测试...\n")
    
    for model_name in models:
        print(f"[{model_name}] 正在生成代码...")
        
        messages = [{"role": "user", "content": prompt}]
        
        try:
            response = await client.chat_completion_with_tools(
                messages=messages,
                model=model_name
            )
            
            # 由于提示词要求不要包含markdown格式，有时模型还是会带上类似 ```html ... ```，这里做个简单清洗
            code_answer = response.content.strip() if response and response.content else ""
            if code_answer.startswith("```html"):
                code_answer = code_answer[7:]
            elif code_answer.startswith("```"):
                code_answer = code_answer[3:]
            if code_answer.endswith("```"):
                code_answer = code_answer[:-3]
            code_answer = code_answer.strip()
            
            if not code_answer:
                code_answer = "<!-- 无返回或生成失败 -->"
                
        except Exception as e:
            print(f"    请求出现异常: {e}")
            code_answer = f"<!-- ERROR: {str(e)} -->"
        
        # 直接生成HTML文件以便于浏览器预览
        report_file = result_dir / f"{model_name}.html"
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(code_answer)
            
        print(f"[{model_name}] 生成完成! 结果已保存至 {report_file}")
        
    print("\n✅ 所有模型网页动画测试并保存完毕！可以直接在浏览器中打开生成的HTML文件查看效果。")

if __name__ == "__main__":
    asyncio.run(test_web_animation_models())
