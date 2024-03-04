import concurrent.futures
import requests
import matplotlib.pyplot as plt
import sys
import os

url_to_request = "http://127.0.0.1:5000/home"
num_threads = 5
num_requests_per_thread = 2

server_counts = {}
current_path = os.path.dirname(os.path.realpath(__file__))


def make_get_request(i):
    for _ in range(num_requests_per_thread):
        try:
            response = requests.get(url_to_request)
            server_id = int(response.json()["message"].split()[-1])

            # Update or initialize the count for the server
            if server_id in server_counts:
                server_counts[server_id] += 1
            else:
                server_counts[server_id] = 1

        except Exception as e:
            print(f"An error occurred: {e}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python script.py <argument> <folder_name>")
        sys.exit(1)

    argument_value = sys.argv[1]
    folder_name = sys.argv[2]

    file_path = f"Analysis/A2/{folder_name}"
    if not os.path.exists(f"{file_path}/Plots"):
        os.makedirs(f"{file_path}/Plots")
    if not os.path.exists(f"{file_path}/Values"):
        os.makedirs(f"{file_path}/Values")

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(make_get_request, i)
                   for i in range(num_threads)]

        concurrent.futures.wait(futures)

    # Bar chart
    server_ids = list(server_counts.keys())
    request_counts = list(server_counts.values())

    plt.bar(server_ids, request_counts, color=[
            "red", "green", "blue", "orange", "purple", "brown", "pink"])

    for i in range(len(request_counts)):
        plt.text(x=server_ids[i], y=request_counts[i]-0.25,
                 s=str(request_counts[i]), size=10, fontweight="bold", ha="center")
    plt.xlabel("Server ID")
    plt.ylabel("Request Count")
    plt.title(
        f"Request Count Handled by Each Server Instance (N = {argument_value})")
    plt.savefig(f"{file_path}/Plots/n{argument_value}.png")

    with open(f"{file_path}/Values/n{argument_value}.txt", "w") as f:
        f.write(str(server_counts))
