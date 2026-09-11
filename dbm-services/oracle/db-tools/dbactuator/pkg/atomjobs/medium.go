package atomjobs

import (
	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/oracle/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/oracle/db-tools/dbactuator/pkg/util"
	"fmt"
	"os/exec"
	"path"
)

// Medium 通用介质包处理
type Medium struct {
	Name string `json:"name" validate:"required"`     // 安装包名
	Md5  string `json:"md5"  validate:"required,md5"` // 安装包MD5
}

// Check TODO
func (m *Medium) Check() error {
	// 判断安装包是否存在
	pkgAbPath := m.GetAbsolutePath()
	if !cmutil.FileExists(pkgAbPath) {
		return fmt.Errorf("%s不存在", pkgAbPath)
	}
	md5, err := util.GetFileMd5(pkgAbPath)
	if err != nil {
		return fmt.Errorf("获取[%s]md5失败, %v", m.Name, err.Error())
	}
	if md5 != m.Md5 {
		return fmt.Errorf("安装包[%s]的md5是[%s],与期望的md5[%s]不符", pkgAbPath, md5, m.Md5)
	}
	return nil
}

// GetAbsolutePath 返回介质存放的绝对路径
func (m *Medium) GetAbsolutePath() string {
	return path.Join(cst.BK_PKG_INSTALL_PATH, m.Name)
}

// Unzip 解压介质包到 BK_PKG_INSTALL_PATH 目录
// 目前仅支持 .zip 格式（Oracle 官方安装包均为 zip）
func (m *Medium) Unzip() error {
	pkgAbPath := m.GetAbsolutePath()
	destDir := cst.BK_PKG_INSTALL_PATH
	// -o: 覆盖已存在文件不提示；-q: 静默模式
	cmd := exec.Command("unzip", "-o", "-q", pkgAbPath, "-d", destDir)
	output, err := cmd.CombinedOutput()
	if err != nil {
		return fmt.Errorf("解压[%s]到[%s]失败: %v, 输出: %s",
			pkgAbPath, destDir, err, string(output))
	}
	return nil
}

func (m *Medium) Untar() error {
	pkgAbPath := m.GetAbsolutePath()
	destDir := cst.BK_PKG_INSTALL_PATH
	// -o: 覆盖已存在文件不提示；-q: 静默模式
	cmd := exec.Command("tar", "-xvf", pkgAbPath, "-C", destDir)
	output, err := cmd.CombinedOutput()
	if err != nil {
		return fmt.Errorf("解压[%s]到[%s]失败: %v, 输出: %s",
			pkgAbPath, destDir, err, string(output))
	}
	return nil
}
