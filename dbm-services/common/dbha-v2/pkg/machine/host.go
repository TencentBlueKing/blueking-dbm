/**
 * MIT License
 *
 * Copyright (c) 2023 腾讯蓝鲸
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 */

package machine

import (
	"net"
	"strings"

	"dbm-services/common/dbha-v2/pkg/gerrors"
)

// GetLocalIPs Obtain local ips
func GetLocalIPs() ([]string, error) {
	var ips []string

	interfaces, err := net.Interfaces()
	if err != nil {
		return nil, err
	}

	for _, iface := range interfaces {
		if !isPhysicalInterface(iface) {
			continue
		}

		addrs, err := iface.Addrs()
		if err != nil {
			continue
		}

		for _, addr := range addrs {
			if ipnet, ok := addr.(*net.IPNet); ok {
				ip := ipnet.IP

				if ip.IsLoopback() {
					continue
				}
				if ip.IsLinkLocalUnicast() {
					continue
				}

				if ip.IsLinkLocalMulticast() {
					continue
				}

				if ip.IsMulticast() {
					continue
				}

				if ip.IsUnspecified() {
					continue
				}

				ips = append(ips, ip.String())
			}
		}
	}

	return ips, nil
}

// GetLocalIPWithInterface Obtain local ip with interface
func GetLocalIPWithInterface(interfaceName string) (string, error) {
	iface, err := net.InterfaceByName(interfaceName)
	if err != nil {
		return "", err
	}

	addrs, err := iface.Addrs()
	if err != nil {
		return "", err
	}

	for _, addr := range addrs {
		if ipnet, ok := addr.(*net.IPNet); ok && !ipnet.IP.IsLoopback() {
			if ipnet.IP.To4() != nil {
				return ipnet.IP.String(), nil
			}
		}
	}

	return "", gerrors.Newf(gerrors.Failure, "interface %s has no ipv4 address", interfaceName)
}

func isPhysicalInterface(iface net.Interface) bool {
	// 1. check interface flags
	if iface.Flags&net.FlagUp == 0 {
		return false
	}
	if iface.Flags&net.FlagLoopback != 0 {
		return false
	}

	// 2. check mac address
	// Virtual network cards usually have a specific OUI
	// (Organizationally Unique Identifier)
	mac := iface.HardwareAddr
	if len(mac) >= 3 {
		oui := mac[:3]
		// Common Virtualization Technology's OUI
		virtualOUIs := map[[3]byte]string{
			{0x00, 0x0C, 0x29}: "VMware",
			{0x00, 0x50, 0x56}: "VMware",
			{0x00, 0x05, 0x69}: "VMware",
			{0x00, 0x1C, 0x14}: "VMware",
			{0x00, 0x1C, 0x42}: "Parallels",
			{0x00, 0x16, 0x3E}: "Xen",
			{0x00, 0x0F, 0x4B}: "Xen",
			{0x00, 0x1C, 0x42}: "Parallels",
			{0x08, 0x00, 0x27}: "VirtualBox",
			{0x0A, 0x00, 0x27}: "VirtualBox",
			{0x02, 0x16, 0x3E}: "Microsoft Hyper-V",
			{0x00, 0x15, 0x5D}: "Microsoft Hyper-V",
		}

		var ouiBytes [3]byte
		copy(ouiBytes[:], oui)
		if _, isVirtual := virtualOUIs[ouiBytes]; isVirtual {
			return false
		}
	}

	// 3. check MAC address is all zero or multicast address
	if len(mac) > 0 {
		isZeroMAC := true
		for _, b := range mac {
			if b != 0 {
				isZeroMAC = false
				break
			}
		}

		if isZeroMAC {
			return false
		}

		// check multicast bit (least significant bit of the lowest byte)
		if mac[0]&0x01 != 0 {
			return false
		}
	}

	// 4. check interface name patterns
	name := strings.ToLower(iface.Name)
	virtualPatterns := []string{
		"docker", "veth", "br-", "virbr", "vmnet",
		"vboxnet", "tap", "tun", "wg", "utun",
		"bond", "kube", "cni", "flannel", "vpn",
		"ppp", "tunnel", "gre", "gretap", "wireguard",
	}

	for _, pattern := range virtualPatterns {
		if strings.Contains(name, pattern) {
			return false
		}
	}

	return true
}
