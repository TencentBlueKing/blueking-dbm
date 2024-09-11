// Package elasticsearch TODO
package elasticsearch

import (
	"bytes"
	"encoding/json"
	"fmt"
	"html/template"
	"os"
	"os/user"
	"runtime"
	"strings"
	"time"

	"dbm-services/bigdata/db-tools/dbactuator/pkg/components"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/rollback"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util/esutil"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util/osutil"
	"dbm-services/common/go-pubpkg/logger"

	"github.com/ghodss/yaml"
	"github.com/hashicorp/go-version"
)

// InstallEsComp TODO
type InstallEsComp struct {
	GeneralParam *components.GeneralParam
	Params       *InstallEsParams
	ESYaml
	ESConfig
	RollBackContext rollback.RollBackObjects
}

// InstallEsParams TODO
type InstallEsParams struct {
	EsConfigs      json.RawMessage `json:"es_configs"`                      // elasticsearch.yml
	EsVersion      string          `json:"es_version"  validate:"required"` // 版本号eg: 7.10.2
	HTTPPort       int             `json:"http_port" `                      // http端口
	MasterIP       string          `json:"master_ip"`                       // master ip, eg: ip1,ip2,ip3
	MasterNodename string          `json:"master_nodename" `                // master ip, eg: ip1,ip2,ip3
	JvmMem         string          `json:"jvm_mem"`                         //  eg: 10g
	Host           string          `json:"host" validate:"required,ip" `
	HotInstances   int             `json:"hot_instances"`   // 热节点实例数
	ColdInstances  int             `json:"cold_instances" ` // 冷节点实例数
	Instances      int             `json:"instances"`
	ClusterName    string          `json:"cluster_name"` // 集群名
	Role           string          `json:"role"`         //  eg: master, hot, cold, client
	Username       string          `json:"username" `
	Password       string          `json:"password" `
	BkBizID        int             `json:"bk_biz_id"`
	DbType         string          `json:"db_type"`
	ServiceType    string          `json:"service_type"`
}

// InitDirs TODO
type InitDirs = []string

// Port TODO
type Port = int

// ESConfig 目录定义等
type ESConfig struct {
	InstallDir string `json:"install_dir"` // /data
	EsenvDir   string `json:"esenv_dir"`   //  /data/esenv
	PkgDir     string `json:"pkg_idr"`     // /data/install/
	EsDir      string
}

// ESYaml TODO
// elaticsearch.yml
type ESYaml struct {
	ClusterName                           string `yaml:"cluster.name"` // cluster.name
	NodeName                              string `yaml:"node.name"`    // node.name
	NodeAttrTag                           string `yaml:"node.attr.tag"`
	NetworkHost                           string `yaml:"network.host"`         // network.host
	NetworkPublishhost                    string `yaml:"network.publish_host"` // network.publish_host
	NodeData                              bool   `yaml:"node.data"`            //  node.data
	NodeIngest                            bool   `yaml:"node.ingest"`          // node.Ingest
	NodeMaster                            bool   `yaml:"node.master"`          //  node.master
	NodeMl                                bool   `yaml:"node.ml"`
	HTTPPort                              int    `yaml:"http.port"`            //  http.port
	PathData                              string `yaml:"path.data"`            // path.data
	PathLogs                              string `yaml:"path.logs"`            // path.logs
	DiscoverySeedHosts                    string `yaml:"discovery.seed_hosts"` // discovery.seed_hosts
	ClusterInitialMasterNodes             string `yaml:"cluster.initial_master_nodes"`
	Processors                            int    `yaml:"processors"` // rrocessors
	BootstrapMemoryLock                   bool   `yaml:"bootstrap.memory_lock"`
	BootstrapSystemCallFilter             bool   `yaml:"bootstrap.system_call_filter"`
	XpackMonitoringCollectionEnabled      bool   `yaml:"xpack.monitoring.collection.enabled"`
	ClusterRoutingAllocationSameShardHost bool   `yaml:"cluster.routing.allocation.same_shard.host"`
	DiscoveryZenPingUnicastHosts          string `yaml:"discovery.zen.ping.unicast.hosts"` // 兼容5.4
	NodeRoles                             string `yaml:"node.roles"`                       // 8.0参数
}

