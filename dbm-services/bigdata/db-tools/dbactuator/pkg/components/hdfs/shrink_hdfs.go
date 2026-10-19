package hdfs

import (
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util/hdfsutil"
	"encoding/json"
	"fmt"
	"net"
	"strings"
	"time"

	"dbm-services/bigdata/db-tools/dbactuator/pkg/components"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/components/hdfs/util"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/rollback"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util/osutil"
	"dbm-services/common/go-pubpkg/logger"

	"github.com/pkg/errors"
)

// UpdateDfsHostParams TODO
type UpdateDfsHostParams struct {
	DataNodeHosts string `json:"data_node_hosts"  validate:"required"`
	ConfFile      string `json:"conf_file"  validate:"required"`
	Operation     string `json:"operation"  validate:"required"`
	// LegacyDnHost 为 true 时，不直接按 IP 增删，而是先去 hosts 文件里查这个 DN 实际登记的是
	// IP 还是存量 dn-<ip> 域名，再按真实的那一行增删。只在缩容打开，扩容追加 include 保持 false，
	// 新 DN 一律按 IP 登记。
	LegacyDnHost bool `json:"legacy_dn_host"`
	// HostSourceFile 为 dfs.hosts(include) 文件，是 DN 登记形式的权威来源。
	// 仅 LegacyDnHost 且 Add(追加 exclude) 时使用：exclude 里还没有该 DN，需要以 include 中
	// 的登记形式为准追加，才能和 NameNode 识别到的 DN 标识对上，退役才会生效。
	HostSourceFile string `json:"host_source_file"`
}

// UpdateDfsHostService TODO
type UpdateDfsHostService struct {
	GeneralParam *components.GeneralParam
	InstallParams
	Params *UpdateDfsHostParams

	RollBackContext rollback.RollBackObjects
}

// UpdateDfsHost TODO
func (i *UpdateDfsHostService) UpdateDfsHost() (err error) {

	for _, dnIp := range strings.Split(i.Params.DataNodeHosts, ",") {
		dnIp = strings.TrimSpace(dnIp)
		if dnIp == "" {
			continue
		}
		dnHost := i.resolveDfsHostLine(dnIp)
		switch i.Params.Operation {
		case Add:
			if dfsHostLineExists(i.Params.ConfFile, dnHost) {
				logger.Info("dfs host line %s already exists in %s, skip", dnHost, i.Params.ConfFile)
				continue
			}
			executeCmd := fmt.Sprintf("echo %s >> %s", quoteShell(dnHost), quoteShell(i.Params.ConfFile))
			if _, err = osutil.ExecShellCommand(false, executeCmd); err != nil {
				logger.Error("%s execute failed, %v", executeCmd, err)
				return err
			}
		case Remove:
			executeCmd := fmt.Sprintf("sed -i %s %s", quoteShell("/^"+sedLiteral(dnHost)+"$/d"),
				quoteShell(i.Params.ConfFile))
			if _, err = osutil.ExecShellCommand(false, executeCmd); err != nil {
				logger.Error("%s execute failed, %v", executeCmd, err)
				return err
			}
		default:
			return errors.Errorf("unsupported dfs host operation: %s", i.Params.Operation)
		}
	}
	logger.Info("update dfs hosts successfully")
	return nil
}

// resolveDfsHostLine 返回某个 DataNode IP 在 hosts 文件里对应的那一行。
// 非 legacy 直接用 IP。legacy 时按文件里的真实内容判断登记的是 IP 还是存量 dn-<ip> 域名：
//   - Add(追加 exclude) 以 HostSourceFile(即 dfs.hosts) 为准，保证与 include 的登记形式一致；
//   - Remove 以正在操作的 ConfFile 为准，删除文件里真实存在的那一行；
//   - 两种形式都查不到时兜底用 IP。
func (i *UpdateDfsHostService) resolveDfsHostLine(dnIp string) string {
	if !i.Params.LegacyDnHost {
		return dnIp
	}
	refFile := i.Params.ConfFile
	if i.Params.Operation == Add && i.Params.HostSourceFile != "" {
		refFile = i.Params.HostSourceFile
	}
	// 优先匹配 IP，其次匹配存量 dn-<ip> 域名
	for _, candidate := range []string{dnIp, legacyDnDomain(dnIp)} {
		if candidate == "" {
			continue
		}
		if dfsHostLineExists(refFile, candidate) {
			return candidate
		}
	}
	return dnIp
}

