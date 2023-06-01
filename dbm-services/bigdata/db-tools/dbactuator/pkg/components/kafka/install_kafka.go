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
	KafkaConfig
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
	ZookeeperIp   string            `json:"zookeeper_ip" `   // zookeeper ip, eg: ip1,ip2,ip3
	ZookeeperConf string            `json:"zookeeper_conf" ` // zookeeper ip, eg: ip1,ip2,ip3
	MyId          int               `json:"my_id" `          // 默认副本数
	JvmMem        string            `json:"jvm_mem"`         //  eg: 10g
	Host          string            `json:"host" `
	ClusterName   string            `json:"cluster_name" ` // 集群名
	Username      string            `json:"username" `
	Password      string            `json:"password" `
	BkBizId       int               `json:"bk_biz_id"`
	DbType        string            `json:"db_type"`
	ServiceType   string            `json:"service_type"`
}

// InitDirs TODO
type InitDirs = []string

// Port TODO
type Port = int
type socket = string

// KafkaConfig 目录定义等
type KafkaConfig struct {
	InstallDir   string `json:"install_dir"`  // /data
	KafkaEnvDir  string `json:"kafkaenv_dir"` //  /data/kafkaenv
	KafkaDir     string
	ZookeeperDir string
}

// RenderConfig 需要替换的配置值 Todo
type RenderConfig struct {
	ClusterName          string
	NodeName             string
	HttpPort             int
	CharacterSetServer   string
	InnodbBufferPoolSize string
	Logdir               string
	ServerId             uint64
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
func (i *InstallKafkaComp) InitKafkaNode() (err error) {

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
	if err = ioutil.WriteFile(scriptFile, scripts, 0644); err != nil {
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
	// Todo: check supervisor exist
	// supervisor

	if !util.FileExists(cst.DefaultKafkaSupervisorConf) {
		logger.Error("supervisor not exist, %v", err)
		return err

	}

	extraCmd := fmt.Sprintf("rm -rf %s", i.KafkaEnvDir+"/"+"python")
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}
	extraCmd = fmt.Sprintf("ln -sf %s %s", i.KafkaEnvDir+"/"+"pypy-5.9.0", i.KafkaEnvDir+"/"+"python")
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	extraCmd = fmt.Sprintf("rm -rf %s", "/etc/supervisord.conf")
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}
	extraCmd = fmt.Sprintf("ln -sf %s %s", i.KafkaEnvDir+"/"+"supervisor/conf/supervisord.conf", "/etc/supervisord.conf")
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	extraCmd = fmt.Sprintf("rm -rf %s", "/usr/local/bin/supervisorctl")
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

	extraCmd = fmt.Sprintf("rm -rf %s", "/usr/local/bin/supervisord")
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}
	extraCmd = fmt.Sprintf("ln -sf %s %s", i.KafkaEnvDir+"/"+"python/bin/supervisord", "/usr/local/bin/supervisord")
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	extraCmd = fmt.Sprintf("sed -i 's/esenv/kafkaenv/g' %s", i.KafkaEnvDir+"/supervisor/check_supervisord.sh")
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	extraCmd = fmt.Sprintf("sed -i 's/esenv/kafkaenv/g' %s", i.KafkaEnvDir+"/supervisor/conf/supervisord.conf")
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	extraCmd = fmt.Sprintf("sed -i 's/esenv/kafkaenv/g' %s", i.KafkaEnvDir+"/supervisor/bin/supervisorctl")
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	extraCmd = fmt.Sprintf("sed -i 's/esenv/kafkaenv/g' %s", i.KafkaEnvDir+"/pypy-5.9.0/bin/supervisord")
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	extraCmd = fmt.Sprintf("sed -i 's/esenv/kafkaenv/g' %s", i.KafkaEnvDir+"/python/bin/supervisorctl")
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	extraCmd = fmt.Sprintf("rm %s ", i.KafkaEnvDir+"/supervisor/conf/elasticsearch.ini")
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
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
		`echo '*/1 * * * *  /data/kafkaenv/supervisor/check_supervisord.sh >> /data/kafkaenv/supervisor/check_supervisord.err 2>&1' >>/home/mysql/crontab.bak`
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	extraCmd = `crontab -u mysql /home/mysql/crontab.bak`
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
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