// RenderConfig 需要替换的配置值 Todo
type RenderConfig struct {
	ClusterName          string
	NodeName             string
	HTTPPort             int
	CharacterSetServer   string
	InnodbBufferPoolSize string
	Logdir               string
	ServerID             uint64
}

// InitDefaultParam TODO
func (i *InstallEsComp) InitDefaultParam() (err error) {
	logger.Info("start InitDefaultParam")
	// var mountpoint string

	i.InstallDir = cst.DefaultInstallDir
	i.EsenvDir = cst.DefaulEsEnv
	i.PkgDir = cst.DefaultPkgDir
	i.EsDir = cst.DefaultEsDir
	i.PathLogs = cst.DefaulEsLogDir
	i.HTTPPort = cst.DefaultHttpPort
	i.NodeIngest = cst.IsNodeIngest
	i.NodeMl = cst.IsNodeMl
	i.BootstrapMemoryLock = cst.IsBootstrapMemoryLock
	i.BootstrapSystemCallFilter = cst.IsBootstrapSystemCall
	i.XpackMonitoringCollectionEnabled = cst.IsXpackMoinitorEnabled

	return nil
}

// InitEsDirs TODO
/*
创建实例相关的数据，日志目录以及修改权限
*/
func (i *InstallEsComp) InitEsDirs() error {

	instances := i.Params.Instances
	username := i.Params.Username
	password := i.Params.Password
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
	extraCmd := fmt.Sprintf("mkdir -p %s ;mkdir -p %s ; mkdir -p %s ; mkdir -p %s ; chown -R mysql %s",
		cst.DefaultInstallDir, cst.DefaulEsEnv, cst.DefaulEsDataDir, cst.DefaulEsLogDir, "/data/es*")
	if _, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("初始化实例目录失败:%s", err.Error())
		return err
	}

	logger.Info("修改系统参数")
	memlock := []byte(`* soft memlock unlimited
* hard memlock unlimited
mysql soft memlock unlimited
mysql hard memlock unlimited`)
	limitFile := "/etc/security/limits.d/es-nolock.conf"
	if err := os.WriteFile(limitFile, memlock, 0644); err != nil {
		logger.Error("write %s failed, %v", limitFile, err)
	}

	extraCmd =
		`sed -i -e "/vm.max_map_count/d" -e "/vm.swappiness/d" /etc/sysctl.conf ;
		echo -e "vm.max_map_count=262144\nvm.swappiness=1" >> /etc/sysctl.conf ;sysctl -p`
	if _, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("修改系统参数失败", err.Error())
	}

	logger.Info("写入/etc/profile")
	scripts := []byte(fmt.Sprintf(`cat << 'EOF' > /data/esenv/esprofile
export JAVA_HOME=/data/esenv/es_1/jdk
export CLASSPATH=".:$JAVA_HOME/lib:$JRE/lib:$CLASSPATH"
export ES_HOME=/data/esenv/es_1
export ES_CONF_DIR=$ES_HOME/config
export PATH=${JAVA_HOME}/bin:${ES_HOME}/bin:${ES_HOME}/sbin:$PATH
export ES_USERNAME=%s
export ES_PASSWORD=%s
EOF
chown mysql  /data/esenv/esprofile
sed -i '/esprofile/d' /etc/profile
echo "source /data/esenv/esprofile" >>/etc/profile`, username, password))

	scriptFile := "/data/esenv/init.sh"
	if err := os.WriteFile(scriptFile, scripts, 0644); err != nil {
		logger.Info("write %s failed, %v", scriptFile, err)
	}

	extraCmd = fmt.Sprintf("bash %s", scriptFile)
	if _, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Info("修改系统参数失败:%s", err.Error())
	}
	for ins := 1; ins <= instances; ins++ {
		logDir := fmt.Sprintf("%s%d", cst.DefaulEsLogDir, ins)
		dataDir := fmt.Sprintf("%s%d", cst.DefaulEsDataDir, ins)
		extraCmd := fmt.Sprintf(`mkdir -p %s ;
		chown -R mysql  %s ;
		mkdir -p %s ;
		chown -R mysql %s`, logDir, logDir, dataDir, dataDir)
		if _, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
			logger.Error("初始化实例目录失败:%s", err.Error())
			return err
		}
	}
	return nil
}

