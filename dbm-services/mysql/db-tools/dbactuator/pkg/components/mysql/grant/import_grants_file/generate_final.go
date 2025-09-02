package import_grants_file

import (
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql/grant/import_grants_file/internal/listener"
	"fmt"
	"os"
	"path/filepath"
	"slices"
	"strings"
)

func (c *ImportGrantsFile) GenerateFinalFile() (err error) {
	c.finalFilename = fmt.Sprintf("final-%s", c.Params.Filename)
	fp := filepath.Join(c.workDir, c.finalFilename)
	f, err := os.OpenFile(fp, os.O_WRONLY|os.O_CREATE|os.O_TRUNC, os.ModePerm)
	if err != nil {
		return err
	}
	defer func() {
		_ = f.Close()
	}()

	c.lineCount = 0
	for _, l := range c.finalListeners {
		var nonSysAuthOptions []*listener.AuthOptionStruct

		logger.Info("filter %s system users", l.ToSql())
		for _, ap := range l.AuthOptions {
			fullNameHost := strings.Trim(ap.Username, "'`") // 把两头可能的单引号去掉方便处理

			idx := slices.IndexFunc(c.Params.IgnoreUsers, func(iu string) bool {
				return strings.HasPrefix(fullNameHost, iu)
			})

			// 不是系统账号
			if idx < 0 {
				// 残留的 J_ 账号
				// 源 ip 在 ModifyPrivs 里已经提前修改为 dest ip 了
				if (strings.HasSuffix(fullNameHost, "@'localhost") ||
					strings.HasSuffix(fullNameHost, "@`localhost") ||
					strings.HasSuffix(fullNameHost, fmt.Sprintf("@'%s", c.destIp)) ||
					strings.HasSuffix(fullNameHost, fmt.Sprintf("@`%s", c.destIp))) &&
					strings.HasPrefix(fullNameHost, "J_") {
					logger.Info("maybe also system user: %s, ignored", fullNameHost)
				} else {
					logger.Info("local normal user: %s", fullNameHost)
					nonSysAuthOptions = append(nonSysAuthOptions, ap)
				}
			} else {
				logger.Info("%s will be ignored", fullNameHost)
			}
		}

		//系统账号不生成 sql
		if len(nonSysAuthOptions) <= 0 {
			logger.Info("whole %s ignored", l.ToSql())
			continue
		}

		l.AuthOptions = nonSysAuthOptions

		_, err = f.WriteString(strings.Trim(l.ToSql(), ";") + ";\n")
		if err != nil {
			return err
		}
		c.lineCount++
	}

	_, err = f.WriteString("FLUSH PRIVILEGES;\n")
	if err != nil {
		return err
	}
	c.lineCount++

	// 写完文件把内存释放掉
	c.finalListeners = nil
	return nil
}
