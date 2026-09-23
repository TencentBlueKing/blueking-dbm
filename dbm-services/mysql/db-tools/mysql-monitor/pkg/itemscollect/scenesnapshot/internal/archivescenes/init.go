package archivescenes

import (
	"compress/gzip"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"time"

	"dbm-services/mysql/db-tools/mysql-monitor/pkg/config"
)

/*
快照归档目录结构, 时间信息全部编码在名字里:

	scenes/processlist.20000.20260923/20260923121345.gz
	       └── <场景>.<端口>.<日期>  └── <日期时间>.gz

清理时直接解析名字, 不去 stat 每个文件, 否则按 @every 1m 的频率,
单实例单场景一天就有 1440 个文件, 同机多实例时每轮要做几万次 lstat.
*/
const (
	dirDateLayout  = "20060102"
	fileTimeLayout = "20060102150405"
	fileNameExt    = ".gz"
)

// dirPrefix 归档目录前缀, 带上端口, 保证同机多实例互不干扰
func dirPrefix(name string) string {
	return fmt.Sprintf("%s.%d.", name, config.MonitorConfig.Port)
}

// DeleteOld 删除 name 相关的过期快照, 只保留最近 hours 小时
//
// 利用目录名里的日期做剪枝, 大部分目录连 ReadDir 都不需要:
//   - 日期早于 cutoff 那天: 整个目录都过期了, 直接删
//   - 日期等于 cutoff 那天: 只有这一个目录需要进去按文件名判断
//   - 日期晚于 cutoff 那天: 全部保留, 跳过
//
// 所以单轮开销是 1 次 ReadDir(basePath) + 最多 1 次 ReadDir(边界目录), 且没有 stat
func DeleteOld(name string, basePath string, hours int) error {
	if hours <= 0 {
		return nil
	}

	cutoff := time.Now().Add(-time.Duration(hours) * time.Hour)
	cutoffDate := cutoff.Format(dirDateLayout)
	prefix := dirPrefix(name)

	entries, err := os.ReadDir(basePath)
	if err != nil {
		if os.IsNotExist(err) {
			return nil
		}
		return err
	}

	for _, entry := range entries {
		if !entry.IsDir() || !strings.HasPrefix(entry.Name(), prefix) {
			continue
		}

		// 名字里解析不出日期的目录不敢动
		date := strings.TrimPrefix(entry.Name(), prefix)
		if _, err := time.Parse(dirDateLayout, date); err != nil {
			continue
		}

		// 定长零填充的日期, 字典序等价于时间序
		if date > cutoffDate {
			continue
		}

		dirPath := filepath.Join(basePath, entry.Name())
		if date < cutoffDate {
			if err := os.RemoveAll(dirPath); err != nil && !os.IsNotExist(err) {
				return err
			}
			continue
		}

		// date == cutoffDate, 这一天的文件有的过期有的没过期
		if err := deleteOldInDir(dirPath, cutoff); err != nil {
			return err
		}
	}

	return nil
}

// deleteOldInDir 按文件名时间删除目录下过期的快照, 目录删空后一并移除
func deleteOldInDir(dirPath string, cutoff time.Time) error {
	files, err := os.ReadDir(dirPath)
	if err != nil {
		if os.IsNotExist(err) {
			return nil
		}
		return err
	}

	remain := 0
	for _, f := range files {
		// 名字里解析不出时间的文件不敢动
		fileTime, err := time.ParseInLocation(
			fileTimeLayout,
			strings.TrimSuffix(f.Name(), fileNameExt),
			cutoff.Location(),
		)
		if err != nil || !fileTime.Before(cutoff) {
			remain++
			continue
		}

		if err := os.RemoveAll(filepath.Join(dirPath, f.Name())); err != nil && !os.IsNotExist(err) {
			return err
		}
	}

	if remain == 0 {
		if err := os.Remove(dirPath); err != nil && !os.IsNotExist(err) {
			return err
		}
	}

	return nil
}

func Write(name string, basePath string, content []byte) error {
	now := time.Now()

	archivePath := filepath.Join(
		basePath,
		dirPrefix(name)+now.Format(dirDateLayout),
	)

	err := os.MkdirAll(archivePath, 0777)
	if err != nil {
		return err
	}

	filePath := filepath.Join(archivePath, now.Format(fileTimeLayout)+fileNameExt)
	file, err := os.OpenFile(filePath, os.O_CREATE|os.O_RDWR, 0777)
	if err != nil {
		return err
	}
	defer func() {
		_ = file.Close()
	}()

	gw := gzip.NewWriter(file)
	_, err = gw.Write(content)
	if err != nil {
		return err
	}
	defer func() {
		_ = gw.Close()
	}()

	return nil
}