// InstallZookeeper TODO
/**
 * @description: 安装zookeeper
 * @return {*}
 */
func (i *InstallKafkaComp) InstallZookeeper() (err error) {

	var (
		nodeIp           string = i.Params.Host
		myId             int    = i.Params.MyId
		zookeeperConf    string = i.Params.ZookeeperConf
		username         string = i.Params.Username
		password         string = i.Params.Password
		ZookeeperBaseDir string = fmt.Sprintf("%s/zookeeper-%s", cst.DefaultKafkaEnv, cst.DefaultZookeeperVersion)
	)

	if _, err := net.Dial("tcp", fmt.Sprintf("%s:%d", nodeIp, 2181)); err == nil {
		logger.Error("zookeeper process exist")
		return errors.New("zookeeper process exist")
	}

	zookeeperLink := fmt.Sprintf("%s/zk", cst.DefaultKafkaEnv)
	extraCmd := fmt.Sprintf("rm -rf %s", zookeeperLink)
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}
	extraCmd = fmt.Sprintf("ln -s %s %s ", ZookeeperBaseDir, zookeeperLink)
	if output, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("link zookeeperLink failed, %s, %s", output, err.Error())
		return err
	}

	extraCmd = fmt.Sprintf(`echo 'export USERNAME=%s
export PASSWORD=%s'>> /etc/profile`, username, password)
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	// mkdir
	extraCmd = fmt.Sprintf("rm -rf %s", cst.DefaultZookeeperLogDir)
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}
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

	logger.Info("zoo.cfg")
	extraCmd = fmt.Sprintf(`echo "tickTime=2000
initLimit=10
syncLimit=5
dataDir=%s
dataLogDir=%s
autopurge.snapRetainCount=3
autopurge.purgeInterval=1
reconfigEnabled=true
skipACL=yes
dynamicConfigFile=%s" > %s`, cst.DefaultZookeeperDataDir, cst.DefaultZookeeperLogsDir, cst.DefaultZookeeperDynamicConf, zookeeperLink+"/conf/zoo.cfg")
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	extraCmd = fmt.Sprintf(`echo "%s" > %s`, zookeeperConf, cst.DefaultZookeeperDynamicConf)
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	extraCmd = fmt.Sprintf(`echo %d > %s`, myId, cst.DefaultZookeeperDataDir+"/myid")
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	logger.Info("配置jvm参数")
	extraCmd = fmt.Sprintf(`echo "export JVMFLAGS=\"-Xms1G -Xmx4G \$JVMFLAGS\"" > %s`, zookeeperLink+"/conf/java.env")
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	logger.Info("生成zookeeper.ini文件")
	zookeeperini := esutil.GenZookeeperini()
	zookeeperiniFile := fmt.Sprintf("%s/zookeeper.ini", cst.DefaultKafkaSupervisorConf)
	if err = ioutil.WriteFile(zookeeperiniFile, zookeeperini, 0); err != nil {
		logger.Error("write %s failed, %v", zookeeperiniFile, err)
	}

	extraCmd = fmt.Sprintf("chmod 777 %s/zookeeper.ini ", cst.DefaultKafkaSupervisorConf)
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	extraCmd = fmt.Sprintf("chown -R mysql %s ", i.KafkaEnvDir)
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	if err = esutil.SupervisorctlUpdate(); err != nil {
		logger.Error("supervisort update failed %v", err)
	}

	extraCmd = fmt.Sprintf("sleep 10")
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	if _, err := net.Dial("tcp", fmt.Sprintf("%s:%d", nodeIp, 2181)); err != nil {
		logger.Error("zookeeper start failed %v", err)
		return err
	}

	return nil
}

