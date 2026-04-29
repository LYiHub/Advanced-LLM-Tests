import asyncio
import os
import json
from pathlib import Path
from dotenv import load_dotenv
from llm_client import LLMClient

# 加载环境变量
current_dir = Path(__file__).parent
dotenv_path = current_dir / ".env"
if not dotenv_path.exists():
    dotenv_path = current_dir.parent / ".env"
load_dotenv(dotenv_path=dotenv_path)

async def test_knowledge_models():
    """测试模型知识问答并导出Markdown报告"""
    
    models = [
        "deepseek-v4-pro",
        "gpt-5.4",
        "kimi-k2.6",
        "claude-opus-4-7",
        "claude-sonnet-4-6",
        "gemini-3.1-pro-preview",
        "glm-5.1"
    ]
    
    # 准备测试数据和结果目录
    questions = [
        {
            "id": 1,
            "question": "1685年，画师将要为蒙默斯公爵画一幅肖像画。但在画师开始绘画前，他向仆人要了一些针线。他这是要缝什么呢？",
            "answer": "蒙默斯公爵在当年7月被击败并斩首。画师专门画遗像，要针线是为了把公爵的脑袋缝回脖子上去。"
        },
        {
            "id": 2,
            "question": "一匹马一整天都在匀速行走，但令人吃惊的是，它的两条腿走了34公里，另外两条却只走了30公里。发生了什么事？",
            "answer": "这匹马今日的工作是拉磨。"
        },
        {
            "id": 3,
            "question": "20世纪70年代，一名男子经过数星期长途旅行后终于回到故乡，但人们却发现他正飘在大海上。这是怎么回事呢？",
            "answer": "该男子名为尼尔-奥尔登-阿姆斯特朗，旅行的目的地是——月球。"
        },
        {
            "id": 4,
            "question": "女孩偷偷把自己38分的卷子改成了88分，她的父亲看到试卷后狠狠地给了她一巴掌，怒吼道:“你这8怎么一半是绿的一半是红的，你以为我傻吗?”女孩被打后，委屈地哭了起来。过了一会儿，父亲突然崩溃了。请问父亲为什么崩溃？",
            "answer": "父亲发现了女儿是红绿色盲。红绿色盲是伴X隐性遗传病，只有父母双方都提供致病的X染色体女儿才会患病。但父亲自己并不是红绿色盲，他提供的那一条染色体无论如何也不会携带致病基因。"
        }
    ]
    
    result_dir = current_dir / "test_results" / "模型知识测试"
    result_dir.mkdir(parents=True, exist_ok=True)

    try:
        client = LLMClient()
    except Exception as e:
        print(f"初始化 LLM 客户端失败: {e}")
        return

    print("开始模型逻辑推理测试...\n")
    
    for model_name in models:
        print(f"[{model_name}] 正在答题...")
        
        results = []
        total = len(questions)
        
        for q in questions:
            prompt = (
                f"【注意：禁止使用任何网络搜索工具或联网能力，请仅凭你的已有知识和逻辑直接给出清晰的答案。】\n\n"
                f"题目：{q['question']}"
            )
            
            messages = [{"role": "user", "content": prompt}]
            
            try:
                response = await client.chat_completion_with_tools(
                    messages=messages,
                    model=model_name
                )
                
                answer_content = response.content.strip() if response and response.content else ""
                
                results.append({
                    "id": q["id"],
                    "question": q["question"],
                    "correct_answer": q["answer"],
                    "model_answer": answer_content or "无返回"
                })
                
            except Exception as e:
                print(f"    题目 {q['id']} 出现异常: {e}")
                results.append({
                    "id": q["id"],
                    "question": q["question"],
                    "correct_answer": q["answer"],
                    "model_answer": f"ERROR: {str(e)}"
                })
        
        # 生成Markdown报告
        md_content = f"# {model_name} 知识测试报告\n\n"
        
        md_content += "## 详细答题记录\n\n"
        
        for r in results:
            md_content += f"### 题目 {r['id']}\n\n"
            md_content += f"**问题：**\n{r['question']}\n\n"
            md_content += f"**参考答案：**\n{r['correct_answer']}\n\n"
            md_content += f"**模型回答：**\n{r['model_answer']}\n\n"
            md_content += "---\n\n"
            
        report_file = result_dir / f"{model_name}.md"
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(md_content)
            
        print(f"[{model_name}] 测试完成! 结果已保存至 {report_file}")
        
    print("\n✅ 所有模型测试并保存完毕！")

if __name__ == "__main__":
    asyncio.run(test_knowledge_models())
