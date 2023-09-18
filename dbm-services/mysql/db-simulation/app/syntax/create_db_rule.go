package syntax

// Checker TODO
func (c CreateDBResult) Checker(mysqlVersion string) (r *CheckerResult) {
	r = &CheckerResult{}
	// 检查库名规范
	// R.CreateTableRule.NormalizedName指明yaml文件中的键，根据键获得item 进而和 val比较
	etypesli, charsli := NameCheck(c.DbName, mysqlVersion)
	for i, etype := range etypesli {
		r.Parse(R.CreateTableRule.NormalizedName, etype, charsli[i])
	}
	return
}

// SpiderChecker TODO
func (c CreateDBResult) SpiderChecker(mysqlVersion string) (r *CheckerResult) {
	return c.Checker(mysqlVersion)
}
