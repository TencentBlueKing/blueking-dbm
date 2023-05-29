package netutil

import (
	"fmt"
	"net"
)

// GetAllIpAddr 获取本机所有ip地址
func GetAllIpAddr() []string {
	addrs, err := net.InterfaceAddrs()
	if err != nil {
		fmt.Println(err)
		return nil
	}
	var ipList []string
	for _, address := range addrs {
		if ipnet, ok := address.(*net.IPNet); ok && !ipnet.IP.IsLoopback() {
			if ipnet.IP.To4() != nil {
				ipList = append(ipList, ipnet.IP.String())
			}
		}
	}
	return ipList
}
