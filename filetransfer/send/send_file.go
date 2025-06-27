package main

import (
	"bufio"
	"encoding/json"
	"fmt"
	"io"
	"net"
	"os"
	"path/filepath"
	"strings"
)

// Config 结构体用于解析JSON配置文件
type Config struct {
	DefaultIP      string `json:"default_ip"`
	DefaultPort    string `json:"default_port"`
	DefaultSaveDir string `json:"default_save_dir"`
}

// loadConfig 加载JSON配置文件
func loadConfig(path string) (Config, error) {
	var config Config
	configFile, err := os.Open(path)
	if err != nil {
		// 如果文件不存在，返回一个带有默认值的空配置，而不是错误
		if os.IsNotExist(err) {
			return Config{
				DefaultIP:   "127.0.0.1",
				DefaultPort: "9999",
			}, nil
		}
		return config, err
	}
	defer configFile.Close()
	decoder := json.NewDecoder(configFile)
	err = decoder.Decode(&config)
	return config, err
}

func main() {
	// 加载配置
	config, err := loadConfig("config.json")
	if err != nil {
		fmt.Println("警告: 读取配置文件失败, 将使用默认值:", err)
		// 提供一个默认的配置以便程序可以继续
		config = Config{
			DefaultIP:   "127.0.0.1",
			DefaultPort: "9999",
		}
	}

	// 从用户输入获取目标IP和端口
	reader := bufio.NewReader(os.Stdin)

	fmt.Printf("请输入接收方IP地址 (默认为 %s): ", config.DefaultIP)
	ipAddress, _ := reader.ReadString('\n')
	ipAddress = strings.TrimSpace(ipAddress)
	if ipAddress == "" {
		ipAddress = config.DefaultIP
	}

	fmt.Printf("请输入接收方端口 (默认为 %s): ", config.DefaultPort)
	portStr, _ := reader.ReadString('\n')
	portStr = strings.TrimSpace(portStr)
	if portStr == "" {
		portStr = config.DefaultPort
	}

	// 获取要发送的文件或文件夹路径
	fmt.Print("请输入要发送的文件或文件夹路径: ")
	path, _ := reader.ReadString('\n')
	path = strings.TrimSpace(path)

	// 检查路径是否存在
	info, err := os.Stat(path)
	if err != nil {
		if os.IsNotExist(err) {
			fmt.Println("错误: 文件或文件夹不存在。")
		} else {
			fmt.Println("获取路径信息失败:", err)
		}
		return
	}

	// 连接到接收方
	conn, err := net.Dial("tcp", ipAddress+":"+portStr)
	if err != nil {
		fmt.Println("连接失败:", err)
		return
	}
	defer conn.Close()

	fmt.Println("已连接到接收方，开始传输...")

	// 根据是文件还是目录进行不同处理
	if info.IsDir() {
		err = sendDirectory(conn, path)
	} else {
		err = sendFile(conn, path, filepath.Base(path))
	}

	if err != nil {
		fmt.Printf("传输过程中发生错误: %v\n", err)
	} else {
		fmt.Println("传输完成!")
	}
}

// sendDirectory 遍历目录并发送文件和子目录
func sendDirectory(conn net.Conn, dirPath string) error {
	// We use the parent of the source directory as the base
	// so that the receiver creates the source directory itself.
	baseDir := filepath.Dir(dirPath)
	return filepath.Walk(dirPath, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return err
		}

		// Get relative path
		relPath, err := filepath.Rel(baseDir, path)
		if err != nil {
			return err
		}
		// Use forward slashes for cross-platform compatibility
		relPath = filepath.ToSlash(relPath)

		if info.IsDir() {
			// Send directory information
			fmt.Printf("发送目录: %s\n", relPath)
			_, err = fmt.Fprintf(conn, "D\n%s\n", relPath)
			return err
		}
		// It's a file, send it
		return sendFile(conn, path, relPath)
	})
}

// sendFile 发送单个文件
func sendFile(conn net.Conn, filePath string, relPath string) error {
	file, err := os.Open(filePath)
	if err != nil {
		fmt.Printf("打开文件失败 '%s': %v\n", filePath, err)
		return err
	}
	defer file.Close()

	fileInfo, err := file.Stat()
	if err != nil {
		fmt.Printf("获取文件信息失败 '%s': %v\n", filePath, err)
		return err
	}

	// Send file metadata (type, path, size)
	_, err = fmt.Fprintf(conn, "F\n%s\n%d\n", relPath, fileInfo.Size())
	if err != nil {
		return err
	}

	fmt.Printf("发送文件: %s (%.2f MB)\n", relPath, float64(fileInfo.Size())/1024/1024)

	// Send file content with progress
	bytesSent := int64(0)
	buffer := make([]byte, 4096)
	for {
		bytesRead, err := file.Read(buffer)
		if err != nil {
			if err == io.EOF {
				break
			}
			return err
		}

		_, err = conn.Write(buffer[:bytesRead])
		if err != nil {
			return err
		}

		bytesSent += int64(bytesRead)
		// Use carriage return to show progress on a single line
		fmt.Printf("\r发送进度 (%s): %.2f%% ", relPath, float64(bytesSent)/float64(fileInfo.Size())*100)
	}
	fmt.Println() // Print a newline after the loop finishes
	return nil
}
