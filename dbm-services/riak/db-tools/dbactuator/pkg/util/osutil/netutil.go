package osutil

import (
	"net"
	"strconv"
	"time"

	"github.com/pkg/errors"
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

// GetLocalIPAddrs TODO
func GetLocalIPAddrs() ([]string, error) {
	ifaces, err := net.Interfaces()
	if err != nil {
		return nil, errors.Wrap(err, "get local ipaddrs")
	}
	ipAddrs := []string{}
	for _, i := range ifaces {
		addrs, err := i.Addrs()
		if err != nil {
			return nil, errors.Wrap(err, "get local ipaddr")
		}
		for _, addr := range addrs {
			var ip net.IP
			switch v := addr.(type) {
			case *net.IPNet:
				ip = v.IP
			case *net.IPAddr:
				ip = v.IP
			}
			ipAddrs = append(ipAddrs, ip.String())
		}
	}
	if len(ipAddrs) == 0 {
		return nil, errors.New("failed to get any local ipaddr")
	}
	return ipAddrs, nil
}
