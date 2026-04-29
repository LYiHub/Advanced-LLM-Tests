# glm-5.1 长上下文测试报告

## 测试问题

在小说《全职高手》中，撕裂末日的重量是多少？

## 阶段一：无上下文作答结果

*（用于验证模型是否自带该精确记忆）*

LLM调用发生异常: Error code: 400 - {'error': {'message': '系统检测到输入或生成内容可能包含不安全或敏感内容，请您避免输入易产生敏感内容的提示语，感谢您的配合。', 'type': 'upstream_error', 'param': '', 'code': '1301'}}

## 阶段二：包含全文本作答结果

*（用于测试长文本提取能力及报错情况）*

LLM调用发生异常: Error code: 400 - {'error': {'message': 'Prompt exceeds max length', 'type': 'upstream_error', 'param': '', 'code': '1261'}}
[glm-5.1] 测试完成! 结果已保存至 c:\Users\lyi\Documents\AppData\Project\LLM_Test\test_results\长上下文测试\glm-5.1.md
