package native

// SpiderAdminDbWork TODO
type SpiderAdminDbWork struct {
	DbWorker
}

// ConnSpiderAdmin TODO
func (o InsObject) ConnSpiderAdmin() (*SpiderAdminDbWork, error) {
	dbwork, err := NewDbWorkerNoPing(o.spiderAdminTcpDsn(), o.User, o.Pwd)
	return &SpiderAdminDbWork{DbWorker: *dbwork}, err
}

// GetMasterSptRouters 获取主分片路由
func (t *DbWorker) GetMasterSptRouters() (servers []Server, err error) {
	err = t.Queryx(&servers, "select  * from  mysql.servers  where Wrapper='mysql'")
	return
}

// GetSlaveSptRouters 获取从分片路由
func (t *DbWorker) GetSlaveSptRouters() (servers []Server, err error) {
	err = t.Queryx(&servers, "select  * from  mysql.servers  where Wrapper='mysql_slave'")
	return
}
