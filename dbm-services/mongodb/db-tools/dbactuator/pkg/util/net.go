package util

import (
	"fmt"
	"net"
)

// GetIpv4InterfaceName 根据ipv4地址获取网络接口名
// https://stackoverflow.com/questions/23529663/how-to-get-all-addresses-and-masks-from-local-interfaces-in-go
func GetIpv4InterfaceName(ipv4 string) (interName string, err error) {
	var ifaces []net.Interface
	var addrs []net.Addr

	ifaces, err = net.Interfaces()
	if err != nil {
		err = fmt.Errorf("net.Interfaces fail,err:%v", err)
		return
	}
	for _, i := range ifaces {
		addrs, err = i.Addrs()
		if err != nil {
			// err = fmt.Errorf("%s get addrs fail,err:%v", i.Name, err)
			continue
		}
		for _, a := range addrs {
			switch v := a.(type) {
			case *net.IPAddr:
				if v.IP.String() == ipv4 {
					return i.Name, nil
				}

			case *net.IPNet:
				if v.IP.String() == ipv4 {
					return i.Name, nil
				}
			}
		}
	}
	err = fmt.Errorf("ipv4:%s not found interfacename", ipv4)
	return
}

// GetInterfaceIpv4Addr 获取网络接口对应的 ipv4地址
// https://gist.github.com/schwarzeni/f25031a3123f895ff3785970921e962c
func GetInterfaceIpv4Addr(interfaceName string) (addr string, err error) {
	var (
		ief      *net.Interface
		addrs    []net.Addr
		ipv4Addr net.IP
	)
	if ief, err = net.InterfaceByName(interfaceName); err != nil { // get interface
		err = fmt.Errorf("net.InterfaceByName %s fail,err:%v", interfaceName, err)
		return
	}
	if addrs, err = ief.Addrs(); err != nil { // get addresses
		return
	}
	for _, addr := range addrs { // get ipv4 address
		if ipv4Addr = addr.(*net.IPNet).IP.To4(); ipv4Addr != nil {
			break
		}
	}
	if ipv4Addr == nil {
		return "", fmt.Errorf("interface %s don't have an ipv4 address\n", interfaceName)
	}
	return ipv4Addr.String(), nil
}
