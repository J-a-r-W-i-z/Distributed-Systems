import os
import sys
import matplotlib.pyplot as plt
import numpy as np


def read_server_counts(file_path):
    with open(file_path, 'r') as file:
        lines = file.readlines()
        server_counts = {int(line.split(',')[0]): int(
            line.split(',')[1]) for line in lines}
    return server_counts


def calculate_statistics(server_counts):
    load_values = list(server_counts.values())
    average_load = np.mean(load_values)
    std_deviation = np.std(load_values)
    return average_load, std_deviation


def main():
    if len(sys.argv) != 3:
        print("Usage: python script.py <start_N> <end_N>")
        sys.exit(1)

    start_N, end_N = int(sys.argv[1]), int(sys.argv[2])
    results = []

    for i in range(start_N, end_N + 1):
        file_path = f'Analysis/A2/Values/n{i}.txt'
        server_counts = read_server_counts(file_path)
        average_load, std_deviation = calculate_statistics(server_counts)

        results.append({
            'N': i,
            'Average Load': average_load,
            'Standard Deviation': std_deviation
        })

    # Plotting
    plt.plot([result['N'] for result in results], [result['Average Load']
             for result in results], marker='o', label='Average Load')
    plt.errorbar([result['N'] for result in results], [result['Average Load'] for result in results], yerr=[
                 result['Standard Deviation'] for result in results], linestyle='None', color='gray', capsize=5)

    plt.xlabel('Number of Servers (N)')
    plt.ylabel('Average Load')
    plt.title('Average Load of Servers')
    plt.legend()
    plt.show()


if __name__ == "__main__":
    main()
