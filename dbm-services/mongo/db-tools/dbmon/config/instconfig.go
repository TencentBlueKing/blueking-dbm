package config

// InstConfigIdTypeAddr TODO
const InstConfigIdTypeAddr = "addr"

// InstConfigIdTypeCluster TODO
const InstConfigIdTypeCluster = "cluster"

// InstConfig 实例配置
// MongoDB同一机器上会有不同的集群的节点，需要有不同的配置
type InstConfig struct {
	Id      string // ip:port or hostname:port
	IdType  string // addr or cluster
	Segment string
	Prop    string
	Value   string
	Mtime   string
}

// InstConfigList TODO
type InstConfigList []InstConfig

// Len 用于排序
func (list *InstConfigList) Len() int {
	return len(*list)
}

// Get 获取配置，不存在返回nil
// addr 的配置优先级高于 cluster 的配置
func (list *InstConfigList) Get(cluster, addr, segment, key string) *InstConfig {
	var clusterConfig *InstConfig
	for _, c := range *list {
		if c.Id == addr && c.Segment == segment && c.Prop == key {
			return &c
		} else if c.Id == cluster && c.Segment == segment && c.Prop == key {
			clusterConfig = &c
		}
	}
	return clusterConfig
}
