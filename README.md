# 前沿大语言模型评测项目 (Advanced-LLM-Tests)

本项目旨在对市面上主流的大型语言模型（LLM）进行多维度的能力测试与横向对比。项目中预制了自动化测试脚本以及丰富的测评体系，从而能够直观地比较各模型在长上下文、逻辑推理、代码编写（网页动画、智能体编程）、知识广度及写作等各个应用场景下的性能表现。

## 测试模型范围 (Models Tested)
项目中收集并测试了如下主流的大语言模型：
- **Claude 系列**：Claude Opus 4.7, Claude Sonnet 4.6
- **DeepSeek**：DeepSeek V4 Pro
- **Gemini**：Gemini 3.1 Pro Preview
- **GLM (智谱)**：GLM 5.1
- **GPT (OpenAI)**：GPT-5.4
- **Kimi (月之暗面)**：Kimi K2.6

## 核心测试维度 (Evaluation Dimensions)
1. **逻辑推理测试 (Logic Test)**：`logic_test.py`
2. **知识测试 (Knowledge Test)**：`knowledge_test.py`
3. **写作测试 (Writing Test)**：`writing_test.py`, `writing_test_2.py`
4. **长上下文理解 (Long Context Test)**：`long_context_test.py` (使用了长文本语料《全职高手.txt》作测试)
5. **网页前端与动画编码 (Web Animation Test)**：`web_animation_test.py` 及变体，考察模型手写网页特效代码的能力。
6. **智能体编程测试 (Agent Programming Test)**：侧重于考察模型进行系统设计及复杂工程代码的能力（详见 `test_results/智能体编程测试`）。

## 项目结构
- `llm_client.py`：基础的 LLM 请求封装客户端，提供模型对话支持以及 Tool Call 工具集成的公共方法。
- `*_test*.py`：各个垂类的自动化测试执行脚本。
- `全职高手.txt`：长上下文分析专项测试所需的底层长文本材料。
- `test_results/`：不同模型在各维度测试下生成的原始结果记录与评分报告。

## 运行与安装 (Getting Started)

1. 环境依赖：
   - 依赖 Python 环境和 `openai` 等库。
   ```bash
   pip install openai python-dotenv
   ```
2. 配置环境变量：
   在项目根目录下新建一个 `.env` 文件，内容如下
   ```env
   LLM_URL=填写你的API转发或代理地址
   OPENAI_API_KEY=你的API_KEY
   ```
3. 执行测试：
   可以直接运行各个测试脚本，例如：
   ```bash
   python logic_test.py
   ```
   测试输出将会自动保存到 `test_results/` 相应的目录下。
