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

async def test_web_animation_models_2():
    """测试模型生成第二组网页动画代码并导出HTML文件"""
    
    models = [
        "deepseek-v4-pro",
        "gpt-5.4",
        "kimi-k2.6",
        "claude-opus-4-7",
        "claude-sonnet-4-6",
        "gemini-3.1-pro-preview",
        "glm-5.1"
    ]
    
    prompt = """请你编写一个完全包含在一个HTML文件内的网页，来实现以下动态设计序列。请只输出完整的 HTML 代码内容，不要包含任何 Markdown 格式标记（如 ```html）及其他解释性对话文字。

极简流畅的动态设计（Motion Design）序列。全程纯黑背景。
黑底白字的极简美学。无剪辑——全程是一个单一、连续、未被打破的视觉演变过程，保证动画是连续的，不存在直接切换。锁定静态的中心画幅，无摄像机运动。所有的运动都在主体内部发生。绝对纯黑背景上的自发光纯白形态，无噪点，无阴影。

0–1秒 [起源/ORIGIN]：画面正中心生成一个白点。它脉动一次——三个同心圆环像心跳一样向外荡出涟漪，然后消散在黑色中。
1–2秒 [线条/LINE]：这个点被拉伸成一条极细的白色水平线，以弹性的缓出（ease-out）运动延伸至画面边缘。
2–4秒 [网格→圆/GRID → CIRCLE]：这条线增殖成一个由九条平行的水平线和垂直线组成的精密网格，交错出现。网格发生扭曲——外侧的线条向内弯曲，整个结构旋转，直线弯曲成弧线，最终汇聚成一个完美的几何圆形轮廓。
4–6秒 [线框→实体球/WIREFRAME → SOLID SPHERE]：圆形挤压延伸成一个 3D 的线框球体，每一条经纬线都清晰锐利，绕其垂直轴缓慢旋转。线框平滑地被填充——渐变成一个纯白色的实体表面，左侧偏上象限带有一抹柔和的镜面高光。
6–8秒 [界面/INTERFACE]：球体扁平化，展开成一个干净的矩形平面——一个带有圆角的极简手机界面。内部出现抽象的 UI 元素：状态栏、圆角应用图标网格、底部横条（Home indicator）。全部是黑底上的白色线条艺术。
8–10秒 [立方体→绽放/CUBE → BLOOM]：界面向内折叠，坍缩成一个等距视角的线框立方体，并翻转一次。立方体的六个面同时向外剥离，每一面都变成一片光滑的白色椭圆形花瓣——像失重状态下的花朵一样绽放开来。
10–12秒 [涡流/VORTEX]：花朵消散成数百个微小的白色粒子，在受控的椭圆涡流中绕中心盘旋，有些顺时针，有些逆时针，每一个都遵循精确的数学轨迹，柔和地闪烁。
12–13秒 [手表/WATCH]：粒子减速并自我组织——汇聚并瞬间归位，组集成为一块手表的轮廓：一个带有表耳的干净矩形表壳轮廓，完全由粒子构建而成。
13–14秒 [坍缩/COLLAPSE]：手表溶解成流动的白色缎带，压缩成一个高密度的单一白色球体。它脉动一次——比之前更亮——然后迅速向内坍缩成一个极其明亮的点。
14–15秒 [LOGO/标志]：这个点静止并保持无声的一拍。然后它扩展成一个干净极简的品牌 Logo——黑底上的白色无衬线文字。一圈温暖的琥珀色光芒从 Logo 背后的中心出发完成一次脉冲发光，然后淡出为黑色。白色的文字保留在屏幕上。

风格：奢华科技品牌动态视觉识别，包豪斯极简主义，数学般的精准。
氛围：宁静、必然、智慧、高级。"""
    
    result_dir = current_dir / "test_results" / "模型网页动画测试2"
    result_dir.mkdir(parents=True, exist_ok=True)

    try:
        client = LLMClient()
    except Exception as e:
        print(f"初始化 LLM 客户端失败: {e}")
        return

    print("开始模型网页复杂动画生成能力测试...\n")
    
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
        
    print("\n✅ 第二组模型复杂网页动画测试并保存完毕！")

if __name__ == "__main__":
    asyncio.run(test_web_animation_models_2())