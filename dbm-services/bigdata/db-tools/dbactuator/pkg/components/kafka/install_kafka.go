package kafka

import (
	"fmt"
	"io/ioutil"
	"net"
	"net/http"
	"net/url"
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

	"github.com/pkg/errors"
)

// InstallKafkaComp TODO
type InstallKafkaComp struct {
	GeneralParam *components.GeneralParam
	Params       *InstallKafkaParams
	KfConfig
	RollBackContext rollback.RollBackObjects
}

// InstallKafkaParams TODO
type InstallKafkaParams struct {
	KafkaConfigs  map[string]string `json:"kafka_configs" `  // elasticsearch.yml
	Version       string            `json:"version" `        // 版本号eg: 7.10.2
	Port          int               `json:"port" `           // 连接端口
	JmxPort       int               `json:"jmx_port" `       // 连接端口
	Retention     int               `json:"retention" `      // 保存时间
	Replication   int               `json:"replication" `    // 默认副本数
	Partition     int               `json:"partition" `      // 默认分区数
	Factor        int               `json:"factor" `         // __consumer_offsets副本数
	ZookeeperIP   string            `json:"zookeeper_ip" `   // zookeeper ip, eg: ip1,ip2,ip3
	ZookeeperConf string            `json:"zookeeper_conf" ` // zookeeper ip, eg: ip1,ip2,ip3
	MyID          int               `json:"my_id" `          // 默认副本数
	JvmMem        string            `json:"jvm_mem"`         //  eg: 10g
	Host          string            `json:"host" `
	ClusterName   string            `json:"cluster_name" ` // 集群名
	Username      string            `json:"username" `
	Password      string            `json:"password" `
	BkBizID       int               `json:"bk_biz_id"`
	DbType        string            `json:"db_type"`
	ServiceType   string            `json:"service_type"`
}

// InitDirs TODO
type InitDirs = []string

// Port TODO
type Port = int

// KfConfig 目录定义等
type KfConfig struct {
	InstallDir   string `json:"install_dir"`  // /data
	KafkaEnvDir  string `json:"kafkaenv_dir"` //  /data/kafkaenv
	KafkaDir     string
	ZookeeperDir string
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

// CmakConfig Kafka manager config
type CmakConfig struct {
	ZookeeperIP string
	ClusterName string
	Version     string
	Username    string
	Password    string
	NodeIP      string
	HTTPPath    string
}

// InitDefaultParam TODO
func (i *InstallKafkaComp) InitDefaultParam() (err error) {
	logger.Info("start InitDefaultParam")
	// var mountpoint string
	i.InstallDir = cst.DefaultPkgDir
	i.KafkaEnvDir = cst.DefaultKafkaEnv
	i.KafkaDir = cst.DefaultKafkaDir
	i.ZookeeperDir = cst.DefaultZookeeperDir

	return nil
}

// InitKafkaNode TODO
/*
创建实例相关的数据，日志目录以及修改权限
*/
func (i *InstallKafkaComp) InitKafkaNode() error {

	execUser := cst.DefaultExecUser
	logger.Info("检查用户[%s]是否存在", execUser)
	if _, err := user.Lookup(execUser); err != nil {
		logger.Info("用户[%s]不存在，开始创建", execUser)
		if output, err := osutil.ExecShellCommand(false,
			fmt.Sprintf("useradd %s -g root -s /bin/bash -d /home/mysql",
				execUser)); err != nil {
			logger.Error("创建系统用户[%s]失败,%s, %v", execUser, output, err.Error())
			return err
		}
		logger.Info("用户[%s]创建成功", execUser)
	} else {
		logger.Info("用户[%s]存在, 跳过创建", execUser)
	}

	// mkdir
	extraCmd := fmt.Sprintf("rm -rf %s", i.KafkaEnvDir)
	if _, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("初始化实例目录失败:%s", err.Error())
		return err
	}
	extraCmd = fmt.Sprintf("mkdir -p %s ; chown -R mysql %s", i.KafkaEnvDir, "/data/kafka*")
	if _, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("初始化实例目录失败:%s", err.Error())
		return err
	}

	logger.Info("写入/etc/profile")
	scripts := []byte(`sed -i '/500000/d' /etc/profile
sed -i '/JAVA_HOME/d' /etc/profile
sed -i '/LC_ALL/d' /etc/profile
sed -i '/mysql/d' /etc/profile
sed -i '/USERNAME/d' /etc/profile
sed -i '/PASSWORD/d' /etc/profile
echo 'ulimit -n 500000
export JAVA_HOME=/data/kafkaenv/jdk
export JRE=$JAVA_HOME/jre
export PATH=$JAVA_HOME/bin:$JRE_HOME/bin:$PATH
export CLASSPATH=".:$JAVA_HOME/lib:$JRE/lib:$CLASSPATH"
export LC_ALL=en_US
export PATH=/usr/local/mysql/bin/:$PATH'>> /etc/profile

source /etc/profile`)

	scriptFile := "/data/kafkaenv/init.sh"
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

