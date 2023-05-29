package hdfs

import (
	"bytes"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/components"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/components/hdfs/config_tpl"
	util2 "dbm-services/bigdata/db-tools/dbactuator/pkg/components/hdfs/util"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/rollback"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util/esutil"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util/osutil"
	"dbm-services/common/go-pubpkg/logger"
	"fmt"
	"io/ioutil"
	"math"
	"strings"
)

// InstallHdfsService TODO
type InstallHdfsService struct {
	GeneralParam *components.GeneralParam
	Params       *InstallHdfsParams

	InstallParams
	RollBackContext rollback.RollBackObjects
}

// InstallHdfsParams from db_flow
type InstallHdfsParams struct {
	Host          string          `json:"host" validate:"required,ip"`
	HdfsSite      util2.ConfigMap `json:"hdfs-site"`
	CoreSite      util2.ConfigMap `json:"core-site"`
	ZooCfg        util2.ConfigMap `json:"zoo.cfg"`
	InstallConfig `json:"install"`

	HttpPort      int               `json:"http_port" validate:"required"`
	RpcPort       int               `json:"rpc_port" validate:"required"`
	Version       string            `json:"version"  validate:"required"`     // 版本号eg: 2.6.0-cdh-5.4.11
	ClusterName   string            `json:"cluster_name" validate:"required"` // 集群名
	HaproxyPasswd string            `json:"haproxy_passwd"`                   // haproxy密码
	HostMap       map[string]string `json:"host_map"`
	Nn1Ip         string            `json:"nn1_ip" validate:"required"` // nn1 ip, eg: ip1
	Nn2Ip         string            `json:"nn2_ip" validate:"required"` // nn2 ip, eg: ip1
	ZkIps         string            `json:"zk_ips" validate:"required"` // master ip, eg: ip1,ip2,ip3
	JnIps         string            `json:"jn_ips" validate:"required"` // master ip, eg: ip1,ip2,ip3
	DnIps         string            `json:"dn_ips" validate:"required"` // master ip, eg: ip1,ip2,ip3

}

// InstallParams HDFS安装配置 now by default
type InstallParams struct {
	InstallDir        string `json:"install_dir"`
	JdkDir            string `json:"jdk_dir"`
	PkgDir            string `json:"pkg_dir"`
	MetaDataDir       string `json:"meta_data_dir"`
	HdfsHomeDir       string `json:"hdfs_home_dir"`
	HdfsConfDir       string `json:"hdfs_conf_dir"`
	SupervisorConfDir string `json:"supervisor_conf_dir"`
	ExecuteUser       string `json:"exec_user"`
	JdkVersion        string `json:"jdk_version"`
	ZkVersion         string `json:"zk_version"`
}

// InstallConfig TODO
type InstallConfig struct {
	JdkVersion string `json:"jdkVersion"` // JDK 版本号
	HaProxyRpm string `json:"haproxy_rpm"`
}

// HaProxyConfig TODO
type HaProxyConfig struct {
	clusterName string
}

// InitDefaultInstallParam TODO
func InitDefaultInstallParam() (params InstallParams) {
	logger.Info("start InitDefaultInstallParam")

	return InstallParams{
		PkgDir:            DefaultPkgDir,
		InstallDir:        DefaultInstallDir,
		JdkDir:            DefaultJdkDir,
		MetaDataDir:       DefaultMetaDataDir,
		HdfsHomeDir:       DefaultHdfsHomeDir,
		SupervisorConfDir: DefaultSupervisorConfDir,
		ExecuteUser:       DefaultExecuteUser,
		JdkVersion:        DefaultJdkVersion,
		HdfsConfDir:       DefaultHdfsConfDir,
		ZkVersion:         DefaultZkVersion,
	}

}

// InstallSupervisor TODO
func (i *InstallHdfsService) InstallSupervisor() (err error) {

	// 默认supervisor目录已解压到安装目录下
	if !util.FileExists(DefaultSupervisorConfDir) {
		logger.Error("supervisor not exist, %v", err)
		return err

	}

	extraCmd := fmt.Sprintf("ln -sf %s %s", i.InstallDir+"/"+"supervisor/conf/supervisord.conf", "/etc/supervisord.conf")
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	extraCmd = fmt.Sprintf("ln -sf %s %s", i.InstallDir+"/"+"supervisor/bin/supervisorctl", "/usr/local/bin/supervisorctl")
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	extraCmd = fmt.Sprintf("ln -sf %s %s", i.InstallDir+"/"+"python/bin/supervisord", "/usr/local/bin/supervisord")
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	// 写入hadopo-daemon-wrapper.sh
	data, err := config_tpl.HadoopDaemonWrapper.ReadFile(config_tpl.HadoopDaemonWrapperFileName)
	if err != nil {
		logger.Error("read shell template failed %s", err.Error())
		return err
	}
	if err = ioutil.WriteFile(i.HdfsHomeDir+"/sbin/"+config_tpl.HadoopDaemonWrapperFileName, data, 07555); err != nil {
		logger.Error("write hadoop-daemon shell failed %s", err.Error())
		return err
	}

	extraCmd = fmt.Sprintf("chown -R %s %s ", i.ExecuteUser, i.InstallDir)
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	startCmd := "/usr/local/bin/supervisord -c /data/hadoopenv/supervisor/conf/supervisord.conf"
	logger.Info(fmt.Sprintf("execute supervisor [%s] begin", startCmd))
	pid, err := osutil.RunInBG(false, startCmd)
	logger.Info(fmt.Sprintf("execute supervisor [%s] end, pid: %d", startCmd, pid))
	if err != nil {
		return err
	}
	return nil
}

