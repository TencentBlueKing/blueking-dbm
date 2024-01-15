package mongoprocess

// MongoProcess todo
type MongoProcess struct {
	Ip      string
	Port    int
	Pid     int
	DataDir string
}

// NewMongoProcess todo
func NewMongoProcess(ip string, port int) *MongoProcess {
	return &MongoProcess{
		Ip:      "",
		Port:    0,
		Pid:     0,
		DataDir: "",
	}
}

// Login todo
func (m *MongoProcess) Login(timeoutSecond int) error {
	return nil
}

// Start todo
func (m *MongoProcess) Start() error {
	return nil
}

// Stop todo
func (m *MongoProcess) Stop() error {
	return nil
}
