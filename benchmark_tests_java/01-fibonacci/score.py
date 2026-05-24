import os
import subprocess


def score(workdir):
    bin_fib = os.path.join(workdir, "bin", "org", "fibonacci")
    if not os.path.isdir(bin_fib):
        return 0.0
    class_files = [f for f in os.listdir(bin_fib) if f.endswith(".class")]
    if not class_files:
        return 0.0

    compiled_score = 0.3
    classpath = os.path.join(workdir, "bin")
    class_name = "org.fibonacci.FibonacciCalculator"

    # (N, expected fib(N))
    test_cases = [(1, 1), (2, 1), (5, 5), (10, 55), (15, 610)]
    passed = 0
    for n, expected in test_cases:
        try:
            result = subprocess.run(
                ["java", "-cp", classpath, class_name, str(n)],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0 and result.stdout.strip() == str(expected):
                passed += 1
        except Exception:
            pass

    if passed == 0:
        return compiled_score
    return compiled_score + (1.0 - compiled_score) * (passed / len(test_cases))
