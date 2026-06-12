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
)

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