// DecompressKafkaPkg TODO
/**
 * @description:  校验、解压kafka安装包
 * @return {*}
 */
func (i *InstallKafkaComp) DecompressKafkaPkg() (err error) {

	pkgAbPath := "kafkapack-" + i.Params.Version + ".tar.gz"
	extraCmd := fmt.Sprintf("cp %s %s", i.InstallDir+"/"+pkgAbPath, i.KafkaEnvDir)
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}
	if err = os.Chdir(i.KafkaEnvDir); err != nil {
		return fmt.Errorf("cd to dir %s failed, err:%w", i.KafkaEnvDir, err)
	}
	if output, err := osutil.ExecShellCommand(false, fmt.Sprintf("tar zxf %s", pkgAbPath)); err != nil {
		logger.Error("tar zxf %s error:%s,%s", pkgAbPath, output, err.Error())
		return err
	}

	logger.Info("kafka binary directory: %s", i.KafkaEnvDir)
	if _, err := os.Stat(i.KafkaEnvDir); err != nil {
		logger.Error("%s check failed, %v", i.KafkaEnvDir, err)
		return err
	}
	logger.Info("decompress kafka pkg successfully")
	return nil
}

// InstallSupervisor TODO
/**
 * @description:  安装supervisor
 * @return {*}
 */
func (i *InstallKafkaComp) InstallSupervisor() (err error) {
	// check supervisor exist
	if !util.FileExists(cst.DefaultKafkaSupervisorConf) {
		logger.Error("supervisor not exist, %v", err)
		return err
	}
	extraCmd := fmt.Sprintf("ln -sf %s %s", i.KafkaEnvDir+"/"+"pypy-5.9.0", i.KafkaEnvDir+"/"+"python")
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}
	extraCmd = fmt.Sprintf("ln -sf %s %s", i.KafkaEnvDir+"/"+"supervisor/conf/supervisord.conf",
		"/etc/supervisord.conf")
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}
	extraCmd = fmt.Sprintf("ln -sf %s %s", i.KafkaEnvDir+"/"+"supervisor/bin/supervisorctl",
		"/usr/local/bin/supervisorctl")
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}
	extraCmd = fmt.Sprintf("ln -sf %s %s", i.KafkaEnvDir+"/"+"python/bin/supervisord",
		"/usr/local/bin/supervisord")
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	if err = sedEsConfig(i.KafkaEnvDir); err != nil {
		return err
	}

	extraCmd = fmt.Sprintf("chown -R mysql %s ", i.KafkaEnvDir)
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}
	extraCmd = "ps -ef | grep supervisord | grep -v grep | awk {'print \"kill -9 \" $2'} | sh"
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}
	// crontab
	if err = configCrontab(); err != nil {
		return err
	}
	startCmd := `su - mysql -c "/usr/local/bin/supervisord -c /data/kafkaenv/supervisor/conf/supervisord.conf"`
	logger.Info(fmt.Sprintf("execute supervisor [%s] begin", startCmd))
	pid, err := osutil.RunInBG(false, startCmd)
	logger.Info(fmt.Sprintf("execute supervisor [%s] end, pid: %d", startCmd, pid))
	if err != nil {
		return err
	}
	return nil
}

