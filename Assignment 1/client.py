import concurrent.futures
import requests

url_to_request = "http://127.0.0.1:5000/home"
num_threads = 50
num_requests_per_thread = 200


def make_get_request(i):
    for _ in range(num_requests_per_thread):
        try:
            response = requests.get(url_to_request)
            # Do something with the response, e.g., check status code or content
            print(i+1)
        except Exception as e:
            print(f"An error occurred: {e}")


if __name__ == "__main__":
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        # Use 'submit' to asynchronously submit tasks to the executor
        futures = [executor.submit(make_get_request, i)
                   for i in range(num_threads)]

        # Wait for all tasks to complete
        concurrent.futures.wait(futures)
