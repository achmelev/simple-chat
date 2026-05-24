# Benchmark

The `/benchmark` command evaluates an LLM against a set of tasks and reports a score for each one.

---

## Usage

```
/benchmark <directory>
```

**Single-task mode** — if `<directory>` contains a `config.yaml` file directly, that directory is treated as one task and run immediately.

**Multi-task mode** — if `<directory>` contains no `config.yaml`, every subdirectory is treated as a separate task and run in alphabetical order. A weighted average score is printed at the end.

---

## Task directory layout

Each task lives in its own directory and must contain exactly two files:

```
my-task/
  config.yaml   # task configuration
  score.py      # scoring function
```

### config.yaml

| Key | Required | Description |
|-----|----------|-------------|
| `description` | yes | Short human-readable description of the task |
| `prompt` | yes | The prompt sent to the LLM |
| `time` | yes | Time limit in minutes; streaming is stopped when exceeded |
| `difficulty` | no | Numeric weight used for the weighted average (default: 1.0) |

Example:

```yaml
description: Java program computing Fibonacci numbers
prompt: |
  Write a Java program that reads N from args[0] and prints fib(N).
  ...
time: 5
difficulty: 2.0
```

### score.py

Must define a single function:

```python
def score(workdir: str) -> float:
    ...
```

`workdir` is the absolute path to the directory the LLM worked in. The function must return a `float` between `0.0` (complete failure) and `1.0` (perfect). It is executed via Python's `exec()` in the context of the running program.

---

## How a task runs

1. The conversation history is cleared and a fresh tool environment is created.
2. A uniquely named work directory (`workdir_YYYYMMDD_HHMMSS`) is created inside the task directory and set as the current working directory for the LLM session.
3. The prompt is sent to the LLM and the response is streamed token by token.
4. Elapsed time is checked after every chunk. If the time limit is exceeded the stream is cut and the task scores `0.0`.
5. After the LLM finishes (or times out), `score(workdir)` is called to calculate the result.
6. If the score is `1.0` the work directory is deleted. Otherwise it is left in place for inspection.

---

## Output

During a run each task prints a header with its name, description, and time limit, followed by the prompt as it would appear if a user had typed it. After scoring:

```
[Benchmark] Score for my-task: 0.750  (difficulty: 2.0)
```

In multi-task mode a summary is printed at the end:

```
============================================================
[Benchmark] Final Results:
  01-fibonacci:  1.000  (difficulty: 1.0, Java Fibonacci numbers)
  02-word-count: 0.750  (difficulty: 2.0, Java word frequency counter)
  ...
  Weighted average score: 0.864
============================================================
```

---

## Writing a scoring function

A typical `score.py` awards partial credit:

- **0.0** — nothing useful was produced (e.g. no compiled output found)
- **0.3** — partial progress (e.g. source compiled but program output is wrong)
- **1.0** — all automated checks pass

The function receives the work directory path and can inspect any files the LLM created, compile and run code, or do anything else needed to verify the result. Any files created by the scoring function inside `workdir` are left in place (not cleaned up) so they are available alongside the LLM's output when inspecting a failed run.

---

## Example: javatest

The `javatest/` directory contains five Java tasks of increasing difficulty:

| Directory | Difficulty | Time | Tests |
|-----------|-----------|------|-------|
| `01-fibonacci` | 1.0 | 3 min | Basic loops/recursion |
| `02-word-count` | 2.0 | 5 min | Collections and sorting |
| `03-shapes` | 3.0 | 7 min | OOP, inheritance, polymorphism |
| `04-concurrent-counter` | 4.0 | 8 min | Thread safety and synchronization |
| `05-expression-evaluator` | 5.0 | 12 min | Recursive expression parsing |

Run the full suite:

```
/benchmark javatest/
```

Run a single task:

```
/benchmark javatest/01-fibonacci
```
