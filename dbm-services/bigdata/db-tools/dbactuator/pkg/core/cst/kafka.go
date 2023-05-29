package cst

const (
	// DefaultKafkaDataDir TODO
	DefaultKafkaDataDir = "/data/kafkadata"
	// DefaultKafkaPort TODO
	DefaultKafkaPort = 9092 // 默认端口
	// DefaultKafkaEnv TODO
	DefaultKafkaEnv = "/data/kafkaenv" // kafka安装包存放目录
	// DefaultKafkaLogDir TODO
	DefaultKafkaLogDir = "/data/kafkalog"
	// DefaultZookeeperLogDir TODO
	DefaultZookeeperLogDir = "/data/zklog"
	// DefaultKafkaDir TODO
	DefaultKafkaDir = DefaultKafkaEnv + "/kafka"
	// DefaultZookeeperDir TODO
	DefaultZookeeperDir = DefaultKafkaEnv + "/zk"
	// DefaultZookeeperLogsDir TODO
	DefaultZookeeperLogsDir = DefaultKafkaEnv + "/zookeeper/logs"
	// DefaultZookeeperDataDir TODO
	DefaultZookeeperDataDir = DefaultKafkaEnv + "/zookeeper/data"
	// DefaultZookeeperConfDir TODO
	DefaultZookeeperConfDir = DefaultKafkaEnv + "/zookeeper/conf"
	// DefaultZookeeperDynamicConf TODO
	DefaultZookeeperDynamicConf = DefaultZookeeperConfDir + "/zoo.cfg.dynamic"
	// DefaultKafkaSupervisorConf TODO
	DefaultKafkaSupervisorConf = DefaultKafkaEnv + "/supervisor/conf"
	// DefaultZookeeperVersion TODO
	DefaultZookeeperVersion = "3.6.3"
	// DefaultZookeeperShell TODO
	DefaultZookeeperShell = DefaultKafkaDir + "/bin/zookeeper-shell.sh"
	// DefaultTopicBin TODO
	DefaultTopicBin = DefaultKafkaDir + "/bin/kafka-topics.sh"
	// DefaultReassignPartitionsBin TODO
	DefaultReassignPartitionsBin = DefaultKafkaDir + "/bin/kafka-reassign-partitions.sh"
)
