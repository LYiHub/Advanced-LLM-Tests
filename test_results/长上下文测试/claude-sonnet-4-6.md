# claude-sonnet-4-6 长上下文测试报告

## 测试问题

在小说《全职高手》中，撕裂末日的重量是多少？

## 阶段一：无上下文作答结果

*（用于验证模型是否自带该精确记忆）*

根据我对《全职高手》小说的了解，**撕裂末日**是叶修（君莫笑）使用的武器，其重量为**168斤**。

这把枪是叶修在游戏中的标志性武器之一，重量极为沉重，普通玩家角色难以使用。

（如有记忆偏差，请以原著为准。）

## 阶段二：包含全文本作答结果

*（用于测试长文本提取能力及报错情况）*

LLM调用发生异常: Error code: 400 - {'error': {'message': 'Provider returned error ({"raw":"{\\"type\\":\\"error\\",\\"error\\":{\\"type\\":\\"invalid_request_error\\",\\"message\\":\\"prompt is too long: 1134608 tokens > 1000000 maximum\\"},\\"request_id\\":\\"req_011CaTZEsNbgRg3R2XAa5EXQ\\"}","provider_name":"Azure","is_byok":false})', 'type': 'upstream_error', 'param': '', 'code': 400, 'metadata': {'raw': '{"type":"error","error":{"type":"invalid_request_error","message":"prompt is too long: 1134608 tokens > 1000000 maximum"},"request_id":"req_011CaTZEsNbgRg3R2XAa5EXQ"}', 'provider_name': 'Azure', 'is_byok': False}}}
[claude-sonnet-4-6] 测试完成! 结果已保存至 c:\Users\lyi\Documents\AppData\Project\LLM_Test\test_results\长上下文测试\claude-sonnet-4-6.md

