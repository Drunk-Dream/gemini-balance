## Brief overview
本规则适用于本项目中 `redis-py` 库的使用，旨在解决因同步/异步操作导致的类型检查错误。

## Coding best practices
- 当使用 `redis-py` 库时，如果遇到由于同步和异步操作不兼容导致的返回值类型错误，可以直接在受影响的代码行末尾添加 `# type: ignore` 注释来忽略该错误。
- 示例：
  ```python
  # 假设 redis_client 是一个异步 Redis 客户端实例
  result = await redis_client.get("some_key")  # type: ignore
