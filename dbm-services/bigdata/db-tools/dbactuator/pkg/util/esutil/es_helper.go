package esutil

import (
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"os"
	"strconv"
	"strings"

	"dbm-services/common/go-pubpkg/logger"
)

// EsInsObject TODO
type EsInsObject struct {
	Host     string `json:"host"`      // es实例ip
	HTTPPort int    `json:"http_port"` // es实例http端口
	UserName string `json:"username"`  // es实例用户名
	Password string `json:"password"`  // es实例密码
}

// Node TODO
type Node struct {
	IP          string `json:"ip"`
	InstanceNum int    `json:"instance_num"`
}

// Allocation TODO
type Allocation struct {
	Node   string `json:"node"`
	IP     string `json:"ip"`
	Shards string `json:"shards"`
}

// DoExclude 排除节点
func (o EsInsObject) DoExclude(nodes []string) error {
	client := &http.Client{}
	ips := strings.Join(nodes[:], ",")
	var b strings.Builder
	b.WriteString(fmt.Sprintf(`{
        "transient": {
            "cluster.routing.allocation.exclude._ip": "%s"
        }
    }`, ips))

	req, err := http.NewRequest("PUT", fmt.Sprintf("http://%s:%d/_cluster/settings", o.Host, o.HTTPPort),
		strings.NewReader(b.String()))
	if err != nil {
		logger.Error("Exclude请求失败", err)
		return err
	}

	req.SetBasicAuth(o.UserName, o.Password)
	req.Header.Set("Content-Type", "application/json")

	resp, err := client.Do(req)
	if err != nil {
		logger.Error("Exclude请求失败", err)
		return err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		logger.Error("exclude请求响应不为200,", resp)
		return errors.New("exclude请求响应不为200")
	}

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		logger.Error("读取响应体失败", err)
		return err
	}

	logger.Info("res", string(body))

	return nil
}

// CheckEmptyOnetime 检查指定的节点是否已经没有分片，如果没有分片返回true，否则返回false
func (o EsInsObject) CheckEmptyOnetime(nodes []string) (sum int, ok bool, err error) {
	// 初始化返回值
	ok = false
	sum = 0

	// 创建HTTP客户端
	client := &http.Client{}

	// 创建HTTP请求
	req, err := http.NewRequest("GET", fmt.Sprintf("http://%s:%d/_cat/allocation?format=json", o.Host, o.HTTPPort), nil)
	if err != nil {
		logger.Error("创建请求失败", err)
		return -1, ok, err
	}

	// 设置用户名和密码
	req.SetBasicAuth(o.UserName, o.Password)

	// 发送请求
	resp, err := client.Do(req)
	if err != nil {
		logger.Error("发送请求失败", err)
		return -1, ok, err
	}
	defer resp.Body.Close()

	// 读取响应体
	body, err := io.ReadAll(resp.Body)
	if err != nil {
		logger.Error("读取响应体失败", err)
		return -1, ok, err
	}

	// 解析响应体
	var allocations []Allocation
	if err = json.Unmarshal(body, &allocations); err != nil {
		logger.Error("解析响应体失败: %s", err)
		return -1, ok, err
	}

	// 计算分片总数
	for _, ip := range nodes {
		for _, allocation := range allocations {
			if allocation.Node == "UNASSIGNED" {
				continue
			}
			if allocation.IP == ip {
				logger.Info("IP %s has %s shards\n", ip, allocation.Shards)
				shards, _ := strconv.Atoi(allocation.Shards)
				sum += shards
			}
		}
	}

	// 如果分片总数为0，表示数据迁移完成
	if sum == 0 {
		logger.Info("Shards migration finished.")
		ok = true
		err = nil
	}

	return sum, ok, err
}

// CheckNodes 检查指定的节点是否已经成功扩容
func (o EsInsObject) CheckNodes(nodes []Node) (ok bool, err error) {
	// 初始化返回值
	ok = true

	// 预期的节点总数
	totalIns := 0
	// ip列表
	ips := make([]string, 0)
	for _, n := range nodes {
		ips = append(ips, n.IP)
		totalIns += n.InstanceNum
	}
	logger.Info("扩容的机器列表 %v", ips)
	logger.Info("预期的实例数 %d", totalIns)

	// 创建HTTP客户端
	client := &http.Client{}

	// 创建HTTP请求
	req, err := http.NewRequest("GET", fmt.Sprintf("http://%s:%d/_cat/nodes", o.Host, o.HTTPPort), nil)
	if err != nil {
		logger.Error("创建请求失败", err)
		return false, err
	}

	// 设置用户名和密码
	req.SetBasicAuth(o.UserName, o.Password)

	// 发送请求
	resp, err := client.Do(req)
	if err != nil {
		logger.Error("发送请求失败", err)
		return false, err
	}
	defer resp.Body.Close()

	// 读取响应体
	body, err := io.ReadAll(resp.Body)
	if err != nil {
		logger.Error("读取响应体失败", err)
		return false, err
	}

	// 解析响应体
	catList := strings.Split(string(body), "\n")

	// ip计数器
	nodeCounters := make(map[string]int)
	// 实际扩容的节点数
	sum := 0
	for _, r := range catList {
		// 获取第一列
		ip := strings.Fields(r)[0]
		if containStr(ips, ip) {
			nodeCounters[ip]++
			sum++
		}
	}
	logger.Info("实际扩容结果: %v", nodeCounters)
	logger.Info("实际扩容的节点总数：[%d]", sum)
	if sum != totalIns {
		ok = false
		err = fmt.Errorf("map: %v", nodeCounters)
	}

	return ok, err
}

func containStr(s []string, e string) bool {
	for _, a := range s {
		if a == e {
			return true
		}
	}
	return false
}

// CheckEsHealth 检查Elasticsearch集群的健康状态
func (o EsInsObject) CheckEsHealth() (err error) {
	// 创建HTTP客户端
	client := &http.Client{}

	// 创建HTTP请求
	req, err := http.NewRequest("GET", fmt.Sprintf("http://%s:%d", o.Host, o.HTTPPort), nil)
	if err != nil {
		return fmt.Errorf("创建请求失败: %s", err)
	}

	// 设置用户名和密码
	req.SetBasicAuth(o.UserName, o.Password)

	// 发送请求
	resp, err := client.Do(req)
	if err != nil {
		return fmt.Errorf("发送请求失败: %s", err)
	}
	defer resp.Body.Close()

	// 检查响应状态码
	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("响应错误: %s", string(body))
	}

	return nil
}

// GetCredentials 获取Elasticsearch的用户名和密码
// 如果环境变量ES_USERNAME或ES_PASSWORD为空，则使用输入的参数作为返回
// 否则返回环境变量的值
func GetCredentials(defaultUsername, defaultPassword string) (username, password string) {
	// 获取环境变量ES_USERNAME
	username = os.Getenv("ES_USERNAME")
	if username == "" {
		// 如果ES_USERNAME为空，使用默认的用户名
		username = defaultUsername
	}

	// 获取环境变量ES_PASSWORD
	password = os.Getenv("ES_PASSWORD")
	if password == "" {
		// 如果ES_PASSWORD为空，使用默认的密码
		password = defaultPassword
	}

	return username, password
}
