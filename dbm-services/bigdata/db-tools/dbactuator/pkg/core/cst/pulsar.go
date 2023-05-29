package cst

const (
	// DefaultPulsarDataDir TODO
	DefaultPulsarDataDir = "/data/pulsardata"

	// DefaultPulsarEnvDir TODO
	DefaultPulsarEnvDir = "/data/pulsarenv"

	// DefaultPulsarLogDir TODO
	DefaultPulsarLogDir = "/data/pulsarlog"

	// DefaultPulsarSupervisorConfDir TODO
	DefaultPulsarSupervisorConfDir = DefaultPulsarEnvDir + "/supervisor/conf"

	// DefaultPulsarZkDir TODO
	DefaultPulsarZkDir = DefaultPulsarEnvDir + "/zookeeper"

	// DefaultPulsarZkConf TODO
	DefaultPulsarZkConf = DefaultPulsarZkDir + "/conf/zookeeper.conf"

	// DefaultPulsarBkDir TODO
	DefaultPulsarBkDir = DefaultPulsarEnvDir + "/bookkeeper"

	// DefaultPulsarBkConf TODO
	DefaultPulsarBkConf = DefaultPulsarBkDir + "/conf/bookkeeper.conf"

	// DefaultPulsarBrokerDir TODO
	DefaultPulsarBrokerDir = DefaultPulsarEnvDir + "/broker"

	// DefaultPulsarBrokerConf TODO
	DefaultPulsarBrokerConf = DefaultPulsarBrokerDir + "/conf/broker.conf"

	// DefaultPulsarManagerDir TODO
	DefaultPulsarManagerDir = DefaultPulsarEnvDir + "/pulsar-manager/pulsar-manager"

	// DefaultPulsarManagerConf TODO
	DefaultPulsarManagerConf = DefaultPulsarManagerDir + "/application.properties"
)