// legacyDnDomain 返回 IPv4 对应的存量 dn-<ip> 域名，非 IPv4 返回空串。
func legacyDnDomain(host string) string {
	if ip := net.ParseIP(host); ip != nil && ip.To4() != nil {
		return "dn-" + strings.ReplaceAll(ip.To4().String(), ".", "-")
	}
	return ""
}

func dfsHostLineExists(confFile string, host string) bool {
	checkCmd := fmt.Sprintf("grep -qxF -- %s %s", quoteShell(host), quoteShell(confFile))
	_, err := osutil.ExecShellCommand(false, checkCmd)
	return err == nil
}

func quoteShell(s string) string {
	return "'" + strings.ReplaceAll(s, "'", `'\''`) + "'"
}

// sedLiteral 转义 sed 基本正则和分隔符，避免 IP 中的点匹配任意字符。
func sedLiteral(s string) string {
	replacer := strings.NewReplacer(
		`\`, `\\`,
		`.`, `\.`,
		`*`, `\*`,
		`[`, `\[`,
		`]`, `\]`,
		`^`, `\^`,
		`$`, `\$`,
		`/`, `\/`,
	)
	return replacer.Replace(s)
}

const (
	// CheckDecommissionRetryTimes 检查 DataNode 退役进度的最大轮询次数。
	// 单次执行最多轮询 10 次，最多发生 9 次等待，配合 CheckDecommissionWaitTime=5min，
	// 总等待时长上限约 45 分钟（外加每轮 hdfs CLI 与 HTTP 请求耗时），控制在作业平台单次脚本执行超时（3600s）以内，
	// 避免被作业平台强杀导致真实失败原因丢失。
	// 超过上限后本 actor 返回失败，由人工在 dbm 流程上重试；本检查为只读操作，可安全重复执行。
	CheckDecommissionRetryTimes = 10
	// CheckDecommissionWaitTime 每次轮询之间的等待时间
	CheckDecommissionWaitTime = 5 * time.Minute
	// DataNodeStateDecommissioned NameNode JMX 中表示 DataNode 已退役完成的 adminState 取值
	DataNodeStateDecommissioned = "Decommissioned"
)

// CheckDecommissionParams TODO
type CheckDecommissionParams struct {
	Host          string `json:"host" validate:"required,ip"`
	DataNodeHosts string `json:"data_node_hosts"  validate:"required"`
	DataNodePort  int    `json:"data_node_port"`
	HttpPort      int    `json:"http_port"  validate:"required"`
	Version       string `json:"version"  validate:"required"`
	Password      string `json:"password"`
}

// CheckDecommissionService TODO
type CheckDecommissionService struct {
	GeneralParam *components.GeneralParam
	InstallParams
	Params          *CheckDecommissionParams
	RollBackContext rollback.RollBackObjects
}

// CheckDatanodeDecommission 循环检查 DataNode 节点退役进度，直到退役完成或超过最大重试次数。
// 每次调用 checkDatanodeDecommissionOnce 判断是否完成；
// 未完成且后面仍有重试机会时，等待 CheckDecommissionWaitTime 后继续重试，最多检查 CheckDecommissionRetryTimes 次。
func (c *CheckDecommissionService) CheckDatanodeDecommission() (err error) {
	logger.Info("start checking DataNode decommission progress, max retry %d times, interval %s",
		CheckDecommissionRetryTimes, CheckDecommissionWaitTime)

	for i := 0; i < CheckDecommissionRetryTimes; i++ {
		done, checkErr := c.checkDatanodeDecommissionOnce()
		if checkErr != nil {
			// request or parse error, return immediately without retry
			logger.Error("check DataNode decommission progress failed: %s", checkErr.Error())
			return checkErr
		}
		if done {
			logger.Info("Datanode Decommission completed")
			return nil
		}

		if i < CheckDecommissionRetryTimes-1 {
			logger.Info("Datanode is still decommissioning, check %d/%d not finished, wait %s and retry",
				i+1, CheckDecommissionRetryTimes, CheckDecommissionWaitTime)
			time.Sleep(CheckDecommissionWaitTime)
		}
	}

	return fmt.Errorf("datanode decommission still not finished after %d attempts", CheckDecommissionRetryTimes)
}

// checkDatanodeDecommissionOnce 单次检查 DataNode 节点退役进度。
// 返回值：
//   - done == true 表示 data_node_hosts 中所有节点均已退役完成（AdminState=Decommissioned 或已进入 deadNodes）；
//   - done == false && err == nil 表示仍有节点处于退役中，调用方应继续重试；
//   - err != nil 表示请求/解析异常或节点状态无法确认，重试也不会自愈，调用方应中止重试并返回错误。
func (c *CheckDecommissionService) checkDatanodeDecommissionOnce() (done bool, err error) {
	// 获取当前 Active NameNode 域名，用于直连 NN Web 接口查询 DataNode 退役进度
	visitHost, err := hdfsutil.GetActiveNNWithoutClusterName()
	if err != nil {
		logger.Error("get active NameNode host failed, %s", err.Error())
		return false, err
	}

	urlFormat := "http://root:%s@%s:%d/jmx?qry=Hadoop:service=NameNode,name=NameNodeInfo"
	responseBody, err := util.HttpGet(fmt.Sprintf(urlFormat, c.Params.Password, visitHost, c.Params.HttpPort))
	if err != nil {
		return false, err
	}
	var beans map[string][]NameNodeInfoBean
	if err = json.Unmarshal(responseBody, &beans); err != nil {
		logger.Error("transfer response to json failed, %s", err.Error())
		return false, err
	}
	// 同时覆盖两种异常：JSON 里没有 beans 字段（nil slice）与 "beans": []（长度 0 的非 nil slice）。
	// 前者可能是接口结构变更；后者可能是接口异常/主备切换瞬间——两者都不应直接访问 [0] 引发 panic。
	if len(beans["beans"]) == 0 {
		logger.Error("namenode jmx response has empty beans")
		return false, errors.New("namenode jmx response has empty beans")
	}
	nameNodeInfoBean := beans["beans"][0]
	logger.Debug("LiveNodesStr is [%s]", nameNodeInfoBean.LiveNodesStr)
	logger.Debug("DeadNodesStr is [%s]", nameNodeInfoBean.DeadNodesStr)

	var liveNodeMap DataNodeMap
	var deadNodeMap DataNodeMap
	if err = json.Unmarshal([]byte(nameNodeInfoBean.LiveNodesStr), &liveNodeMap); err != nil {
		logger.Error("transfer LiveNodesStr to json failed, %s", err.Error())
		return false, err
	}
	if err = json.Unmarshal([]byte(nameNodeInfoBean.DeadNodesStr), &deadNodeMap); err != nil {
		logger.Error("transfer DeadNodesStr to json failed, %s", err.Error())
		return false, err
	}
	dnHostArr := strings.Split(c.Params.DataNodeHosts, ",")
	logger.Info("check decommission progress of %d datanodes", len(dnHostArr))
	result := true
	for _, dnHost := range dnHostArr {
		if value, ok := findDataNode(liveNodeMap, dnHost); ok {
			if value.AdminState == DataNodeStateDecommissioned {
				logger.Info("datanode %s is in liveNodes, adminState is %s, decommission finished",
					dnHost, value.AdminState)
			} else {
				logger.Info("datanode %s is in liveNodes, adminState is %s, still decommissioning",
					dnHost, value.AdminState)
				result = false
			}
		} else if _, ok := findDataNode(deadNodeMap, dnHost); ok {
			logger.Info("datanode %s is in deadNodes, decommission finished", dnHost)
		} else {
			// 检查时节点仍在 dfs.hosts 内，NameNode 必然把它归入 liveNodes 或 deadNodes。
			// 两处都查不到说明主机标识与 NameNode 上报的不一致，此时无法确认退役进度，
			// 不能当作退役完成放行后续的剔除与数据清理步骤。
			logger.Error("datanode %s is in neither liveNodes nor deadNodes, can not confirm decommission state", dnHost)
			return false, errors.Errorf("datanode %s is in neither liveNodes nor deadNodes", dnHost)
		}
	}
	return result, nil
}

// DataNodeMap TODO
type DataNodeMap map[string]DataNodeStruct

// findDataNode matches both the current hostname parameter and the future IP parameter.
// NameNode JMX map keys and xferaddr values may include the DataNode transfer port.
func findDataNode(nodes DataNodeMap, target string) (DataNodeStruct, bool) {
	for _, candidate := range dataNodeHostCandidates(target) {
		for nodeName, node := range nodes {
			if strings.EqualFold(normalizeDataNodeHost(nodeName), candidate) ||
				strings.EqualFold(normalizeDataNodeHost(node.TransferAddr), candidate) {
				return node, true
			}
		}
	}
	return DataNodeStruct{}, false
}

// dataNodeHostCandidates returns the original node address first, followed by the
// legacy dn-<IPv4> hostname used by the current HDFS deployment protocol.
func dataNodeHostCandidates(target string) []string {
	targetHost := normalizeDataNodeHost(target)
	if targetHost == "" {
		return nil
	}
	candidates := []string{targetHost}
	if ip := net.ParseIP(targetHost); ip != nil && ip.To4() != nil {
		candidates = append(candidates, "dn-"+strings.ReplaceAll(ip.To4().String(), ".", "-"))
	}
	return candidates
}

// normalizeDataNodeHost removes an optional transfer port while preserving hostnames,
// IPv4 addresses, and bracketed or unbracketed IPv6 addresses.
func normalizeDataNodeHost(address string) string {
	address = strings.TrimSpace(address)
	if host, _, err := net.SplitHostPort(address); err == nil {
		return strings.Trim(host, "[]")
	}
	return strings.Trim(address, "[]")
}

// DataNodeStruct TODO
type DataNodeStruct struct {
	InfoAddr       string `json:"infoAddr"`
	AdminState     string `json:"adminState"`
	TransferAddr   string `json:"xferaddr"`
	Decommissioned bool   `json:"decommissioned"`
}

// NameNodeInfoBean TODO
type NameNodeInfoBean struct {
	LiveNodesStr            string `json:"LiveNodes"`
	DeadNodesStr            string `json:"DeadNodes"`
	DecommissioningNodesStr string `json:"DecomNodes"`
}

// CheckDecommissionResult TODO
type CheckDecommissionResult struct {
	Result bool        `json:"result"`
	Detail DataNodeMap `json:"detail"`
}

// RefreshNodesParams TODO
type RefreshNodesParams struct {
	Host string `json:"host" validate:"required,ip"`
}

// RefreshNodesService TODO
type RefreshNodesService struct {
	GeneralParam *components.GeneralParam
	InstallParams
	Params          *RefreshNodesParams
	RollBackContext rollback.RollBackObjects
}

// RefreshNodes TODO
func (r *RefreshNodesService) RefreshNodes() (err error) {
	execCommand := fmt.Sprintf("su - %s -c \"hdfs dfsadmin -refreshNodes\"", r.ExecuteUser)
	// 不检查是否执行成功
	if _, err := osutil.ExecShellCommand(false, execCommand); err != nil {
		logger.Error("[%s] execute failed, %v", execCommand, err)
	}
	return nil
}