// InstallJournalNode TODO
func (i *InstallHdfsService) InstallJournalNode() (err error) {
	return i.SupervisorUpdateConfig(JournalNode)
}

// InstallNn1 TODO
func (i *InstallHdfsService) InstallNn1() (err error) {

	formatCommand := fmt.Sprintf("su - %s -c \"source /etc/profile ; hdfs namenode -format -force 2> /dev/null\"",
		i.ExecuteUser)
	if _, err = osutil.ExecShellCommand(false, formatCommand); err != nil {
		// 不通过指令是否返回0判断是否初始化完成
		logger.Error("%s execute failed, %v", formatCommand, err)
	}
	// 判断是否生成了快照文件
	nameDir, err := osutil.ExecShellCommand(false, "hdfs getconf -confKey dfs.namenode.name.dir | xargs echo -n")
	if err != nil {
		logger.Error("get metadata dir execute failed, %v", err)
		return err
	}
	logger.Info("richie-test: %s", nameDir)
	if strings.HasPrefix(nameDir, "file://") {
		nameDir = strings.TrimPrefix(nameDir, "file://")
	}
	logger.Info("richie-test after Trim Prefix: %s", nameDir)

	checkCmd := fmt.Sprintf("ls -ltr %s/current/ | grep fsimage", nameDir)
	if _, err = osutil.ExecShellCommand(false, checkCmd); err != nil {
		logger.Error("%s execute failed, %v", checkCmd, err)
		return err
	}

	// 默认执行成功，不捕获err，不校验(校验需要到JN部署机器上进行，若非部署在同一台比较难实现)
	initSharedEditsCommand := fmt.Sprintf(
		"su - %s -c \"source /etc/profile ; hdfs namenode -initializeSharedEdits -force 2> /dev/null\"", i.ExecuteUser)
	if _, err = osutil.ExecShellCommand(false, initSharedEditsCommand); err != nil {
		logger.Error("%s execute failed, %v", initSharedEditsCommand, err)
	}
	return i.SupervisorUpdateConfig(NameNode)
}

// InstallNn2 TODO
func (i *InstallHdfsService) InstallNn2() (err error) {

	standbyCommand := fmt.Sprintf("su - %s -c \"hdfs namenode -bootstrapStandby -force 2> /dev/null\"", i.ExecuteUser)
	if _, err = osutil.ExecShellCommand(false, standbyCommand); err != nil {
		logger.Error("%s execute failed, %v", standbyCommand, err)
	}
	// 判断是否生成了快照文件
	nameDir, err := osutil.ExecShellCommand(false, "hdfs getconf -confKey dfs.namenode.name.dir | xargs echo -n")
	if err != nil {
		logger.Error("get metadata dir execute failed, %v", err)
		return err
	}
	if strings.HasPrefix(nameDir, "file://") {
		nameDir = strings.TrimPrefix(nameDir, "file://")
	}
	checkCmd := fmt.Sprintf("ls -ltr %s/current/ | grep fsimage", nameDir)
	if _, err = osutil.ExecShellCommand(false, checkCmd); err != nil {
		logger.Error("%s execute failed, %v", checkCmd, err)
		return err
	}
	sleepCommand := fmt.Sprintf("su - %s -c \"sleep 30 \"", i.ExecuteUser)
	if _, err = osutil.ExecShellCommand(false, sleepCommand); err != nil {
		logger.Error("%s execute failed, %v", sleepCommand, err)
	}

	if err = i.SupervisorUpdateConfig(NameNode); err != nil {
		logger.Error("SupervisorUpdateConfig failed, %v", err)
		return err
	}

	formatZKCommand := fmt.Sprintf("su - %s -c \"source /etc/profile; hdfs zkfc -formatZK -force 2> /dev/null\"",
		i.ExecuteUser)
	if _, err = osutil.ExecShellCommand(false, formatZKCommand); err != nil {
		logger.Error("%s execute failed, %v", formatZKCommand, err)
	}

	return nil
}

