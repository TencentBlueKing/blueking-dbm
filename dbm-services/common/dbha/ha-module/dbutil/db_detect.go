package dbutil

import (
	"bytes"
	"fmt"
	"strconv"
	"strings"
	"time"

	"dbm-services/common/dbha/ha-module/constvar"
	"dbm-services/common/dbha/ha-module/log"
	"dbm-services/common/dbha/ha-module/types"

	"golang.org/x/crypto/ssh"
)

// SlaveInfo defined slave switch info
type SlaveInfo struct {
	Ip             string `json:"ip"`
	Port           int    `json:"port"`
	IsStandBy      bool   `json:"is_stand_by"`
	Status         string `json:"status"`
	BinlogFile     string `json:"binlog_file"`
	BinlogPosition uint64 `json:"binlog_position"`
}

// DumperInfo tbinlogdumper info
type DumperInfo struct {
	Ip   string `json:"ip"`
	Port int    `json:"port"`
}

// DBInstanceInfoDetail instance detail info from cmdb api
type DBInstanceInfoDetail struct {
	IP            string `json:"ip"`
	Port          int    `json:"port"`
	AdminPort     int    `json:"admin_port"`
	BKIdcCityID   int    `json:"bk_idc_city_id"`
	LogicalCityID int    `json:"logical_city_id"`
	InstanceRole  string `json:"instance_role"`
	//only TenDBCluster's spider node used
	SpiderRole       string       `json:"spider_role"`
	Status           string       `json:"status"`
	Cluster          string       `json:"cluster"`
	BKBizID          int          `json:"bk_biz_id"`
	ClusterType      string       `json:"cluster_type"`
	MachineType      string       `json:"machine_type"`
	Receiver         []SlaveInfo  `json:"receiver"`
	ProxyInstanceSet []ProxyInfo  `json:"proxyinstance_set"`
	BindEntry        BindEntry    `json:"bind_entry"`
	ClusterId        int          `json:"cluster_id"`
	BinlogDumperSet  []DumperInfo `json:"tbinlogdumpers"`
}

// DataBaseDetect interface
type DataBaseDetect interface {
	Detection() error
	// Serialization agent call this to serializa instance info, and then send to gdm
	Serialization() ([]byte, error)

	NeedReporter() bool
	GetDBType() types.DBType
	// GetDetectType agent send detect type to gm, gm use this key to find callback func
	GetDetectType() string
	GetStatus() types.CheckStatus
	GetAddress() (string, int)
	GetApp() string
	GetCluster() string
	GetClusterType() string
	GetClusterId() int
	UpdateReporterTime()
}

// BaseDetectDB db detect base struct
type BaseDetectDB struct {
	Ip             string
	Port           int
	App            string
	DBType         types.DBType
	ReporterTime   time.Time
	ReportInterval int
	Status         types.CheckStatus
	//cluster name
	Cluster string
	//cluster type name
	ClusterType string
	//cluster id
	ClusterId int
	SshInfo   Ssh
}

// BaseDetectDBResponse agent do detect and response
type BaseDetectDBResponse struct {
	DBIp        string `json:"db_ip"`
	DBPort      int    `json:"db_port"`
	DBType      string `json:"db_type"`
	App         string `json:"app"`
	Status      string `json:"status"`
	Cluster     string `json:"cluster"`
	ClusterType string `json:"cluster_type"`
	ClusterId   int    `json:"cluster_id"`
}

// Ssh detect configure
type Ssh struct {
	Port      int
	User      string
	Pass      string
	Dest      string
	Timeout   int
	MaxUptime int64
}

