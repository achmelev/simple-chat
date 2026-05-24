import os
import subprocess


def score(workdir):
    bin_concurrent = os.path.join(workdir, "bin", "org", "concurrent")
    if not os.path.isdir(bin_concurrent):
        return 0.0
    class_files = [f for f in os.listdir(bin_concurrent) if f.endswith(".class")]
    if not class_files:
        return 0.0

    compiled_score = 0.3
    classpath = os.path.join(workdir, "bin")
    class_name = "org.concurrent.ConcurrentCounter"

    num_threads, increments = 20, 500
    expected = str(num_threads * increments)  # 10000
    runs = 5
    passed = 0

    for _ in range(runs):
        try:
            result = subprocess.run(
                ["java", "-cp", classpath, class_name,
                 str(num_threads), str(increments)],
                capture_output=True, text=True, timeout=15,
            )
            if result.returncode == 0 and result.stdout.strip() == expected:
                passed += 1
        except Exception:
            pass

    if passed == 0:
        return compiled_score
    if passed == runs:
        return 1.0
    return compiled_score + (1.0 - compiled_score) * (passed / runs)
