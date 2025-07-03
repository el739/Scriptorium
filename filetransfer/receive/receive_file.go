package main

import (
	"bufio"
	"encoding/json"
	"fmt"
	"io"
	"net"
	"os"
	"path/filepath"
	"strconv"
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
				DefaultIP:      "127.0.0.1",
				DefaultPort:    "9999",
				DefaultSaveDir: ".",
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
			DefaultIP:      "127.0.0.1",
			DefaultPort:    "9999",
			DefaultSaveDir: ".",
		}
	}

	// 从用户输入获取监听端口和保存目录
	reader := bufio.NewReader(os.Stdin)

	fmt.Printf("请输入接收文件的端口 (默认为 %s): ", config.DefaultPort)
	portStr, _ := reader.ReadString('\n')
	portStr = strings.TrimSpace(portStr)
	if portStr == "" {
		portStr = config.DefaultPort
	}

	fmt.Printf("请输入文件保存目录 (默认为 %s): ", config.DefaultSaveDir)
	saveDir, _ := reader.ReadString('\n')
	saveDir = strings.TrimSpace(saveDir)
	if saveDir == "" {
		saveDir = config.DefaultSaveDir
	}

	// 确保保存目录存在
	if err := os.MkdirAll(saveDir, 0755); err != nil {
		fmt.Println("创建保存目录失败:", err)
		return
	}

	// 开始监听
	listener, err := net.Listen("tcp", ":"+portStr)
	if err != nil {
		fmt.Println("监听端口失败:", err)
		return
	}
	defer listener.Close()

	fmt.Printf("文件接收服务已启动，在端口 %s 上等待连接...\n", portStr)

	for {
		fmt.Println("\n-------------------------------------------------")
		fmt.Printf("等待新的文件传输会话...\n")

		// 接受连接
		conn, err := listener.Accept()
		if err != nil {
			fmt.Println("接受连接失败:", err)
			continue // 不要退出，继续等待下一个连接
		}

		// 使用匿名函数处理每个连接，以便 defer conn.Close() 能正确执行
		func(conn net.Conn) {
			defer conn.Close()
			fmt.Printf("连接已建立 (%s)，准备接收...\n", conn.RemoteAddr().String())

			// 循环接收文件/目录
			connReader := bufio.NewReader(conn)
			for {
				// 读取条目类型 (D for Directory, F for File)
				typeStr, err := connReader.ReadString('\n')
				if err != nil {
					if err == io.EOF {
						break // 连接关闭，正常结束
					}
					fmt.Println("读取条目类型失败:", err)
					return // 结束此连接的处理
				}
				typeStr = strings.TrimSpace(typeStr)

				if typeStr == "D" {
					err = receiveDirectory(connReader, saveDir)
				} else if typeStr == "F" {
					err = receiveFile(connReader, saveDir)
				} else if typeStr == "" { // 可能是发送端正常关闭前的空行
					continue
				} else {
					fmt.Printf("接收到未知的条目类型: '%s'\n", typeStr)
					continue
				}

				if err != nil {
					fmt.Printf("\n处理条目时发生错误: %v\n", err)
					// 不立即返回，尝试继续处理下一个条目
				}
			}
			fmt.Printf("\n来自 %s 的传输会话已结束.\n", conn.RemoteAddr().String())
		}(conn)
	}
}

// receiveDirectory 处理接收到的目录信息
func receiveDirectory(reader *bufio.Reader, saveDir string) error {
	relPath, err := reader.ReadString('\n')
	if err != nil {
		return fmt.Errorf("读取目录路径失败: %w", err)
	}
	relPath = strings.TrimSpace(relPath)

	// 安全检查：确保相对路径不会访问到上级目录
	if strings.Contains(relPath, "..") {
		return fmt.Errorf("检测到不安全的目录路径: %s", relPath)
	}

	fullPath := filepath.Join(saveDir, relPath)
	fmt.Printf("创建目录: %s\n", fullPath)
	return os.MkdirAll(fullPath, 0755)
}

// receiveFile 处理接收到的文件信息和内容
func receiveFile(reader *bufio.Reader, saveDir string) error {
	// 1. 读取相对路径
	relPath, err := reader.ReadString('\n')
	if err != nil {
		return fmt.Errorf("读取文件路径失败: %w", err)
	}
	relPath = strings.TrimSpace(relPath)

	// 安全检查
	if strings.Contains(relPath, "..") {
		return fmt.Errorf("检测到不安全的文件路径: %s", relPath)
	}

	// 2. 读取文件大小
	fileSizeStr, err := reader.ReadString('\n')
	if err != nil {
		return fmt.Errorf("读取文件大小失败: %w", err)
	}
	fileSize, err := strconv.ParseInt(strings.TrimSpace(fileSizeStr), 10, 64)
	if err != nil {
		return fmt.Errorf("解析文件大小失败: %w", err)
	}

	fullPath := filepath.Join(saveDir, relPath)
	fmt.Printf("接收文件: %s (%.2f MB)\n", fullPath, float64(fileSize)/1024/1024)

	// 确保父目录存在
	if err := os.MkdirAll(filepath.Dir(fullPath), 0755); err != nil {
		return fmt.Errorf("创建父目录失败: %w", err)
	}

	// 3. 创建文件
	outputFile, err := os.Create(fullPath)
	if err != nil {
		return fmt.Errorf("创建文件失败: %w", err)
	}
	defer outputFile.Close()

	// 4. 接收文件内容
	bytesReceived, err := io.CopyN(outputFile, reader, fileSize)
	if err != nil {
		return fmt.Errorf("接收文件内容失败: %w", err)
	}

	if bytesReceived != fileSize {
		return fmt.Errorf("文件大小不匹配: 预期 %d, 收到 %d", fileSize, bytesReceived)
	}

	return nil
}