// DoSSH do ssh detect
func (b *BaseDetectDB) DoSSH(shellStr string) error {
	conf := &ssh.ClientConfig{
		Timeout:         time.Second * time.Duration(b.SshInfo.Timeout), // ssh 连接time out 时间一秒钟, 如果ssh验证错误 会在一秒内返回
		User:            b.SshInfo.User,
		HostKeyCallback: ssh.InsecureIgnoreHostKey(), // 这个可以， 但是不够安全
		// HostKeyCallback: hostKeyCallBackFunc(h.Host),
	}
	conf.Auth = []ssh.AuthMethod{
		ssh.KeyboardInteractive(b.ReturnSshInteractive()),
		ssh.Password(b.SshInfo.Pass),
	}
	addr := fmt.Sprintf("%s:%d", b.Ip, b.SshInfo.Port)
	sshClient, err := ssh.Dial("tcp", addr, conf)
	if err != nil {
		log.Logger.Warnf("ssh connect failed. ip:%s, port:%d, err:%s", b.Ip, b.Port, err.Error())
		return err
	}
	defer sshClient.Close()

	session, err := sshClient.NewSession()
	if err != nil {
		log.Logger.Warnf("ssh new session failed. ip:%s, port:%d, err:%s", b.Ip, b.Port, err.Error())
		return err
	}
	defer session.Close()

	_, err = session.CombinedOutput(shellStr)

	if err != nil {
		log.Logger.Warnf("ssh run command failed. ip:%s, port:%d, err:%s", b.Ip, b.Port, err.Error())
		return err
	}

	return nil
}

// DoExtendSSH establishes an SSH connection, executes a command, and fetches the system uptime
func (b *BaseDetectDB) DoExtendSSH(shellStr string) error {
	// 创建 SSH 配置
	conf := &ssh.ClientConfig{
		Timeout:         time.Second * time.Duration(b.SshInfo.Timeout),
		User:            b.SshInfo.User,
		HostKeyCallback: ssh.InsecureIgnoreHostKey(),
		Auth: []ssh.AuthMethod{
			ssh.KeyboardInteractive(b.ReturnSshInteractive()),
			ssh.Password(b.SshInfo.Pass),
		},
	}

	// 创建 SSH 连接
	addr := fmt.Sprintf("%s:%d", b.Ip, b.SshInfo.Port)
	sshClient, err := ssh.Dial("tcp", addr, conf)
	if err != nil {
		log.Logger.Warnf("SSH connect failed. IP: %s, Port: %d, Error: %s", b.Ip, b.SshInfo.Port, err.Error())
		return err
	}
	defer sshClient.Close()

	// 创建新的 SSH 会话以执行命令
	session, err := sshClient.NewSession()
	if err != nil {
		log.Logger.Warnf("SSH new session failed. IP: %s, Port: %d, Error: %s", b.Ip, b.SshInfo.Port, err.Error())
		return err
	}
	defer session.Close()

	// 执行命令
	if _, err := session.CombinedOutput(shellStr); err != nil {
		log.Logger.Warnf("SSH run command failed. IP: %s, Port: %d, Error: %s", b.Ip, b.SshInfo.Port, err.Error())
		return err
	}

	// 创建新的 SSH 会话以获取系统启动时间
	session, err = sshClient.NewSession()
	if err != nil {
		log.Logger.Warnf("SSH new session for uptime failed. IP: %s, Port: %d, Error: %s", b.Ip, b.SshInfo.Port, err.Error())
		return err
	}
	defer session.Close()

	// 执行获取系统启动时间的命令
	var output bytes.Buffer
	session.Stdout = &output
	if err := session.Run("cat /proc/uptime"); err != nil {
		log.Logger.Warnf("Fetch machine uptime failed: %s", err.Error())
		return err
	}

	// 解析命令输出，获取系统启动时间（以秒为单位）
	fields := strings.Fields(output.String())
	if len(fields) < 1 {
		log.Logger.Warnf("Parse machine uptime failed, output: %s", output.String())
		return fmt.Errorf("invalid uptime output: %s", output.String())
	}

	uptimeSeconds, err := strconv.ParseFloat(fields[0], 64)
	if err != nil {
		log.Logger.Warnf("Convert machine uptime failed: %s", err.Error())
		return err
	}

	uptimeSecondsInt := int64(uptimeSeconds)
	log.Logger.Warnf("Machine uptime seconds: %d", uptimeSecondsInt)
	if uptimeSecondsInt < b.SshInfo.MaxUptime {
		return fmt.Errorf("machine is running, uptime: %d less than max uptime: %d", uptimeSecondsInt, b.SshInfo.MaxUptime)
	}

	return nil
}

