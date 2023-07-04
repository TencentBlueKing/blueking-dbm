package cst

import "time"

const (
	// Environment TODO
	Environment = "enviroment"
	// Test TODO
	Test = "test"
)

const (
	// TIMELAYOUT TODO
	TIMELAYOUT = "2006-01-02 15:04:05"
	// TIMELAYOUTSEQ TODO
	TIMELAYOUTSEQ = "2006-01-02_15:04:05"
	// TimeLayoutDir TODO
	TimeLayoutDir = "20060102150405"
)

const (
	// BK_PKG_INSTALL_PATH 默认文件下发路径
	BK_PKG_INSTALL_PATH = "/data/install"
)

// GetNowTimeLayoutStr 20060102150405
func GetNowTimeLayoutStr() string {
	return time.Now().Format(TimeLayoutDir)
}
