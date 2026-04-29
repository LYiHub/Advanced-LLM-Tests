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

async def test_web_animation_models_3():
    """测试模型生成第三组网页动画代码（3D传动机构）并导出HTML文件"""
    
    models = [
        "deepseek-v4-pro",
        "gpt-5.4",
        "kimi-k2.6",
        "claude-opus-4-7",
        "claude-sonnet-4-6",
        "gemini-3.1-pro-preview",
        "glm-5.1"
    ]
    
    prompt = """请你编写一个完全包含在一个HTML文件内的完整的网页，来制作一个交互式的“汽车变速箱工作原理”3D演示动画。

请只输出完整的 HTML 代码内容，不要包含任何 Markdown 格式标记（如 ```html）及其他解释性对话文字。

具体需求如下：

1. 技术栈：
   - 必须使用 Three.js 构建 3D 场景（通过 `https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js` 引入）。
   - 包含 OrbitControls 以支持用户鼠标拖拽旋转、侧移和缩放视角（同样需要引入对应版本的 OrbitControls）。

2. 3D 模型与场景生成：
   - 引擎输入轴：用旋转的圆柱体表示，颜色设定为红色，转速代表发动机转速。
   - 离合器与齿轮组：使用多个不同大小的齿轮（通过多边形柱体或定制对象模拟）构成。要直观展示主动齿轮和从动齿轮的啮合状态。
   - 输出轴：另一根圆柱体，颜色设定为蓝青色，其转速需严格根据啮合齿轮的传动比演算并旋转。

3. 交互控制面板（UI）：
   - 页面一侧提供一个科技感强、具有毛玻璃(Backdrop-filter)或半透明背景的 UI 控制面板。
   - 包含控件：
     - 发动机转速 (RPM) 滑块：调整输入轴的基础转速。
     - 挡位切换按钮：空挡 (N)、一挡 (1)、二挡 (2)、三挡 (3)、倒挡 (R)。
     - 实时数据 HUD：悬浮显示当前的“实际传动比”、“离合器状态”、“输入 RPM”和“输出 RPM”（输出 = 输入 / 传动比）。

4. 动画与工作逻辑：
   - 换挡过程：切换挡位时，用平滑动画（如利用 TWEEN 或是自建趋近动画）表现同步器或齿轮的轴向位移，模拟分离与啮合的过程。
   - 离合器模拟：当切换到非空挡时，模拟离合器的接合过程（如通过调整一个透明度或缩放动画来表现离合器片的接触状态），并在此过程中平滑过渡输入轴与齿轮组的转速关系。
   - 运行逻辑：
     - 空挡 (N)：由于无齿轮锁定，输出轴转速为 0。
     - 1、2、3挡：配置不同传动比（如 3.0, 2.0, 1.0），此时输出轴按比例与输入轴同向（或设定固定反向）旋转。
     - 倒挡 (R)：引入倒挡惰轮理念，使输出轴反向旋转。
   - 采用 requestAnimationFrame 实现主渲染和物理运行逻辑。

5. 视觉效果：
   - 科技蓝图风格：纯黑或极暗灰背景，辅助以底部的网格平面（GridHelper）。
   - 材质渲染：齿轮和轴可使用 MeshStandardMaterial 或带 wireframe（线架）的材质组合，表现机械结构精密感与工业透视感。
   - 光源布置：提供环境光和能够产生高光的直射光/点光源。
"""
    
    result_dir = current_dir / "test_results" / "模型网页动画测试3"
    result_dir.mkdir(parents=True, exist_ok=True)

    try:
        client = LLMClient()
    except Exception as e:
        print(f"初始化 LLM 客户端失败: {e}")
        return

    print("开始模型网页3D传动机构交互能力测试...\n")
    
    for model_name in models:
        print(f"[{model_name}] 正在生成代码...")
        
        messages = [{"role": "user", "content": prompt}]
        
        try:
            response = await client.chat_completion_with_tools(
                messages=messages,
                model=model_name
            )
            
            # 清理代码
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
        
    print("\n✅ 第三组模型 3D 网页动画测试（传动机构）并保存完毕！")

if __name__ == "__main__":
    asyncio.run(test_web_animation_models_3())