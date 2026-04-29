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

async def test_logic_models():
    """测试模型逻辑推理并导出Markdown报告"""
    
    models = [
        "deepseek-v4-pro",
        "gpt-5.4",
        "kimi-k2.6",
        "claude-opus-4-7",
        "claude-sonnet-4-6",
        "gemini-3.1-pro-preview",
        "glm-5.1"
    ]
    
    question = """这是一份由10道单项选择题组成的逻辑测试，每道题的答案均在A、B、C、D这四个选项中。请基于题目描述与各选项间的逻辑制约关系，推导出所有题目的正确答案。提示：各题之间往往暗含着交叉线索，必须全局统筹考虑。
1. 当前这道题的最终选项为：
A. A   B. B   C. C   D. D

2. 下列选项中，能代表第5道题正确答案的一项是：
A. C   B. D   C. A   D. B

3. 下列四道题目中，只有一道题的正确选项与其余三道题不同，这道题是：
A. 第3题   B. 第6题   C. 第2题   D. 第4题

4. 下面列出的四组题目中，哪一组的两道题目选项完全相同：
A. 第1题和第5题   B. 第2题和第7题   C. 第1题和第9题   D. 第6题和第10题

5. 本道题目的正确选项，与下列哪道题的正确选项一样：
A. 第8题   B. 第4题   C. 第9题   D. 第7题

6. 下列哪一组的两道题，其正确选项均与第8题的正确选项一致：
A. 第2题和第4题   B. 第1题和第6题   C. 第3题和第10题   D. 第5题和第9题

7. 纵观这十道题的全部答案，被选择次数最少的选项字母是：
A. C   B. B   C. A   D. D

8. 下列哪道题目的正确答案，其字母序号在字母表中与第1题答案的字母序号互不相邻：
A. 第7题   B. 第5题   C. 第2题   D. 第10题

9. 假如“第1题和第6题选项一致”这个命题与“第X题和第5题选项一致”这两个命题的真假性恰好相反，则X应为：
A. 第6题   B. 第10题   C. 第2题   D. 第9题

10. 在这十道题的最终答案里，出现频次最高的字母数量和最低的字母数量相减，差值是：
A. 3   B. 2   C. 4   D. 1"""

    correct_answer = "1. B, 2. C, 3. A, 4. C, 5. A, 6. C, 7. D, 8. A, 9. B, 10. A"
    
    result_dir = current_dir / "test_results" / "模型逻辑推理测试"
    result_dir.mkdir(parents=True, exist_ok=True)

    try:
        client = LLMClient()
    except Exception as e:
        print(f"初始化 LLM 客户端失败: {e}")
        return

    print("开始模型逻辑推理测试...\n")
    
    for model_name in models:
        print(f"[{model_name}] 正在答题...")
        
        prompt = (
            f"【注意：禁止使用任何网络搜索工具或联网能力，请仅凭你的逻辑推理能力直接给出这10道题的答案及解析。】\n\n"
            f"题目：\n{question}"
        )
        
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
        md_content = f"# {model_name} 逻辑推理测试报告\n\n"
        md_content += f"## 题目\n\n```text\n{question}\n```\n\n"
        md_content += f"## 正确答案\n\n{correct_answer}\n\n"
        md_content += f"## 模型回答\n\n{model_answer}\n\n"
        
        report_file = result_dir / f"{model_name}.md"
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(md_content)
            
        print(f"[{model_name}] 测试完成! 结果已保存至 {report_file}")
        
    print("\n✅ 所有模型测试并保存完毕！")

if __name__ == "__main__":
    asyncio.run(test_logic_models())
