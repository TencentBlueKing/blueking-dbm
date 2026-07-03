package saveproxyconnlog

import (
	"fmt"
	"log/slog"
	"os"
	"path/filepath"
	"strconv"
	"strings"

	"dbm-services/mysql/db-tools/mysql-monitor/pkg/config"
)

// offsetRegFile 返回 offset 注册文件路径
// 格式: {executable_dir}/connlog_offset.{port}.reg
func offsetRegFilePath() string {
	executable, _ := os.Executable()
	return filepath.Join(
		filepath.Dir(executable),
		fmt.Sprintf("connlog_offset.%d.reg", config.MonitorConfig.Port),
	)
}

// offsetData offset 文件中保存的数据
type offsetData struct {
	Offset int64  // 上次读取到的字节偏移量
	Inode  uint64 // 文件的 inode，用于检测文件是否被轮转替换
}

// loadOffset 从 reg 文件中加载上次保存的 offset
// 如果文件不存在（首次运行），返回 offset=0, inode=0
func loadOffset() offsetData {
	content, err := os.ReadFile(offsetRegFilePath())
	if err != nil {
		if os.IsNotExist(err) {
			slog.Info("offset reg file not found, first run")
			return offsetData{}
		}
		slog.Warn("read offset reg file failed", slog.String("error", err.Error()))
		return offsetData{}
	}

	parts := strings.SplitN(strings.TrimSpace(string(content)), ",", 2)
	if len(parts) < 2 {
		slog.Warn("invalid offset reg file format", slog.String("content", string(content)))
		return offsetData{}
	}

	offset, err := strconv.ParseInt(parts[0], 10, 64)
	if err != nil {
		slog.Warn("parse offset failed", slog.String("error", err.Error()))
		return offsetData{}
	}

	inode, err := strconv.ParseUint(parts[1], 10, 64)
	if err != nil {
		slog.Warn("parse inode failed", slog.String("error", err.Error()))
		return offsetData{}
	}

	slog.Info("loaded offset", slog.Int64("offset", offset), slog.Uint64("inode", inode))
	return offsetData{Offset: offset, Inode: inode}
}

// saveOffset 将当前 offset 和 inode 保存到 reg 文件
func saveOffset(data offsetData) error {
	content := fmt.Sprintf("%d,%d", data.Offset, data.Inode)
	err := os.WriteFile(offsetRegFilePath(), []byte(content), 0644)
	if err != nil {
		slog.Error("save offset reg file failed", slog.String("error", err.Error()))
		return err
	}
	slog.Info("saved offset", slog.Int64("offset", data.Offset), slog.Uint64("inode", data.Inode))
	return nil
}
