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


async def test_web_animation_models_4():
    """测试模型生成第四组网页动画代码（液态玻璃与鼠标光效）并导出HTML文件"""
    
    models = [
        "deepseek-v4-pro",
        "gpt-5.4",
        "kimi-k2.6",
        "claude-opus-4-7",
        "claude-sonnet-4-6",
        "gemini-3.1-pro-preview",
        "glm-5.1"
    ]
    
    prompt = """请你作为一名前端UI/UX设计高级专家，设计一个完整的公司首页。请只输出完整的 HTML 代码内容，不要包含任何 Markdown 格式标记（如 ```html）及其他解释性对话文字。

设计主题：高级感的液态玻璃（Liquid Glassmorphism）风格的交互主页，避免使用泛滥的AI感网页设计，如蓝紫配色等。

具体需求：
1. 视觉风格与背景：页面采用深色高级背景，背景中需要包含不断缓慢平滑变形、漂浮的深蓝色液态流体形状，营造出神秘、未来感的氛围。
2. 核心视觉材质：要求展现出极佳的光学折射感，当底层流动的流体形状透过毛玻璃边缘时，能够模拟玻璃上的透视、折射、流动效果。
3. 鼠标微交互：鼠标需要对屏幕元素造成影响，比如改变液态玻璃质感等。
4. 流畅度与呈现：确保所有的流体形变、光影追踪和微交互动画在视觉上表现平滑、流畅且自然，展现顶级的网页动效水准。
5. 内容呈现：设定这是一家前沿的大模型科技公司。页面需要包含一个大模型公司首页应有的基础内容层，包括但不限于首屏标语及行动呼吁（Hero区）、几项核心AI业务或大模型产品特性展示，以及页底。请为其生成合适且专业的文案，并自行设计这些内容如何完美融入液态玻璃风格的主题之中。

请自由发挥和设计，展示你的创意和技术实力，打造一个审美出众的前沿网页体验。"""
    
    result_dir = current_dir / "test_results" / "模型网页动画测试4"
    result_dir.mkdir(parents=True, exist_ok=True)

    try:
        client = LLMClient()
    except Exception as e:
        print(f"初始化 LLM 客户端失败: {e}")
        return

    print("开始模型网页液态玻璃风格光效交互能力测试...\n")
    
    for model_name in models:
        print(f"[{model_name}] 正在生成代码...")
        
        messages = [{"role": "user", "content": prompt}]
        
        try:
            response = await client.chat_completion_with_tools(
                messages=messages,
                model=model_name
            )
            
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
        
        report_file = result_dir / f"{model_name}.html"
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(code_answer)
            
        print(f"[{model_name}] 生成完成! 结果已保存至 {report_file}")
        
    print("\n✅ 第四组模型 液态玻璃毛玻璃互动 网页动画测试保存完毕！")

if __name__ == "__main__":
    asyncio.run(test_web_animation_models_4())