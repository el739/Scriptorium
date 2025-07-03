import requests
import time
import os
import socket
from contextlib import contextmanager

# --- Configuration ---
# The file containing the list of IP addresses to test.
IP_FILE = './assets/fast_ips.txt'
# The URL of the file to download for the speed test. We use HTTPS.
DOWNLOAD_URL = 'https://your_cft_domain.cloudfront.net/50mb.test'
# The hostname that corresponds to the CloudFront distribution.
HOSTNAME = 'your_cft_domain.cloudfront.net'
# --- End Configuration ---

@contextmanager
def force_ip_resolution(hostname, ip):
    """
    A context manager to temporarily force a hostname to resolve to a specific IP.
    """
    original_create_connection = socket.create_connection

    def new_create_connection(address, *args, **kwargs):
        # If the address matches the hostname we want to override,
        # use the forced IP. Otherwise, use the original address.
        if address[0] == hostname:
            forced_address = (ip, address[1])
            return original_create_connection(forced_address, *args, **kwargs)
        return original_create_connection(address, *args, **kwargs)

    # Monkey-patch the socket's create_connection function
    socket.create_connection = new_create_connection
    try:
        yield
    finally:
        # Always restore the original function
        socket.create_connection = original_create_connection


def test_speed(ip, url, hostname):
    """
    Tests the download speed from a specific IP address by forcing DNS resolution.

    Args:
        ip (str): The IP address to test.
        url (str): The URL of the file to download (must contain the hostname).
        hostname (str): The hostname to intercept and redirect to the IP.

    Returns:
        A tuple containing (speed_in_mbps, error_message).
        If the download is successful, error_message is None.
    """
    print(f"Testing IP: {ip}...")

    # --- 新增内容 ---
    # 伪装成一个标准的浏览器User-Agent
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    # --- 新增内容结束 ---

    try:
        with force_ip_resolution(hostname, ip):
            start_time = time.time()

            # --- 修改内容 ---
            # 在请求中加入headers
            response = requests.get(url, headers=headers, stream=True, timeout=30)
            # --- 修改内容结束 ---
            
            response.raise_for_status()

            # 检查响应头，确保我们得到的是一个大文件而不是文本
            content_type = response.headers.get('Content-Type', '')
            if 'text/html' in content_type or 'text/plain' in content_type:
                 # 提前读取一小部分内容来判断
                try:
                    first_bytes = next(response.iter_content(128))
                    if b'I just served you' in first_bytes:
                         return 0, "Server returned a fake response, likely due to User-Agent."
                    # 如果不是伪造的响应，需要把已经读取的字节加回来
                    total_downloaded = len(first_bytes)
                except StopIteration:
                    total_downloaded = 0 # 文件很小
            else:
                total_downloaded = 0

            # 下载文件的剩余部分（或全部）
            for chunk in response.iter_content(chunk_size=8192):
                total_downloaded += len(chunk)

            end_time = time.time()

            duration = end_time - start_time
            if duration == 0:
                return 0, "Duration was zero, cannot calculate speed."

            speed = (total_downloaded * 8) / (1024 * 1024) / duration

            return speed, None

    except requests.exceptions.RequestException as e:
        return 0, str(e)

def main():
    """
    Main function to run the speed test.
    """
    # Check if the IP file exists
    if not os.path.exists(IP_FILE):
        print(f"Error: IP file not found at '{IP_FILE}'")
        print("Please create this file and add IP addresses, one per line.")
        return

    # Read IPs from the file
    with open(IP_FILE, 'r') as f:
        ips = [line.strip() for line in f if line.strip()]

    if not ips:
        print(f"No IP addresses found in '{IP_FILE}'.")
        return

    print(f"Starting speed test for {len(ips)} IPs from '{IP_FILE}'...")
    print(f"Test file: {DOWNLOAD_URL}\n")

    results = {}

    # Test each IP
    for ip in ips:
        speed, error = test_speed(ip, DOWNLOAD_URL, HOSTNAME)
        if error:
            print(f"  Error: {error}")
            results[ip] = 0
        else:
            print(f"  Speed: {speed:.2f} Mbps")
            results[ip] = speed

    print("\n--- Results Summary ---")
    # Sort results by speed in descending order
    sorted_results = sorted(results.items(), key=lambda item: item[1], reverse=True)

    for ip, speed in sorted_results:
        print(f"IP: {ip:<15} | Speed: {speed:.2f} Mbps")

if __name__ == "__main__":
    main()