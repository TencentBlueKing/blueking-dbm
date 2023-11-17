package pulsar

import (
	"encoding/json"
	"fmt"
	"io/ioutil"
	"os"
	"os/user"
	"strconv"
	"strings"
	"time"

	"dbm-services/bigdata/db-tools/dbactuator/pkg/components"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/rollback"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util/osutil"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util/pulsarutil"
	"dbm-services/common/go-pubpkg/logger"
)

// InstallPulsarComp TODO
type InstallPulsarComp struct {
	GeneralParam *components.GeneralParam
	Params       *InstallPulsarParams
	PulsarConfig
	RollBackContext rollback.RollBackObjects
}

// InstallPulsarParams TODO
type InstallPulsarParams struct {
	ZkHost               string          `json:"zk_host"`                             // zk列表，逗号分隔，域名/IP
	Domain               string          `json:"domain"`                              // 域名
	ClusterName          string          `json:"cluster_name"`                        // 集群名
	ZkID                 int             `json:"zk_id" `                              // zookeeper的id
	ZkConfigs            json.RawMessage `json:"zk_configs"`                          // 从dbconfig获取的zookeeper的配置信息
	BkConfigs            json.RawMessage `json:"bk_configs"`                          // 从dbconfig获取的bookkeeper的配置信息
	BrokerConfigs        json.RawMessage `json:"broker_configs"`                      // 从dbconfig获取的broker的配置信息
	PulsarVersion        string          `json:"pulsar_version"  validate:"required"` // 版本号eg: 2.10.1
	Host                 string          `json:"host" validate:"required,ip" `        // 本机IP
	Partitions           int             `json:"partitions"`                          // 默认partition数量
	RetentionTime        int             `json:"retention_time"`                      // 默认retention时间
	EnsembleSize         int             `json:"ensemble_size"`                       // 默认ensemble大小
	WriteQuorum          int             `json:"write_quorum"`                        // 默认写入quorum
	AckQuorum            int             `json:"ack_quorum"`                          // 默认确认quorum
	Token                string          `json:"token"`                               // zk生成的token
	Role                 string          `json:"role"`                                // pulsar角色，枚举zookeeper、bookkeeper、broker
	BrokerWebServicePort int             `json:"broker_web_service_port"`             // broker http服务端口
	Username             string          `json:"username"`                            // 用户名
	Password             string          `json:"password"`                            // 密码
	HostMap              json.RawMessage `json:"host_map"`                            // 写入/etc/hosts的映射
	NginxSubPath         string          `json:"nginx_sub_path"`                      // 替换ui中反向代理的路径
}

// InitDirs TODO
type InitDirs = []string

// Port TODO
type Port = int

// PulsarConfig ig 目录定义等
type PulsarConfig struct {
	InstallDir   string `json:"install_dir"`   // /data
	PulsarenvDir string `json:"pulsarenv_dir"` //  /data/pulsarenv
	PkgDir       string `json:"pkg_idr"`       // /data/install/
	PulsarDir    string
}

// GenerateTokenResult TODO
type GenerateTokenResult struct {
	Token string `json:"token"`
}

// InitDefaultParam TODO
func (i *InstallPulsarComp) InitDefaultParam() (err error) {
	logger.Info("start InitDefaultParam")
	// var mountpoint string
	i.InstallDir = cst.DefaultInstallDir
	i.PulsarenvDir = cst.DefaultPulsarEnvDir
	i.PkgDir = cst.DefaultPkgDir

	return nil
}

