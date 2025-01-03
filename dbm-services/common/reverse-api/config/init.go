package config

const CommonConfigDir = "/home/mysql/common_config"
const NginxProxyAddrsFileName = "nginx_proxy.list"
const ReverseApiBase = "apis/proxypass/reverse_api"

type ReverseApiName string

func (c ReverseApiName) String() string {
	return string(c)
}
