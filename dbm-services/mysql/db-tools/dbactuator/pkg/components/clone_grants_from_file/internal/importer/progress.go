package importer

import (
	"bufio"
	"dbm-services/common/go-pubpkg/logger"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strconv"
	"strings"
)

// progressFilePath 返回 SQL 文件对应的进度文件路径
// 规则：SQL 文件路径 + ".progress" 后缀
func progressFilePath(sqlFilePath string) string {
	return sqlFilePath + ".progress"
}

// readProgress 读取进度文件，返回已成功执行的最后行号
// 如果进度文件不存在，返回 0（表示从头开始）
// 如果进度文件内容无法解析，返回明确的错误
func readProgress(sqlFilePath string) (int, error) {
	pf := progressFilePath(sqlFilePath)

	data, err := os.ReadFile(pf)
	if err != nil {
		if errors.Is(err, os.ErrNotExist) {
			return 0, nil
		}
		logger.Error("读取进度文件 %s 失败: %v", pf, err)
		return 0, fmt.Errorf("读取进度文件 %s 失败: %w", pf, err)
	}
	logger.Info("读取进度文件成功 pf=%s size=%d", pf, len(data))

	content := strings.TrimSpace(string(data))
	if content == "" {
		logger.Error("进度文件 %s 内容为空", pf)
		return 0, fmt.Errorf("进度文件 %s 内容为空", pf)
	}

	lineNo, err := strconv.Atoi(content)
	if err != nil {
		logger.Error("进度文件 %s 内容无法解析为行号: %q: %v", pf, content, err)
		return 0, fmt.Errorf("进度文件 %s 内容无法解析为行号: %q: %w", pf, content, err)
	}
	logger.Info("解析进度文件行号成功 pf=%s lineNo=%d", pf, lineNo)

	if lineNo < 0 {
		logger.Error("进度文件 %s 中的行号无效: %d", pf, lineNo)
		return 0, fmt.Errorf("进度文件 %s 中的行号无效: %d", pf, lineNo)
	}

	return lineNo, nil
}

// writeProgress 原子写入进度文件
// 先写入临时文件，再通过 os.Rename 原子替换，避免写入中途崩溃导致进度文件损坏
func writeProgress(sqlFilePath string, lineNo int) error {
	pf := progressFilePath(sqlFilePath)
	dir := filepath.Dir(pf)

	tmpFile, err := os.CreateTemp(dir, ".progress-tmp-*")
	if err != nil {
		logger.Error("创建临时进度文件失败: %v", err)
		return fmt.Errorf("创建临时进度文件失败: %w", err)
	}
	tmpPath := tmpFile.Name()

	_, writeErr := fmt.Fprintf(tmpFile, "%d\n", lineNo)
	closeErr := tmpFile.Close()

	if writeErr != nil {
		_ = os.Remove(tmpPath)
		logger.Error("写入临时进度文件失败: %v", writeErr)
		return fmt.Errorf("写入临时进度文件失败: %w", writeErr)
	}
	if closeErr != nil {
		_ = os.Remove(tmpPath)
		logger.Error("关闭临时进度文件失败: %v", closeErr)
		return fmt.Errorf("关闭临时进度文件失败: %w", closeErr)
	}

	if err := os.Rename(tmpPath, pf); err != nil {
		_ = os.Remove(tmpPath)
		logger.Error("原子替换进度文件失败: %v", err)
		return fmt.Errorf("原子替换进度文件失败: %w", err)
	}

	return nil
}

// removeProgress 删除进度文件
// 如果文件不存在，不返回错误
func removeProgress(sqlFilePath string) error {
	pf := progressFilePath(sqlFilePath)
	err := os.Remove(pf)
	if err != nil && !errors.Is(err, os.ErrNotExist) {
		logger.Error("删除进度文件 %s 失败: %v", pf, err)
		return fmt.Errorf("删除进度文件 %s 失败: %w", pf, err)
	}
	return nil
}

// countLines 统计文件的总行数
// 用于在恢复执行前校验进度文件中的行号是否超出 SQL 文件实际行数
func countLines(filePath string) (int, error) {
	f, err := os.Open(filePath)
	if err != nil {
		logger.Error("打开文件 %s 失败: %v", filePath, err)
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
		logger.Error("读取文件 %s 失败: %v", filePath, err)
		return 0, fmt.Errorf("读取文件 %s 失败: %w", filePath, err)
	}

	return count, nil
}