// DoSSHForWindows do ssh detect for window
// todo 后面需要考虑去掉cygwin的依赖
func (b *BaseDetectDB) DoSSHForWindows(shellStr string) error {
	conf := &ssh.ClientConfig{
		Timeout:         time.Second * time.Duration(b.SshInfo.Timeout), // ssh 连接time out 时间一秒钟, 如果ssh验证错误 会在一秒内返回
		User:            b.SshInfo.User,
		HostKeyCallback: ssh.InsecureIgnoreHostKey(), // 这个可以， 但是不够安全
		Config: ssh.Config{
			Ciphers: []string{"arcfour"}, // 指定加密算法，目前利用sygwin联调
		},
	}
	conf.Auth = []ssh.AuthMethod{
		ssh.KeyboardInteractive(b.ReturnSshInteractive()),
		ssh.Password(b.SshInfo.Pass),
	}
	addr := fmt.Sprintf("%s:%d", b.Ip, b.SshInfo.Port)
	sshClient, err := ssh.Dial("tcp", addr, conf)
	if err != nil {
		log.Logger.Warnf("ssh connect failed. ip:%s, port:%d, err:%s", b.Ip, b.Port, err.Error())
		return err
	}
	defer sshClient.Close()

	session, err := sshClient.NewSession()
	if err != nil {
		log.Logger.Warnf("ssh new session failed. ip:%s, port:%d, err:%s", b.Ip, b.Port, err.Error())
		return err
	}
	defer session.Close()

	_, err = session.CombinedOutput(shellStr)
	if err != nil {
		log.Logger.Warnf("ssh run command failed. ip:%s, port:%d, err:%s", b.Ip, b.Port, err.Error())
		return err
	}

	return nil
}

// NeedReporter decide whether need report detect result to HADB
func (b *BaseDetectDB) NeedReporter() bool {
	var need bool
	if b.Status == constvar.DBCheckSuccess {
		now := time.Now()
		if now.After(b.ReporterTime.Add(time.Second * time.Duration(b.ReportInterval))) {
			need = true
		} else {
			need = false
		}
		// log.Logger.Debugf("now time:%s, reporter time:%s, reporter interval:%d, need:%s",
		// 	now.String(), b.ReporterTime.String(), b.ReportInterval, need)
	} else {
		need = true
	}
	return need
}

// GetAddress return instance's ip, port
func (b *BaseDetectDB) GetAddress() (ip string, port int) {
	return b.Ip, b.Port
}

// GetDBType return dbType
func (b *BaseDetectDB) GetDBType() types.DBType {
	return b.DBType
}

// GetDetectType return detect type
// prefer to use cluster type name, but consider compatibility with currently dbType
func (b *BaseDetectDB) GetDetectType() string {
	return string(b.DBType)
}

// GetStatus return status
func (b *BaseDetectDB) GetStatus() types.CheckStatus {
	return b.Status
}

// GetApp return app info
func (b *BaseDetectDB) GetApp() string {
	return b.App
}

// GetCluster return cluster info
func (b *BaseDetectDB) GetCluster() string {
	return b.Cluster
}

// GetClusterId return cluster id
func (b *BaseDetectDB) GetClusterId() int {
	return b.ClusterId
}

// GetClusterType return cluster type
func (b *BaseDetectDB) GetClusterType() string {
	return b.ClusterType
}

// UpdateReporterTime update report info
func (b *BaseDetectDB) UpdateReporterTime() {
	b.ReporterTime = time.Now()
}

// ReturnSshInteractive return ssh interactive info
func (b *BaseDetectDB) ReturnSshInteractive() ssh.KeyboardInteractiveChallenge {
	return func(user, instruction string, questions []string, echos []bool) (answers []string, err error) {
		answers = make([]string, len(questions))
		// The second parameter is unused
		for n := range questions {
			answers[n] = b.SshInfo.Pass
		}

		return answers, nil
	}
}

// NewDBResponse init db response struct, use to unmarshal
func (b *BaseDetectDB) NewDBResponse() BaseDetectDBResponse {
	return BaseDetectDBResponse{
		DBIp:        b.Ip,
		DBPort:      b.Port,
		App:         b.App,
		Status:      string(b.Status),
		Cluster:     b.Cluster,
		DBType:      string(b.DBType),
		ClusterType: b.ClusterType,
	}
}
