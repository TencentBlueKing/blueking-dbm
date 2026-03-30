package importer

import (
	"dbm-services/common/go-pubpkg/logger"
	"fmt"

	_ "github.com/go-sql-driver/mysql"
	"github.com/jmoiron/sqlx"
)

// ImportFile 是 ImportFile 的核心实现，接受已建立的数据库连接
// 编排整体流程：校验进度 → 执行 SQL → 清理进度文件
func ImportFile(conn *sqlx.Conn, filePath string) error {
	// 校验进度，获取应跳过的行数和总行数
	lastDoneLine, totalLines, done, err := validateProgress(filePath)
	if err != nil {
		logger.Error("校验进度失败: %v", err)
		return err
	}
	logger.Info("校验进度成功 file=%s lastDoneLine=%d totalLines=%d", filePath, lastDoneLine, totalLines)
	if done {
		logger.Info("文件已导入完成，跳过 file=%s", filePath)
		return nil
	}

	// 输出工作摘要
	remaining := totalLines - lastDoneLine
	if lastDoneLine == 0 {
		logger.Info("开始导入 %s 共 %d 行", filePath, totalLines)
	} else {
		logger.Info("从断点恢复导入 %s 已完成 %d 行，剩余 %d 行", filePath, lastDoneLine, remaining)

	}

	// 逐行执行 SQL
	executed, lastLine, err := executeSQL(conn, filePath, lastDoneLine, totalLines)
	if err != nil {
		logger.Error("执行 SQL 失败: %v", err)
		return err
	}

	if err := removeProgress(filePath); err != nil {
		logger.Error("清理进度文件失败: %v", err)
		return fmt.Errorf("清理进度文件失败: %v", err)
	}

	logger.Info("导入完成 %s 共 %d 行, last line %d", filePath, executed, lastLine)
	return nil
}
