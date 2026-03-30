package spider

import (
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/clone_grants_from_file/internal/pkg"
	"fmt"
)

// processCreateUser 处理 CREATE USER 语句：Spider 节点原样输出，不加 IF NOT EXISTS。
// 返回 true 表示该语句已被处理。
func processCreateUser(stmt string, lastUser *string, userCount *int, w *pkg.Writers) (bool, error) {
	// 先尝试 modern 格式 (IDENTIFIED WITH 'plugin')，再尝试 legacy 格式 (IDENTIFIED BY PASSWORD)
	var user, host string
	if matches := pkg.ReCreateUser.FindStringSubmatch(stmt); matches != nil {
		user, host, _, _, _, _ = pkg.ExtractCreateUserFields(matches)
	} else if matches := pkg.ReCreateUserLegacy.FindStringSubmatch(stmt); matches != nil {
		user, host, _, _, _ = pkg.ExtractCreateUserLegacyFields(matches)
	} else if matches := pkg.ReCreateUserPlain.FindStringSubmatch(stmt); matches != nil {
		user, host, _, _ = pkg.ExtractCreateUserPlainFields(matches)
	} else {
		return false, nil
	}

	key := user + "@" + host

	if key != *lastUser {
		*userCount++
		*lastUser = key
	}

	if err := w.WriteCreate(fmt.Sprintf("%s;\n", stmt)); err != nil {
		logger.Error("process create user write create: %v", err)
		return true, err
	}
	logger.Info("parsed spider CREATE USER user=%s", key)
	return true, nil
}
