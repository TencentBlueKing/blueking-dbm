package pkg

import (
	"bufio"
	"dbm-services/common/go-pubpkg/logger"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"
)

// OutputFiles 记录 ParseFile 生成的输出文件路径。
type OutputFiles struct {
	CreateUser string // CREATE USER 语句文件
	GrantPriv  string // GRANT 语句文件
	Combined   string // 合并的完整 SQL 文件
	SystemUser string // 系统用户语句文件
}

// Writers 封装解析过程中需要的输出 writer。
type Writers struct {
	CreateWriter        *bufio.Writer
	GrantWriter         *bufio.Writer
	TranslatedSqlWriter *bufio.Writer
	SystemUserWriter    *bufio.Writer
}

// WriteCreate 将 SQL 语句写入 CreateWriter 和 TranslatedSqlWriter。
func (w *Writers) WriteCreate(sql string) error {
	if _, err := w.CreateWriter.WriteString(sql); err != nil {
		return fmt.Errorf("write create sql: %w", err)
	}
	if _, err := w.TranslatedSqlWriter.WriteString(sql); err != nil {
		return fmt.Errorf("write translated sql: %w", err)
	}
	return nil
}

// WriteGrant 将 SQL 语句写入 GrantWriter 和 TranslatedSqlWriter。
func (w *Writers) WriteGrant(sql string) error {
	if _, err := w.GrantWriter.WriteString(sql); err != nil {
		return fmt.Errorf("write grant sql: %w", err)
	}
	if _, err := w.TranslatedSqlWriter.WriteString(sql); err != nil {
		return fmt.Errorf("write translated sql: %w", err)
	}
	return nil
}

// WriteSystemUser 将系统用户相关的 SQL 语句写入 SystemUserWriter。
func (w *Writers) WriteSystemUser(sql string) error {
	if _, err := w.SystemUserWriter.WriteString(sql); err != nil {
		return fmt.Errorf("write system user sql: %w", err)
	}
	return nil
}

// Flush 刷新所有 writer 的缓冲区。
func (w *Writers) Flush() error {
	if err := w.CreateWriter.Flush(); err != nil {
		return fmt.Errorf("flush create writer: %w", err)
	}
	if err := w.GrantWriter.Flush(); err != nil {
		return fmt.Errorf("flush grant writer: %w", err)
	}
	if err := w.TranslatedSqlWriter.Flush(); err != nil {
		return fmt.Errorf("flush translated sql writer: %w", err)
	}
	if err := w.SystemUserWriter.Flush(); err != nil {
		return fmt.Errorf("flush system user writer: %w", err)
	}
	return nil
}

// NewWriters 创建一组 Writers，写入指定的 io.Writer。
func NewWriters(createW, grantW, translatedW, systemUserW io.Writer) *Writers {
	return &Writers{
		CreateWriter:        bufio.NewWriter(createW),
		GrantWriter:         bufio.NewWriter(grantW),
		TranslatedSqlWriter: bufio.NewWriter(translatedW),
		SystemUserWriter:    bufio.NewWriter(systemUserW),
	}
}

// outputSuffix 根据源文件路径生成带后缀的输出文件路径。
// 始终返回绝对路径，避免下游依赖工作目录。
// 例如 /data/backup.sql + "create_user" → /data/backup.create_user.sql
func outputSuffix(srcPath, suffix string) string {
	absPath, _ := filepath.Abs(srcPath)
	dir := filepath.Dir(absPath)
	ext := filepath.Ext(absPath)
	base := strings.TrimSuffix(filepath.Base(absPath), ext)
	return filepath.Join(dir, base+"."+suffix+ext)
}

// OutputFilePaths 根据源文件路径计算所有输出文件的绝对路径，不创建文件。
func OutputFilePaths(srcPath string) OutputFiles {
	return OutputFiles{
		CreateUser: outputSuffix(srcPath, "create_user"),
		GrantPriv:  outputSuffix(srcPath, "grant_priv"),
		Combined:   outputSuffix(srcPath, "combined"),
		SystemUser: outputSuffix(srcPath, "system_user"),
	}
}

// CreateOutputFiles 根据源文件路径创建输出文件，返回 Writers、OutputFiles 和关闭函数。
// 调用方必须在使用完毕后先调用 Writers.Flush()，再调用 closeFunc 关闭文件。
func CreateOutputFiles(srcPath string) (w *Writers, out OutputFiles, closeFunc func(), err error) {
	out.CreateUser = outputSuffix(srcPath, "create_user")
	out.GrantPriv = outputSuffix(srcPath, "grant_priv")
	out.Combined = outputSuffix(srcPath, "combined")
	out.SystemUser = outputSuffix(srcPath, "system_user")

	var files []*os.File

	closeAll := func() {
		for _, f := range files {
			_ = f.Close()
		}
	}

	createFp, e := os.Create(out.CreateUser)
	if e != nil {
		err = fmt.Errorf("create output file %s: %w", out.CreateUser, e)
		return
	}
	files = append(files, createFp)

	grantFp, e := os.Create(out.GrantPriv)
	if e != nil {
		closeAll()
		err = fmt.Errorf("create output file %s: %w", out.GrantPriv, e)
		return
	}
	files = append(files, grantFp)

	combinedFp, e := os.Create(out.Combined)
	if e != nil {
		closeAll()
		err = fmt.Errorf("create output file %s: %w", out.Combined, e)
		return
	}
	files = append(files, combinedFp)

	systemUserFp, e := os.Create(out.SystemUser)
	if e != nil {
		closeAll()
		err = fmt.Errorf("create output file %s: %w", out.SystemUser, e)
		return
	}
	files = append(files, systemUserFp)

	w = NewWriters(createFp, grantFp, combinedFp, systemUserFp)
	closeFunc = closeAll
	return
}

// CountFileLines 统计文件的行数。
func CountFileLines(filePath string) (int, error) {
	f, err := os.Open(filePath)
	if err != nil {
		return 0, fmt.Errorf("打开文件 %s 失败: %w", filePath, err)
	}
	defer func() {
		_ = f.Close()
	}()

	scanner := bufio.NewScanner(f)
	scanner.Buffer(make([]byte, 0, 1024*1024), 1024*1024)

	count := 0
	for scanner.Scan() {
		count++
	}

	if err := scanner.Err(); err != nil {
		return 0, fmt.Errorf("读取文件 %s 失败: %w", filePath, err)
	}

	return count, nil
}

// LogOutputSummary 统计并输出所有结果文件的行数摘要。
func LogOutputSummary(out OutputFiles) error {
	for _, item := range []struct {
		name string
		path string
	}{
		{"create_user", out.CreateUser},
		{"grant_priv", out.GrantPriv},
		{"combined", out.Combined},
		{"system_user", out.SystemUser},
	} {
		lines, err := CountFileLines(item.path)
		if err != nil {
			logger.Error("统计输出文件行数失败 file=%s error=%v", item.path, err)
			return err
		}
		logger.Info("type=%s file=%s lines=%d", item.name, item.path, lines)
	}

	return nil
}
