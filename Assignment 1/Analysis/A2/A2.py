import concurrent.futures
import requests
import matplotlib.pyplot as plt
import sys
import os

url_to_request = "http://127.0.0.1:5000/home"
num_threads = 50
num_requests_per_thread = 200

server_counts = {}


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
    # Check if the argument is provided
    if len(sys.argv) != 2:
        print("Usage: python script.py <argument>")
        sys.exit(1)

    # Get the argument
    argument_value = sys.argv[1]

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
        f"Request Count Handled by Each Server Instance (n{argument_value})")
    # save the figure in current directory/n{argument_value}.png
    plt.savefig(f"Analysis/A2/Plots/n{argument_value}.png")

    with open(f"Analysis/A2/Values/n{argument_value}.txt", "w") as f:
        f.write(str(server_counts))
