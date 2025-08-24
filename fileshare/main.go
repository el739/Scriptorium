package main

import (
	"crypto/rand"
	"encoding/hex"
	"flag"
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"strings"
)

var (
	host = flag.String("host", "localhost", "Host to bind the server to")
	port = flag.String("port", "8080", "Port to bind the server to")
	publicURL = flag.String("public-url", "", "Public URL for generating download links (e.g., https://mydomain.com:8080)")
)

const (
	uploadDir = "./uploads"
	staticDir = "./static"
)

func main() {
	// Parse command line flags
	flag.Parse()

	// Ensure upload directory exists
	err := os.MkdirAll(uploadDir, os.ModePerm)
	if err != nil {
		fmt.Printf("Failed to create upload directory: %v\n", err)
		return
	}

	// Serve static files
	http.Handle("/", http.FileServer(http.Dir(staticDir)))

	// Handle file uploads
	http.HandleFunc("/upload", uploadHandler)

	// Handle file downloads
	http.HandleFunc("/download/", downloadHandler)

	addr := fmt.Sprintf("%s:%s", *host, *port)
	fmt.Printf("Server starting on http://%s\n", addr)
	err = http.ListenAndServe(addr, nil)
	if err != nil {
		fmt.Printf("Server failed to start: %v\n", err)
	}
}

func uploadHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	// Parse multipart form with max memory of 32MB
	err := r.ParseMultipartForm(32 << 20)
	if err != nil {
		http.Error(w, "Unable to parse form", http.StatusBadRequest)
		return
	}

	// Get file from form
	file, handler, err := r.FormFile("file")
	if err != nil {
		http.Error(w, "Unable to get file from form", http.StatusBadRequest)
		return
	}
	defer file.Close()

	// Generate a unique filename
	id, err := generateID()
	if err != nil {
		http.Error(w, "Failed to generate ID", http.StatusInternalServerError)
		return
	}

	// Get file extension
	ext := filepath.Ext(handler.Filename)
	filename := id + ext
	filepath := filepath.Join(uploadDir, filename)

	// Create the file
	dst, err := os.Create(filepath)
	if err != nil {
		http.Error(w, "Unable to create file", http.StatusInternalServerError)
		return
	}
	defer dst.Close()

	// Copy uploaded file to destination
	_, err = io.Copy(dst, file)
	if err != nil {
		http.Error(w, "Unable to save file", http.StatusInternalServerError)
		return
	}

	// Return download link
	var downloadURL string
	if *publicURL != "" {
		downloadURL = fmt.Sprintf("%s/download/%s", *publicURL, filename)
	} else {
		downloadURL = fmt.Sprintf("http://%s:%s/download/%s", *host, *port, filename)
	}
	response := fmt.Sprintf(`
	<!DOCTYPE html>
	<html>
	<head>
		<meta charset="UTF-8">
		<title>Upload Successful</title>
		<style>
			body { font-family: Arial, sans-serif; margin: 40px; }
			.success { color: green; }
			a { color: #007cba; }
		</style>
	</head>
	<body>
		<h1 class="success">File uploaded successfully!</h1>
		<p>Your file has been uploaded successfully.</p>
		<p><a href="%s" target="_blank">Download your file</a></p>
		<p>Download link: <code>%s</code></p>
		<p><a href="/">Upload another file</a></p>
	</body>
	</html>
	`, downloadURL, downloadURL)

	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	w.WriteHeader(http.StatusOK)
	w.Write([]byte(response))
}

func downloadHandler(w http.ResponseWriter, r *http.Request) {
	// Extract filename from URL path
	filename := strings.TrimPrefix(r.URL.Path, "/download/")
	if filename == "" {
		http.Error(w, "Filename not specified", http.StatusBadRequest)
		return
	}

	// Security check: prevent directory traversal
	if strings.Contains(filename, "..") || strings.Contains(filename, "/") || strings.Contains(filename, "\\") {
		http.Error(w, "Invalid filename", http.StatusBadRequest)
		return
	}

	// Construct file path
	filepath := filepath.Join(uploadDir, filename)

	// Check if file exists
	if _, err := os.Stat(filepath); os.IsNotExist(err) {
		http.Error(w, "File not found", http.StatusNotFound)
		return
	}

	// Set content disposition header for download
	w.Header().Set("Content-Disposition", fmt.Sprintf("attachment; filename=\"%s\"", filename))
	w.Header().Set("Content-Type", "application/octet-stream")

	// Serve the file
	http.ServeFile(w, r, filepath)
}

func generateID() (string, error) {
	bytes := make([]byte, 16)
	_, err := rand.Read(bytes)
	if err != nil {
		return "", err
	}
	return hex.EncodeToString(bytes), nil
}
