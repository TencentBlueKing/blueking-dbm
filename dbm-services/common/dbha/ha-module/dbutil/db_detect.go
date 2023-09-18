package dbutil

import (
	"fmt"
	"time"

	"dbm-services/common/dbha/ha-module/constvar"
	"dbm-services/common/dbha/ha-module/log"
	"dbm-services/common/dbha/ha-module/types"
	"dbm-services/common/dbha/ha-module/util"

	"golang.org/x/crypto/ssh"
)

// DataBaseDetect interface
type DataBaseDetect interface {
	Detection() error
	Serialization() ([]byte, error)

	NeedReporter() bool
	GetType() types.DBType
	GetStatus() types.CheckStatus
	GetAddress() (string, int)
	GetApp() string
	GetCluster() string
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
	Cluster        string
	SshInfo        Ssh
}

// BaseDetectDBResponse detect response struct
type BaseDetectDBResponse struct {
	AgentIp string `json:"agent_ip"`
	DBIp    string `json:"db_ip"`
	DBPort  int    `json:"db_port"`
	App     string `json:"app"`
	Status  string `json:"status"`
	Cluster string `json:"cluster"`
}

// Ssh detect configure
type Ssh struct {
	Port    int
	User    string
	Pass    string
	Dest    string
	Timeout int
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

// NeedReporter decide whether need report detect result
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

// GetType return dbType
func (b *BaseDetectDB) GetType() types.DBType {
	return b.DBType
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
		AgentIp: util.LocalIp,
		DBIp:    b.Ip,
		DBPort:  b.Port,
		App:     b.App,
		Status:  string(b.Status),
		Cluster: b.Cluster,
	}
}
