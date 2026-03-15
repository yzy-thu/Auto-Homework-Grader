import csv
import os


def export_csv(results, output_path, columns=None):
    """Export grading results to a CSV file with UTF-8 BOM for Excel compatibility.

    Args:
        results: list of dicts. Each dict has metadata keys + "score", "feedback", "error".
        output_path: path to write the CSV file.
        columns: ordered list of metadata column names (e.g. ["学号", "姓名"]).
                 If None, defaults to ["学号", "姓名"].
                 "分数", "反馈", "错误信息" are always appended as the last columns.
    """
    if columns is None:
        columns = ["学号", "姓名"]

    header = columns + ["分数", "反馈", "错误信息"]

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        for r in results:
            meta = r.get("meta", {})
            row = [meta.get(col, "") for col in columns]
            row.append(r.get("score", ""))
            row.append(r.get("feedback", ""))
            row.append(r.get("error", ""))
            writer.writerow(row)
