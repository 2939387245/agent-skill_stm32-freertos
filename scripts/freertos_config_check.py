#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FreeRTOSConfig.h 配置文件验证工具

功能：
- 检查 FreeRTOSConfig.h 关键配置宏定义
- 验证配置值的有效性
- 输出 JSON 格式结果（便于 CI 集成）
- 支持命令行参数和标准输入

使用方法：
    python freertos_config_check.py FreeRTOSConfig.h
    python freertos_config_check.py FreeRTOSConfig.h --json
    cat FreeRTOSConfig.h | python freertos_config_check.py --stdin

作者：STM32 + FreeRTOS Agent Skill
"""

import re
import sys
import json
import argparse
from typing import Dict, List, Optional, Tuple, Any, Sequence
from dataclasses import dataclass, asdict
from enum import Enum


class CheckStatus(Enum):
    """检查结果状态"""
    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"
    SKIP = "skip"


@dataclass
class ConfigCheck:
    """单个配置检查结果"""
    name: str           # 宏名称
    expected: str       # 期望值
    actual: Optional[str]  # 实际值
    status: str         # pass/fail/warning/skip
    message: str        # 说明信息


@dataclass
class CheckResult:
    """整体检查结果"""
    file: str
    checks: List[Dict[str, Any]]
    summary: Dict[str, int]


class FreeRTOSConfigChecker:
    """FreeRTOSConfig.h 配置文件检查器"""

    # 必需配置项及期望值
    REQUIRED_CHECKS = [
        ("configUSE_PREEMPTION", "1", "启用抢占式调度"),
        ("configUSE_PORT_OPTIMISED_TASK_SELECTION", "1", "使用硬件优先级选择"),
        ("configTICK_RATE_HZ", None, "系统节拍频率（通常为 1000）"),
    ]

    # 推荐配置项及期望值
    RECOMMENDED_CHECKS = [
        ("configUSE_IDLE_HOOK", "1", "启用空闲任务钩子（低功耗用）"),
        ("configUSE_TICK_HOOK", "0", "禁用系统节拍钩子（除非必要）"),
        ("configCHECK_FOR_STACK_OVERFLOW", "2", "启用堆栈溢出检测"),
        ("configUSE_TRACE_FACILITY", "1", "启用 trace 功能"),
        ("configUSE_STATS_FORMATTING_FUNCTIONS", "1", "启用统计格式化函数"),
        ("configGENERATE_RUN_TIME_STATS", "0", "运行时统计（调试时可开启）"),
        ("configUSE_CO_ROUTINES", "0", "禁用协程（推荐使用任务）"),
        ("configMAX_PRIORITIES", None, "最大任务优先级数（通常 32）"),
        ("configMINIMAL_STACK_SIZE", None, "最小堆栈大小（通常 128）"),
        ("configTOTAL_HEAP_SIZE", None, "动态分配堆大小（根据需求设置）"),
    ]

    # 可选配置项及期望值
    OPTIONAL_CHECKS = [
        ("configUSE_MUTEXES", "1", "启用互斥锁"),
        ("configUSE_RECURSIVE_MUTEXES", "1", "启用递归互斥锁"),
        ("configUSE_COUNTING_SEMAPHORES", "1", "启用计数信号量"),
        ("configUSE_TASK_NOTIFICATIONS", "1", "启用任务通知"),
        ("configUSE_TIMERS", "1", "启用软件定时器"),
        ("configTIMER_TASK_PRIORITY", None, "定时器任务优先级"),
        ("configTIMER_QUEUE_LENGTH", None, "定时器队列长度"),
        ("configTIMER_TASK_STACK_DEPTH", None, "定时器任务堆栈深度"),
        ("configUSE_TICKLESS_IDLE", "0", "禁用 Tickless 低功耗（需要额外配置）"),
        ("configCPU_CLOCK_HZ", None, "CPU 时钟频率"),
        ("configSYSTICK_CLOCK_HZ", None, "SysTick 时钟频率"),
        ("configKERNEL_INTERRUPT_PRIORITY", None, "内核中断优先级"),
        ("configMAX_SYSCALL_INTERRUPT_PRIORITY", None, "最大系统调用中断优先级"),
        ("configASSERT(x)", None, "断言定义"),
    ]

    # 禁用配置项
    DISABLED_CHECKS: List[Tuple[str, Optional[str], str]] = [
        ("configUSE_16_BIT_TICKS", "0", "禁用 16 位 tick（必须为 0）"),
    ]

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.checks: List[ConfigCheck] = []

    def parse_config_file(self, content: str) -> Dict[str, str]:
        """
        解析 FreeRTOSConfig.h 文件内容

        Args:
            content: 文件内容字符串

        Returns:
            宏定义字典 {宏名: 值}
        """
        defines = {}

        # 匹配 #define 宏定义
        pattern = r'^\s*#\s*define\s+(\w+)(?:\s+([^\/\n]+))?'
        for match in re.finditer(pattern, content, re.MULTILINE):
            name = match.group(1)
            value = match.group(2)
            if value:
                # 清理值
                value = value.strip()
                # 移除行尾注释
                comment_idx = value.find('//')
                if comment_idx >= 0:
                    value = value[:comment_idx].strip()
                defines[name] = value

        return defines

    def check_value(self, name: str, expected: Optional[str],
                    actual: Optional[str]) -> Tuple[CheckStatus, str]:
        """
        检查配置值

        Args:
            name: 宏名称
            expected: 期望值（None 表示只需存在）
            actual: 实际值

        Returns:
            (状态, 说明信息)
        """
        if actual is None:
            return CheckStatus.FAIL, f"宏 {name} 未定义"

        # 处理特殊期望值
        if expected is None:
            # 只需要存在
            return CheckStatus.PASS, f"{name} = {actual}"

        # 精确匹配
        if actual == expected:
            return CheckStatus.PASS, f"{name} = {actual}"

        # 数值匹配（处理进制前缀）
        try:
            if actual.startswith(('0x', '0X')):
                actual_int = int(actual, 16)
            elif actual.startswith('0') and len(actual) > 1:
                actual_int = int(actual, 8)
            else:
                actual_int = int(actual)

            if expected.startswith(('0x', '0X')):
                expected_int = int(expected, 16)
            else:
                expected_int = int(expected)

            if actual_int == expected_int:
                return CheckStatus.PASS, f"{name} = {actual}"
        except ValueError:
            pass

        # 值不匹配
        if expected in ('0', '1'):
            return CheckStatus.FAIL, f"{name} 应为 {expected}，实际为 {actual}"
        else:
            return CheckStatus.WARNING, f"{name} 推荐值为 {expected}，实际为 {actual}"

    def run_checks(self, defines: Dict[str, str],
                   check_list: Sequence[Tuple[str, Optional[str], str]],
                   category: str) -> None:
        """
        运行一组检查

        Args:
            defines: 宏定义字典
            check_list: 检查项列表
            category: 检查类别（用于输出）
        """
        for name, expected, description in check_list:
            actual = defines.get(name)

            status, message = self.check_value(name, expected, actual)

            if status == CheckStatus.FAIL and actual is None:
                message = f"{description}：{message}"

            self.checks.append(ConfigCheck(
                name=name,
                expected=str(expected) if expected else "defined",
                actual=actual,
                status=status.value,
                message=message
            ))

            if self.verbose and status != CheckStatus.PASS:
                print(f"[{category}] {name}: {message}")

    def check_config(self, content: str, filename: str = "FreeRTOSConfig.h") -> CheckResult:
        """
        执行完整的配置检查

        Args:
            content: 文件内容
            filename: 文件名（用于输出）

        Returns:
            检查结果
        """
        defines = self.parse_config_file(content)
        self.checks = []

        # 运行所有检查
        self.run_checks(defines, self.REQUIRED_CHECKS, "必需")
        self.run_checks(defines, self.RECOMMENDED_CHECKS, "推荐")
        self.run_checks(defines, self.OPTIONAL_CHECKS, "可选")
        self.run_checks(defines, self.DISABLED_CHECKS, "禁用")

        # 计算摘要
        summary = {
            "passed": sum(1 for c in self.checks if c.status == "pass"),
            "failed": sum(1 for c in self.checks if c.status == "fail"),
            "warnings": sum(1 for c in self.checks if c.status == "warning"),
            "skipped": sum(1 for c in self.checks if c.status == "skip"),
            "total": len(self.checks)
        }

        # 构建结果
        result = CheckResult(
            file=filename,
            checks=[asdict(c) for c in self.checks],
            summary=summary
        )

        return result

    def print_result(self, result: CheckResult) -> None:
        """打印人类可读的结果"""
        print(f"\n{'='*60}")
        print(f"FreeRTOSConfig.h 检查结果: {result.file}")
        print(f"{'='*60}")

        # 打印摘要
        summary = result.summary
        print(f"\n摘要: 通过={summary['passed']}, "
              f"失败={summary['failed']}, "
              f"警告={summary['warnings']}, "
              f"总计={summary['total']}")

        # 打印详细信息
        print(f"\n详细结果:")
        print("-" * 60)

        # 先打印失败的
        for check in result.checks:
            if check["status"] == "fail":
                self._print_check(check, "❌")

        # 再打印警告的
        for check in result.checks:
            if check["status"] == "warning":
                self._print_check(check, "⚠️")

        # 最后打印通过的
        passed_count = 0
        for check in result.checks:
            if check["status"] == "pass":
                passed_count += 1
                if passed_count <= 10:  # 只显示前 10 个
                    self._print_check(check, "✅")

        if passed_count > 10:
            print(f"... 还有 {passed_count - 10} 个检查通过")

        print("-" * 60)

        # 打印建议
        failed_checks = [c for c in result.checks if c["status"] == "fail"]
        if failed_checks:
            print(f"\n建议修复项:")
            for check in failed_checks:
                print(f"  - {check['name']}: {check['message']}")

    def _print_check(self, check: Dict, icon: str) -> None:
        """打印单个检查结果"""
        print(f"{icon} {check['name']}")
        print(f"   期望: {check['expected']}, 实际: {check['actual']}")
        print(f"   说明: {check['message']}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="FreeRTOSConfig.h 配置文件验证工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s FreeRTOSConfig.h
  %(prog)s FreeRTOSConfig.h --json
  %(prog)s FreeRTOSConfig.h --verbose
  cat FreeRTOSConfig.h | %(prog)s --stdin
        """
    )

    parser.add_argument("filename", nargs="?", help="配置文件路径")
    parser.add_argument("--json", action="store_true",
                        help="输出 JSON 格式")
    parser.add_argument("--stdin", action="store_true",
                        help="从标准输入读取")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="详细输出")
    parser.add_argument("--output", "-o", help="输出到文件")

    args = parser.parse_args()

    # 读取配置文件
    content = ""

    if args.stdin:
        content = sys.stdin.read()
        filename = "<stdin>"
    elif args.filename:
        try:
            with open(args.filename, "r", encoding="utf-8") as f:
                content = f.read()
            filename = args.filename
        except FileNotFoundError:
            print(f"错误: 文件未找到: {args.filename}")
            sys.exit(1)
        except Exception as e:
            print(f"错误: 读取文件失败: {e}")
            sys.exit(1)
    else:
        parser.print_help()
        sys.exit(1)

    # 检查文件内容
    if not content.strip():
        print("错误: 配置文件为空")
        sys.exit(1)

    # 运行检查
    checker = FreeRTOSConfigChecker(verbose=args.verbose)
    result = checker.check_config(content, filename)

    # 输出结果
    if args.json:
        # JSON 格式输出
        output = json.dumps(asdict(result), indent=2, ensure_ascii=False)
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(output)
        else:
            print(output)
    else:
        # 人类可读格式
        checker.print_result(result)

        # 如果指定输出文件
        if args.output:
            output = json.dumps(asdict(result), indent=2, ensure_ascii=False)
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(output)
            print(f"\n结果已保存到: {args.output}")

    # 返回退出码
    if result.summary["failed"] > 0:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