// InstallMaster TODO
/**
 * @description: 安装master
 * @return {*}
 */
func (i *InstallEsComp) InstallMaster() (err error) {

	logger.Info("部署master开始...")
	if err := i.InstallEsBase(i.Params.Role, 1); err != nil {
		logger.Error("部署master失败. %v", err)
		return err
	}
	logger.Info("部署master结束...")

	return nil
}

// InstallClient TODO
/**
 * @description: 安装client
 * @return {*}
 */
func (i *InstallEsComp) InstallClient() (err error) {

	logger.Info("部署ES client开始...")
	if err := i.InstallEsBase(i.Params.Role, 1); err != nil {
		logger.Error("部署ES client失败. %v", err)
		return err
	}
	logger.Info("部署client结束...")

	return nil
}

// InstallHot TODO
/**
 * @description: 安装hot
 * @return {*}
 */
func (i *InstallEsComp) InstallHot() (err error) {

	logger.Info("部署ES 热节点开始...")
	if err := i.InstallEsBase(i.Params.Role, i.Params.Instances); err != nil {
		logger.Error("部署ES 热节点失败. %v", err)
		return err
	}
	logger.Info("部署热节点结束...")

	return nil
}

// InstallCold TODO
/**
 * @description: 安装cold
 * @return {*}
 */
func (i *InstallEsComp) InstallCold() (err error) {
	logger.Info("部署ES 冷节点开始...")
	if err := i.InstallEsBase(i.Params.Role, i.Params.Instances); err != nil {
		logger.Error("部署ES 冷节点失败. %v", err)
		return err
	}
	logger.Info("部署冷节点结束...")
	return nil
}

// InstallEsBase 安装ES基础方法
/**
 * @description: 安装ES基础方法
 * @return {*}
 */