func sedEsConfig(kafkaEnvDir string) (err error) {
	extraCmd := fmt.Sprintf("sed -i 's/esenv/kafkaenv/g' %s", kafkaEnvDir+"/supervisor/check_supervisord.sh")
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}
	extraCmd = fmt.Sprintf("sed -i 's/esenv/kafkaenv/g' %s", kafkaEnvDir+"/supervisor/conf/supervisord.conf")
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}
	extraCmd = fmt.Sprintf("sed -i 's/esenv/kafkaenv/g' %s", kafkaEnvDir+"/supervisor/bin/supervisorctl")
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}
	extraCmd = fmt.Sprintf("sed -i 's/esenv/kafkaenv/g' %s", kafkaEnvDir+"/pypy-5.9.0/bin/supervisord")
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}
	extraCmd = fmt.Sprintf("sed -i 's/esenv/kafkaenv/g' %s", kafkaEnvDir+"/python/bin/supervisorctl")
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}
	extraCmd = fmt.Sprintf("rm %s ", kafkaEnvDir+"/supervisor/conf/elasticsearch.ini")
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}
	return nil
}

func configCrontab() (err error) {
	extraCmd := `crontab  -l -u mysql >/home/mysql/crontab.bak`
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
	}
	extraCmd = `sed -i '/check_supervisord.sh/d' /home/mysql/crontab.bak`
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}
	extraCmd = fmt.Sprintf(
		`echo '*/1 * * * *  %s >> /data/kafkaenv/supervisor/check_supervisord.err 2>&1' >>%s`,
		"/data/kafkaenv/supervisor/check_supervisord.sh", "/home/mysql/crontab.bak")
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}
	extraCmd = `crontab -u mysql /home/mysql/crontab.bak`
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}
	return nil
}

// InstallZookeeper TODO
/**
 * @description: 安装zookeeper
 * @return {*}
 */
func (i *InstallKafkaComp) InstallZookeeper() error {

	var (
		nodeIP           = i.Params.Host
		myID             = i.Params.MyID
		zookeeperConf    = i.Params.ZookeeperConf
		username         = i.Params.Username
		password         = i.Params.Password
		ZookeeperBaseDir = fmt.Sprintf("%s/zookeeper-%s", cst.DefaultKafkaEnv, cst.DefaultZookeeperVersion)
	)

	if _, err := net.Dial("tcp", fmt.Sprintf("%s:%d", nodeIP, 2181)); err == nil {
		logger.Error("zookeeper process exist")
		return errors.New("zookeeper process exist")
	}

	zookeeperLink := fmt.Sprintf("%s/zk", cst.DefaultKafkaEnv)
	extraCmd := fmt.Sprintf("ln -s %s %s ", ZookeeperBaseDir, zookeeperLink)
	if output, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("link zookeeperLink failed, %s, %s", output, err.Error())
		return err
	}

	// mkdir
	extraCmd = fmt.Sprintf("mkdir -p %s ; mkdir -p %s ; mkdir -p %s ; mkdir -p %s ; chown -R mysql %s",
		cst.DefaultZookeeperLogsDir, cst.DefaultZookeeperDataDir, cst.DefaultZookeeperConfDir, cst.DefaultZookeeperLogDir,
		"/data/kafka*")
	if _, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("初始化实例目录失败:%s", err.Error())
		return err
	}

	extraCmd = fmt.Sprintf("chown -R mysql %s", cst.DefaultZookeeperLogDir)
	if _, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("初始化实例目录失败:%s", err.Error())
		return err
	}

	if err := configZookeeper(username, password, zookeeperLink, zookeeperConf, myID); err != nil {
		return err
	}

	logger.Info("生成zookeeper.ini文件")
	zookeeperini := esutil.GenZookeeperini()
	zookeeperiniFile := fmt.Sprintf("%s/zookeeper.ini", cst.DefaultKafkaSupervisorConf)
	if err := ioutil.WriteFile(zookeeperiniFile, zookeeperini, 0); err != nil {
		logger.Error("write %s failed, %v", zookeeperiniFile, err)
	}

	extraCmd = fmt.Sprintf("chmod 777 %s/zookeeper.ini ", cst.DefaultKafkaSupervisorConf)
	if _, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	extraCmd = fmt.Sprintf("chown -R mysql %s ", i.KafkaEnvDir)
	if _, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	if err := esutil.SupervisorctlUpdate(); err != nil {
		logger.Error("supervisort update failed %v", err)
	}

	// sleep 30
	time.Sleep(30 * time.Second)

	if _, err := net.Dial("tcp", fmt.Sprintf("%s:%d", nodeIP, 2181)); err != nil {
		logger.Error("zookeeper start failed %v", err)
		return err
	}

	return nil
}

