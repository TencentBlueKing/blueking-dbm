package cst

const (
	// DefaultKafkaDataDir Kafka默认数据目录
	DefaultKafkaDataDir = "/data/kafkadata"
	// DefaultKafkaPort Kafka默认端口
	DefaultKafkaPort = 9092
	// DefaultKafkaEnv Kafka默认环境目录
	DefaultKafkaEnv = "/data/kafkaenv"
	// DefaultKafkaLogDir Kafka默认日志目录
	DefaultKafkaLogDir = "/data/kafkalog"
	// DefaultZookeeperLogDir zk默认日志目录
	DefaultZookeeperLogDir = "/data/zklog"
	// DefaultKafkaDir kafka程序目录
	DefaultKafkaDir = DefaultKafkaEnv + "/kafka"
	// DefaultZookeeperDir zk程序目录
	DefaultZookeeperDir = DefaultKafkaEnv + "/zk"
	// DefaultZookeeperLogsDir zk写入日志目录
	DefaultZookeeperLogsDir = DefaultKafkaEnv + "/zookeeper/logs"
	// DefaultZookeeperDataDir zk数据目录
	DefaultZookeeperDataDir = DefaultKafkaEnv + "/zookeeper/data"
	// DefaultZookeeperConfDir zk配置文件目录
	DefaultZookeeperConfDir = DefaultKafkaEnv + "/zookeeper/conf"
	// DefaultZookeeperDynamicConf zk配置文件路径
	DefaultZookeeperDynamicConf = DefaultZookeeperConfDir + "/zoo.cfg.dynamic"
	// DefaultKafkaSupervisorConf supervisor配置目录
	DefaultKafkaSupervisorConf = DefaultKafkaEnv + "/supervisor/conf"
	// DefaultZookeeperVersion zk版本
	DefaultZookeeperVersion = "3.6.3"
	// DefaultZookeeperShell  zookeeper-shell.sh路径
	DefaultZookeeperShell = DefaultKafkaDir + "/bin/zookeeper-shell.sh"
	// DefaultTopicBin kafka-topics.sh路径
	DefaultTopicBin = DefaultKafkaDir + "/bin/kafka-topics.sh"
	// DefaultReassignPartitionsBin kafka-reassign-partitions.sh路径
	DefaultReassignPartitionsBin = DefaultKafkaDir + "/bin/kafka-reassign-partitions.sh"
	// Kafka0102 kafka 0.10.2
	Kafka0102 = "0.10.2"
	// PlanJSONFile kafka均衡计划路径
	PlanJSONFile = DefaultKafkaEnv + "/plan.json"
	// RollbackFile kafka均衡回退路径
	RollbackFile = DefaultKafkaEnv + "/rollback.json"
	// KafkaConfigFile kafka broker配置文件
	KafkaConfigFile = DefaultKafkaDir + "/config/server.properties"
	// KafkaTmpConfig 配置文件路径
	KafkaTmpConfig = "/tmp/server.properties"
	// KafkaZKPort zk默认端口
	KafkaZKPort = 2181
	// KafkaMaxHeap 最大堆内存单位MB
	KafkaMaxHeap = 30720
	// Kafka64GB 单位MB
	Kafka64GB = 61440
)