// InitPulsarDirs TODO
/*
创建实例相关的数据，日志目录以及修改权限
*/
func (i *InstallPulsarComp) InitPulsarDirs() error {
	execUser := cst.DefaultExecUser
	logger.Info("检查用户[%s]是否存在", execUser)
	if _, err := user.Lookup(execUser); err != nil {
		logger.Info("用户[%s]不存在，开始创建", execUser)
		if output, err := osutil.ExecShellCommand(false, fmt.Sprintf("useradd %s -g root -s /bin/bash -d /home/mysql",
			execUser)); err != nil {
			logger.Error("创建系统用户[%s]失败,%s, %v", execUser, output, err.Error())
			return err
		}
		logger.Info("用户[%s]创建成功", execUser)
	} else {
		logger.Info("用户[%s]存在, 跳过创建", execUser)
	}

	// mkdir
	extraCmd := fmt.Sprintf("mkdir -p %s ;mkdir -p %s ; mkdir -p %s ; chown -R mysql %s",
		cst.DefaultInstallDir, cst.DefaultPulsarEnvDir, cst.DefaultPulsarLogDir, "/data*/pulsar*")
	if _, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("初始化实例目录失败:%s", err.Error())
		return err
	}

	// mkdir /data*/pulsardata
	dataDir, _ := pulsarutil.GetAllDataDir()
	for _, dir := range dataDir {
		extraCmd = fmt.Sprintf("mkdir -p /%s/pulsardata", dir)
		if _, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
			logger.Error("创建目录/%s/pulsardata失败: %s", dir, err.Error())
			return err
		}
	}

	// chown
	extraCmd = fmt.Sprintf("chown -R mysql %s", "/data*/pulsar*")
	if _, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("修改owner失败:%s", err.Error())
		return err
	}

	logger.Info("写入/etc/profile")
	scripts := []byte(`cat << 'EOF' > /data/pulsarenv/pulsarprofile
ulimit -n 500000
export JAVA_HOME=/data/pulsarenv/java/jdk
export JRE=$JAVA_HOME/jre
export PATH=$JAVA_HOME/bin:$JRE_HOME/bin:$PATH
export CLASSPATH=".:$JAVA_HOME/lib:$JRE/lib:$CLASSPATH"
export LC_ALL=en_US
EOF

chown mysql  /data/pulsarenv/pulsarprofile

sed -i '/pulsarprofile/d' /etc/profile
echo "source /data/pulsarenv/pulsarprofile" >>/etc/profile`)

	scriptFile := fmt.Sprintf("%s/init.sh", cst.DefaultPulsarEnvDir)
	if err := ioutil.WriteFile(scriptFile, scripts, 0644); err != nil {
		logger.Error("write %s failed, %v", scriptFile, err)
	}

	extraCmd = fmt.Sprintf("bash %s", scriptFile)
	if _, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("修改系统参数失败:%s", err.Error())
		return err
	}
	return nil
}

// InstallZookeeper TODO
/**
 * @description: 安装zookeeper
 * @return {*}
 */
func (i *InstallPulsarComp) InstallZookeeper() (err error) {
	var (
		// version   string   = i.Params.PulsarVersion
		zkHost = strings.Split(i.Params.ZkHost, ",")
		host   = i.Params.Host
		// zkBaseDir string   = fmt.Sprintf("%s/apache-pulsar-%s", cst.DefaultPulsarEnvDir, version)
	)
	logger.Info("部署zookeeper开始...")

	/*
		extraCmd := fmt.Sprintf("ln -s %s %s ", zkBaseDir, cst.DefaultPulsarZkDir)
		if output, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
			logger.Error("link failed, %s, %s", output, err.Error())
			return err
		}
	*/

	// 创建数据目录
	pulsarlogDir := cst.DefaultPulsarLogDir
	pulsardataDir := cst.DefaultPulsarDataDir
	extraCmd := fmt.Sprintf(`mkdir -p %s ;
		chown -R mysql  %s ;
		mkdir -p %s ;
		chown -R mysql %s`, pulsarlogDir, pulsarlogDir, pulsardataDir, pulsardataDir)
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("初始化实例目录失败:%s", err.Error())
		return err
	}

	extraCmd = fmt.Sprintf("echo %d > %s/myid", i.Params.ZkID, cst.DefaultPulsarDataDir)
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("写入myid失败:%s", err.Error())
		return err
	}

	logger.Info("zookeeper.cfg")
	// 生成zookeeper.conf
	zkCfg, err := i.GenConfig(i.Params.ZkConfigs)
	if err != nil {
		logger.Error("解析dbconfig失败: %s\n%v", err.Error(), i.Params.ZkConfigs)
		return err
	}

	// 替换zookeeper.conf中的变量
	zkCfg = strings.ReplaceAll(zkCfg, "{{data_dir}}", cst.DefaultPulsarDataDir)
	zkCfg = strings.ReplaceAll(zkCfg, "{{data_log_dir}}", cst.DefaultPulsarLogDir)
	zkCfg = strings.ReplaceAll(zkCfg, "{{zk_host_list[0]}}", zkHost[0])
	zkCfg = strings.ReplaceAll(zkCfg, "{{zk_host_list[1]}}", zkHost[1])
	zkCfg = strings.ReplaceAll(zkCfg, "{{zk_host_list[2]}}", zkHost[2])
	// 监听本机IP
	zkCfg = strings.ReplaceAll(zkCfg, "{{client_port_address}}", host)

	logger.Info("zookeeper.conf:\n%s", zkCfg)

	if err = ioutil.WriteFile(cst.DefaultPulsarZkConf, []byte(zkCfg), 0644); err != nil {
		logger.Error("write %s failed, %v", cst.DefaultPulsarZkConf, err)
		return err
	}

	logger.Info("生成zookeeper.ini文件")
	zkini := pulsarutil.GenZookeeperIni()
	zkiniFile := fmt.Sprintf("%s/zookeeper.ini", cst.DefaultPulsarSupervisorConfDir)
	if err = ioutil.WriteFile(zkiniFile, zkini, 0644); err != nil {
		logger.Error("write %s failed, %v", zkiniFile, err)
	}

	if err = pulsarutil.SupervisorctlUpdate(); err != nil {
		logger.Error("supervisor update failed %v", err)
		return err
	}

	// sleep 30s for waiting zk up
	time.Sleep(30 * time.Second)
	logger.Info("部署zookeeper结束...")
	return nil
}

