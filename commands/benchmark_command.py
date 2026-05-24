import json
import os
import shutil
import time
import traceback
from datetime import datetime
from typing import Callable, List, Union

import yaml

from commands.base import Command, CommandResult


class BenchmarkCommand(Command):

    def __init__(self, conversation: list, tool_registry, cfg: dict, system_prompt: str,
                 stream_chat_fn: Callable, validate_message_fn: Callable,
                 append_message_fn: Callable):
        self._conversation = conversation
        self._tool_registry = tool_registry
        self._cfg = cfg
        self._system_prompt = system_prompt
        self._stream_chat = stream_chat_fn
        self._validate_message = validate_message_fn
        self._append_message = append_message_fn

    def name(self) -> str:
        return "benchmark"

    def short_description(self) -> str:
        return "Run benchmark tasks from a directory"

    def description(self) -> str:
        return (
            "Runs a set of benchmark tasks from a directory.\n"
            "Each task subdirectory must contain:\n"
            "  config.yaml  (keys: description, prompt, time)\n"
            "  score.py     (defines: score(workdir: str) -> float)\n"
            "Usage: /benchmark <directory>"
        )

    def execute(self, arguments: List[str]) -> Union[str, CommandResult, None]:
        if not arguments:
            return "Usage: /benchmark <directory>"

        benchmark_dir = arguments[0]
        if not os.path.isdir(benchmark_dir):
            return f"Not a directory: {benchmark_dir}"

        original_dir = os.getcwd()

        # Single-task mode: config.yaml lives directly in the given directory
        if os.path.isfile(os.path.join(benchmark_dir, "config.yaml")):
            self._run_task(benchmark_dir, original_dir)
            return None

        # Multi-task mode: each subdirectory is a task
        task_dirs = sorted([
            os.path.join(benchmark_dir, d)
            for d in os.listdir(benchmark_dir)
            if os.path.isdir(os.path.join(benchmark_dir, d))
        ])

        if not task_dirs:
            return f"No task subdirectories found in: {benchmark_dir}"

        results = []
        for task_dir in task_dirs:
            result = self._run_task(task_dir, original_dir)
            if result is not None:
                results.append(result)

        if not results:
            return "No tasks were completed."

        print(f"\n{'='*60}")
        print("[Benchmark] Final Results:")
        for task_name, description, score, difficulty in results:
            print(f"  {task_name}: {score:.3f}  (difficulty: {difficulty}, {description})")
        total_weight = sum(d for _, _, _, d in results)
        weighted_avg = sum(s * d for _, _, s, d in results) / total_weight
        print(f"  Weighted average score: {weighted_avg:.3f}")
        print(f"{'='*60}")

        return None

    def _run_task(self, task_dir: str, original_dir: str):
        """Run a single benchmark task. Returns (task_name, description, score, difficulty) or None on skip."""
        task_name = os.path.basename(task_dir)
        config_path = os.path.join(task_dir, "config.yaml")
        score_py_path = os.path.join(task_dir, "score.py")

        if not os.path.isfile(config_path):
            print(f"[Benchmark] Skipping {task_name}: missing config.yaml")
            return None
        if not os.path.isfile(score_py_path):
            print(f"[Benchmark] Skipping {task_name}: missing score.py")
            return None

        with open(config_path, "r", encoding="utf-8") as f:
            task_config = yaml.safe_load(f) or {}

        description = task_config.get("description", task_name)
        prompt = task_config.get("prompt", "")
        time_minutes = task_config.get("time", 5)
        difficulty = float(task_config.get("difficulty", 1.0))
        time_limit_seconds = time_minutes * 60

        if not prompt:
            print(f"[Benchmark] Skipping {task_name}: missing prompt in config.yaml")
            return None

        print(f"\n{'='*60}")
        print(f"[Benchmark] Task: {task_name}")
        print(f"[Benchmark] Description: {description}")
        print(f"[Benchmark] Time limit: {time_minutes} min")
        print(f"{'='*60}")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        workdir = os.path.join(task_dir, f"workdir_{timestamp}")
        os.makedirs(workdir, exist_ok=True)

        self._conversation.clear()
        self._conversation.append({"role": "system", "content": self._system_prompt})
        self._tool_registry.reset()

        print("You (finish with empty line. Type /quit to exit, /help for available commands):")
        print(prompt)
        print()

        os.chdir(workdir)
        start_time = time.time()
        timed_out = False
        try:
            timed_out = self._run_llm_loop(prompt, time_limit_seconds, start_time)
        except Exception as e:
            print(f"[Benchmark] Error running task {task_name}: {e}")
            traceback.print_exc()
        finally:
            os.chdir(original_dir)

        if timed_out:
            score = 0.0
        else:
            score = self._calculate_score(score_py_path, workdir)
        if score == 1.0:
            shutil.rmtree(workdir, ignore_errors=True)
        else:
            print(f"[Benchmark] Work dir kept for inspection: {workdir}")
        print(f"[Benchmark] Score for {task_name}: {score:.3f}  (difficulty: {difficulty})")
        return (task_name, description, score, difficulty)

    def _run_llm_loop(self, prompt: str, time_limit_seconds: float, start_time: float) -> bool:
        """Run the LLM conversation loop. Returns True if the time limit was exceeded."""
        self._conversation.append({"role": "user", "content": prompt})

        while True:
            if time.time() - start_time >= time_limit_seconds:
                print("\n[Benchmark] Time limit reached before LLM call")
                return True

            try:
                message = self._stream_chat(
                    self._conversation, self._cfg, self._tool_registry,
                    time_limit_seconds=time_limit_seconds,
                    start_time=start_time,
                )
            except Exception as e:
                print(f"\n[Benchmark] LLM error: {e}")
                return False

            if message.get("timed_out"):
                print("\n[Benchmark] Time limit exceeded during streaming")
                self._append_message(self._conversation, message)
                return True

            try:
                self._validate_message(message, self._cfg)
            except Exception as e:
                print(f"\n[Benchmark] Response validation error: {e}")
                return False

            self._append_message(self._conversation, message)

            if self._cfg.get("use_finish_reason", True):
                finish_reason = message.get("finish_reason")
                if finish_reason in ("stop", "length", "content_filter"):
                    return False
                elif finish_reason == "tool_calls":
                    if not self._execute_tool_calls(message, start_time, time_limit_seconds):
                        return True
                else:
                    return False
            else:
                tool_calls = message.get("tool_calls", [])
                if tool_calls:
                    if not self._execute_tool_calls(message, start_time, time_limit_seconds):
                        return True
                else:
                    return False

    def _execute_tool_calls(self, message: dict, start_time: float,
                             time_limit_seconds: float) -> bool:
        """Execute all tool calls in the message. Returns True to continue the LLM loop."""
        for tool_call in message["tool_calls"]:
            if time.time() - start_time >= time_limit_seconds:
                print("\n[Benchmark] Time limit reached during tool execution")
                return False

            name = tool_call["function"]["name"]
            args_str = tool_call["function"]["arguments"]
            try:
                args = json.loads(args_str) if args_str else {}
            except json.JSONDecodeError:
                args = {}

            print(self._tool_registry.short_format_call(name, args))

            try:
                result = self._tool_registry.execute(name, args)
            except Exception as e:
                result = f"ERROR: {e}"

            if self._cfg.get("trace", {}).get("toolcall", False):
                try:
                    call_string = self._tool_registry.format_call(name, args, result)
                    print(f"\n{call_string}\n")
                except Exception:
                    pass

            self._conversation.append({
                "role": "tool",
                "tool_call_id": tool_call["id"],
                "content": result,
            })

        return True

    def _calculate_score(self, score_py_path: str, workdir: str) -> float:
        """Execute score.py and call score(workdir), returning a float 0.0–1.0."""
        if not os.path.isfile(score_py_path):
            print(f"[Benchmark] score.py not found at {score_py_path}")
            return 0.0
        try:
            with open(score_py_path, "r", encoding="utf-8") as f:
                code = f.read()
            namespace = {}
            exec(code, namespace)  # noqa: S102
            score_fn = namespace.get("score")
            if score_fn is None:
                print("[Benchmark] score.py does not define a 'score' function")
                return 0.0
            result = score_fn(workdir)
            return float(result)
        except Exception as e:
            print(f"[Benchmark] Error calculating score: {e}")
            traceback.print_exc()
            return 0.0
