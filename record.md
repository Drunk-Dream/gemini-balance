### gemini 请求，非流式：

{
"candidates": [
{
"content": {
"parts": [
{
"text": "Here are a few ways to explain how AI works in Chinese, keeping it very brief:\n\n**Concise & Common:**\n\n* **模拟人类智能 (mó nǐ rén lèi zhì néng)** - Simulates human intelligence.\n* **学习和思考 (xué xí hé sī kǎo)** - Learns and thinks.\n* **数据驱动决策 (shù jù qū dòng jué cè)** - Data-driven decision-making.\n\n**Slightly More Descriptive (but still short):**\n\n* **通过学习大量数据来模仿和执行智能任务。(tōng guò xué xí dà liàng shù jù lái mó fǎng hé zhí xíng zhì néng rèn wù.)** - By learning from vast amounts of data, it imitates and performs intelligent tasks.\n\nChoose the one that best fits the context you need!"
}
],
"role": "model"
},
"finishReason": "STOP",
"index": 0
}
],
"usageMetadata": {
"promptTokenCount": 11,
"candidatesTokenCount": 193,
"totalTokenCount": 204,
"promptTokensDetails": [
{
"modality": "TEXT",
"tokenCount": 11
}
]
},
"modelVersion": "gemini-2.5-flash-lite",
"responseId": "5I_PaPiJA8WHz7IP0MaXsQ8"
}

### gemini 请求，流式：

data: {"candidates": [{"content": {"parts": [{"text": "**"}],"role": "model"},"index": 0}],"usageMetadata": {"promptTokenCount": 11,"candidatesTokenCount": 1,"totalTokenCount": 12,"promptTokensDetails": [{"modality": "TEXT","tokenCount": 11}]},"modelVersion": "gemini-2.5-flash-lite","responseId": "P5LPaI6_LYbhz7IPkcnKwA4"}

data: {"candidates": [{"content": {"parts": [{"text": "AI is like a smart computer that learns from data and solves problems.**\n\nIn"}],"role": "model"},"index": 0}],"usageMetadata": {"promptTokenCount": 11,"candidatesTokenCount": 17,"totalTokenCount": 28,"promptTokensDetails": [{"modality": "TEXT","tokenCount": 11}]},"modelVersion": "gemini-2.5-flash-lite","responseId": "P5LPaI6_LYbhz7IPkcnKwA4"}

data: {"candidates": [{"content": {"parts": [{"text": " Chinese:\n\n**AI 就像一个聪明的电脑，它从数据中学习并解决问题。**\n\nHere are a few more concise options, focusing on different aspects:\n\n* **学习数据，解决问题。** (Lear"}],"role": "model"},"index": 0}],"usageMetadata": {"promptTokenCount": 11,"candidatesTokenCount": 66,"totalTokenCount": 77,"promptTokensDetails": [{"modality": "TEXT","tokenCount": 11}]},"modelVersion": "gemini-2.5-flash-lite","responseId": "P5LPaI6_LYbhz7IPkcnKwA4"}

data: {"candidates": [{"content": {"parts": [{"text": "ns data, solves problems.) - Very direct and to the point.\n* **模拟智能，处理信息。** (Simulates intelligence, processes information.) - Highlights the \"intelligence\" aspect and data handling.\n* **"}],"role": "model"},"index": 0}],"usageMetadata": {"promptTokenCount": 11,"candidatesTokenCount": 114,"totalTokenCount": 125,"promptTokensDetails": [{"modality": "TEXT","tokenCount": 11}]},"modelVersion": "gemini-2.5-flash-lite","responseId": "P5LPaI6_LYbhz7IPkcnKwA4"}

data: {"candidates": [{"content": {"parts": [{"text": "数据驱动，智能决策。** (Data-driven, intelligent decision-making.) - Emphasizes the reliance on data for smart choices."}],"role": "model"},"finishReason": "STOP","index": 0}],"usageMetadata": {"promptTokenCount": 11,"candidatesTokenCount": 143,"totalTokenCount": 154,"promptTokensDetails": [{"modality": "TEXT","tokenCount": 11}]},"modelVersion": "gemini-2.5-flash-lite","responseId": "P5LPaI6_LYbhz7IPkcnKwA4"}