// InstallZKFC TODO
func (i *InstallHdfsService) InstallZKFC() (err error) {
	return i.SupervisorUpdateConfig(ZKFC)
}

// InstallDataNode TODO
func (i *InstallHdfsService) InstallDataNode() (err error) {
	if _, err = osutil.ExecShellCommand(false, "rm -rf /data/hadoopdata/data"); err != nil {
		logger.Error("delete data dir failed, %v", err)
	}
	extraCmd := fmt.Sprintf(`sed -i -e "s/{{dn_host}}/%s/g" %s`, i.Params.HostMap[i.Params.Host],
		i.HdfsConfDir+"/hdfs-site.xml")
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
	}
	// 更新DN的数据目录配置及初始化
	hdfsDirs := util2.GetHdfsDataMountDir()
	hdfsDirStr := ""
	for _, hdfsDir := range hdfsDirs {
		mkdirCmd := fmt.Sprintf("mkdir -p %s/hadoopdata", hdfsDir)
		if _, err = osutil.ExecShellCommand(false, mkdirCmd); err != nil {
			logger.Error("%s execute failed, %v", mkdirCmd, err)
		}
		chownCmd := fmt.Sprintf("chown -R %s %s ", i.ExecuteUser, hdfsDir)
		if _, err = osutil.ExecShellCommand(false, chownCmd); err != nil {
			logger.Error("%s execute failed, %v", chownCmd, err)
		}
		hdfsDirStr = fmt.Sprintf("%s%s/hadoopdata/data,", hdfsDirStr, hdfsDir)
	}
	hdfsDirStr = strings.TrimSuffix(hdfsDirStr, ",")
	replaceConfCmd := fmt.Sprintf(`sed -i -e "s/file:\/\/\/data\/hadoopdata\/data/%s/g" %s`,
		strings.ReplaceAll(hdfsDirStr, "/", "\\/"),
		i.HdfsConfDir+"/hdfs-site.xml")
	if _, err = osutil.ExecShellCommand(false, replaceConfCmd); err != nil {
		logger.Error("%s execute failed, %v", replaceConfCmd, err)
	}
	return i.SupervisorUpdateConfig(DataNode)
}

// ServiceCommand TODO
func ServiceCommand(service string, command string) error {
	execCommand := fmt.Sprintf("service %s %s", service, command)
	_, err := osutil.RunInBG(false, execCommand)
	return err
}

