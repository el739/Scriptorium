# Go File Upload Server

A simple web server written in Go that allows users to upload files and provides download links for those files.

## Features

- Upload files through a web interface
- Automatically generates unique download links for uploaded files
- Secure file handling with unique filenames
- Configurable host and port settings
- Simple and clean user interface

## Directory Structure

```
.
├── main.go              # Main server code
├── README.md            # This file
├── static/              # Static HTML files
│   └── index.html       # Upload page
└── uploads/             # Uploaded files (created automatically)
```

## Getting Started

### Prerequisites

- Go 1.16 or higher installed on your system

### Running the Server

1. Clone or download this repository
2. Navigate to the project directory
3. Run the server:

```bash
go run main.go
```

By default, the server will start on `http://localhost:8080`.

### Configuration Options

You can configure the host and port using command-line flags:

```bash
# Change the port
go run main.go -port 3000

# Change the host
go run main.go -host 0.0.0.0

# Change both host and port
go run main.go -host 0.0.0.0 -port 3000

# Specify a public URL for download links (useful for CDNs and reverse proxies)
go run main.go -host 0.0.0.0 -port 80 -public-url https://mydomain.com
```

### Using the Server

1. Open your web browser and navigate to the server address (e.g., `http://localhost:8080`)
2. Click "Choose File" to select a file to upload
3. Click "Upload File"
4. After successful upload, you'll receive a download link
5. You can share this link with others to allow them to download the file

### How It Works

1. When a file is uploaded, the server:
   - Generates a unique ID for the file
   - Preserves the original file extension
   - Saves the file in the `uploads/` directory
   - Provides a download link in the response

2. When accessing a download link:
   - The server retrieves the file from the `uploads/` directory
   - Sets appropriate headers for file download
   - Streams the file to the client

### Security Features

- File names are randomized to prevent conflicts and enhance security
- Directory traversal attacks are prevented by validating file paths
- File extensions are preserved but file contents are not executed
- Files are stored outside the web root directory

## Using with Custom Domains, CDNs, and Reverse Proxies

### Custom Domains

You can use a custom domain like "mydomain.com" by specifying the host and port when running the server:

```bash
go run main.go -host mydomain.com -port 80
```

Make sure your domain's DNS is properly configured to point to your server's IP address.

### Using with CDNs

When using a CDN (Content Delivery Network), you'll want download links to point to your CDN rather than your origin server. Use the `-public-url` flag to specify the CDN URL:

```bash
go run main.go -host 0.0.0.0 -port 8080 -public-url https://cdn.yourdomain.com
```

This way:
- The server listens on all interfaces (0.0.0.0) on port 8080
- Uploads are sent directly to your origin server
- Download links point to your CDN URL

### Using with Cloudflare Proxy

When using Cloudflare as a reverse proxy, configure your server like this:

```bash
go run main.go -host 127.0.0.1 -port 8080 -public-url https://mydomain.com
```

This configuration:
- Binds the server to localhost (127.0.0.1) for security
- Uses port 8080 (can be any available port)
- Generates download links that point to your Cloudflare-proxied domain
- Keeps your origin server hidden behind Cloudflare

Configure your Cloudflare DNS to proxy traffic to your origin server's IP address and port.

## Building for Production

To build a binary for deployment:

```bash
go build -o fileserver main.go
./fileserver  # Run on Linux/Mac
fileserver.exe  # Run on Windows
```

## License

This project is open source and available under the MIT License.
