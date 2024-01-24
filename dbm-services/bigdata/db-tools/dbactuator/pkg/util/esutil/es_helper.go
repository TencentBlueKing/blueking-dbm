package esutil

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"strconv"
	"strings"
	"time"

	"dbm-services/common/go-pubpkg/logger"

	"github.com/elastic/go-elasticsearch/v7"
	"github.com/elastic/go-elasticsearch/v7/esapi"
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

// Conn TODO
func (o EsInsObject) Conn() (*elasticsearch.Client, error) {
	return elasticsearch.NewClient(
		elasticsearch.Config{
			Addresses: []string{fmt.Sprintf("http://%s:%d", o.Host, o.HTTPPort)},
			Username:  o.UserName,
			Password:  o.Password,
		})
}

// DoExclude TODO
func (o EsInsObject) DoExclude(nodes []string) error {
	esclient, err := o.Conn()

	if err != nil {
		logger.Error("es连接失败", err)
		return err
	}

	ips := strings.Join(nodes[:], ",")
	var b strings.Builder
	b.WriteString(fmt.Sprintf(`{
        "transient": {
            "cluster.routing.allocation.exclude._ip": "%s"
        }
}`, ips))

	req := esapi.ClusterPutSettingsRequest{
		Body: strings.NewReader(b.String()),
	}

	res, err := req.Do(context.Background(), esclient)
	if err != nil {
		logger.Error("Exclude请求失败", err)
		return err
	}

	if res.StatusCode != 200 {
		logger.Error("exclude请求响应不为200,", res)
		return errors.New("exclude请求响应不为200")
	}

	logger.Info("res", res)

	return nil
}

// CheckEmpty TODO
func (o EsInsObject) CheckEmpty(nodes []string) error {
	const SleepInterval = 60 * time.Second

	esclient, err := o.Conn()

	if err != nil {
		logger.Error("es连接失败", err)
		return err
	}

	for {
		req := esapi.CatAllocationRequest{
			NodeID: nodes,  // 过滤特定的的nodes
			Format: "json", // 输出格式为json
		}
		res, err := req.Do(context.Background(), esclient)
		if err != nil {
			logger.Info("cat api失败", err)
		}
		defer res.Body.Close()

		resBody := res.String()
		logger.Info("allocations", resBody)

		var allocations []Allocation
		if err := json.NewDecoder(res.Body).Decode(&allocations); err != nil {
			logger.Error("Error parsing the response body: %s", err)
		}

		sum := 0
		for _, allocation := range allocations {
			logger.Info("allocations: %v", allocation)
			if allocation.Node == "UNASSIGNED" {
				continue
			}
			shards, _ := strconv.Atoi(allocation.Shards)
			sum += shards
		}
		// sum为0表示数据搬迁完成
		if sum == 0 {
			logger.Info("shard搬迁完毕")
			break
		}

		time.Sleep(SleepInterval)
	}

	return nil
}

// CheckEmptyOnetime TODO
func (o EsInsObject) CheckEmptyOnetime(nodes []string) (sum int, ok bool, err error) {

	ok = false
	sum = 0

	esclient, err := o.Conn()
	if err != nil {
		logger.Error("es连接失败", err)
		return -1, ok, err
	}

	req := esapi.CatAllocationRequest{
		NodeID: nodes,  // 过滤特定的的nodes
		Format: "json", // 输出格式为json
	}
	res, err := req.Do(context.Background(), esclient)
	if err != nil {
		logger.Error("cat api失败", err)
		return -1, ok, err
	}

	defer res.Body.Close()

	resBody := res.String()
	logger.Info("allocations", resBody)

	var allocations []Allocation
	if err = json.NewDecoder(res.Body).Decode(&allocations); err != nil {
		logger.Error("Error parsing the response body: %s", err)
		return -1, ok, err
	}

	for _, allocation := range allocations {
		logger.Info("allocations: %v", allocation)
		if allocation.Node == "UNASSIGNED" {
			continue
		}
		shards, _ := strconv.Atoi(allocation.Shards)
		sum += shards
	}

	// sum为0表示数据搬迁完成
	if sum == 0 {
		logger.Info("Shards migration finished.")
		ok = true
		err = nil
	}

	return sum, ok, err
}

// CheckNodes TODO
func (o EsInsObject) CheckNodes(nodes []Node) (ok bool, err error) {
	ok = true
	err = nil
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

	esclient, err := o.Conn()

	if err != nil {
		logger.Error("es连接失败", err)
		return false, err
	}

	req := esapi.CatNodesRequest{}
	res, err := req.Do(context.Background(), esclient)
	if err != nil {
		logger.Info("cat api失败", err)
		return false, err
	}

	resBody := res.String()
	logger.Info("原始cat/nodes输出 %v", resBody)

	// remove http code
	catResults := strings.Replace(strings.TrimSuffix(resBody, "\n"), "[200 OK] ", "", -1)
	catList := strings.Split(catResults, "\n")

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

// CheckEsHealth TODO
func (o EsInsObject) CheckEsHealth() (err error) {
	esclient, err := o.Conn()

	if err != nil {
		return fmt.Errorf("rror creating the client: %s", err)
	}

	// 1. Get cluster info
	//
	res, err := esclient.Info()
	if err != nil {
		return fmt.Errorf("error getting response: %s", err)
	}
	// Check response status
	if res.IsError() {
		return fmt.Errorf("error: %s", res.String())
	}
	return nil
}