func configZookeeper(username string, password string, zookeeperLink string, zookeeperConf string,
	myID int) (err error) {
	extraCmd := fmt.Sprintf(`echo 'export USERNAME=%s
export PASSWORD=%s'>> /etc/profile`, username, password)
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	logger.Info("zoo.cfg")
	extraCmd = fmt.Sprintf(zookeeperConfig, cst.DefaultZookeeperDataDir, cst.DefaultZookeeperLogsDir,
		cst.DefaultZookeeperDynamicConf, zookeeperLink+"/conf/zoo.cfg")
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	extraCmd = fmt.Sprintf(`echo "%s" > %s`, zookeeperConf, cst.DefaultZookeeperDynamicConf)
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	extraCmd = fmt.Sprintf(`echo %d > %s`, myID, cst.DefaultZookeeperDataDir+"/myid")
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	logger.Info("配置jvm参数")
	extraCmd = fmt.Sprintf(`echo "export JVMFLAGS=\"-Xms1G -Xmx4G \$JVMFLAGS\"" > %s`,
		zookeeperLink+"/conf/java.env")
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}
	return nil
}

const zookeeperConfig = `echo "tickTime=2000
initLimit=10
syncLimit=5
dataDir=%s
dataLogDir=%s
autopurge.snapRetainCount=3
autopurge.purgeInterval=1
reconfigEnabled=true
skipACL=yes
dynamicConfigFile=%s" > %s`

// InitKafkaUser TODO
func (i *InstallKafkaComp) InitKafkaUser() (err error) {

	var (
		zookeeperIP  = i.Params.ZookeeperIP
		version      = i.Params.Version
		username     = i.Params.Username
		password     = i.Params.Password
		kafkaBaseDir = fmt.Sprintf("%s/kafka-%s", cst.DefaultKafkaEnv, version)
	)
	zookeeperIPList := strings.Split(zookeeperIP, ",")
	extraCmd := fmt.Sprintf(
		"%s %s:2181,%s:2181,%s:2181/ %s \"%s=[iterations=8192,password=%s],%s=[password=%s]\" %s %s",
		kafkaBaseDir+"/bin/kafka-configs.sh --zookeeper",
		zookeeperIPList[0], zookeeperIPList[1], zookeeperIPList[2],
		"--alter --add-config",
		"SCRAM-SHA-256",
		password,
		"SCRAM-SHA-512",
		password,
		"--entity-type users --entity-name",
		username)
	if output, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("copy basedir failed, %s, %s", output, err.Error())
		return err
	}

	return nil
}

// InstallBroker TODO
/**
 * @description: 安装broker
 * @return {*}
 */
