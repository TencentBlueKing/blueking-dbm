package remoteOperation

import (
	"dbm-services/redis/redis-dts/pkg/constvar"
	"dbm-services/redis/redis-dts/util"
	"fmt"
	"path/filepath"
	"time"

	"go.uber.org/zap"
)

// 无实际作用,仅确保实现了 RemoteOperation 接口
var _ RemoteOperation = (*IAbsClient)(nil)

// IAbsClient do remote operations by ssh.exp/scp.exp.2
type IAbsClient struct {
	RemoteUser     string // 如 test_user
	RemotePassword string // 如 test_password
	RemoteIP       string // 如 1.1.1.1
	RemotePort     int    // 如 22
	scpTool        string
	sshTool        string
	logger         *zap.Logger
}

// NewIAbsClient new
func NewIAbsClient(remoteUser, remotePasswd, remoteIP string, remotePort int, logger *zap.Logger) (cli *IAbsClient,
	err error) {
	cli = &IAbsClient{
		RemoteUser:     remoteUser,
		RemotePassword: remotePasswd,
		RemoteIP:       remoteIP,
		RemotePort:     remotePort,
		logger:         logger,
	}
	cli.scpTool, err = util.IsToolExecutableInCurrDir("scp.exp.2")
	if err != nil {
		logger.Error(err.Error())
		return
	}
	cli.sshTool, err = util.IsToolExecutableInCurrDir("ssh.exp")
	if err != nil {
		logger.Error(err.Error())
		return
	}
	return
}

// NewIAbsClientByEnvVars new client by env variables
func NewIAbsClientByEnvVars(remoteIP string, logger *zap.Logger) (cli *IAbsClient, err error) {
	var absPasswd, absUser string
	var absPort int
	absPasswd, err = constvar.GetABSPassword()
	if err != nil {
		logger.Error(err.Error())
		return
	}
	absUser = constvar.GetABSUser()
	absPort = constvar.GetABSPort()
	return NewIAbsClient(
		absUser, absPasswd,
		remoteIP, absPort, logger,
	)
}

// RemoteDownload download file from remote server
func (c *IAbsClient) RemoteDownload(srcDir, dstDir string, fileName string, bwlimitMB int64) (err error) {
	srcFile := filepath.Join(srcDir, fileName)
	if bwlimitMB == 0 {
		bwlimitMB = 400 * 1024
	}
	if fileName == "" {
		srcFile = srcDir
	}
	pullTimeout := constvar.GetABSPullTimeout()
	/*example:
	./scp.exp.2 $remoteIP $remoteUser "$remoteSPASSWD" $ABSPORT /data/dbbak/30000_backup /data/dbbak/ pull 400000 3600
	*/
	pullCmd := fmt.Sprintf(`%s %s %s %s %d %s %s pull %d %d`,
		c.scpTool, c.RemoteIP,
		c.RemoteUser, c.RemotePassword, c.RemotePort,
		srcFile, dstDir, bwlimitMB, int64(pullTimeout.Seconds()))
	logPullCmd := fmt.Sprintf(`%s %s %s 'xxxxx' %d %s %s pull %d %d`,
		c.scpTool, c.RemoteIP, c.RemoteUser, c.RemotePort,
		srcFile, dstDir, bwlimitMB, int64(pullTimeout.Seconds()))
	c.logger.Info(logPullCmd)

	// _, err = util.RunLocalCmd("bash", []string{"-c", pullCmd}, "", nil, pullTimeout, c.logger)
	_, err = util.RunLocalCmd("bash", []string{"-c", pullCmd}, "", nil, 3600*time.Second, c.logger)
	return
}

// RemoteBash TODO
func (c *IAbsClient) RemoteBash(cmd string) (ret string, err error) {
	bashCmd := fmt.Sprintf(`
export ABSIP=%s
export ABSUSER=%s
export ABSPASSWD=%s
export ABSPORT=%d
export ABSSSHTIMEOUT=3600
%s %q`, c.RemoteIP, c.RemoteUser, c.RemotePassword, c.RemotePort, c.sshTool, cmd)

	logCmd := fmt.Sprintf(`
export ABSIP=%s
export ABSUSER=%s
export ABSPASSWD=xxxxx
export ABSPORT=%d
export ABSSSHTIMEOUT=3600
%s %q`, c.RemoteIP, c.RemoteUser, c.RemotePort, c.sshTool, cmd)
	c.logger.Info(logCmd)

	ret, err = util.RunLocalCmd("bash", []string{"-c", bashCmd}, "", nil,
		3600*time.Second, c.logger)
	return
}
