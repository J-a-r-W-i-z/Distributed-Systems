import os
import matplotlib.pyplot as plt
import numpy as np
import sys


def read_server_counts(file_path):
    with open(file_path, "r") as file:
        content = file.read().strip()
        if not content.startswith("{") or not content.endswith("}"):
            print(f"Invalid content in {file_path}. Skipping...")
            return None
        return eval(content)


def calculate_statistics(server_counts):
    if server_counts is None:
        return None, None
    load_values = list(server_counts.values())
    std_deviation = np.std(load_values)
    return std_deviation


def main():
    if len(sys.argv) != 2:
        print("Usage: python script.py <folder_name>")
        sys.exit(1)

    folder_name = sys.argv[1]
    plot_file_path = f"Analysis/A2/{folder_name}"
    values_folder = f"{plot_file_path}/Values"

    files = sorted([f for f in os.listdir(
        values_folder) if f.endswith(".txt")])

    results = []

    for file in files:
        file_path = os.path.join(values_folder, file)
        server_counts = read_server_counts(file_path)
        std_deviation = calculate_statistics(server_counts)

        if std_deviation is not None:
            results.append({
                "N": int(file[1]),
                "Standard Deviation": std_deviation
            })

    if not results:
        print("No valid data found. Exiting.")
        return

    # Sorting results based on N
    results.sort(key=lambda x: x["N"])

    # Plotting with a line connecting the dots
    plt.plot([result["N"] for result in results], [result["Standard Deviation"]
             for result in results], marker="o", label="Standard Deviation")

    # Showing values on dots
    for result in results:
        plt.text(result["N"], result["Standard Deviation"],
                 f'{result["Standard Deviation"]:.2f}', fontsize=8, ha="center", va="bottom")

    plt.xlabel("Number of Servers (N)")
    plt.ylabel("Standard Deviation")
    plt.title("Standard Deviation of Server Counts")
    plt.legend()
    plt.savefig(f"{plot_file_path}/standard_deviation.png")


if __name__ == "__main__":
    main()
