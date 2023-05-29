package log

import (
	"dbm-services/common/go-pubpkg/logger"
	"os"
	"path/filepath"
)

// InitLogger TODO
func InitLogger() error {
	executable, _ := os.Executable()
	executeDir := filepath.Dir(executable)
	if err := os.Chdir(executeDir); err != nil {
		os.Stderr.WriteString(err.Error())
		os.Exit(1)
	}
	logFileDir := filepath.Join(executeDir, "logs")
	_ = os.MkdirAll(logFileDir, 0755)
	fileName := filepath.Join(logFileDir, "rotatebinlog.log")
	fi, err := os.OpenFile(fileName, os.O_CREATE|os.O_APPEND|os.O_WRONLY, os.ModePerm)
	if err != nil {
		os.Stderr.WriteString(err.Error())
		os.Exit(1)
		// return errors.WithMessage(err, "init logger")
	}

	extMap := map[string]string{}
	l := logger.New(fi, true, logger.InfoLevel, extMap)
	logger.ResetDefault(l)
	logger.Sync()
	return nil
}
