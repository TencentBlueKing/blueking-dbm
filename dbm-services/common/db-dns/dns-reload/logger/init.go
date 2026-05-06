package logger

import (
	"dnsReload/config"
	"io"
	"io/ioutil"
	"log"
	"os"
	"path/filepath"
	"strconv"

	"gopkg.in/natefinch/lumberjack.v2"
)

var (
	Trace   *log.Logger
	Info    *log.Logger
	Warning *log.Logger
	Error   *log.Logger
)

// getConfigSafe 安全获取配置，不存在返回默认值
func getConfigSafe(key, defaultVal string) string {
	val := config.GetConfig(key)
	if val == "" || val == key { // 有些配置系统找不到会返回key本身
		return defaultVal
	}
	return val
}

// parseIntSafe 安全解析整数
func parseIntSafe(s string, defaultVal int) int {
	if i, err := strconv.Atoi(s); err == nil {
		return i
	}
	return defaultVal
}

// parseBoolSafe 安全解析布尔值
func parseBoolSafe(s string, defaultVal bool) bool {
	if b, err := strconv.ParseBool(s); err == nil {
		return b
	}
	return defaultVal
}

// InitLogger 初始化带轮转的日志
func InitLogger() {
	errorLogPath := config.GetConfig("error_log_path")
	infoLogPath := config.GetConfig("info_log_path")

	// 确保日志目录存在
	for _, path := range []string{errorLogPath, infoLogPath} {
		if dir := filepath.Dir(path); dir != "." {
			if err := os.MkdirAll(dir, 0755); err != nil {
				log.Fatalf("创建日志目录 %s 失败: %v", dir, err)
			}
		}
	}

	// 读取配置（不存在则使用默认值，不会报错）
	maxSize := parseIntSafe(getConfigSafe("log_max_size", "100"), 100)
	maxBackups := parseIntSafe(getConfigSafe("log_max_backups", "10"), 10)
	maxAge := parseIntSafe(getConfigSafe("log_max_age", "7"), 7)
	compress := parseBoolSafe(getConfigSafe("log_compress", "true"), true)
	toConsole := parseBoolSafe(getConfigSafe("log_to_console", "false"), false)

	// 创建写入器
	errorWriter := &lumberjack.Logger{
		Filename:   errorLogPath,
		MaxSize:    maxSize,
		MaxBackups: maxBackups,
		MaxAge:     maxAge,
		Compress:   compress,
		LocalTime:  true,
	}

	infoWriter := &lumberjack.Logger{
		Filename:   infoLogPath,
		MaxSize:    maxSize,
		MaxBackups: maxBackups,
		MaxAge:     maxAge,
		Compress:   compress,
		LocalTime:  true,
	}

	// 构建输出目标
	var errorDest io.Writer = errorWriter
	var infoDest io.Writer = infoWriter

	if toConsole {
		errorDest = io.MultiWriter(errorWriter, os.Stderr)
		infoDest = io.MultiWriter(infoWriter, os.Stdout)
	}

	// 初始化日志
	Trace = log.New(ioutil.Discard,
		"TRACE: ",
		log.Ldate|log.Ltime|log.Lshortfile)

	Info = log.New(infoDest,
		"INFO: ",
		log.Ldate|log.Ltime|log.Lshortfile)

	Warning = log.New(infoDest,
		"WARNING: ",
		log.Ldate|log.Ltime|log.Lshortfile)

	Error = log.New(errorDest,
		"ERROR: ",
		log.Ldate|log.Ltime|log.Lshortfile)
}
