package importer

import (
	"context"
	"fmt"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/clone_grants_from_file/internal/pkg"

	"github.com/jmoiron/sqlx"
)

// validateProgress 校验进度文件的合法性
// 返回值：
//   - lastDoneLine: 上次成功执行的最后行号（0 表示从头开始）
//   - totalLines: SQL 文件总行数
//   - done: 如果为 true，表示所有行已在上次执行中完成，无需再执行
//   - err: 校验过程中的错误
func validateProgress(filePath string) (lastDoneLine int, totalLines int, done bool, err error) {
	lastDoneLine, err = readProgress(filePath)
	if err != nil {
		logger.Error("读取进度信息失败: %v", err)
		return 0, 0, false, fmt.Errorf("读取进度信息失败: %w", err)
	}
	logger.Info("读取进度信息成功 lastDoneLine=%d file=%s", lastDoneLine, filePath)

	totalLines, err = countLines(filePath)
	if err != nil {
		logger.Error("统计文件行数失败: %v", err)
		return 0, 0, false, fmt.Errorf("统计文件行数失败: %w", err)
	}
	logger.Info("统计文件行数成功 file=%s totalLines=%d", filePath, totalLines)

	if lastDoneLine == 0 {
		return 0, totalLines, false, nil
	}

	if lastDoneLine > totalLines {
		logger.Error(
			"进度文件记录的行号 %d 超出 SQL 文件实际行数 %d，进度文件与 SQL 文件不匹配",
			lastDoneLine, totalLines,
		)
		return 0, 0, false, fmt.Errorf(
			"进度文件记录的行号 %d 超出 SQL 文件实际行数 %d，进度文件与 SQL 文件不匹配",
			lastDoneLine, totalLines,
		)
	}

	if lastDoneLine == totalLines {
		logger.Info("所有行已在上次执行中完成，清理进度文件 file=%s", filePath)
		if err := removeProgress(filePath); err != nil {
			logger.Error("清理进度文件失败: %v", err)
			return 0, 0, false, fmt.Errorf("清理进度文件失败: %w", err)
		}
		logger.Info("清理进度文件成功 file=%s", filePath)
		return 0, totalLines, true, nil
	}

	logger.Info(
		"检测到进度文件，从断点恢复执行 file=%s lastDoneLine=%d totalLines=%d", filePath, lastDoneLine, totalLines,
	)

	return lastDoneLine, totalLines, false, nil
}

// executeSQL 逐行读取 SQL 文件并执行，跳过前 skipLines 行
// 每成功执行一行就持久化进度，遇到错误立即返回
// 返回值：
//   - executed: 本次执行成功的行数
//   - lastLine: 文件的最后行号
//   - err: 执行过程中的错误
func executeSQL(conn *sqlx.Conn, filePath string, skipLines int, totalLines int) (
	executed int, lastLine int, err error,
) {
	scanner, closeFile, openErr := pkg.OpenFileWithScanner(filePath)
	if openErr != nil {
		logger.Error("打开文件 %s 失败: %v", filePath, openErr)
		return 0, 0, fmt.Errorf("打开文件 %s 失败: %w", filePath, openErr)
	}
	defer closeFile()

	ls := pkg.NewLineScanner(scanner, filePath, totalLines)
	defer ls.Stop()

	for ls.Next() {
		if ls.LineNo() <= skipLines {
			continue
		}

		line := ls.Stmt()

		if _, execErr := conn.ExecContext(context.Background(), line); execErr != nil {
			logger.Error("执行第 %d 行失败: %v", ls.LineNo(), execErr)
			return executed, ls.LineNo(), fmt.Errorf("执行第 %d 行失败: %w\n语句: %s", ls.LineNo(), execErr, line)
		}

		if writeErr := writeProgress(filePath, ls.LineNo()); writeErr != nil {
			logger.Error("持久化进度失败（已成功执行到第 %d 行）: %v", ls.LineNo(), writeErr)
			return executed, ls.LineNo(), fmt.Errorf("持久化进度失败（已成功执行到第 %d 行）: %w", ls.LineNo(), writeErr)
		}

		executed++
	}

	if scanErr := ls.Err(); scanErr != nil {
		logger.Error("读取文件 %s 失败: %v", filePath, scanErr)
		return executed, ls.LineNo(), fmt.Errorf("读取文件 %s 失败: %w", filePath, scanErr)
	}

	return executed, ls.LineNo(), nil
}
