## Python 编程规范

为了促进 Python 项目的工程化、标准化和模块化，使其易于维护与添加新功能，请遵循以下规范：

### 1. 依赖管理

- **统一使用 `uv`**: 项目的 Python 依赖统一使用 `uv` 进行管理。
  - 添加依赖: `uv add <package_name>`
  - 移除依赖: `uv remove <package_name>`
  - 运行项目: `uv run <command>`
- **禁止手动修改**: 不要手动编辑 `pyproject.toml` 文件来管理依赖。

### 2. 文件路径管理

- **使用 `pathlib`**: 在代码中处理文件或目录路径时，必须使用 `pathlib` 模块。
- **避免 `os.path`**: 避免 `os.path` 与 `pathlib` 混用，以保持代码风格的统一性和可读性。

### 3. 代码风格与最佳实践

- **PEP8 规范**: 遵循 PEP8 基础规范。
- **命名规范**: 文件和函数命名统一使用小写字母和下划线（snake_case）。
- **类型提示**:
    - **强制类型提示**: 所有变量、函数参数和返回值都必须使用类型提示。
    - **使用最新标准**: 类型提示应遵循最新的 Python 版本标准 (e.g., `list[str]` 而不是 `List[str]`)。
- **卫语句 (Guard Clauses)**:
    - **减少嵌套**: 优先使用卫语句来处理前置条件和异常情况，以减少代码的嵌套层级，提高可读性。
    - **示例**:
      ```python
      # 不推荐
      def process_data(data):
          if data is not None:
              # ... 复杂的逻辑
              return result
          else:
              return None

      # 推荐
      def process_data(data):
          if data is None:
              return None
          # ... 复杂的逻辑
          return result
      ```
- **Import 规范**:
    - **分组排序**: import 语句应分为标准库、第三方库、本地包三组，组间空一行，组内按字母序排序。
    - **禁止未使用**: 移除所有未使用的 import。
- **异常处理**:
    - **精确捕获**: 异常捕获应尽可能精确，严禁使用裸 `except:`。
    - **记录日志**: 在关键的异常处理场景中记录日志，避免静默失败。
- **现代 Python 特性**: 推荐使用 f-string、Enum、dataclasses 等现代 Python 特性来提升代码的可维护性。

### 4. 脚本入口

- **定义 `main()` 函数**: 所有可直接执行的脚本都必须定义一个 `main()` 函数作为程序的入口点。
- **标准调用方式**: 使用 `if __name__ == "__main__"` 结构来调用 `main()` 函数，确保脚本在被导入时不会执行主逻辑。
  ```python
  def main() -> int:
      # 主业务代码
      return 0  # 0 表示成功

  if __name__ == "__main__":
      raise SystemExit(main())
  ```

### 5. 文档字符串 (Docstrings)

- **结构化 Docstring**: 所有函数、类和模块都必须配备结构化的 docstring，清晰地描述其功能、参数和返回值。推荐使用 Google 或 Numpy 风格。
- **结合类型提示**: Docstring 应与类型提示结合使用，提供更全面的代码文档。