func (i *InstallEsComp) InstallEsBase(role string, instances int) error {
	var (
		nodeIP         = i.Params.Host
		ver            = i.Params.EsVersion
		processors     = runtime.NumCPU() / instances
		clusterName    = i.Params.ClusterName
		masterIP       = i.Params.MasterIP
		masterNodename = i.Params.MasterNodename
		port           = i.Params.HTTPPort
		esBaseDir      = fmt.Sprintf("%s/elasticsearch-%s", cst.DefaulEsEnv, ver)
		esConfig       = i.Params.EsConfigs
	)
	isMaster, isData := esutil.GetTfByRole(role)
	roleSet := esutil.GetTfByRole8(role)
	esLink := fmt.Sprintf("%s/es", cst.DefaulEsEnv)
	extraCmd := fmt.Sprintf("ln -s %s %s ", esBaseDir, esLink)
	if output, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("link failed, %s, %s", output, err.Error())
		return err
	}
	cfgMap := make(map[string]interface{})

	if err := json.Unmarshal(esConfig, &cfgMap); err != nil {
		logger.Error("parse esconfig json failed, %s", err)
		return err
	}

	pathData, ok := cfgMap["path_data"].(string)
	if !ok && pathData == "" {
		pathData = cst.DefaulEsDataDir
	}

	pathLog, ok := cfgMap["path_log"].(string)
	if !ok && pathLog == "" {
		pathLog = cst.DefaulEsLogDir
	}

	// deal with multi-disk
	localDisks := esutil.GetPath()
	diskCount := len(localDisks)
	seed := diskCount / instances
	var esdataDir string
	for ins := 1; ins <= instances; ins++ {
		if diskCount != 0 {
			// Generate path, eg: /data1/esdata1, /data2/esdata1 ...
			tPaths := esutil.GenPath(ins, seed, localDisks)
			for k, v := range tPaths {
				// /data -> /data/esdata1
				tPaths[k] = fmt.Sprintf("%s/esdata%d", v, ins)
				// create data dir
				extraCmd = fmt.Sprintf(`mkdir -p %s; chown -R mysql %s`, tPaths[k], tPaths[k])
				logger.Info("Doing create dir [%s]", extraCmd)
				if _, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
					logger.Error("Command [%s] failed, message: [%s]", extraCmd, err)
					return err
				}
			}
			esdataDir = strings.Join(tPaths, ",")
		} else {
			esdataDir = fmt.Sprintf("%s%d", pathData, ins)
			extraCmd = fmt.Sprintf(`mkdir -p %s ;chown -R mysql  %s`, esdataDir, esdataDir)
			if _, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
				logger.Error("Command [%s] failed: %s", extraCmd, err)
				return err
			}
		}

		logger.Info("Instanc [%d] path.data:: [%s] ", esdataDir)

		// create log dir
		eslogDir := fmt.Sprintf("%s%d", pathLog, ins)
		extraCmd = fmt.Sprintf(`mkdir -p %s ;chown -R mysql  %s`, eslogDir, eslogDir)
		if _, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
			logger.Error("Create logdir failed, command [%s]", eslogDir, err)
			return err
		}

		nodeName := fmt.Sprintf("%s-%s_%d", role, nodeIP, ins)
		// cp /data/esenv/elasticsearch-$version /data/esenv/elasticsearch-$version_1
		esBaseDirIns := fmt.Sprintf("%s_%d", esBaseDir, ins)
		if output, err := osutil.ExecShellCommand(false, fmt.Sprintf("cp -a %s %s", esBaseDir, esBaseDirIns)); err != nil {
			logger.Error("copy basedir failed, %s, %s", output, err.Error())
			return err
		}

		// ln -s /data/esenv/elasticsearch-$version_1 /data/esenv/es_1
		esLink := fmt.Sprintf("%s/es_%d", cst.DefaulEsEnv, ins)
		if output, err := osutil.ExecShellCommand(false, fmt.Sprintf("ln -s %s %s ", esBaseDirIns, esLink)); err != nil {
			logger.Error("copy basedir failed, %s, %s", output, err.Error())
			return err
		}

		logger.Info("开始渲染elasticsearch.yml")
		t, err := template.New("es template").Parse(string(esConfig))
		if err != nil {
			logger.Error("Parse elasticsearch.yml template failed, [%s]", err)
			return err
		}

		y := ESYaml{
			ClusterName:                           clusterName,
			NodeName:                              nodeName,
			NodeAttrTag:                           role,
			NetworkHost:                           nodeIP,
			NetworkPublishhost:                    nodeIP,
			NodeData:                              isData,
			NodeMaster:                            isMaster,
			NodeMl:                                i.NodeMl,
			NodeIngest:                            i.NodeIngest,
			HTTPPort:                              port,
			PathData:                              esdataDir,
			PathLogs:                              eslogDir,
			DiscoverySeedHosts:                    masterIP,
			ClusterInitialMasterNodes:             masterNodename,
			Processors:                            processors,
			BootstrapMemoryLock:                   i.BootstrapMemoryLock,
			BootstrapSystemCallFilter:             i.BootstrapSystemCallFilter,
			XpackMonitoringCollectionEnabled:      i.XpackMonitoringCollectionEnabled,
			ClusterRoutingAllocationSameShardHost: true,
			DiscoveryZenPingUnicastHosts:          masterIP,
			NodeRoles:                             roleSet,
		}

		var buf bytes.Buffer
		if err = t.Execute(&buf, y); err != nil {
			logger.Error("渲染elasticsearch.yml模板失败, [%s]", err)
			return err
		}
		logger.Info(buf.String())
		// 转换成yaml
		data, err := yaml.JSONToYAML(buf.Bytes())
		if err != nil {
			logger.Error("Converting json to yaml failed, %s", err)
			return err
		}
		logger.Info("yaml: %s", string(data))

		esYamlFile := fmt.Sprintf("%s/config/elasticsearch.yml", esLink)
		esYamlFileAppend := fmt.Sprintf("%s/config/elasticsearch.yml.append", esLink)
		if err = os.WriteFile(esYamlFile, data, 0644); err != nil {
			logger.Error("write %s failed, %v", esYamlFile, err)
		}

		// cat elasticsearch.yml.append >> elasticsearch.yml
		extraCmd = fmt.Sprintf(`cat %s >> %s`, esYamlFileAppend, esYamlFile)
		logger.Info("Exec command [%s]", extraCmd)
		if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
			logger.Error("%s execute failed, %v", extraCmd, err)
			return err
		}

		// master格式: m1,m2,m3 -> [m1,m2,m3]
		masterIPA := fmt.Sprintf("[%s]", masterIP)
		masterNodenameA := fmt.Sprintf("[%s]", masterNodename)
		v1, _ := version.NewVersion(ver)
		v2, _ := version.NewVersion("7.0")
		if v1.GreaterThan(v2) {
			extraCmd = fmt.Sprintf(
				`sed -i -e '/seed_hosts/s/%s/%s/' -e '/initial_master_nodes/s/%s/%s/' %s`, masterIP, masterIPA,
				masterNodename, masterNodenameA, esYamlFile)
		} else {
			extraCmd = fmt.Sprintf(`sed -i -e '/zen.ping.unicast.hosts/s/%s/%s/' %s`, masterIP, masterIPA, esYamlFile)
		}
		logger.Info("Exec command [%s]", extraCmd)
		if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
			logger.Error("%s execute failed, %v", extraCmd, err)
			return err
		}
		// 格式化 node.roles, eg: master,ingest -> [master, igest]
		roleSetA := fmt.Sprintf("[%s]", roleSet)
		v8, _ := version.NewVersion("8.0")
		if v1.GreaterThan(v8) {
			extraCmd = fmt.Sprintf(`sed -i -e '/node.roles/s/%s/%s/' %s`, roleSet, roleSetA, esYamlFile)
			logger.Info("Exec command [%s]", extraCmd)
			if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
				logger.Error("%s execute failed, %v", extraCmd, err)
				return err
			}
		}
		// 如果节点是client, 增加 node.attr.node_type: client
		if role == cst.EsClient {
			extraCmd = fmt.Sprintf(`sed -i '/node.attr.node_type/d' %s ;
			sed -i '$a node.attr.node_type: client' %s`, esYamlFile, esYamlFile)
			logger.Info("Exec command [%s]", extraCmd)
			if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
				logger.Error("%s execute failed, %v", extraCmd, err)
				return err
			}
		}

		logger.Info("生成jvm参数")
		heapSize, err := esutil.GetInstHeapByIP(uint64(instances))
		if err != nil {
			logger.Error("生成heap失败,将采取的默认heapszie, %s", err)
		}

		// /data/esenv/es_{ins}/config/jvm.options
		heapSizeFile := fmt.Sprintf("%s/config/jvm.options", esLink)
		if err = esutil.SetHeapFile(heapSize, heapSizeFile); err != nil {
			logger.Error("Changing jvm.options failed, %s", err)
			return err
		}

		logger.Info("生成elasticsearch.ini文件")
		esini := esutil.GenEsini(uint64(ins))
		esiniFile := fmt.Sprintf("%s/elasticsearch%d.ini", cst.DefaultSupervisorConf, ins)
		if err = os.WriteFile(esiniFile, esini, 0644); err != nil {
			logger.Error("write %s failed, %v", esiniFile, err)
		}
		port++
	}

	extraCmd = fmt.Sprintf("chown -R mysql %s", cst.DefaulEsEnv)
	if _, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("exec [%s] failed, %s", extraCmd, err.Error())
		return err
	}

	if err := esutil.SupervisorctlUpdate(); err != nil {
		logger.Error("supervisort update failed %v", err)
		return err
	}

	// sleep 60s for wating es up
	time.Sleep(60 * time.Second)
	return nil
}

