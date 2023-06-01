package proxyutil

import (
	"fmt"
	"path"
	"regexp"
	"strconv"
	"strings"
	"time"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/osutil"
)

// StartProxyParam TODO
type StartProxyParam struct {
	InstallPath string // /usr/local/mysql-proxy/bin/mysql-proxy
	ProxyCnf    string // "/etc/proxy.cnf." + fmt.Sprint(startPort)
	Host        string
	Port        int
	ProxyUser   string // check connect
	ProxyPwd    string // check connect
}

// Start TODO
func (s StartProxyParam) Start() (err error) {
	scmd := fmt.Sprintf(
		"su - mysql -c \"cd %s && ./mysql-proxy --defaults-file=%s  &>/dev/null &\"",
		path.Join(s.InstallPath, "bin"), s.ProxyCnf,
	)
	logger.Info("start mysql-proxy commands: [%s]", scmd)
	if _, err = osutil.ExecShellCommand(false, scmd); err != nil {
		return err
	}
	return util.Retry(util.RetryConfig{Times: 6, DelayTime: 5 * time.Second}, func() error { return s.checkStart() })
}

// checkStart 检查mysql proxy 是否启成功
func (s StartProxyParam) checkStart() (err error) {
	shellCmd := fmt.Sprintf("ps -efwww|grep 'mysql-proxy'|grep '%s'|grep -v grep", s.ProxyCnf)
	out, err := osutil.ExecShellCommand(false, shellCmd)
	if err != nil {
		logger.Error("invoke shellCmd[%s] error:%s", shellCmd, err.Error())
		return err
	}
	if !strings.Contains(string(out), s.ProxyCnf) {
		return fmt.Errorf("proxyStartCmd:%s not contain proxyCnf:[%s]", out, s.ProxyCnf)
	}
	// Test Conn ...
	pc, err := native.NewDbWorkerNoPing(fmt.Sprintf("%s:%d", s.Host, s.Port), s.ProxyUser, s.ProxyPwd)
	if err != nil {
		return err
	}
	var ver string
	if ver, err = pc.SelectVersion(); err != nil {
		return err
	}
	logger.Info("Proxy Version %s", ver)
	return
}

// KillDownProxy  停止MySQL Proxy 实例，目前是kill的方式
//
//	@receiver port
//	@return err
func KillDownProxy(port int) (err error) {
	shellCMD := fmt.Sprintf("ps -ef | grep mysql-proxy |grep %s |grep -v grep|wc -l", util.GetProxyCnfName(port))
	output, err := osutil.ExecShellCommand(false, shellCMD)
	if err != nil {
		return err
	}
	if strings.Compare(output, "0") == 0 {
		logger.Info("没有发现proxy进程~")
		return nil
	}
	shellCMD = fmt.Sprintf(
		"ps -ef | grep mysql-proxy | grep %s |grep -v grep |awk '{print $2}'",
		util.GetProxyCnfName(port),
	)
	output, err = osutil.ExecShellCommand(false, shellCMD)
	if err != nil {
		return fmt.Errorf("execute [%s] get an error:%w.output:%s", shellCMD, err, output)
	}
	tmpPids := strings.Split(output, "\n")
	logger.Info("proxy output:%s, tmpPids:%s", output, tmpPids)
	for _, pid := range tmpPids {
		if pid != "" {
			killCMD := fmt.Sprintf("kill -9 %s", pid)
			logger.Info("kill proxy cmd %s", killCMD)
			output, err = osutil.ExecShellCommand(false, killCMD)
			if err != nil {
				return fmt.Errorf("execute [%s] get an error:%w.output:%s", killCMD, err, output)
			}
		}
	}
	return nil
}

// ProxyVersionParse  proxy version 解析
//
//	@receiver proxyVersion
//	@return uint64
func ProxyVersionParse(proxyVersion string) uint64 {
	re := regexp.MustCompile(`mysql-proxy ([\d]+).([\d]+).([\d]+).([\d]+)`)
	result := re.FindStringSubmatch(proxyVersion)
	// [mysql-proxy 0.8.2.4]
	var (
		total    uint64
		billion  string
		million  string
		thousand string
		single   string
		// 0.8.2.4  => 0 * 1000000000 + 8 * 1000000 + 2*1000 + 4
	)
	if len(result) == 0 {
		return 0
	} else if len(result) == 5 {
		billion = result[1]
		million = result[2]
		thousand = result[3]
		single = result[4]
		if billion != "" {
			b, err := strconv.ParseUint(billion, 10, 64)
			if err != nil {
				logger.Info(err.Error())
				b = 0
			}
			total += b * 1000000000
		}
		if million != "" {
			b, err := strconv.ParseUint(million, 10, 64)
			if err != nil {
				logger.Info(err.Error())
				b = 0
			}
			total += b * 1000000
		}
		if thousand != "" {
			t, err := strconv.ParseUint(thousand, 10, 64)
			if err != nil {
				logger.Info(err.Error())
				t = 0
			}
			total += t * 1000
		}
		if single != "" {
			s, err := strconv.ParseUint(single, 10, 64)
			if err != nil {
				logger.Info(err.Error())
				s = 0
			}
			total += s
		}
	} else {
		// impossible condition,just for safe.
		return 0
	}
	return total
}
