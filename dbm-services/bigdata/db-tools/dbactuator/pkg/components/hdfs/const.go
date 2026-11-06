package hdfs

const (
	// DefaultPkgDir TODO
	DefaultPkgDir = "/data/install"
	// DefaultInstallDir TODO
	DefaultInstallDir = "/data/hadoopenv"
	// DefaultJdkDir TODO
	DefaultJdkDir = DefaultInstallDir + "/java"
	// DefaultHttpPort TODO
	DefaultHttpPort = 50070
	// DefaultRpcPort TODO
	DefaultRpcPort = 9000
	// DefaultMetaDataDir TODO
	DefaultMetaDataDir = "/data/hadoopdata"
	// DefaultHdfsHomeDir TODO
	DefaultHdfsHomeDir = DefaultInstallDir + "/hadoop"
	// DefaultSupervisorConfDir TODO
	DefaultSupervisorConfDir = DefaultInstallDir + "/supervisor/conf"
	// DefaultExecuteUser TODO
	DefaultExecuteUser = "hadoop"
	// DefaultHdfsConfDir TODO
	DefaultHdfsConfDir = DefaultHdfsHomeDir + "/etc/hadoop"
	// DefaultJdkVersion TODO
	DefaultJdkVersion = "TencentKona-8.0.9-322"
	// DefaultZkVersion TODO
	DefaultZkVersion = "3.4.5-cdh5.4.11"
	// DefaultHdfsProfile HDFS 环境变量文件，由 sysinit_hdfs.sh 生成，
	// 内含 JAVA_HOME / HADOOP_HOME / HADOOP_CONF_DIR / PATH
	DefaultHdfsProfile = DefaultInstallDir + "/hdfsProfile"
)

// LoadProfileCmd 加载 HDFS 环境变量的命令前缀，用于 su - <user> -c "..." 的命令体开头。
//
// 为什么必须显式加载：
// TLinux 4 的 su 并非 --noprofile，它执行的是 ["-bash", "-c", ...]。
// TLinux 4 的 bash 对这种「通过 argv[0] 标识的非交互登录 shell」不加载 /etc/profile，
// 因此 su - <user> -c "cmd" 里的 cmd 拿不到 JAVA_HOME / HADOOP_HOME，表现为 command not found。
//
// 为什么直接加载 hdfsProfile 而不是 /etc/profile：
//  1. /etc/profile 中的 "source /data/hadoopenv/hdfsProfile" 一行会被多处 sed -i '/hdfsProfile/d'
//     删除（如 node_operation.go 的节点清理），混部或重装场景下加载 /etc/profile 可能拿不到变量；
//  2. /etc/profile 会连带执行 /etc/profile.d/*.sh，这些脚本的 stderr 输出会被
//     osutil.ExecShellCommand 判为执行失败（stderr 非空即失败），直接加载可缩小面。
//
// 为什么用 . 而不是 source：
// source 是 bash 扩展，POSIX sh/dash 不识别。执行用户来自外部参数 exec_user，
// 其登录 shell 不保证是 bash，用 source 可能直接报 source: not found。
const LoadProfileCmd = ". " + DefaultHdfsProfile + ";"

const (
	// All TODO
	All = "all"
	// ZooKeeper TODO
	ZooKeeper = "zookeeper"
	// JournalNode TODO
	JournalNode = "journalnode"
	// NameNode TODO
	NameNode = "namenode"
	// ZKFC TODO
	ZKFC = "zkfc"
	// DataNode TODO
	DataNode = "datanode"
)

const (
	// Stop TODO
	Stop = "stop"
	// Start TODO
	Start = "start"
	// Restart TODO
	Restart = "restart"
	// SupervisorStateRunning supervisorctl status 中表示组件已正常拉起的状态
	SupervisorStateRunning = "RUNNING"
)

const (
	// Add TODO
	Add = "add"
	// Remove TODO
	Remove = "remove"
)

// ExtraCleanUsers 清理 HDFS 节点时需同步删除的额外业务用户列表。
// 注意：Go 切片不支持 const，使用 var 声明，请勿在运行时修改其内容。
var ExtraCleanUsers = []string{"bkbase", "dataflow"}
