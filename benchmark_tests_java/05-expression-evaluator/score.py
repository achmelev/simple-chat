import os
import subprocess


def score(workdir):
    bin_expr = os.path.join(workdir, "bin", "org", "expr")
    if not os.path.isdir(bin_expr):
        return 0.0
    class_files = [f for f in os.listdir(bin_expr) if f.endswith(".class")]
    if not class_files:
        return 0.0

    compiled_score = 0.3
    classpath = os.path.join(workdir, "bin")
    class_name = "org.expr.ExpressionEvaluator"

    test_cases = [
        ("2+3", "5"),
        ("10-3", "7"),
        ("3*4", "12"),
        ("10/3", "3"),           # integer division truncates toward zero
        ("2+3*4", "14"),         # precedence: * before +
        ("2*3+4*5", "26"),       # precedence across multiple operators
        ("(2+3)*4", "20"),       # parentheses override precedence
        ("(2+3)*(4+5)", "45"),   # parentheses on both sides
        ("100/5/4", "5"),        # left-to-right associativity
        ("2+3*4-1", "13"),       # combined precedence
    ]

    passed = 0
    for expr, expected in test_cases:
        try:
            result = subprocess.run(
                ["java", "-cp", classpath, class_name, expr],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0 and result.stdout.strip() == expected:
                passed += 1
        except Exception:
            pass

    if passed == 0:
        return compiled_score
    return compiled_score + (1.0 - compiled_score) * (passed / len(test_cases))
