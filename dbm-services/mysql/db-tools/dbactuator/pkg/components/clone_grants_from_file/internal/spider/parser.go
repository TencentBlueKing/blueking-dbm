package spider

import (
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/clone_grants_from_file/internal"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/clone_grants_from_file/internal/mysql"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/clone_grants_from_file/internal/pkg"
	"fmt"
)

// ParseFile 解析 Spider 节点的 SQL 备份文件，复用 MySQL 的 legacy/modern 解析逻辑。
//
// Spider 1 = legacy（只有 GRANT 语句），Spider 3/4 = modern（有 CREATE USER + GRANT）。
// 与 MySQL 的差异通过 ParseConfig 注入：
//   - IF NOT EXISTS 使用直接语法（非 hint）
//   - SUPER 展开使用 MariaDB 权限（仅 Spider 4）
//   - 系统用户只按用户名判断（不检查 host/sourceIP）
//   - 未识别语句 warn 跳过（不报错）
func ParseFile(
	path string, srcVer, dstVer int64, sourceIP, targetIP string, dynamicSystemUsers []string,
) (pkg.OutputFiles, error) {
	systemUsers := pkg.BuildSystemUserMap(internal.StaticSystemUsers, dynamicSystemUsers)

	totalLines, err := pkg.CountFileLines(path)
	if err != nil {
		logger.Error("count source file lines: %v", err)
		return pkg.OutputFiles{}, fmt.Errorf("统计源文件行数失败: %w", err)
	}
	logger.Info("开始解析 Spider 备份文件 file=%s totalLines=%d srcVer=%d dstVer=%d", path, totalLines, srcVer, dstVer)

	w, out, closeFiles, err := pkg.CreateOutputFiles(path)
	if err != nil {
		logger.Error("create output files: %v", err)
		return pkg.OutputFiles{}, err
	}
	defer closeFiles()

	scanner, closeFile, err := pkg.OpenFileWithScanner(path)
	if err != nil {
		logger.Error("open file with scanner: %v", err)
		return pkg.OutputFiles{}, err
	}
	defer closeFile()

	replacer := pkg.NewHostReplacer(sourceIP, targetIP)

	cfg := &pkg.ParseConfig{
		IsSystemUser: func(user, host string) bool {
			_, ok := systemUsers[user]
			return ok
		},
		AddIfNotExists:       mysql.AddIfNotExistsDirect,
		BuildCreateFromEntry: buildCreateFromEntrySpider,
		ExpandSuper:          expandSuperForSpider4,
		RewritePrivs:         rewritePrivsForSpider,
		StrictUnrecognized:   false,
	}

	if srcVer < 2000000 {
		err = mysql.ParseLegacyFile(scanner, path, totalLines, dstVer, replacer, cfg, w)
	} else {
		err = mysql.ParseModernFile(scanner, path, totalLines, dstVer, replacer, cfg, w)
	}
	if err != nil {
		logger.Error("parse spider backup file: %v", err)
		return pkg.OutputFiles{}, err
	}

	if err := w.Flush(); err != nil {
		logger.Error("flush output: %v", err)
		return pkg.OutputFiles{}, fmt.Errorf("flush output: %w", err)
	}

	logger.Info("Spider 解析完成")
	err = pkg.LogOutputSummary(out)
	if err != nil {
		return pkg.OutputFiles{}, err
	}

	return out, nil
}

// buildCreateFromEntrySpider 根据累积的 UserEntry 信息生成 Spider 的 CREATE USER 语句。
//
// Spider 1 目标：GRANT USAGE 载体格式（兼容 Spider 1）。
// Spider 3/4 目标：CREATE USER IF NOT EXISTS（直接语法，无 hint）。
func buildCreateFromEntrySpider(e *pkg.UserEntry, dstVer int64) string {
	withClause := e.Resources.FormatWithClause()

	if dstVer < 2000000 {
		if e.Hash != "" {
			return fmt.Sprintf("GRANT USAGE ON *.* TO '%s'@'%s' IDENTIFIED BY PASSWORD '%s'%s;\n",
				e.User, e.Host, e.Hash, withClause)
		}
		return fmt.Sprintf("GRANT USAGE ON *.* TO '%s'@'%s'%s;\n",
			e.User, e.Host, withClause)
	}

	if e.Hash != "" {
		return fmt.Sprintf("CREATE USER IF NOT EXISTS '%s'@'%s' IDENTIFIED BY PASSWORD '%s'%s;\n",
			e.User, e.Host, e.Hash, withClause)
	}
	return fmt.Sprintf("CREATE USER IF NOT EXISTS '%s'@'%s'%s;\n",
		e.User, e.Host, withClause)
}