// DecompressEsPkg TODO
/**
 * @description:  校验、解压es安装包
 * @return {*}
 */
func (i *InstallEsComp) DecompressEsPkg() (err error) {
	version := i.Params.EsVersion

	if err = os.Chdir(i.EsenvDir); err != nil {
		return fmt.Errorf("cd to dir %s failed, err:%w", i.InstallDir, err)
	}
	// 判断 /data/esenv/es 目录是否已经存在,如果存在则删除掉
	if util.FileExists(i.EsDir) {
		if _, err = osutil.ExecShellCommand(false, "rm -rf "+i.EsDir); err != nil {
			logger.Error("rm -rf %s error: %w", i.EsenvDir, err)
			return err
		}
	}
	pkgAbPath := fmt.Sprintf("%s/espack-%s.tar.gz", i.PkgDir, version)
	if output, err := osutil.ExecShellCommand(false, fmt.Sprintf("tar zxf %s", pkgAbPath)); err != nil {
		logger.Error("tar zxf %s error:%s,%s", pkgAbPath, output, err.Error())
		return err
	}

	// Uncompress certificate file
	// copy and uncompress,cp /data/install/es_cerfiles.tar.gz /data/esenv/
	cerPkg := "es_cerfiles.tar.gz"
	extraCmd := fmt.Sprintf("cp %s/%s  %s", cst.DefaultPkgDir, cerPkg, cst.DefaulEsEnv)
	logger.Info("Exec %s", extraCmd)
	if _, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("Exec [%s] failed, msg %s", extraCmd, err)
		return err
	}

	extraCmd = fmt.Sprintf("tar zxf %s", cerPkg)
	logger.Info("Exec %s", extraCmd)
	if _, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("Exec [%s] failed, msg %s", extraCmd, err)
		return err
	}

	// copy file to elasticsearch-7.10.2/config
	extraCmd = fmt.Sprintf("cp -a es_cerfiles/* elasticsearch-%s/config/", version)
	logger.Info("Exec %s", extraCmd)
	if _, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("Exec [%s] failed, msg %s", extraCmd, err)
		return err
	}

	logger.Info("es binary directory: %s", i.EsenvDir)
	if _, err := os.Stat(i.EsenvDir); err != nil {
		logger.Error("%s check failed, %v", i.EsenvDir, err)
		return err
	}
	logger.Info("decompress es pkg successfully")
	return nil
}

