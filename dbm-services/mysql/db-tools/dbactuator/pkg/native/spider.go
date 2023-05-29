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
