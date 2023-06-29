package cst

// proxy related
const (
	// DefaultDataRootPath 默认data路径
	DefaultDataRootPath = "/data"
	// AlterNativeDataRootPath 备选data路径
	AlterNativeDataRootPath = "/data1"
	// DefaultProtobufPort riak Protobuf监听接口
	DefaultProtobufPort = 8087
	// DefaultHttpPort riak http监听接口
	DefaultHttpPort = 8098
	// LogPath 日志路径
	LogPath = "/data/riak/log"
	// DataDir data目录
	DataDir = "/riak/data"
	// ConfigPath 配置文件路径
	ConfigPath = "/etc/riak/riak.conf"
	// RiakPkgVersion riak rpm包的版本
	RiakPkgVersion = "riak-2.2.1-1.el6.x86_64"
	// ClusterStatusCmd 命令行查询集群状态
	ClusterStatusCmd = "riak-admin cluster status"
	// OsClearScriptPath sojob空闲检查的脚本
	OsClearScriptPath = "/usr/src/sojob/subjob/isclear/os_is_clear.pl"
)