### openai 请求，非流式：

{
"choices": [
{
"finish_reason": "stop",
"index": 0,
"message": {
"content": "Here are a few ways to explain how AI works in Chinese, each with a slightly different emphasis, in just a few words:\n\n**Most Concise & Direct:**\n\n* **学习数据，做出决策。** (Xuéxí shùjù, zuò chū juécè.) - Learns data, makes decisions.\n* **模拟大脑，解决问题。** (Mónǐ dànǎo, jiějué wèntí.) - Simulates brain, solves problems.\n\n**Slightly More Descriptive:**\n\n* **通过学习，识别模式，预测结果。** (Tōngguò xuéxí, shìbié móshì, yùcè jiéguǒ.) - Through learning, identifies patterns, predicts results.\n* **分析信息，智能响应。** (Fēnxī xìnxī, zhìnéng xiǎngyìng.) - Analyzes information, intelligently responds.\n\nChoose the one that best fits the context and your audience!",
"role": "assistant"
}
}
],
"created": 1758434118,
"id": "RpPPaLS3J-3Uz7IP2NS36Qg",
"model": "gemini-2.5-flash-lite",
"object": "chat.completion",
"usage": {
"completion_tokens": 210,
"prompt_tokens": 12,
"total_tokens": 222
}
}

### openai 请求，流式：

data: {"choices":[{"delta":{"content":"AI","role":"assistant"},"index":0}],"created":1758435793,"id":"0ZnPaL3SD4jmz7IP8Jzo0Ag","model":"gemini-2.5-flash-lite","object":"chat.completion.chunk","usage":{"completion_tokens":1,"prompt_tokens":12,"total_tokens":13}}

data: {"choices":[{"delta":{"content":" works by **learning from data to make decisions.**\n\nIn Chinese:\n\n**AI 通过学习数据来","role":"assistant"},"index":0}],"created":1758435793,"id":"0ZnPaL3SD4jmz7IP8Jzo0Ag","model":"gemini-2.5-flash-lite","object":"chat.completion.chunk","usage":{"completion_tokens":22,"prompt_tokens":12,"total_tokens":34}}

data: {"choices":[{"delta":{"content":"做决策。**\n\nHere's a breakdown:\n\n*   **AI (人工智能)**: Artificial Intelligence\n*   **通过 (tōng guò)**: through, by\n*   **学习 (xué xí)**: learning\n*","role":"assistant"},"index":0}],"created":1758435793,"id":"0ZnPaL3SD4jmz7IP8Jzo0Ag","model":"gemini-2.5-flash-lite","object":"chat.completion.chunk","usage":{"completion_tokens":74,"prompt_tokens":12,"total_tokens":86}}

data: {"choices":[{"delta":{"content":"   **数据 (shù jù)**: data\n*   **来 (lái)**: to (indicates purpose)\n*   **做 (zuò)**: to do, to make\n*   **决策 (ju","role":"assistant"},"index":0}],"created":1758435793,"id":"0ZnPaL3SD4jmz7IP8Jzo0Ag","model":"gemini-2.5-flash-lite","object":"chat.completion.chunk","usage":{"completion_tokens":122,"prompt_tokens":12,"total_tokens":134}}

data: {"choices":[{"delta":{"content":"é cè)**: decisions\n\nYou could also use a slightly simpler version:\n\n**AI 学习数据，然后做决定。** (AI learns data, then makes decisions.)","role":"assistant"},"finish_reason":"stop","index":0}],"created":1758435793,"id":"0ZnPaL3SD4jmz7IP8Jzo0Ag","model":"gemini-2.5-flash-lite","object":"chat.completion.chunk","usage":{"completion_tokens":159,"prompt_tokens":12,"total_tokens":171}}

data: [DONE]