package osutil

import (
	"net"
	"strconv"
	"time"
)

// IsPortUp 判断端口是否开启监听
func IsPortUp(host string, ports ...int) bool {
	for _, port := range ports {
		timeout := time.Second
		hostPort := net.JoinHostPort(host, strconv.Itoa(port))
		conn, err := net.DialTimeout("tcp", hostPort, timeout)
		if err != nil {
			// fmt.Println("Connecting error:", err)
			return false
		}
		if conn != nil {
			defer conn.Close()
			return true
			// fmt.Println("Opened", net.JoinHostPort(host, port))
		}
	}
	return false
}
