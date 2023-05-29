package components

import (
	"dbm-services/bigdata/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util"
	"fmt"
	"path"
	"path/filepath"
	"regexp"
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
	if !util.FileExists(pkgAbPath) {
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
	return regexp.MustCompile("(.tar.gz|.tgz)$").ReplaceAllString(pkgFullName, "")
}

// GePkgEsBaseName TODO
// Todo es包解析
func (m *Medium) GePkgEsBaseName() string {
	return regexp.MustCompile("(.tar.gz|.tgz)$").ReplaceAllString(m.Pkg, "")
}

// GePkgKafkaBaseName TODO
// Todo kafka包解析
func (m *Medium) GePkgKafkaBaseName() string {
	return ""
}

// GePkgHdfsBaseName TODO
// Todo hdfs包解析
func (m *Medium) GePkgHdfsBaseName() string {
	return ""
}
