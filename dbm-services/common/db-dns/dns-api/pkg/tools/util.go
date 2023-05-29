package tools

import (
	"fmt"
	"regexp"
	"strconv"
	"strings"
)

// CheckDomain TODO
func CheckDomain(domain string) (string, error) {
	domain = strings.TrimSpace(domain)
	if !strings.HasSuffix(domain, ".") {
		domain = domain + "."
	}

	var pattern string = `^[a-zA-Z0-9][-a-zA-Z0-9]{0,62}(\.[a-zA-Z0-9][-a-zA-Z0-9]{0,62}){2,8}\.*(#(\d+))?$`
	if idDns, err := regexp.MatchString(pattern, domain); err != nil {
		return "", err
	} else {
		if idDns {
			return domain, nil
		} else {
			return "", fmt.Errorf("domain_name[%s] format error", domain)
		}
	}
}

// CheckIp TODO
func CheckIp(ip string) (string, error) {
	ip = strings.TrimSpace(ip)
	var pattern string = `^(\d+)\.(\d+)\.(\d+)\.(\d+)$`
	if isIp, err := regexp.MatchString(pattern, ip); err != nil {
		return ip, err
	} else {
		if isIp {
			return ip, nil
		} else {
			return "", fmt.Errorf("ip[%s] format error", ip)
		}
	}
}

// CheckInstance TODO
func CheckInstance(instance string) (string, error) {
	instance = strings.TrimSpace(instance)
	var pattern string = `^(\d+)\.(\d+)\.(\d+)\.(\d+)#(\d+)$`
	if isInstance, err := regexp.MatchString(pattern, instance); err != nil {
		return "", err
	} else {
		if isInstance {
			return instance, nil
		} else {
			return "", fmt.Errorf("instance[%s] format error", instance)
		}
	}
}

// GetIpPortByIns TODO
func GetIpPortByIns(ins string) (ip string, port int, err error) {
	if strings.Contains(ins, "#") {
		ins, err = CheckInstance(ins)
		if err != nil {
			return "", 0, err
		}
		// ip格式错误
		ip, err = CheckIp(strings.Split(ins, "#")[0])
		if err != nil {
			return "", 0, err
		}
		// 端口格式错误
		port, err = strconv.Atoi(strings.Split(ins, "#")[1])
		if err != nil {
			return "", 0, err
		}
	} else {
		// 必须带端口
		return "", 0, fmt.Errorf("ins[%s] format not like ip#port", ins)
	}
	return
}

// TransZeroStrings TODO
func TransZeroStrings(s []string) []string {
	if s == nil {
		return []string{}
	}
	return s
}

// TransZeroString TODO
func TransZeroString(s string) string {
	if s == "" {
		return "0"
	}
	return s
}
