package hdfs

import (
	"fmt"
	"os"
	"strings"

	"dbm-services/bigdata/db-tools/dbactuator/pkg/components"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/components/hdfs/config_tpl"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/rollback"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util/osutil"
	"dbm-services/common/go-pubpkg/logger"
)

// InstallHaproxyService TODO
type InstallHaproxyService struct {
	GeneralParam *components.GeneralParam
	Params       *InstallHaproxyParams
	InstallParams
	RollBackContext rollback.RollBackObjects
}

// InstallHaproxyParams from db_flow
type InstallHaproxyParams struct {
	Host          string `json:"host" validate:"required,ip"`
	InstallConfig `json:"install"`
	HttpPort      int               `json:"http_port" validate:"required"`
	RpcPort       int               `json:"rpc_port" validate:"required"`
	ClusterName   string            `json:"cluster_name" validate:"required"` // 集群名
	Password      string            `json:"password"`                         // haproxy密码
	HostMap       map[string]string `json:"host_map"`
	Nn1Ip         string            `json:"nn1_ip" validate:"required"` // nn1 ip, eg: ip1
	Nn2Ip         string            `json:"nn2_ip" validate:"required"` // nn2 ip, eg: ip1
}

// InstallHaProxy TODO
func (i *InstallHaproxyService) InstallHaProxy() (err error) {
	osVersion := "7"
	linuxVersion, _ := osutil.ExecShellCommand(false, "cat /etc/redhat-release | awk '{print $4}'")
	if strings.HasPrefix(linuxVersion, "6") {
		osVersion = "6"
	}

	rpmPackages := strings.Split(i.Params.InstallConfig.HaProxyRpm, ",")
	for _, value := range rpmPackages {
		if strings.Contains(value, "el"+osVersion) {
			extraCmd := fmt.Sprintf("rpm -ivh --nodeps %s/%s > /dev/null", i.InstallDir, value)
			if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
				logger.Error("%s execute failed, %v", extraCmd, err)
			}
		}
	}
	return nil
}

// RenderHaProxyConfig TODO
func (i *InstallHaproxyService) RenderHaProxyConfig() (err error) {

	// 写入健康检查脚本
	shellContent, err := config_tpl.ExternalCheckFile.ReadFile(config_tpl.ExternalCheckFileName)
	if err != nil {
		logger.Error("read external check template failed %s", err.Error())
		return err
	}
	if err = os.WriteFile("/usr/bin/"+config_tpl.ExternalCheckFileName, shellContent, 07555); err != nil {
		logger.Error("write haproxy external check failed %s", err.Error())
		return err
	}

	// 写入haproxy.cfg
	data, err := config_tpl.HaproxyCfgFile.ReadFile(config_tpl.HaproxyCfgFileName)
	if err != nil {
		logger.Error("read config template failed %s", err.Error())
		return err
	}
	if err = os.WriteFile("/etc/haproxy/haproxy.cfg", data, 07555); err != nil {
		logger.Error("write haproxy config failed %s", err.Error())
		return err
	}
	// sed 替换参数
	nn1Host := i.Params.HostMap[i.Params.Nn1Ip]
	nn2Host := i.Params.HostMap[i.Params.Nn2Ip]
	extraCmd := fmt.Sprintf(`sed -i -e "s/{{cluster_name}}/%s/g" -e "s/{{nn1_host}}/%s/g"  -e "s/{{nn2_host}}/%s/g"  %s`,
		i.Params.ClusterName,
		nn1Host, nn2Host, "/etc/haproxy/haproxy.cfg")
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}
	extraCmd = fmt.Sprintf(`sed -i -e "s/{{rpc_port}}/%d/g" -e "s/{{http_port}}/%d/" -e "s/{{password}}/%s/g" %s`,
		i.Params.RpcPort, i.Params.HttpPort, i.Params.Password, "/etc/haproxy/haproxy.cfg")
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}
	return nil

}

// StartHaProxy TODO
func (i *InstallHaproxyService) StartHaProxy() (err error) {
	return ServiceCommand("haproxy", Start)
}