// InitKafkaUser TODO
func (i *InstallKafkaComp) InitKafkaUser() (err error) {

	var (
		zookeeperIp  string = i.Params.ZookeeperIp
		version      string = i.Params.Version
		username     string = i.Params.Username
		password     string = i.Params.Password
		kafkaBaseDir string = fmt.Sprintf("%s/kafka-%s", cst.DefaultKafkaEnv, version)
	)
	zookeeperIpList := strings.Split(zookeeperIp, ",")
	extraCmd := fmt.Sprintf(
		"%s/bin/kafka-configs.sh --zookeeper %s:2181,%s:2181,%s:2181/ --alter --add-config \"SCRAM-SHA-256=[iterations=8192,password=%s],SCRAM-SHA-512=[password=%s]\" --entity-type users --entity-name %s",
		kafkaBaseDir, zookeeperIpList[0], zookeeperIpList[1], zookeeperIpList[2], password, password, username)
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
func (i *InstallKafkaComp) InstallBroker() (err error) {
	var (
		retentionHours int               = i.Params.Retention
		replicationNum int               = i.Params.Replication
		partitionNum   int               = i.Params.Partition
		factor         int               = i.Params.Factor
		nodeIp         string            = i.Params.Host
		port           int               = i.Params.Port
		jmxPort        int               = i.Params.JmxPort
		listeners      string            = fmt.Sprintf("%s:%d", nodeIp, port)
		version        string            = i.Params.Version
		processors     int               = runtime.NumCPU()
		zookeeperIp    string            = i.Params.ZookeeperIp
		kafkaConfigs   map[string]string = i.Params.KafkaConfigs
		kafkaBaseDir   string            = fmt.Sprintf("%s/kafka-%s", cst.DefaultKafkaEnv, version)
		username       string            = i.Params.Username
		password       string            = i.Params.Password
	)

	// ln -s /data/kafkaenv/kafka-$version /data/kafkaenv/kafka
	kafkaLink := fmt.Sprintf("%s/kafka", cst.DefaultKafkaEnv)
	extraCmd := fmt.Sprintf("rm -rf %s", kafkaLink)
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}
	extraCmd = fmt.Sprintf("ln -s %s %s ", kafkaBaseDir, kafkaLink)
	if output, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("copy basedir failed, %s, %s", output, err.Error())
		return err
	}

	// mkdir
	extraCmd = fmt.Sprintf("rm -rf %s", cst.DefaultKafkaLogDir)
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}
	extraCmd = fmt.Sprintf("rm -rf %s", cst.DefaultKafkaDataDir)
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}
	extraCmd = fmt.Sprintf("mkdir -p %s ; mkdir -p %s ; chown -R mysql %s", cst.DefaultKafkaDataDir,
		cst.DefaultKafkaLogDir, "/data/kafka*")
	if _, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("初始化实例目录失败:%s", err.Error())
		return err
	}

	logger.Info("开始渲染server.properties")
	zookeeperIpList := strings.Split(zookeeperIp, ",")
	for k, v := range kafkaConfigs {
		config := k + "=" + v
		logger.Info("config=%s", config)
	}
	extraCmd = fmt.Sprintf(`echo "log.retention.hours=%d
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
security.inter.broker.protocol=SASL_PLAINTEXT" > %s`, retentionHours, replicationNum, partitionNum, processors, factor, processors, processors, cst.DefaultKafkaDataDir, listeners, listeners, zookeeperIpList[0], zookeeperIpList[1], zookeeperIpList[2], kafkaLink+"/config/server.properties")
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	logger.Info("配置jaas")
	extraCmd = fmt.Sprintf(`echo 'KafkaServer {
  org.apache.kafka.common.security.scram.ScramLoginModule required
  username="%s"
  password="%s";
};' > %s`, username, password, kafkaLink+"/config/kafka_server_scram_jaas.conf")
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	logger.Info("配置run-class.sh")
	extraCmd = fmt.Sprintf("sed -i 's/esenv/kafkaenv/g' %s", kafkaLink+"/bin/kafka-run-class.sh")
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	logger.Info("配置start.sh")
	extraCmd = fmt.Sprintf("sed -i '/export KAFKA_HEAP_OPTS=\"-Xmx1G -Xms1G\"/a\\    export JMX_PORT=\"%d\"' %s", jmxPort,
		kafkaLink+"/bin/kafka-server-start.sh")
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
	jvmSize := instMem / 1024
	if jvmSize > 30 {
		jvmSize = 30
	} else {
		jvmSize = jvmSize / 2
	}
	extraCmd = fmt.Sprintf("sed -i 's/-Xmx1G -Xms1G/-Xmx%dG -Xms%dG/g' %s", jvmSize, jvmSize,
		kafkaLink+"/bin/kafka-server-start.sh")
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	extraCmd = fmt.Sprintf("rm -rf insert.txt")
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	extraCmd = fmt.Sprintf(
		"echo \"export KAFKA_OPTS=\\\"\\${KAFKA_OPTS} -javaagent:%s/libs/jmx_prometheus_javaagent-0.17.2.jar=7071:%s/config/kafka-2_0_0.yml\\\"\" >> insert.txt", kafkaLink, kafkaLink)
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	extraCmd = fmt.Sprintf("sed -i '23 r insert.txt' %s", kafkaLink+"/bin/kafka-server-start.sh")
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
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
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	extraCmd = fmt.Sprintf(
		"echo 'exec $base_dir/kafka-run-class.sh $EXTRA_ARGS -Djava.security.auth.login.config=$base_dir/../config/kafka_server_scram_jaas.conf  kafka.Kafka \"$@\"' >> %s", kafkaLink+"/bin/kafka-server-scram-start.sh")
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	logger.Info("生成kafka.ini文件")
	kafkaini := esutil.GenKafkaini()
	kafkainiFile := fmt.Sprintf("%s/kafka.ini", cst.DefaultKafkaSupervisorConf)
	if err = ioutil.WriteFile(kafkainiFile, kafkaini, 0); err != nil {
		logger.Error("write %s failed, %v", kafkainiFile, err)
	}

	extraCmd = fmt.Sprintf("chmod 777 %s/kafka.ini ", cst.DefaultKafkaSupervisorConf)
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	extraCmd = fmt.Sprintf("chown -R mysql %s ", i.KafkaEnvDir)
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	if err = esutil.SupervisorctlUpdate(); err != nil {
		logger.Error("supervisort update failed %v", err)
		return err
	}

	// sleep 60s for wating es up
	time.Sleep(30 * time.Second)

	if _, err := net.Dial("tcp", fmt.Sprintf("%s:%d", nodeIp, port)); err != nil {
		logger.Error("broker start failed %v", err)
		return err
	}
	return nil
}

