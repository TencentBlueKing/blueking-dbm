package reportslowlog

var (
	TimePrefix              = []byte("# Time:")
	UserPrefix              = []byte("# User@Host:")
	QueryTimePrefix         = []byte("# Query_time:")
	SetTimestampPrefix      = []byte("SET timestamp=")
	SetTimestampPrefixUpper = []byte("SET TIMESTAMP=")
)

// 用于 use db 解析的前缀（大小写不敏感，需手动检查）
var (
	usePrefix = []byte("use ")
	UsePrefix = []byte("USE ")
)