func (i *InstallKafkaComp) InstallBroker() error {
	var (
		retentionHours = i.Params.Retention
		replicationNum = i.Params.Replication
		partitionNum   = i.Params.Partition
		factor         = i.Params.Factor
		nodeIP         = i.Params.Host
		port           = i.Params.Port
		jmxPort        = i.Params.JmxPort
		listeners      = fmt.Sprintf("%s:%d", nodeIP, port)
		version        = i.Params.Version
		processors     = runtime.NumCPU()
		zookeeperIP    = i.Params.ZookeeperIP
		kafkaBaseDir   = fmt.Sprintf("%s/kafka-%s", cst.DefaultKafkaEnv, version)
		username       = i.Params.Username
		password       = i.Params.Password
	)

	// ln -s /data/kafkaenv/kafka-$version /data/kafkaenv/kafka
	kafkaLink := fmt.Sprintf("%s/kafka", cst.DefaultKafkaEnv)
	extraCmd := fmt.Sprintf("ln -s %s %s ", kafkaBaseDir, kafkaLink)
	if output, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("copy basedir failed, %s, %s", output, err.Error())
		return err
	}

	extraCmd = fmt.Sprintf("mkdir -p %s ; chown -R mysql %s", cst.DefaultKafkaLogDir, "/data/kafka*")
	if _, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("初始化实例目录失败:%s", err.Error())
		return err
	}

	// 多磁盘判断逻辑
	kafkaDataDir := cst.DefaultKafkaDataDir
	localDisks := esutil.GetPath()
	diskCount := len(localDisks)
	if diskCount != 0 {
		var paths []string
		for _, disk := range localDisks {
			path := disk + "/kafkadata"
			extraCmd = fmt.Sprintf("mkdir -p %s ; chown -R mysql %s", path, path)
			if _, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
				logger.Error("初始化实例目录失败:%s", err.Error())
				return err
			}
			paths = append(paths, path)
		}
		kafkaDataDir = strings.Join(paths, ",")
	} else {
		extraCmd = fmt.Sprintf("mkdir -p %s ; chown -R mysql %s", kafkaDataDir, kafkaDataDir)
		if _, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
			logger.Error("初始化实例目录失败:%s", err.Error())
			return err
		}
	}

	zookeeperIPList := strings.Split(zookeeperIP, ",")
	extraCmd = fmt.Sprintf(kafkaConfig, retentionHours, replicationNum, partitionNum, processors, factor, processors,
		processors, kafkaDataDir, listeners, listeners, zookeeperIPList[0], zookeeperIPList[1], zookeeperIPList[2],
		kafkaLink+"/config/server.properties")
	if _, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	if err := configKafka(username, password, kafkaLink, jmxPort); err != nil {
		return err
	}

	if err := startKafka(i.KafkaEnvDir); err != nil {
		return err
	}

	// sleep 60s for wating kafka up
	time.Sleep(30 * time.Second)

	if _, err := net.Dial("tcp", fmt.Sprintf("%s:%d", nodeIP, port)); err != nil {
		logger.Error("broker start failed %v", err)
		return err
	}
	return nil
}

func configKafka(username string, password string, kafkaLink string, jmxPort int) error {
	logger.Info("配置jaas")
	extraCmd := fmt.Sprintf(`echo 'KafkaServer {
  org.apache.kafka.common.security.scram.ScramLoginModule required
  username="%s"
  password="%s";
};' > %s`, username, password, kafkaLink+"/config/kafka_server_scram_jaas.conf")
	if _, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	logger.Info("配置run-class.sh")
	extraCmd = fmt.Sprintf("sed -i 's/esenv/kafkaenv/g' %s", kafkaLink+"/bin/kafka-run-class.sh")
	if _, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	logger.Info("配置start.sh")
	extraCmd = fmt.Sprintf("sed -i '/export KAFKA_HEAP_OPTS=\"-Xmx1G -Xms1G\"/a\\    export JMX_PORT=\"%d\"' %s",
		jmxPort,
		kafkaLink+"/bin/kafka-server-start.sh")
	if _, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}
	// 配置jvm参数
	if err := configJVM(kafkaLink); err != nil {
		return err
	}

	extraCmd = fmt.Sprintf(
		"echo \"export KAFKA_OPTS=\\\"\\${KAFKA_OPTS} -javaagent:%s=7071:%s/kafka-2_0_0.yml\\\"\" >> %s",
		kafkaLink+"/libs/jmx_prometheus_javaagent-0.17.2.jar", kafkaLink+"/config", "insert.txt")
	if _, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	extraCmd = fmt.Sprintf("sed -i '23 r insert.txt' %s", kafkaLink+"/bin/kafka-server-start.sh")
	if _, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	extraCmd = fmt.Sprintf("cp %s %s", kafkaLink+"/bin/kafka-server-start.sh", kafkaLink+
		"/bin/kafka-server-scram-start.sh")
	if output, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("copy start.sh failed, %s, %s", output, err.Error())
		return err
	}

	extraCmd = fmt.Sprintf("sed -i '$d' %s", kafkaLink+"/bin/kafka-server-scram-start.sh")
	if _, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	extraCmd = fmt.Sprintf(
		"echo 'exec $base_dir/kafka-run-class.sh $EXTRA_ARGS %s=$base_dir/../%s  kafka.Kafka \"$@\"' >> %s",
		"-Djava.security.auth.login.config",
		"config/kafka_server_scram_jaas.conf",
		kafkaLink+"/bin/kafka-server-scram-start.sh")
	if _, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}
	return nil
}

