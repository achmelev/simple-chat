import math
import os
import subprocess


def score(workdir):
    bin_shapes = os.path.join(workdir, "bin", "org", "shapes")
    if not os.path.isdir(bin_shapes):
        return 0.0
    class_files = [f for f in os.listdir(bin_shapes) if f.endswith(".class")]
    if not class_files:
        return 0.0

    compiled_score = 0.3
    classpath = os.path.join(workdir, "bin")
    class_name = "org.shapes.ShapeCalculator"

    shapes_input = (
        "rectangle 3.0 4.0\n"   # area = 12.00
        "circle 2.0\n"          # area = 12.57  (π×4)
        "triangle 6.0 5.0\n"    # area = 15.00
        "rectangle 10.0 2.0\n"  # area = 20.00
        "circle 3.0\n"          # area = 28.27  (π×9)
    )
    expected_lines = [
        f"Rectangle {3.0 * 4.0:.2f}",
        f"Circle {math.pi * 2.0 ** 2:.2f}",
        f"Triangle {0.5 * 6.0 * 5.0:.2f}",
        f"Rectangle {10.0 * 2.0:.2f}",
        f"Circle {math.pi * 3.0 ** 2:.2f}",
    ]

    input_file = os.path.join(workdir, "_score_shapes_input.txt")
    with open(input_file, "w", encoding="utf-8") as f:
        f.write(shapes_input)

    try:
        result = subprocess.run(
            ["java", "-cp", classpath, class_name, input_file],
            capture_output=True, text=True, timeout=10,
        )
    except Exception:
        return compiled_score

    if result.returncode != 0:
        return compiled_score

    output_lines = [line.rstrip() for line in result.stdout.splitlines() if line.strip()]
    if output_lines == expected_lines:
        return 1.0

    matched = sum(1 for a, b in zip(output_lines, expected_lines) if a == b)
    if matched > 0:
        return compiled_score + (0.7 - compiled_score) * (matched / len(expected_lines))
    return compiled_score
