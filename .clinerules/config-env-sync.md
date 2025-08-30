## Brief overview
本规则适用于本项目中配置管理，旨在确保 `backend/app/core/config.py` 与 `.env.example` 文件之间配置项的同步性。

## Development workflow
- **配置同步**: 每当在 `backend/app/core/config.py` 文件中添加新的配置项时，必须同时在 `.env.example` 文件中添加对应的环境变量。
- **格式要求**: `.env.example` 中的新配置项应包含：
    - 环境变量名称。
    - 默认值（如果 `config.py` 中有默认值）。
    - 简洁的中文注释，说明该配置项的用途和默认值。

## 示例
假设在 `backend/app/core/config.py` 中添加了新的配置项：
```python
NEW_FEATURE_ENABLED: bool = os.getenv("NEW_FEATURE_ENABLED", "False").lower() == "true"
```
则在 `.env.example` 中应添加：
```
# 是否启用新功能。设置为 "true" 启用，"false" 禁用。
# 默认值：False
NEW_FEATURE_ENABLED=False