// InitCluster  TODO
/**
 * @description: 初始化集群信息，并创建密钥和token
 * @return {*}
 */
func (i *InstallPulsarComp) InitCluster() error {
	logger.Info("初始化集群信息开始...")
	extraCmd := fmt.Sprintf("%s/bin/pulsar initialize-cluster-metadata "+
		"--cluster %s "+
		"--zookeeper %s "+
		"--configuration-store %s "+
		"--web-service-url http://%s:8080 "+
		"--web-service-url-tls https://%s:8443 "+
		"--broker-service-url pulsar://%s:6650 "+
		"--broker-service-url-tls pulsar+ssl://%s:6651",
		cst.DefaultPulsarZkDir, i.Params.ClusterName,
		i.Params.ZkHost, i.Params.ZkHost,
		i.Params.Domain, i.Params.Domain, i.Params.Domain, i.Params.Domain)
	if output, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("cluster init failed, %s, %s", output, err.Error())
		return err
	}

	logger.Info("生成secret")
	extraCmd = fmt.Sprintf("%s/bin/pulsar tokens create-secret-key --output %s/my-secret.key", cst.DefaultPulsarZkDir,
		cst.DefaultPulsarZkDir)
	if output, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("secret generation failed, %s, %s", output, err.Error())
		return err
	}
	logger.Info("生成token")
	extraCmd = fmt.Sprintf(
		"%s/bin/pulsar tokens create --secret-key file:///%s/my-secret.key --subject super-user > %s/token.txt",
		cst.DefaultPulsarZkDir, cst.DefaultPulsarZkDir, cst.DefaultPulsarZkDir)
	if output, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("token generation failed, %s, %s", output, err.Error())
		return err
	}
	extraCmd = fmt.Sprintf("cat %s/token.txt | xargs echo -n", cst.DefaultPulsarZkDir)
	output, err := osutil.ExecShellCommand(false, extraCmd)
	if err != nil {
		logger.Error("get token failed, %s, %s", output, err.Error())
		return err
	}
	resultStruct := GenerateTokenResult{
		Token: output,
	}
	jsonBytes, err := json.Marshal(resultStruct)
	if err != nil {
		logger.Error("transfer resultStruct to json failed", err.Error())
		return err
	}
	fmt.Printf("<ctx>%s</ctx>", string(jsonBytes))
	logger.Info("初始化集群信息结束...")
	return nil
}

// InstallBookkeeper TODO
/**
 * @description: 安装bookkeeper
 * @return {*}
 */
