package checker

import (
	"context"
	"fmt"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/clone_grants_from_file/internal/pkg"

	"github.com/jmoiron/sqlx"
)

// VerifyCreateUserFile 逐行读取 create_user 文件，验证每个账号在目标 DB 上存在且密码和资源限制一致。
// 与 PreCheckCreateUserFile 的区别：账号不存在也算 mismatch（导入后必须都在）。
func VerifyCreateUserFile(conn *sqlx.Conn, filePath string, dstVer int64) error {
	scanner, closeFile, err := pkg.OpenFileWithScanner(filePath)
	if err != nil {
		logger.Error("open create user file %s: %v", filePath, err)
		return fmt.Errorf("open create user file: %w", err)
	}
	defer closeFile()

	ls := pkg.NewLineScanner(scanner, filePath, 0)
	defer ls.Stop()
	ctx := context.Background()
	var mismatches []string

	for ls.Next() {
		line := ls.Stmt()

		exists, pwMatch, rlMatch, checkErr := CheckAccountOnTarget(ctx, conn, line, dstVer)
		if checkErr != nil {
			logger.Error("verify line %d: %v", ls.LineNo(), checkErr)
			return fmt.Errorf("query error at line %d: %w", ls.LineNo(), checkErr)
		}

		if !exists {
			mismatches = append(mismatches, fmt.Sprintf("line %d: account not found stmt=%s", ls.LineNo(), line))
			continue
		}

		if !pwMatch || !rlMatch {
			mismatches = append(mismatches, fmt.Sprintf("line %d: passwordMatch=%t resourceMatch=%t stmt=%s", ls.LineNo(), pwMatch, rlMatch, line))
		}
	}

	if err := ls.Err(); err != nil {
		logger.Error("reading create user file: %v", err)
		return fmt.Errorf("reading create user file: %w", err)
	}

	if len(mismatches) > 0 {
		for _, m := range mismatches {
			logger.Error("verify mismatch: %s", m)
		}
		return fmt.Errorf("verify failed: %d accounts missing or mismatched", len(mismatches))
	}

	logger.Info("verify create user passed, total lines=%d", ls.LineNo())
	return nil
}
