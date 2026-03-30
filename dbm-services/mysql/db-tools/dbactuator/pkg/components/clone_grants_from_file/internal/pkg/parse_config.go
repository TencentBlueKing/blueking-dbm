package pkg

// UserEntry 保存从源文件中为某个 user@host 累积的创建信息。
type UserEntry struct {
	User, Host string
	Hash       string
	Resources  ResourceLimits
	Style      QuoteStyle
}

// ParseConfig 将 MySQL 和 Spider 的解析差异参数化。
type ParseConfig struct {
	// IsSystemUser 判断是否为系统用户，命中则写入 system_user 文件并跳过。
	IsSystemUser func(user, host string) bool

	// AddIfNotExists 给 CREATE USER 语句加上 IF NOT EXISTS。
	// MySQL 使用 /*!50706 IF NOT EXISTS */ hint 语法，Spider 使用直接语法。
	AddIfNotExists func(stmt string) string

	// BuildCreateFromEntry 根据累积的 UserEntry 生成 CREATE USER 语句（legacy 模式专用）。
	BuildCreateFromEntry func(e *UserEntry, dstVer int64) string

	// ExpandSuper 展开 GRANT 语句中的 SUPER 权限为细粒度权限。
	// MySQL 8.0 使用动态权限，Spider4 使用 MariaDB 权限。
	ExpandSuper func(stmt string, dstVer int64, w *Writers) error

	// RewritePrivs 在写入 grant 文件前对权限名做替换。
	// Spider 4 (MariaDB 10.5+) 将 REPLICATION CLIENT 改名为 BINLOG MONITOR 等。
	// MySQL 实现为 no-op。
	RewritePrivs func(stmt string, dstVer int64) string

	// StrictUnrecognized 遇到无法识别的语句时是否返回错误。
	// true = 返回 error（MySQL 行为），false = warn 并跳过（Spider 行为）。
	StrictUnrecognized bool
}