// InstallManager TODO
/**
 * @description: 安装kafka manager
 * @return {*}
 */
func (i *InstallKafkaComp) InstallManager() (err error) {

	var (
		nodeIp           string = i.Params.Host
		port             int    = i.Params.Port
		clusterName      string = i.Params.ClusterName
		zookeeperIp      string = i.Params.ZookeeperIp
		version          string = i.Params.Version
		username         string = i.Params.Username
		password         string = i.Params.Password
		ZookeeperBaseDir string = fmt.Sprintf("%s/zookeeper-%s", cst.DefaultKafkaEnv, cst.DefaultZookeeperVersion)
		bkBizId          int    = i.Params.BkBizId
		dbType           string = i.Params.DbType
		serviceType      string = i.Params.ServiceType
	)

	zookeeperLink := fmt.Sprintf("%s/zk", cst.DefaultKafkaEnv)
	extraCmd := fmt.Sprintf("rm -rf %s", zookeeperLink)
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}
	extraCmd = fmt.Sprintf("ln -s %s %s ", ZookeeperBaseDir, zookeeperLink)
	if output, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("link zookeeperLink failed, %s, %s", output, err.Error())
		return err
	}

	// mkdir
	extraCmd = fmt.Sprintf("rm -rf %s", cst.DefaultZookeeperLogDir)
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}
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
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	extraCmd = fmt.Sprintf("sed -i 's#dataDir=/tmp/zookeeper#dataDir=%s/zookeeper/data#g' %s", cst.DefaultKafkaEnv,
		zookeeperLink+"/conf/zoo.cfg")
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	logger.Info("生成zookeeper.ini文件")
	zookeeperini := esutil.GenZookeeperini()
	zookeeperiniFile := fmt.Sprintf("%s/zookeeper.ini", cst.DefaultKafkaSupervisorConf)
	if err = ioutil.WriteFile(zookeeperiniFile, zookeeperini, 0); err != nil {
		logger.Error("write %s failed, %v", zookeeperiniFile, err)
	}

	extraCmd = fmt.Sprintf("chmod 777 %s/zookeeper.ini ", cst.DefaultKafkaSupervisorConf)
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	extraCmd = fmt.Sprintf("chown -R mysql %s ", i.KafkaEnvDir)
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	logger.Info("启动zk")
	if err = esutil.SupervisorctlUpdate(); err != nil {
		logger.Error("supervisort update failed %v", err)
	}

	extraCmd = fmt.Sprintf("sleep 5")
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	extraCmd = fmt.Sprintf("sed -i 's/kafka-manager-zookeeper/%s/g' %s", nodeIp,
		i.KafkaEnvDir+"/cmak-3.0.0.5/conf/application.conf")
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	// 修改 play.http.contex="/{bkid}/{dbtype}/{cluster}/kafka_manager"
	httpPath := fmt.Sprintf("/%d/%s/%s/%s", bkBizId, dbType, clusterName, serviceType)

	extraCmd = fmt.Sprintf("sed -i '/play.http.context/s#/#%s#' %s", httpPath,
		i.KafkaEnvDir+"/cmak-3.0.0.5/conf/application.conf")
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	/* 配置账号密码
	basicAuthentication.enabled=true
	basicAuthentication.username=""
	basicAuthentication.password=""

	extraCmd = fmt.Sprintf(
		"sed -i -e '/basicAuthentication.enabled/s/false/true/g'  -e '/basicAuthentication.username/s/admin/%s/g' -e '/basicAuthentication.password/s/password/%s/g' %s", username, password,
		i.KafkaEnvDir+"/cmak-3.0.0.5/conf/application.conf")
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}
	*/

	logger.Info("生成manager.ini文件")
	managerini := esutil.GenManagerini()
	manageriniFile := fmt.Sprintf("%s/manager.ini", cst.DefaultKafkaSupervisorConf)
	if err = ioutil.WriteFile(manageriniFile, managerini, 0); err != nil {
		logger.Error("write %s failed, %v", manageriniFile, err)
	}

	extraCmd = fmt.Sprintf("chmod 777 %s/manager.ini ", cst.DefaultKafkaSupervisorConf)
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	extraCmd = fmt.Sprintf("chown -R mysql %s ", i.KafkaEnvDir)
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	logger.Info("启动manager")
	if err = esutil.SupervisorctlUpdate(); err != nil {
		logger.Error("supervisort update failed %v", err)
	}

	for i := 0; i < 30; i++ {
		extraCmd = fmt.Sprintf("sleep 10")
		if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
			logger.Error("%s execute failed, %v", extraCmd, err)
			return err
		}
		if _, err := net.Dial("tcp", fmt.Sprintf("%s:%d", nodeIp, port)); err == nil {
			break
		}
	}

	extraCmd = fmt.Sprintf(`%s/zk/bin/zkCli.sh create /kafka-manager/mutex ""`, cst.DefaultKafkaEnv)
	osutil.ExecShellCommand(false, extraCmd)
	extraCmd = fmt.Sprintf(`%s/zk/bin/zkCli.sh create /kafka-manager/mutex/locks ""`, cst.DefaultKafkaEnv)
	osutil.ExecShellCommand(false, extraCmd)
	extraCmd = fmt.Sprintf(`%s/zk/bin/zkCli.sh create /kafka-manager/mutex/leases ""`, cst.DefaultKafkaEnv)
	osutil.ExecShellCommand(false, extraCmd)

	zookeeperIpList := strings.Split(zookeeperIp, ",")
	zkHosts := fmt.Sprintf("%s:2181,%s:2181,%s:2181/", zookeeperIpList[0], zookeeperIpList[1], zookeeperIpList[2])
	jaasConfig := fmt.Sprintf(
		"org.apache.kafka.common.security.scram.ScramLoginModule required username=%s  password=%s ;", username, password)
	postData := url.Values{}
	postData.Add("name", clusterName)
	postData.Add("zkHosts", zkHosts)
	postData.Add("kafkaVersion", version)
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
	url := "http://" + nodeIp + ":9000" + httpPath + "/clusters"
	contentType := "application/x-www-form-urlencoded"
	if _, err = http.Post(url, contentType, strings.NewReader(postData.Encode())); err != nil {
		logger.Error("post manager failed, %v", err)
		return err
	}

	return nil
}