func (i *InstallPulsarComp) InstallBookkeeper() error {

	logger.Info("部署Pulsar Bookkeeper开始...")
	var (
		zkHost = strings.Split(i.Params.ZkHost, ",")
	)

	dataDir, _ := pulsarutil.GetAllDataDir()
	for _, dir := range dataDir {
		extraCmd := fmt.Sprintf("mkdir -p /%s/pulsardata", dir)
		if _, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
			logger.Error("创建目录/%s/pulsardata失败: %s", dir, err.Error())
			return err
		}
	}

	// 生成bookkeeper.conf
	bkCfg, err := i.GenConfig(i.Params.BkConfigs)
	if err != nil {
		logger.Error("解析dbconfig失败: %s\n%v", err.Error(), i.Params.BkConfigs)
		return err
	}

	// 替换bookkeeper.conf中的变量
	bkCfg = strings.ReplaceAll(bkCfg, "{{local_ip}}", i.Params.Host)
	bkCfg = strings.ReplaceAll(bkCfg, "{{zk_host_list[0]}}", zkHost[0])
	bkCfg = strings.ReplaceAll(bkCfg, "{{zk_host_list[1]}}", zkHost[1])
	bkCfg = strings.ReplaceAll(bkCfg, "{{zk_host_list[2]}}", zkHost[2])

	var pulsarDataDir []string
	for _, dir := range dataDir {
		pulsarDataDir = append(pulsarDataDir, dir+"/pulsardata")
	}

	bkCfg = strings.ReplaceAll(bkCfg, "{{pulsar_data_dir}}", strings.Join(pulsarDataDir, ","))

	logger.Info("bookkeerper.conf:\n%s", bkCfg)

	if err = ioutil.WriteFile(cst.DefaultPulsarBkConf, []byte(bkCfg), 0644); err != nil {
		logger.Error("write %s failed, %v", cst.DefaultPulsarBkConf, err)
		return err
	}

	// 替换heap和directMemory
	heapSize, directMemSize, err := pulsarutil.GetHeapAndDirectMemInMi()
	if err != nil {
		logger.Error("获取Heap Size和DirectMemSize失败: %s", err.Error())
		return err
	}
	extraCmd := fmt.Sprintf(
		"sed -i \"s/-Xms2g -Xmx2g -XX:MaxDirectMemorySize=2g/-Xms%s -Xmx%s -XX:MaxDirectMemorySize=%s/g\" "+
			"%s/conf/bkenv.sh", heapSize, heapSize, directMemSize, cst.DefaultPulsarBkDir)
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("替换Heap Size和DirectMemSize失败:%s, command: %s", err.Error(), extraCmd)
		return err
	}

	logger.Info("生成bookkeeper.ini文件")
	bkini := pulsarutil.GenBookkeeperIni()
	bkiniFile := fmt.Sprintf("%s/bookkeeper.ini", cst.DefaultPulsarSupervisorConfDir)
	if err = ioutil.WriteFile(bkiniFile, bkini, 0644); err != nil {
		logger.Error("write %s failed, %v", bkiniFile, err)
		return err
	}

	if err = pulsarutil.SupervisorctlUpdate(); err != nil {
		logger.Error("supervisor update failed %v", err)
		return err
	}

	// sleep 10s for waiting bk up
	time.Sleep(10 * time.Second)

	logger.Info("部署Pulsar Bookkeeper结束...")

	return nil
}

// InstallBroker TODO
/**
 * @description: 安装broker
 * @return {*}
 */
