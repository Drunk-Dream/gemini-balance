## Brief overview

- 本规则适用于本项目 Python 开发的编码与协作，全员需遵循。
- 着重依赖管理、代码风格、类型提示与目录规范。

## Communication style

- 沟通简洁、任务驱动，要求明确提出待完成事项。
- 不赘述无关细节，聚焦编码/开发本身的问题。

## Development workflow

- 依赖管理统一使用 uv，`uv add` 添加依赖，`uv remove` 移除依赖，禁止手动修改 pyproject.toml。
- 虚拟环境创建与依赖管理等流程以 uv 官方推荐实践为准。
- 文件及路径管理首选 pathlib 模块，避免 os.path 混用。
- 新增代码、函数需带类型提示，确保类型可读性。

## Coding best practices

- 强制类型提示（type hint），例如：
  ```python
  def func(a: int, b: str) -> bool:
      ...
  ```
- 采用 Flake8 工具，提交前本地通过 Flake8 静态检查。
  - 针对仅风格/排版类的 Flake8 警告（如行超过 88 字符（E501）、函数间缺两空行（E302）等），只做参考，无需强制修复，详见`.clinerules/flake8-lint-waiver.md`。
  - 诸如变量未定义、类型错误、循环引用、语法错误、潜在 bug 等 Flake8 功能性警告，必须严格修复，禁止忽略。
  - waiver 文件如有更新须同步本规范。
- 所有可执行脚本必须定义 main() 函数作为入口，并通过 `if __name__ == "__main__"` 调用：

  ```python
  def main() -> int:
      # 主业务代码
      return exit_code  # 0 表示成功

  if __name__ == "__main__":
      raise SystemExit(main())
  ```

- 路径拼接与管理统一用 pathlib：

  ```python
  from pathlib import Path
  data_dir = Path("data")
  file_path = data_dir / "data.csv"
  ```

- 遵循 PEP8 基础规范。
- 文件/函数命名统一小写，单词间下划线分隔（snake_case）。
- 代码中避免使用魔法数，必要时定义为常量或 Enum。
- 工程依赖仅通过 uv 进行管理，确保环境可复现性，禁止遗漏依赖在 pyproject.toml 之外。
- 每次开发任务完成后，需总结任务并检查是否有新规则产生，有则及时补充到本规范。
- 函数、类、模块均须配备结构化 docstring，强烈建议公有 API 按 Numpy/Google 风格编写，描述输入、输出、异常。
- 异常处理须细致 catch，严禁裸 except，建议关键异常场景记录日志，避免静默 fail。
- import 需分标准库、第三方、本地包三段，组间空行，组内字母序；禁止未使用 import。
- 优先使用 f-string；适当引入 Enum、dataclasses、typing 等现代 Python 特性以提升可维护性。
- 推荐采用卫语句（guard clause）编程，减少不必要的嵌套缩进，使代码结构更清晰。

## Testing standards (测试相关规范)

- 所有自动化测试代码应统一放置于 tests/ 目录，使用 test\_前缀命名，例如 test_xxx.py。
- 推荐使用 pytest 工具进行测试组织与断言，测试代码同样需加类型提示。
- 测试用例应避免对覆盖率、持续集成（CI）和测试数据纳入版本控制的硬性要求。
- 如因外部依赖数据文件缺失，需用 pytest.mark.skipif 跳过该测试，并给出原因说明。
- 测试代码及其断言风格，需通过 Flake8 检查，要求与主代码一致的代码风格和结构。
- 测试代码示例：

  ```python
  import pytest

  @pytest.mark.skipif(not Path("data/example.csv").exists(), reason="缺测试数据")
  def test_xxx():
      ...
  ```

- 覆盖率报告不是强制要求，测试数据无需纳入版本控制，CI/CD 非必选项。
- 有测试相关更新，规则应同步到本文件，保持项目信息一致性。
