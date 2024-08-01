package service

// GetPrivPara 查询权限的入参
type GetPrivPara struct {
	Ips           []string `json:"ips"`
	ImmuteDomains []string `json:"immute_domains"`
	Users         []string `json:"users"`
	Dbs           []string `json:"dbs"`
	ClusterType   *string  `json:"cluster_type"`
	Format        string   `json:"format"`
}

// GrantInfo 查询到的权限信息
type GrantInfo struct {
	Ip           string   `json:"ip"`
	MatchIp      string   `json:"match_ip"`
	ImmuteDomain string   `json:"immute_domain"`
	User         string   `json:"user"`
	Privs        []DbPriv `json:"privs"`
}

// DbPriv db上的权限信息
type DbPriv struct {
	MatchDb string `json:"match_db"` // 实例中匹配的db
	Db      string `json:"db"`       // 目标查询的db
	Priv    string `json:"priv"`     // 权限
}

// RelatedIp 以client ip聚合展示
type RelatedIp struct {
	Ip  string      `json:"ip"`  // client ip
	Dbs []RelatedDb `json:"dbs"` // 目标db列表，以及匹配哪些权限
}

type RelatedDb struct {
	Db      string          `json:"db"`      // 目标db
	Domains []RelatedDomain `json:"domains"` // 目标域名列表，以及匹配哪些权限
}
type RelatedDomain struct {
	ImmuteDomain string        `json:"immute_domain"` // 目标域名
	Users        []RelatedUser `json:"users"`         // 目标db列表，以及匹配哪些权限
}

type RelatedUser struct {
	User     string           `json:"user"`      // 目标user（即匹配的user)
	MatchIps []RelatedMatchIp `json:"match_ips"` // 匹配的ip列表
}

type RelatedMatchIp struct {
	MatchIp  string           `json:"match_ip"`  // 匹配的ip
	MatchDbs []RelatedMatchDb `json:"match_dbs"` // 匹配的db列表
}

type RelatedMatchDb struct {
	MatchDb string `json:"match_db"` // 匹配的db
	Priv    string `json:"priv"`     // 权限
}

// RelatedDomain2 以域名聚合展示
type RelatedDomain2 struct {
	ImmuteDomain string         `json:"immute_domain"` // 目标域名
	Users        []RelatedUser2 `json:"users"`         // 目标db列表，以及匹配哪些权限
}

type RelatedUser2 struct {
	User     string            `json:"user"`      // 目标user（即匹配的user)
	MatchIps []RelatedMatchIp2 `json:"match_ips"` // 匹配的ip列表
}

type RelatedMatchIp2 struct {
	MatchIp  string            `json:"match_ip"`  // 匹配的ip
	MatchDbs []RelatedMatchDb2 `json:"match_dbs"` // 匹配的db列表
}

type RelatedMatchDb2 struct {
	MatchDb string        `json:"match_db"` // 匹配的db
	Priv    string        `json:"priv"`     // 权限
	IpDbs   []RelatedIpDb `json:"ip_dbs"`   // client ip 和 目标db
}

type RelatedIpDb struct {
	Ip string `json:"ip"` // client ip
	Db string `json:"db"` // 目标db
}
