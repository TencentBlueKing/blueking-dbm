package dbbackup_loader

type PhysicalRecover interface {
	PreRun() error
	PostRun() error
}

type TokudbRecover struct {
	*Xtrabackup
}

func (x *TokudbRecover) PreRun() error {
	return x.PreRun()
}

func (x *TokudbRecover) PostRun() error {
	return x.PostRun()
}
