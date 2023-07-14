package mysqlcomm

// GetTdbctlPortBySpider 根据 spider master 端口，获取 tdbctl 端口
// tdbctl port = spider_port + 1000
func GetTdbctlPortBySpider(spiderPort int) int {
	return spiderPort + 1000
}