func (i *InstallPulsarComp) InstallBroker() (err error) {

	logger.Info("部署Pulsar Broker开始...")
	var (
		zkHost = strings.Split(i.Params.ZkHost, ",")
	)

	// 生成broker.conf
	brokerCfg, err := i.GenConfig(i.Params.BrokerConfigs)
	if err != nil {
		logger.Error("解析dbconfig失败: %s\n%v", err.Error(), i.Params.BrokerConfigs)
		return err
	}

	// 替换broker.conf中的变量
	secretKeyDir := fmt.Sprintf("file://%s/my-secret.key", cst.DefaultPulsarBrokerDir)
	brokerCfg = strings.ReplaceAll(brokerCfg, "{{secret_key_dir}}", secretKeyDir)
	brokerCfg = strings.ReplaceAll(brokerCfg, "{{cluster_name}}", i.Params.ClusterName)
	brokerCfg = strings.ReplaceAll(brokerCfg, "{{zk_host_list[0]}}", zkHost[0])
	brokerCfg = strings.ReplaceAll(brokerCfg, "{{zk_host_list[1]}}", zkHost[1])
	brokerCfg = strings.ReplaceAll(brokerCfg, "{{zk_host_list[2]}}", zkHost[2])
	brokerCfg = strings.ReplaceAll(brokerCfg, "{{partitions}}", strconv.Itoa(i.Params.Partitions))
	brokerCfg = strings.ReplaceAll(brokerCfg, "{{retention_time}}", strconv.Itoa(i.Params.RetentionTime))
	brokerCfg = strings.ReplaceAll(brokerCfg, "{{ensemble_size}}", strconv.Itoa(i.Params.EnsembleSize))
	brokerCfg = strings.ReplaceAll(brokerCfg, "{{write_quorum}}", strconv.Itoa(i.Params.WriteQuorum))
	brokerCfg = strings.ReplaceAll(brokerCfg, "{{ack_quorum}}", strconv.Itoa(i.Params.AckQuorum))
	brokerCfg = strings.ReplaceAll(brokerCfg, "{{local_ip}}", i.Params.Host)
	brokerCfg = strings.ReplaceAll(brokerCfg, "{{token}}", i.Params.Token)

	logger.Info("broker.conf:\n%s", brokerCfg)

	if err = ioutil.WriteFile(cst.DefaultPulsarBrokerConf, []byte(brokerCfg), 0644); err != nil {
		logger.Error("write %s failed, %v", cst.DefaultPulsarBrokerConf, err)
		return err
	}

	// 替换heap和directMemory
	heapSize, directMemSize, err := pulsarutil.GetHeapAndDirectMemInMi()
	if err != nil {
		logger.Error("获取Heap Size和DirectMemSize失败: %s", err.Error())
		return err
	}
	extraCmd := fmt.Sprintf(
		"sed -i "+
			"\"s/-Xms2g -Xmx2g -XX:MaxDirectMemorySize=2g/-Xms%s -Xmx%s -XX:MaxDirectMemorySize=%s/g\" %s/conf/pulsar_env.sh",
		heapSize, heapSize, directMemSize, cst.DefaultPulsarBrokerDir)
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("替换Heap Size和DirectMemSize失败:%s, command: %s", err.Error(), extraCmd)
		return err
	}

	logger.Info("生成broker.ini文件")
	brokerini := pulsarutil.GenBrokerIni()
	brokeriniFile := fmt.Sprintf("%s/broker.ini", cst.DefaultPulsarSupervisorConfDir)
	if err = ioutil.WriteFile(brokeriniFile, brokerini, 0644); err != nil {
		logger.Error("write %s failed, %v", brokeriniFile, err)
		return err
	}

	if err = pulsarutil.SupervisorctlUpdate(); err != nil {
		logger.Error("supervisor update failed %v", err)
		return err
	}

	// 更新client.conf
	logger.Info("开始更新client.conf")
	extraCmd = fmt.Sprintf("sed -i '/^authParams=/s/authParams=/authParams=%s/g' %s/conf/client.conf",
		i.Params.Token, cst.DefaultPulsarBrokerDir)
	if _, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("修改client.conf token失败:%s, command: %s", err.Error(), extraCmd)
		return err
	}

	logger.Info("部署Pulsar Broker结束...")

	return nil
}

// StartBroker TODO
/**
 * @description: 启动broker
 * @return {*}
 */
func (i *InstallPulsarComp) StartBroker() (err error) {
	logger.Info("生成broker.ini文件")
	brokerini := pulsarutil.GenBrokerIni()
	brokeriniFile := fmt.Sprintf("%s/broker.ini", cst.DefaultPulsarSupervisorConfDir)
	if err = ioutil.WriteFile(brokeriniFile, brokerini, 0644); err != nil {
		logger.Error("write %s failed, %v", brokeriniFile, err)
		return err
	}

	if err = pulsarutil.SupervisorctlUpdate(); err != nil {
		logger.Error("supervisor update failed %v", err)
		return err
	}

	// sleep 10s for waiting broker up
	time.Sleep(10 * time.Second)

	return nil
}