// InstallSupervisor TODO
/**
 * @description:  安装supervisor
 * @return {*}
 */
func (i *InstallEsComp) InstallSupervisor() (err error) {
	// Todo: check supervisor exist
	// supervisor

	if !util.FileExists(cst.DefaultSupervisorConf) {
		logger.Error("supervisor not exist, %v", err)
		return err
	}

	extraCmd := fmt.Sprintf("ln -sf %s %s", i.EsenvDir+"/"+"supervisor/conf/supervisord.conf", "/etc/supervisord.conf")
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	extraCmd = fmt.Sprintf("ln -sf %s %s", i.EsenvDir+"/"+"supervisor/bin/supervisorctl", "/usr/local/bin/supervisorctl")
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	extraCmd = fmt.Sprintf("ln -sf %s %s", i.EsenvDir+"/"+"python/bin/supervisord", "/usr/local/bin/supervisord")
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	extraCmd = fmt.Sprintf("chown -R mysql %s ", i.EsenvDir)
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

	extraCmd = "echo '*/1 * * * *  /data/esenv/supervisor/check_supervisord.sh " +
		">>/data/esenv/supervisor/check_supervisord.err 2>&1' >>/home/mysql/crontab.bak"
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	extraCmd = `crontab -u mysql /home/mysql/crontab.bak`
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	startCmd := `su - mysql -c "/usr/local/bin/supervisord -c /data/esenv/supervisor/conf/supervisord.conf"`
	logger.Info(fmt.Sprintf("execute supervisor [%s] begin", startCmd))
	pid, err := osutil.RunInBG(false, startCmd)
	logger.Info(fmt.Sprintf("execute supervisor [%s] end, pid: %d", startCmd, pid))
	if err != nil {
		return err
	}
	return nil
}

// InstallKibana TODO
/**
 *  @description: 安装kibana
 *  @return
 */
