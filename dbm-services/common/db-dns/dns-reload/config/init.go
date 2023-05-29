package config

import (
	"bufio"
	"io"
	"log"
	"os"
	"strings"
)

// ConfigMap 读取配置文件
var ConfigMap map[string]string

// InitConfig TODO
func InitConfig(configFile string) {
	ConfigMap = make(map[string]string)
	f, err := os.Open(configFile)
	defer f.Close()
	if err != nil {
		panic(err)
	}

	r := bufio.NewReader(f)
	for {
		b, _, err := r.ReadLine()
		if err != nil {
			if err == io.EOF {
				break
			}
			log.Fatalln("read config error ")
			os.Exit(2)
		}
		s := strings.TrimSpace(strings.ReplaceAll(string(b), "\"", ""))
		index := strings.Index(s, "=")
		if index < 0 {
			continue
		}
		key := strings.TrimSpace(s[:index])
		if len(key) == 0 {
			continue
		}
		value := strings.TrimSpace(s[index+1:])
		if len(value) == 0 {
			continue
		}
		ConfigMap[key] = value
	}
}

// GetConfig TODO
func GetConfig(k string) string {
	v, _ok := ConfigMap[k]
	if !_ok {
		log.Fatalln(" unknown  parameter %s in config ", k)
		os.Exit(2)
	}

	return v
}