// DecompressPulsarPkg TODO
/**
 * @description:  校验、解压pulsar安装包
 * @return {*}
 */
func (i *InstallPulsarComp) DecompressPulsarPkg() error {
	if err := os.Chdir(i.PulsarenvDir); err != nil {
		return fmt.Errorf("cd to dir %s failed, err:%w", i.InstallDir, err)
	}
	// 判断 /data/pulsarenv 目录是否已经存在,如果存在则删除掉
	if util.FileExists(i.PulsarDir) {
		if _, err := osutil.ExecShellCommand(false, "rm -rf "+i.PulsarDir); err != nil {
			logger.Error("rm -rf %s error: %w", i.PulsarenvDir, err)
			return err
		}
	}
	pkgAbPath := fmt.Sprintf("%s/pulsarpack-%s.tar.gz", i.PkgDir, i.Params.PulsarVersion)
	if output, err := osutil.ExecShellCommand(false, fmt.Sprintf("tar zxf %s", pkgAbPath)); err != nil {
		logger.Error("tar zxf %s error:%s,%s", pkgAbPath, output, err.Error())
		return err
	}

	logger.Info("pulsar binary directory: %s", i.PulsarenvDir)
	if _, err := os.Stat(i.PulsarenvDir); err != nil {
		logger.Error("%s check failed, %v", i.PulsarenvDir, err)
		return err
	}
	logger.Info("decompress pulsar pkg successfully")

	if i.Params.Role == "zookeeper" {
		zkBaseDir := fmt.Sprintf("%s/apache-pulsar-%s", cst.DefaultPulsarEnvDir, i.Params.PulsarVersion)
		extraCmd := fmt.Sprintf("ln -sf %s %s ", zkBaseDir, cst.DefaultPulsarZkDir)
		if output, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
			logger.Error("link failed, %s, %s", output, err.Error())
			return err
		}
	} else if i.Params.Role == "bookkeeper" {
		bkBaseDir := fmt.Sprintf("%s/apache-pulsar-%s", cst.DefaultPulsarEnvDir, i.Params.PulsarVersion)
		extraCmd := fmt.Sprintf("ln -sf %s %s ", bkBaseDir, cst.DefaultPulsarBkDir)
		if output, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
			logger.Error("link failed, %s, %s", output, err.Error())
			return err
		}
	} else if i.Params.Role == "broker" {
		brokerBaseDir := fmt.Sprintf("%s/apache-pulsar-%s", cst.DefaultPulsarEnvDir, i.Params.PulsarVersion)
		extraCmd := fmt.Sprintf("ln -sf %s %s ", brokerBaseDir, cst.DefaultPulsarBrokerDir)
		if output, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
			logger.Error("link failed, %s, %s", output, err.Error())
			return err
		}
	}
	logger.Info("link successfully")

	return nil
}

// InstallSupervisor TODO
/**
 * @description:  安装supervisor
 * @return {*}
 */
func (i *InstallPulsarComp) InstallSupervisor() (err error) {

	if !util.FileExists(cst.DefaultPulsarSupervisorConfDir) {
		logger.Error("supervisor not exist, %v", err)
		return err
	}

	extraCmd := fmt.Sprintf("ln -sf %s %s", i.PulsarenvDir+"/"+"supervisor/conf/supervisord.conf", "/etc/supervisord.conf")
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	extraCmd = fmt.Sprintf("ln -sf %s %s", i.PulsarenvDir+"/"+"supervisor/bin/supervisorctl",
		"/usr/local/bin/supervisorctl")
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	extraCmd = fmt.Sprintf("ln -sf %s %s", i.PulsarenvDir+"/"+"python/bin/supervisord", "/usr/local/bin/supervisord")
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	extraCmd = fmt.Sprintf("chown -R mysql %s ", i.PulsarenvDir)
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	// crontab
	extraCmd = `crontab  -l -u mysql >/home/mysql/crontab.bak`
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
	}

	extraCmd = `cp /home/mysql/crontab.bak /home/mysql/crontab.tmp`
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	extraCmd = `sed -i '/check_supervisord.sh/d' /home/mysql/crontab.bak`
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	extraCmd =
		`echo '*/1 * * * *  /data/pulsarenv/supervisor/check_supervisord.sh ` +
			`>> /data/pulsarenv/supervisor/check_supervisord.err 2>&1' >>/home/mysql/crontab.bak`
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	extraCmd = `crontab -u mysql /home/mysql/crontab.bak`
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	startCmd := `su - mysql -c "/usr/local/bin/supervisord -c /data/pulsarenv/supervisor/conf/supervisord.conf"`
	logger.Info(fmt.Sprintf("execute supervisor [%s] begin", startCmd))
	pid, err := osutil.RunInBG(false, startCmd)
	logger.Info(fmt.Sprintf("execute supervisor [%s] end, pid: %d", startCmd, pid))
	if err != nil {
		return err
	}
	return nil
}