func (i *InstallEsComp) InstallKibana() error {
	// check package
	k := esutil.KibanaParam{
		BkBizID:     i.Params.BkBizID,
		DbType:      i.Params.DbType,
		ClusterName: i.Params.ClusterName,
		ServiceType: i.Params.ServiceType,
		Host:        i.Params.Host,
		HTTPPort:    i.Params.HTTPPort,
		Username:    i.Params.Username,
		Password:    i.Params.Password,
		Version:     i.Params.EsVersion,
	}
	kibanaPkgDir := fmt.Sprintf("%s/kibana-%s-linux-x86_64", cst.DefaulEsEnv, i.Params.EsVersion)
	kibanaLink := fmt.Sprintf("%s/kibana", cst.DefaulEsEnv)
	extraCmd := fmt.Sprintf("ln -sf %s %s", kibanaPkgDir, kibanaLink)
	if _, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	// 生成kibana.yml

	yamldata := k.GenKibanaYaml()
	// 生成elasticsearch.yml
	kyaml := "/data/esenv/kibana/config/kibana.yml"
	if err := os.WriteFile(kyaml, yamldata, 0644); err != nil {
		logger.Error("write %s failed, %v", kyaml, err)
	}

	// kibana.ini
	data := esutil.GenKibanaini()
	kini := "/data/esenv/supervisor/conf/kibana.ini"
	if err := os.WriteFile(kini, data, 0644); err != nil {
		logger.Error("write %s failed, %v", kini, err)
	}
	if err := esutil.SupervisorctlUpdate(); err != nil {
		return err
	}
	return nil
}

// InitGrant TODO
/**
 *  @description: 权限初始化
 *  @return
 */
func (i *InstallEsComp) InitGrant() (err error) {
	username := i.Params.Username
	password := i.Params.Password
	host := i.Params.Host
	version := i.Params.EsVersion

	scripts := esutil.GenBoostScript()

	scriptFile := "/data/esenv/boost.sh"
	if err = os.WriteFile(scriptFile, scripts, 0644); err != nil {
		logger.Error("write %s failed, %v", scriptFile, err)
		return err
	}

	extraCmd := fmt.Sprintf("bash %s %s %s %s %s", scriptFile, username, password, host, version)
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	return nil
}

// InstallTelegraf TODO
/**
 *  @description: 部署telegraf
 *  @return
 */
func (i *InstallEsComp) InstallTelegraf() (err error) {
	clusterName := i.Params.ClusterName
	host := i.Params.Host
	esHost := fmt.Sprintf("%s:%d", host, i.Params.HTTPPort)
	teConfFile := "/data/esenv/telegraf/etc/telegraf/telegraf.conf"
	extraCmd := fmt.Sprintf(`sed -i -e "s/CLUSTER_NAME/%s/" -e "s/HOSTNAME/%s/"  -e "s/ESHOST/%s/"  %s`, clusterName, host,
		esHost, teConfFile)
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	extraCmd = "cp -a  /data/esenv/telegraf/telegraf.ini /data/esenv/supervisor/conf/"
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	_ = esutil.SupervisorctlUpdate()

	return nil
}

// InstallNodeExporter TODO
/**
 *  @description: 部署node exporter
 *  @return
 */
func (i *InstallEsComp) InstallNodeExporter() (err error) {
	data := []byte(`[program:node_exporter]
command=/data/esenv/node_exporter/node_exporter --web.listen-address=":9100" ; 
numprocs=1 ; number of processes copies to start (def 1)
autostart=true ; start at supervisord start (default: true)
startsecs=3 ; # of secs prog must stay up to be running (def. 1)
startretries=99 ; max # of serial start failures when starting (default 3)
autorestart=true ; when to restart if exited after running (def: unexpected)
exitcodes=0 ; 'expected' exit codes used with autorestart (default 0,2)
user=mysql ;
redirect_stderr=true ; redirect proc stderr to stdout (default false)
stdout_logfile=/data/esenv/node_exporter/node_exporter_startup.log ; stdout log path, NONE for none; default AUTO
stdout_logfile_maxbytes=50MB ; max # logfile bytes b4 rotation (default 50MB)
stdout_logfile_backups=10 ; # of stdout logfile backups (default 10)`)

	exporterIni := "/data/esenv/supervisor/conf/node_exporter.ini"

	if err = os.WriteFile(exporterIni, data, 0644); err != nil {
		logger.Error("write %s failed, %v", exporterIni, err)
	}

	_ = esutil.SupervisorctlUpdate()
	return nil
}
