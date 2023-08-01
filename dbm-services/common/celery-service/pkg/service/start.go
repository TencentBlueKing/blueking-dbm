package service

func Start(address string) error {
	Init()
	return r.Run(address)
}
