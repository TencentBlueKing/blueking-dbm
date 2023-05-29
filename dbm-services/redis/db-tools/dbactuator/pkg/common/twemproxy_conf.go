package common

import (
	"fmt"
	"os"
	"strconv"
	"strings"

	"github.com/pkg/errors"
	"gopkg.in/yaml.v2"
)

const twemproxyBucketMax = 420000

type twemproxyConfServer struct {
	Addr        string
	App         string
	Weight      int
	BucketStart int
	BucketEnd   int
	RouterLine  string
	Status      int
}

// Output 生成Server配置中的行
func (s twemproxyConfServer) Output() string {
	// :1是权重，我们的架构里，权重都一样，都设置为相同的.
	return fmt.Sprintf("%s:1 %s %d-%d %d", s.Addr, s.App, s.BucketStart, s.BucketEnd, s.Status)
}

// ReFormatTwemproxyConfServer 重新格式化，
func ReFormatTwemproxyConfServer(serverLines []string) (newServerLines []string, err error) {
	bucketSum := 0
	confServers := make([]twemproxyConfServer, 0)
	if len(serverLines) == 0 {
		return nil, errors.Errorf("empty")
	}
	for _, line := range serverLines {
		server, err := newTwemproxyConfServerFromLine(line)
		if err != nil {
			return nil, errors.Errorf("bad format, line:%s", line)
		}
		if server.Status != 1 {
			return nil, errors.Errorf("bad status:%d, line:%s", server.Status, line)
		}
		confServers = append(confServers, *server)
		bucketSum += 1 + server.BucketEnd - server.BucketStart
	}
	if bucketSum != twemproxyBucketMax {
		return nil, errors.Errorf("bucket sum is Not %d", twemproxyBucketMax)
	}
	newServerLines = make([]string, 0, len(serverLines))
	for i := range confServers {
		newServerLines = append(newServerLines, confServers[i].Output())
	}
	return newServerLines, nil

}

// newTwemproxyConfServerFromLine 生成Server配置中的行
func newTwemproxyConfServerFromLine(line string) (*twemproxyConfServer, error) {
	var server twemproxyConfServer

	fs := strings.Fields(line)
	if len(fs) != 4 {
		return nil, errors.Errorf("bad line")
	}

	fs0 := strings.Split(fs[0], ":")
	if len(fs0) == 2 {
		server.Addr = fs[0]
		server.Weight = 1
	} else if len(fs0) == 3 {
		server.Addr = strings.Join(fs0[0:2], ":")
		server.Weight = 1
	}

	server.App = fs[1]
	bucket := strings.Split(fs[2], "-")
	if len(bucket) != 2 {
		return nil, errors.Errorf("bad line")
	}
	server.BucketStart, _ = strconv.Atoi(bucket[0])
	server.BucketEnd, _ = strconv.Atoi(bucket[1])
	server.Status, _ = strconv.Atoi(fs[3])

	if server.BucketStart < 0 || server.BucketEnd < 0 ||
		server.BucketStart > server.BucketEnd ||
		server.BucketEnd >= twemproxyBucketMax {
		return nil, errors.Errorf("bad line")
	}
	return &server, nil
}

// TwemproxyConf 负责处理生成Twemproxy的配置文件
type TwemproxyConf struct {
	NosqlProxy struct {
		Listen             string   `yaml:"listen"`
		Password           string   `yaml:"password"`
		RedisPassword      string   `yaml:"redis_password"`
		SlowMs             int      `yaml:"slowms"`
		Redis              bool     `yaml:"redis"`
		Distribution       string   `yaml:"distribution"`
		Hash               string   `yaml:"hash"`
		ServerFailureLimit int      `yaml:"server_failure_limit"`
		AutoEjectHosts     bool     `yaml:"auto_eject_hosts"`
		PreConnect         bool     `yaml:"preconnect"`
		ServerRetryTimeout int      `yaml:"server_retry_timeout"`
		ServerConnections  int      `yaml:"server_connections"`
		HashTag            string   `yaml:"hash_tag,omitempty"`
		Backlog            int      `yaml:"backlog"`
		Servers            []string `yaml:"servers"` //
	} `yaml:"nosqlproxy"`
}

// NewTwemproxyConf Do NewTwemproxyConf
func NewTwemproxyConf() *TwemproxyConf {
	return &TwemproxyConf{}
}

// Load do load from file
func (yc *TwemproxyConf) Load(filePath string) error {
	out, err := os.ReadFile(filePath)
	if err != nil {
		return err
	}

	err = yaml.Unmarshal(out, yc)
	return err
}

// Save do save to file
func (yc *TwemproxyConf) Save(filePath string, perm os.FileMode) error {
	out, err := yaml.Marshal(yc)
	if err != nil {
		return err
	}
	return os.WriteFile(filePath, out, perm)
}

// CheckServersValid 检查Servers 本身的合法性.
func (yc *TwemproxyConf) CheckServersValid(serverLines []string) error {
	_, err := ReFormatTwemproxyConfServer(serverLines)
	return err
}