func configJVM(kafkaLink string) (err error) {
	var instMem uint64

	if instMem, err = esutil.GetInstMem(); err != nil {
		logger.Error("获取实例内存失败, err: %w", err)
		return fmt.Errorf("获取实例内存失败, err: %w", err)
	}
	jvmSize := instMem / 1024
	if jvmSize > 30 {
		jvmSize = 30
	} else {
		jvmSize = jvmSize / 2
	}
	extraCmd := fmt.Sprintf("sed -i 's/-Xmx1G -Xms1G/-Xmx%dG -Xms%dG/g' %s", jvmSize, jvmSize,
		kafkaLink+"/bin/kafka-server-start.sh")
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}
	return nil
}

func startKafka(kafkaEnvDir string) (err error) {
	logger.Info("生成kafka.ini文件")
	kafkaini := esutil.GenKafkaini()
	kafkainiFile := fmt.Sprintf("%s/kafka.ini", cst.DefaultKafkaSupervisorConf)
	if err = ioutil.WriteFile(kafkainiFile, kafkaini, 0); err != nil {
		logger.Error("write %s failed, %v", kafkainiFile, err)
	}

	extraCmd := fmt.Sprintf("chmod 777 %s/kafka.ini ", cst.DefaultKafkaSupervisorConf)
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	extraCmd = fmt.Sprintf("chown -R mysql %s ", kafkaEnvDir)
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	if err = esutil.SupervisorctlUpdate(); err != nil {
		logger.Error("supervisort update failed %v", err)
		return err
	}
	return nil
}

const kafkaConfig = `echo "log.retention.hours=%d
default.replication.factor=%d
num.partitions=%d
num.network.threads=%d
num.recovery.threads.per.data.dir=2
offsets.topic.replication.factor=%d
transaction.state.log.replication.factor=3
transaction.state.log.min.isr=3
group.initial.rebalance.delay.ms=3000
num.io.threads=%d
num.replica.fetchers=%d
unclean.leader.election.enable=true
delete.topic.enable=true
auto.leader.rebalance.enable=true
auto.create.topics.enable=true
socket.send.buffer.bytes=102400
socket.receive.buffer.bytes=102400
socket.request.max.bytes=104857600
log.flush.interval.messages=10000
log.flush.interval.ms=1000
log.cleanup.policy=delete
log.segment.bytes=1073741824
log.retention.check.interval.ms=300000
zookeeper.connection.timeout.ms=6000
log.dirs=%s
listeners=SASL_PLAINTEXT://%s
advertised.listeners=SASL_PLAINTEXT://%s
zookeeper.connect=%s:2181,%s:2181,%s:2181/
# List of enabled mechanisms, can be more than one
sasl.enabled.mechanisms=SCRAM-SHA-512

# Specify one of of the SASL mechanisms
sasl.mechanism.inter.broker.protocol=SCRAM-SHA-512
security.inter.broker.protocol=SASL_PLAINTEXT" > %s`

// InstallManager TODO
/**
 * @description: 安装kafka manager
 * @return {*}
 */
