import os
import subprocess


def score(workdir):
    bin_wc = os.path.join(workdir, "bin", "org", "wordcount")
    if not os.path.isdir(bin_wc):
        return 0.0
    class_files = [f for f in os.listdir(bin_wc) if f.endswith(".class")]
    if not class_files:
        return 0.0

    compiled_score = 0.3
    classpath = os.path.join(workdir, "bin")
    class_name = "org.wordcount.WordCount"

    # "the"=3, "fox"=2, then 6 words with count=1 sorted alphabetically
    test_text = "the quick brown fox jumps over the lazy dog the fox"
    expected_lines = [
        "the: 3",
        "fox: 2",
        "brown: 1",
        "dog: 1",
        "jumps: 1",
        "lazy: 1",
        "over: 1",
        "quick: 1",
    ]

    input_file = os.path.join(workdir, "_score_wc_input.txt")
    with open(input_file, "w", encoding="utf-8") as f:
        f.write(test_text + "\n")

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
