package components

import (
	"fmt"
	"path"
	"path/filepath"
	"regexp"
	"strings"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
)

// Medium 通用介质包处理
type Medium struct {
	Pkg    string `json:"pkg" validate:"required"`          // 安装包名
	PkgMd5 string `json:"pkg_md5"  validate:"required,md5"` // 安装包MD5
}

// Check TODO
func (m *Medium) Check() (err error) {
	var fileMd5 string
	// 判断安装包是否存在
	pkgAbPath := m.GetAbsolutePath()
	if !cmutil.FileExists(pkgAbPath) {
		return fmt.Errorf("%s不存在", pkgAbPath)
	}
	if fileMd5, err = util.GetFileMd5(pkgAbPath); err != nil {
		return fmt.Errorf("获取[%s]md5失败, %v", m.Pkg, err.Error())
	}
	// 校验md5
	if fileMd5 != m.PkgMd5 {
		return fmt.Errorf("安装包的md5不匹配,[%s]文件的md5[%s]不正确", fileMd5, m.PkgMd5)
	}
	return
}

// GetAbsolutePath 返回介质存放的绝对路径
func (m *Medium) GetAbsolutePath() string {
	return path.Join(cst.BK_PKG_INSTALL_PATH, m.Pkg)
}

// GePkgBaseName 例如将 mysql-5.7.20-linux-x86_64-tmysql-3.1.5-gcs.tar.gz
// 解析出 mysql-5.7.20-linux-x86_64-tmysql-3.1.5-gcs
// 用于做软连接使用
func (m *Medium) GePkgBaseName() string {
	pkgFullName := filepath.Base(m.GetAbsolutePath())
	return regexp.MustCompile("(.tar.gz|.tgz|.tar.xz)$").ReplaceAllString(pkgFullName, "")
}

// GetPkgTypeName 通过介质包文件名称获取对应的组件类型
// 比如  mysql-5.7.20-linux-x86_64-tmysql-3.1.5-gcs.tar.gz 解析成 mysql
// 比如  mariadb-10.3.7-linux-x86_64-tspider-3.7.8-gcs.tar.gz 解析成 mariadb
// tdbctl mysql-5.7.20-linux-x86_64-tdbctl-2.4.2.tar.gz
// 官方包名：mysql-8.0.32-linux-glibc2.12-x86_64.tar.xz mysql-5.7.42-linux-glibc2.12-x86_64.tar.gz
// txsql: mysql-txsql-8.0.30-12345678-linux-x86_64.tar.gz
func (m *Medium) GetPkgTypeName() string {
	if strings.Contains(m.Pkg, "tdbctl") {
		return cst.PkgTypeTdbctl
	} else if strings.Contains(m.Pkg, "tspider") {
		return cst.PkgTypeSpider
	} else if strings.HasPrefix(m.Pkg, "mysql-") {
		return cst.PkgTypeMysql
	} else {
		return strings.Split(m.Pkg, "-")[0]
	}
}
