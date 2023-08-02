package cst

const (
	// DefaulEsDataDir TODO
	DefaulEsDataDir = "/data/esdata"
	// DefaultInstallDir TODO
	DefaultInstallDir = "/data"
	// DefaultHttpPort TODO
	DefaultHttpPort = 9200 // 默认端口
	// DefaulEsLogDir TODO
	DefaulEsLogDir = "/data/eslog"
	// DefaulEsEnv TODO
	DefaulEsEnv = "/data/esenv" // es安装包存放目录
	// DefaultEsDir TODO
	DefaultEsDir = DefaulEsEnv + "/es_1"
	// DefaulEsConfigDir TODO
	DefaulEsConfigDir = DefaultEsDir + "/config"
	// DefaultSupervisorConf TODO
	DefaultSupervisorConf = DefaulEsEnv + "/supervisor/conf"
	// DefaultJvmOptionD TODO
	DefaultJvmOptionD = DefaultEsDir + "/config/jvm.options.d"
	// DefaultEsConfigFile TODO
	DefaultEsConfigFile = DefaultEsDir + "/config/elasticsearch.yml"
	// DefaultExecUser TODO
	DefaultExecUser = "mysql"
	// DefaultInfluxdbExecUser TODO
	DefaultInfluxdbExecUser = "influxdb"
	// DefaultPkgDir TODO
	DefaultPkgDir = "/data/install" // 介质存放目录
	// EsHot TODO
	EsHot = "hot"
	// EsCold TODO
	EsCold = "cold"
	// EsMaster TODO
	EsMaster = "master"
	// EsClient TODO
	EsClient = "client"
	// IsXpackMoinitorEnabled TODO
	IsXpackMoinitorEnabled = false
	// IsXpackSecurityEnabled TODO
	IsXpackSecurityEnabled = false
	// IsNodeIngest TODO
	IsNodeIngest = true
	// IsNodeMl TODO
	IsNodeMl = false
	// IsBootstrapMemoryLock TODO
	IsBootstrapMemoryLock = false
	// IsBootstrapSystemCall TODO
	IsBootstrapSystemCall = false
	// ES7102 TODO
	ES7102 = "7.10.2"
	// ESYmlAppend TODO
	ESYmlAppend = "elasticsearch.yml.append"
)

// KibanaWhiteList TODO
var (
	KibanaWhiteList = []string{"securitytenant", "Authorization"}
	Kibanatenancy   = []string{"Private", "Global"}
	KibanaRole      = []string{"kibana_read_only"}
)

// CertificateFile
var (
	CerFile710 = []string{"root-ca.pem", "root-ca-key.pem", "admin.pem",
		"admin-key.pem", "node1.pem", "node1_http.pem",
		"node1.key", "node1_http.key", "elasticsearch.yml.append"}

	CerFile = []string{"elastic-stack-ca.p12", "elastic-certificates.p12",
		"elasticsearch.yml.append", "es_passfile", "elasticsearch.keystore"}
)
