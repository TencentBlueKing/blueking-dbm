package logger

import (
	"dnsReload/config"
	"io"
	"io/ioutil"
	"log"
	"os"
)

// 初始化日志
var (
	Trace   *log.Logger
	Info    *log.Logger
	Warning *log.Logger
	Error   *log.Logger
)

// InitLogger TODO
func InitLogger() {
	errFile, err := os.OpenFile(config.GetConfig("error_log_path"),
		os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0666)
	if err != nil {
		log.Fatalln("Failed to open error log file:", err)
	}

	Trace = log.New(ioutil.Discard,
		"TRACE: ",
		log.Ldate|log.Ltime|log.Lshortfile)

	Info = log.New(os.Stdout,
		"INFO: ",
		log.Ldate|log.Ltime|log.Lshortfile)

	Warning = log.New(os.Stdout,
		"WARNING: ",
		log.Ldate|log.Ltime|log.Lshortfile)

	Error = log.New(io.MultiWriter(errFile),
		"ERROR: ",
		log.Ldate|log.Ltime|log.Lshortfile)
}
