package mysql

import (
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/clone_grants_from_file/internal"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/clone_grants_from_file/internal/pkg"
	"fmt"
)

// ParseFile 读取 SQL 备份文件，根据源版本分发到对应的解析函数。
// <= 56 使用 ParseLegacyFile，>= 57 使用 ParseModernFile。
// 输出文件与源文件同目录，文件名基于源文件名添加后缀。
// 返回生成的输出文件路径信息。
func ParseFile(
	path string, srcVer, dstVer int64, sourceIP, targetIP string, dynamicSystemUsers []string,
) (pkg.OutputFiles, error) {
	systemUsers := pkg.BuildSystemUserMap(internal.StaticSystemUsers, dynamicSystemUsers)

	totalLines, err := pkg.CountFileLines(path)
	if err != nil {
		logger.Error("统计源文件行数失败: %v", err)
		return pkg.OutputFiles{}, fmt.Errorf("统计源文件行数失败: %w", err)
	}
	logger.Info("file=%s totalLines=%d srcVer=%d dstVer=%d", path, totalLines, srcVer, dstVer)

	w, out, closeFiles, err := pkg.CreateOutputFiles(path)
	if err != nil {
		logger.Error("CreateOutputFiles: %v", err)
		return pkg.OutputFiles{}, err
	}
	defer closeFiles()

	scanner, closeFile, err := pkg.OpenFileWithScanner(path)
	if err != nil {
		logger.Error("OpenFileWithScanner: %v", err)
		return pkg.OutputFiles{}, err
	}
	defer closeFile()

	replacer := pkg.NewHostReplacer(sourceIP, targetIP)

	cfg := &pkg.ParseConfig{
		IsSystemUser: func(user, host string) bool {
			return pkg.IsSystemOrJobUser(user, host, sourceIP, systemUsers)
		},
		AddIfNotExists:       AddIfNotExistsHint,
		BuildCreateFromEntry: BuildCreateFromEntryMySQL,
		ExpandSuper:          expandSuperPrivilege,
		RewritePrivs:         rewritePrivsNoop,
		StrictUnrecognized:   true,
	}

	if srcVer < 5007000 {
		err = ParseLegacyFile(scanner, path, totalLines, dstVer, replacer, cfg, w)
	} else {
		err = ParseModernFile(scanner, path, totalLines, dstVer, replacer, cfg, w)
	}
	if err != nil {
		logger.Error("parse backup file: %v", err)
		return pkg.OutputFiles{}, err
	}

	if err := w.Flush(); err != nil {
		logger.Error("flush output: %v", err)
		return pkg.OutputFiles{}, fmt.Errorf("flush output: %w", err)
	}

	err = pkg.LogOutputSummary(out)
	if err != nil {
		return pkg.OutputFiles{}, err
	}

	return out, nil
}
