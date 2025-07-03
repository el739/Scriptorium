package main

import (
	"bufio"
	"log"
	"math/rand"
	"net"
	"os"
	"sort"
	"sync"
	"time"

	"github.com/go-ping/ping"
)

const (
	pingCount      = 3                      // 每个IP Ping的次数
	maxLatency     = 500 * time.Millisecond // 最大平均延迟
	concurrentJobs = 200                    // 并发执行的goroutine数量
	inputFile      = "../assets/ip.txt"
	outputFile     = "../assets/fast_ips.txt"
)

// PingResult stores the IP and its latency.
type PingResult struct {
	IP      string
	Latency time.Duration
}

// inc increments an IP address.
func inc(ip net.IP) {
	for j := len(ip) - 1; j >= 0; j-- {
		ip[j]++
		if ip[j] > 0 {
			break
		}
	}
}

// ipsFromCIDR generates all IP addresses from a CIDR string.
func ipsFromCIDR(cidr string) ([]string, error) {
	ip, ipnet, err := net.ParseCIDR(cidr)
	if err != nil {
		return nil, err
	}

	var ips []string
	for ip := ip.Mask(ipnet.Mask); ipnet.Contains(ip); inc(ip) {
		ips = append(ips, ip.String())
	}
	// remove network address and broadcast address
	if len(ips) > 2 {
		return ips[1 : len(ips)-1], nil
	}
	return ips, nil
}

// worker function that pings IPs from the jobs channel and sends good results to the results channel.
func worker(id int, jobs <-chan string, results chan<- PingResult, wg *sync.WaitGroup) {
	defer wg.Done()
	for ip := range jobs {
		pinger, err := ping.NewPinger(ip)
		if err != nil {
			// Skip invalid IPs
			continue
		}
		pinger.SetPrivileged(true) // Required on some systems
		pinger.Count = pingCount
		pinger.Timeout = time.Second * time.Duration(pingCount) // Timeout for the whole ping operation

		err = pinger.Run() // Blocks until finished
		if err != nil {
			continue
		}

		stats := pinger.Statistics()
		if stats.PacketsRecv > 0 && stats.AvgRtt < maxLatency {
			log.Printf("IP: %s, Latency: %v\n", stats.Addr, stats.AvgRtt)
			results <- PingResult{IP: stats.Addr, Latency: stats.AvgRtt}
		}
	}
}

func main() {
	log.Println("Starting IP ping test...")

	// Read CIDRs from input file
	file, err := os.Open(inputFile)
	if err != nil {
		log.Fatalf("Failed to open input file %s: %v", inputFile, err)
	}
	defer file.Close()

	var cidrs []string
	scanner := bufio.NewScanner(file)
	for scanner.Scan() {
		cidrs = append(cidrs, scanner.Text())
	}
	if err := scanner.Err(); err != nil {
		log.Fatalf("Error reading input file: %v", err)
	}

	jobs := make(chan string, concurrentJobs)
	results := make(chan PingResult, 1000) // Buffer for good IPs
	var wg sync.WaitGroup

	// Start workers
	for w := 1; w <= concurrentJobs; w++ {
		wg.Add(1)
		go worker(w, jobs, results, &wg)
	}
	log.Printf("Started %d workers.\n", concurrentJobs)

	// Goroutine to send all IPs to the jobs channel
	go func() {
		r := rand.New(rand.NewSource(time.Now().UnixNano()))
		for _, cidr := range cidrs {
			ips, err := ipsFromCIDR(cidr)
			if err != nil {
				log.Printf("Could not parse CIDR %s: %v", cidr, err)
				continue
			}

			if len(ips) > 50 {
				r.Shuffle(len(ips), func(i, j int) { ips[i], ips[j] = ips[j], ips[i] })
				ips = ips[:50]
			}

			log.Printf("Adding %d IPs from %s to the queue.\n", len(ips), cidr)
			for _, ip := range ips {
				jobs <- ip
			}
		}
		close(jobs)
	}()

	// Goroutine to wait for all workers to finish and then close the results channel
	go func() {
		wg.Wait()
		close(results)
	}()

	// Collect results
	var goodIPs []PingResult
	for result := range results {
		goodIPs = append(goodIPs, result)
	}

	log.Printf("Found %d IPs with latency < %v.\n", len(goodIPs), maxLatency)

	// Sort the IPs by latency
	sort.Slice(goodIPs, func(i, j int) bool {
		return goodIPs[i].Latency < goodIPs[j].Latency
	})

	// Write results to output file
	output, err := os.Create(outputFile)
	if err != nil {
		log.Fatalf("Failed to create output file %s: %v", outputFile, err)
	}
	defer output.Close()

	writer := bufio.NewWriter(output)
	for _, result := range goodIPs {
		_, _ = writer.WriteString(result.IP + "\n")
	}
	writer.Flush()

	log.Printf("Successfully wrote %d IPs to %s.\n", len(goodIPs), outputFile)
}