func (i *InstallKafkaComp) InstallManager() error {

	var (
		nodeIP           = i.Params.Host
		port             = i.Params.Port
		clusterName      = i.Params.ClusterName
		zookeeperIP      = i.Params.ZookeeperIP
		version          = i.Params.Version
		username         = i.Params.Username
		password         = i.Params.Password
		ZookeeperBaseDir = fmt.Sprintf("%s/zookeeper-%s", cst.DefaultKafkaEnv, cst.DefaultZookeeperVersion)
		bkBizID          = i.Params.BkBizID
		dbType           = i.Params.DbType
		serviceType      = i.Params.ServiceType
	)

	if err := installZookeeper(ZookeeperBaseDir, i.KafkaEnvDir); err != nil {
		return err
	}

	// Sleep 10 secs
	time.Sleep(10 * time.Second)

	extraCmd := fmt.Sprintf("sed -i 's/kafka-manager-zookeeper/%s/g' %s", nodeIP,
		i.KafkaEnvDir+"/cmak-3.0.0.5/conf/application.conf")
	if _, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	// 修改 play.http.contex="/{bkid}/{dbtype}/{cluster}/kafka_manager"
	httpPath := fmt.Sprintf("/%d/%s/%s/%s", bkBizID, dbType, clusterName, serviceType)

	extraCmd = fmt.Sprintf("sed -i '/play.http.context/s#/#%s#' %s", httpPath,
		i.KafkaEnvDir+"/cmak-3.0.0.5/conf/application.conf")
	if _, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	/* 配置账号密码
	basicAuthentication.enabled=true
	basicAuthentication.username=""
	basicAuthentication.password=""
	*/
	extraCmd = fmt.Sprintf(`sed -i -e  '/basicAuthentication.enabled/s/false/true/' \
	-e '/basicAuthentication.username/s/""/"%s"/' \
	-e '/basicAuthentication.password/s/""/"%s"/'   %s `, username, password,
		i.KafkaEnvDir+"/cmak-3.0.0.5/conf/application.conf")

	logger.Info("Exec: [%s]", extraCmd)
	if _, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	if err := startManager(i.KafkaEnvDir); err != nil {
		return err
	}

	for i := 0; i < 30; i++ {
		time.Sleep(10 * time.Second)
		if _, err := net.Dial("tcp", fmt.Sprintf("%s:%d", nodeIP, port)); err == nil {
			break
		}
	}
	cmak := CmakConfig{
		ZookeeperIP: zookeeperIP,
		ClusterName: clusterName,
		Version:     version,
		Username:    username,
		Password:    password,
		NodeIP:      nodeIP,
		HTTPPath:    httpPath,
	}
	if err := configCluster(cmak); err != nil {
		return err
	}

	return nil
}

func installZookeeper(zookeeperBaseDir string, kafkaEnvDir string) error {
	zookeeperLink := fmt.Sprintf("%s/zk", cst.DefaultKafkaEnv)
	extraCmd := fmt.Sprintf("ln -s %s %s ", zookeeperBaseDir, zookeeperLink)
	if output, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("link zookeeperLink failed, %s, %s", output, err.Error())
		return err
	}

	// mkdir
	extraCmd = fmt.Sprintf("mkdir -p %s ; mkdir -p %s ; mkdir -p %s ; chown -R mysql %s",
		cst.DefaultZookeeperLogsDir, cst.DefaultZookeeperDataDir, cst.DefaultZookeeperLogDir, "/data/kafka*")
	if _, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("初始化实例目录失败:%s", err.Error())
		return err
	}

	extraCmd = fmt.Sprintf("chown -R mysql %s", cst.DefaultZookeeperLogDir)
	if _, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("初始化实例目录失败:%s", err.Error())
		return err
	}

	logger.Info("zoo.cfg")
	extraCmd = fmt.Sprintf(`cp %s %s`, zookeeperLink+"/conf/zoo_sample.cfg", zookeeperLink+"/conf/zoo.cfg")
	if _, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	extraCmd = fmt.Sprintf("sed -i 's#dataDir=/tmp/zookeeper#dataDir=%s/zookeeper/data#g' %s", cst.DefaultKafkaEnv,
		zookeeperLink+"/conf/zoo.cfg")
	if _, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	logger.Info("生成zookeeper.ini文件")
	zookeeperini := esutil.GenZookeeperini()
	zookeeperiniFile := fmt.Sprintf("%s/zookeeper.ini", cst.DefaultKafkaSupervisorConf)
	if err := ioutil.WriteFile(zookeeperiniFile, zookeeperini, 0); err != nil {
		logger.Error("write %s failed, %v", zookeeperiniFile, err)
	}

	extraCmd = fmt.Sprintf("chmod 777 %s/zookeeper.ini ", cst.DefaultKafkaSupervisorConf)
	if _, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	extraCmd = fmt.Sprintf("chown -R mysql %s ", kafkaEnvDir)
	if _, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	logger.Info("启动zk")
	if err := esutil.SupervisorctlUpdate(); err != nil {
		logger.Error("supervisort update failed %v", err)
	}
	return nil
}

func startManager(kafkaEnvDir string) (err error) {
	logger.Info("生成manager.ini文件")
	managerini := esutil.GenManagerini()
	manageriniFile := fmt.Sprintf("%s/manager.ini", cst.DefaultKafkaSupervisorConf)
	if err = ioutil.WriteFile(manageriniFile, managerini, 0); err != nil {
		logger.Error("write %s failed, %v", manageriniFile, err)
	}

	extraCmd := fmt.Sprintf("chmod 777 %s/manager.ini ", cst.DefaultKafkaSupervisorConf)
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	extraCmd = fmt.Sprintf("chown -R mysql %s ", kafkaEnvDir)
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	logger.Info("启动manager")
	if err = esutil.SupervisorctlUpdate(); err != nil {
		logger.Error("supervisort update failed %v", err)
	}
	return nil
}