// InstallHaProxy TODO
func (i *InstallHdfsService) InstallHaProxy() (err error) {
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
func (i *InstallHdfsService) RenderHaProxyConfig() (err error) {

	// 写入haproxy.cfg
	data, err := config_tpl.HaproxyCfgFile.ReadFile(config_tpl.HaproxyCfgFileName)
	if err != nil {
		logger.Error("read config template failed %s", err.Error())
		return err
	}
	if err = ioutil.WriteFile("/etc/haproxy/haproxy.cfg", data, 07555); err != nil {
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
	extraCmd = fmt.Sprintf(
		`sed -i -e "s/{{nn1_ip}}/%s/g" -e "s/{{nn2_ip}}/%s/g"  -e "s/{{http_port}}/%d/" -e "s/{{haproxy_passwd}}/%s/g" %s`,
		i.Params.Nn1Ip,
		i.Params.Nn2Ip, i.Params.HttpPort, i.Params.HaproxyPasswd, "/etc/haproxy/haproxy.cfg")
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}
	return nil

}

// StartHaProxy TODO
func (i *InstallHdfsService) StartHaProxy() (err error) {
	return ServiceCommand("haproxy", Start)
}

// HadoopDaemonCommand TODO
func HadoopDaemonCommand(component string, options string) (err error) {
	execCommand := fmt.Sprintf("su - hadoop -c \"hadoop-daemon.sh %s %s\"", options, component)
	if _, err = osutil.ExecShellCommand(false, execCommand); err != nil {
		logger.Error("%s execute failed, %v", execCommand, err)
		return err
	}
	return nil
}

// SupervisorUpdateConfig TODO
func (i *InstallHdfsService) SupervisorUpdateConfig(component string) (err error) {
	return SupervisorUpdateHdfsConfig(i.SupervisorConfDir, component)
}

// RenderHdfsConfig TODO
func (i *InstallHdfsService) RenderHdfsConfig() (err error) {

	logger.Info("now hdfs conf dir is %s", i.HdfsConfDir)
	// 封装hdfs-site.xml
	hdfsSiteData, _ := util2.TransMap2Xml(i.Params.HdfsSite)
	if err = ioutil.WriteFile(i.HdfsConfDir+"/"+"hdfs-site.xml", hdfsSiteData, 0644); err != nil {
		logger.Error("write config failed %s", err.Error())
		return err
	}
	// 封装core-site.xml
	coreSiteData, _ := util2.TransMap2Xml(i.Params.CoreSite)
	if err = ioutil.WriteFile(i.HdfsConfDir+"/"+"core-site.xml", coreSiteData, 0644); err != nil {
		logger.Error("write config failed %s", err.Error())
		return err
	}

	dnIps := strings.Split(i.Params.DnIps, ",")
	buf := bytes.NewBufferString("")
	for index, _ := range dnIps {
		dnHost := i.Params.HostMap[dnIps[index]]
		buf.WriteString(fmt.Sprintln(dnHost))
	}
	if err = ioutil.WriteFile(i.HdfsConfDir+"/"+"dfs.include", buf.Bytes(), 0644); err != nil {
		logger.Error("write config failed %s", err.Error())
		return err
	}

	nn1Host := i.Params.HostMap[i.Params.Nn1Ip]
	nn2Host := i.Params.HostMap[i.Params.Nn2Ip]
	extraCmd := fmt.Sprintf(`sed -i -e "s/{{cluster_name}}/%s/" -e "s/{{nn1_host}}/%s/"  -e "s/{{nn2_host}}/%s/"  %s`,
		i.Params.ClusterName,
		nn1Host, nn2Host, i.HdfsConfDir+"/*")
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}
	extraCmd = fmt.Sprintf(`sed -i -e "s/{{http_port}}/%d/" -e "s/{{rpc_port}}/%d/" %s`, i.Params.HttpPort,
		i.Params.RpcPort, i.HdfsConfDir+"/*")
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	zkArr := strings.Split(i.Params.ZkIps, ",")
	extraCmd = fmt.Sprintf(`sed -i -e "s/{{zk0_ip}}/%s/" -e "s/{{zk1_ip}}/%s/" -e "s/{{zk2_ip}}/%s/" %s`, zkArr[0],
		zkArr[1], zkArr[2], i.HdfsConfDir+"/*")
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	jnArr := strings.Split(i.Params.JnIps, ",")
	extraCmd = fmt.Sprintf(`sed -i -e "s/{{jn0_host}}/%s/" -e "s/{{jn1_host}}/%s/" -e "s/{{jn2_host}}/%s/" %s`,
		jnArr[0], jnArr[1], jnArr[2], i.HdfsConfDir+"/*")
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	// 配置jvm参数
	var instMem uint64

	if instMem, err = esutil.GetInstMem(); err != nil {
		logger.Error("获取实例内存失败, err: %w", err)
		return fmt.Errorf("获取实例内存失败, err: %w", err)
	}
	jvmNameNodeSize := int(math.Floor(0.8 * float64(instMem) / 1024))
	jvmDataNodeSize := int(math.Floor(0.6 * float64(instMem) / 1024))

	// Todo 修改DataNode 数据目录配置，mkdir
	extraCmd = fmt.Sprintf(`sed -i -e "s/{{NN_JVM_MEM}}/%s/" -e "s/{{DN_JVM_MEM}}/%s/" %s`,
		fmt.Sprintf("-Xms%dG -Xmx%dG", jvmNameNodeSize, jvmNameNodeSize),
		fmt.Sprintf("-Xms%dG -Xmx%dG", jvmDataNodeSize, jvmDataNodeSize),
		i.HdfsConfDir+"/hadoop-env.sh")
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	return nil

}

// RenderHdfsConfigWithoutParams TODO
func (i *InstallHdfsService) RenderHdfsConfigWithoutParams() (err error) {
	// 写入log4j.properties
	data, err := config_tpl.Log4jPropertiesFile.ReadFile(config_tpl.Log4jPropertiesFileName)
	if err != nil {
		logger.Error("read config template failed %s", err.Error())
		return err
	}
	if err = ioutil.WriteFile(i.HdfsConfDir+"/"+config_tpl.Log4jPropertiesFileName, data, 07555); err != nil {
		logger.Error("write tmp config failed %s", err.Error())
		return err
	}

	// 写入rack-aware.sh
	data, err = config_tpl.RackAwareFile.ReadFile(config_tpl.RackAwareFileName)
	if err != nil {
		logger.Error("read config template script failed %s", err.Error())
		return err
	}
	if err = ioutil.WriteFile(i.HdfsConfDir+"/"+config_tpl.RackAwareFileName, data, 07555); err != nil {
		logger.Error("write tmp config failed %s", err.Error())
		return err
	}

	return nil
}