// GenConfig TODO
func (i *InstallPulsarComp) GenConfig(message json.RawMessage) (string, error) {
	cfgMap := make(map[string]interface{})
	strResult := ""
	err := json.Unmarshal(message, &cfgMap)
	if err != nil {
		logger.Error("%s cannot resolve to map", string(message))
		return strResult, err
	}
	for k, v := range cfgMap {
		strResult = fmt.Sprintf("%s\n%s=%v", strResult, k, v)
	}

	return strResult, err
}

// InstallPulsarManager TODO
func (i *InstallPulsarComp) InstallPulsarManager() (err error) {

	if !util.FileExists(cst.DefaultPulsarManagerDir) {
		logger.Error("pulsar-manager not exist, %v", err)
		return err
	}

	logger.Info("部署Pulsar Manager开始...")
	// 修改application.properties
	extraCmd := fmt.Sprintf(
		"sed -i \"s/backend.broker.pulsarAdmin.authParams=/backend.broker.pulsarAdmin.authParams=%s/g\" %s", i.Params.Token,
		cst.DefaultPulsarManagerConf)
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("修改backend.broker.pulsarAdmin.authParams失败: %s, command: %s", err.Error(), extraCmd)
		return err
	}
	// 设置默认环境
	extraCmd = fmt.Sprintf("sed -i \"s/default.environment.name=/default.environment.name=%s/g\" %s", i.Params.ClusterName,
		cst.DefaultPulsarManagerConf)
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("修改default.environment.name失败: %s, command: %s", err.Error(), extraCmd)
		return err
	}
	extraCmd = fmt.Sprintf(
		"sed -i \"s/default.environment.service_url=/default.environment.service_url=http:\\/\\/%s:%d/g\" %s",
		i.Params.Domain, i.Params.BrokerWebServicePort, cst.DefaultPulsarManagerConf)
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("修改default.environment.name失败: %s, command: %s", err.Error(), extraCmd)
		return err
	}

	// 修改ui中反向代理的子路径
	extraCmd = fmt.Sprintf("sed -i \"s#{{nginx_sub_path}}#%s#g\" `grep \"{{nginx_sub_path}}\" -rl %s`",
		i.Params.NginxSubPath, cst.DefaultPulsarManagerDir)
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("修改nginx子路径失败: %s, command: %s", err.Error(), extraCmd)
		return err
	}

	logger.Info("生成pulsar-manager.ini文件")
	pulsarManagerIni := pulsarutil.GenPulsarManagerIni()
	pulsarManagerIniFile := fmt.Sprintf("%s/pulsar-manager.ini", cst.DefaultPulsarSupervisorConfDir)
	if err = ioutil.WriteFile(pulsarManagerIniFile, pulsarManagerIni, 0644); err != nil {
		logger.Error("write %s failed, %v", pulsarManagerIniFile, err)
		return err
	}

	if err = pulsarutil.SupervisorctlUpdate(); err != nil {
		logger.Error("supervisor update failed %v", err)
		return err
	}

	logger.Info("等待60秒....")
	if _, err := osutil.ExecShellCommand(false, "sleep 60"); err != nil {
		logger.Error("等待60s失败, %s", err.Error())
		return err
	}

	logger.Info("部署Pulsar Manager结束...")

	return nil
}

// InitPulsarManager  TODO
/**
 * @description: 初始化Pulsar Manager
 * @return {*}
 */