func configCluster(cmak CmakConfig) (err error) {
	extraCmd := fmt.Sprintf(`%s/zk/bin/zkCli.sh create /kafka-manager/mutex ""`, cst.DefaultKafkaEnv)
	_, _ = osutil.ExecShellCommand(false, extraCmd)
	extraCmd = fmt.Sprintf(`%s/zk/bin/zkCli.sh create /kafka-manager/mutex/locks ""`, cst.DefaultKafkaEnv)
	_, _ = osutil.ExecShellCommand(false, extraCmd)
	extraCmd = fmt.Sprintf(`%s/zk/bin/zkCli.sh create /kafka-manager/mutex/leases ""`, cst.DefaultKafkaEnv)
	_, _ = osutil.ExecShellCommand(false, extraCmd)

	zookeeperIPList := strings.Split(cmak.ZookeeperIP, ",")
	zkHosts := fmt.Sprintf("%s:2181,%s:2181,%s:2181/", zookeeperIPList[0], zookeeperIPList[1], zookeeperIPList[2])
	jaasConfig := fmt.Sprintf("%s required username=%s  password=%s ;",
		"org.apache.kafka.common.security.scram.ScramLoginModule", cmak.Username, cmak.Password)
	postData := url.Values{}
	postData.Add("name", cmak.ClusterName)
	postData.Add("zkHosts", zkHosts)
	postData.Add("kafkaVersion", cmak.Version)
	postData.Add("jmxEnabled", "true")
	postData.Add("jmxUser", "")
	postData.Add("jmxPass", "")
	postData.Add("logkafkaEnabled", "true")
	postData.Add("pollConsumers", "true")
	postData.Add("filterConsumers", "true")
	postData.Add("activeOffsetCacheEnabled", "true")
	postData.Add("displaySizeEnabled", "true")
	postData.Add("tuning.brokerViewUpdatePeriodSeconds", "30")
	postData.Add("tuning.clusterManagerThreadPoolSize", "2")
	postData.Add("tuning.clusterManagerThreadPoolQueueSize", "100")
	postData.Add("tuning.kafkaCommandThreadPoolSize", "2")
	postData.Add("tuning.kafkaCommandThreadPoolQueueSize", "100")
	postData.Add("tuning.logkafkaCommandThreadPoolSize", "2")
	postData.Add("tuning.logkafkaCommandThreadPoolQueueSize", "100")
	postData.Add("tuning.logkafkaUpdatePeriodSeconds", "30")
	postData.Add("tuning.partitionOffsetCacheTimeoutSecs", "5")
	postData.Add("tuning.brokerViewThreadPoolSize", "17")
	postData.Add("tuning.brokerViewThreadPoolQueueSize", "1000")
	postData.Add("tuning.offsetCacheThreadPoolSize", "17")
	postData.Add("tuning.offsetCacheThreadPoolQueueSize", "1000")
	postData.Add("tuning.kafkaAdminClientThreadPoolSize", "17")
	postData.Add("tuning.kafkaAdminClientThreadPoolQueueSize", "1000")
	postData.Add("tuning.kafkaManagedOffsetMetadataCheckMillis", "30000")
	postData.Add("tuning.kafkaManagedOffsetGroupCacheSize", "1000000")
	postData.Add("tuning.kafkaManagedOffsetGroupExpireDays", "7")
	postData.Add("securityProtocol", "SASL_PLAINTEXT")
	postData.Add("saslMechanism", "SCRAM-SHA-512")
	postData.Add("jaasConfig", jaasConfig)
	// http://localhost:9000/{prefix}/clusters
	url := "http://" + cmak.NodeIP + ":9000" + cmak.HTTPPath + "/clusters"
	contentType := "application/x-www-form-urlencoded"
	if _, err = http.Post(url, contentType, strings.NewReader(postData.Encode())); err != nil {
		logger.Error("post manager failed, %v", err)
		return err
	}
	return nil
}