func (i *InstallPulsarComp) InitPulsarManager() (err error) {
	logger.Info("初始化Pulsar Manager开始...")
	logger.Info("生成csrf token")
	extraCmd := "curl http://localhost:7750/pulsar-manager/csrf-token -s"
	csrfToken := ""
	output, err := osutil.ExecShellCommand(false, extraCmd)
	if err != nil {
		logger.Error("get csrf token failed, %s, %s", output, err.Error())
		return err
	}
	csrfToken = output

	logger.Info("设置pulsar manager 用户名、密码")
	extraCmd = fmt.Sprintf(
		`curl -H "X-XSRF-TOKEN: %s" -H "Cookie: XSRF-TOKEN=%s;"`+
			` -H "Content-Type: application/json" -X PUT "http://localhost:7750/pulsar-manager/users/superuser"`+
			` -s -d '{"name": "%s", "password": "%s", "description": "admin", "email": "username@test.org"}'`, csrfToken,
		csrfToken, i.Params.Username, i.Params.Password)

	if output, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("set username/password failed, %s, %s", output, err.Error())
		return err
	}

	logger.Info("初始化Pulsar Manager结束...")
	return nil
}

// AddHostsFile  TODO
/**
 * @description: 增加hosts文件配置，仅用于内部测试
 * @return {*}
 */
func (i *InstallPulsarComp) AddHostsFile() error {
	logger.Info("增加hosts文件配置开始....")
	logger.Info("原始hosts文件: ")
	extraCmd := "cat  /etc/hosts"
	output, err := osutil.ExecShellCommand(false, extraCmd)
	if err != nil {
		logger.Error("cat /etc/hosts failed, %s, %s", output, err.Error())
		return err
	}
	logger.Info("%s", output)

	logger.Info("备份hosts文件")
	extraCmd = "cp /etc/hosts /etc/hosts.backup"
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s exec failed, %s", extraCmd, err.Error())
		return err
	}

	logger.Info("清理历史测试信息")
	extraCmd = "sed -i \"/# dba test for dbm/d\" /etc/hosts"
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s exec failed, %s", extraCmd, err.Error())
		return err
	}

	logger.Info("写入host文件")
	hostMap := make(map[string]string)

	err = json.Unmarshal(i.Params.HostMap, &hostMap)
	if err != nil {
		logger.Error("%s cannot resolve to map", string(i.Params.HostMap))
		return err
	}
	strResult := ""
	for k, v := range hostMap {
		strResult = fmt.Sprintf("%s\n%s %s # dba test for dbm", strResult, k, v)
	}
	logger.Info("写入host内容: %s", strResult)
	extraCmd = fmt.Sprintf("echo \"%s\" >> /etc/hosts", strResult)
	if _, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s exec failed, %s", extraCmd, err.Error())
		return err
	}

	return nil
}

// ModifyHostsFile  TODO
/**
 * @description: 修改hosts文件配置，仅用于内部测试
 * @return {*}
 */
func (i *InstallPulsarComp) ModifyHostsFile() error {
	logger.Info("修改hosts文件配置开始....")
	logger.Info("原始hosts文件: ")
	extraCmd := "cat /etc/hosts"
	output, err := osutil.ExecShellCommand(false, extraCmd)
	if err != nil {
		logger.Error("cat /etc/hosts failed, %s, %s", output, err.Error())
		return err
	}
	logger.Info("%s", output)

	logger.Info("修改host文件")
	hostMap := make(map[string]string)

	err = json.Unmarshal(i.Params.HostMap, &hostMap)
	if err != nil {
		logger.Error("%s cannot resolve to map", string(i.Params.HostMap))
		return err
	}
	for _, v := range hostMap {
		extraCmd = fmt.Sprintf("sed -i \"/%s/d\" /etc/hosts", v)
		if _, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
			logger.Error("%s exec failed, %s", extraCmd, err.Error())
			return err
		}
	}

	strResult := ""
	for k, v := range hostMap {
		strResult = fmt.Sprintf("%s\n%s %s # dba test for dbm", strResult, k, v)
	}
	logger.Info("写入host内容: %s", strResult)
	extraCmd = fmt.Sprintf("echo \"%s\" >> /etc/hosts", strResult)
	if _, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s exec failed, %s", extraCmd, err.Error())
		return err
	}

	return nil
}
