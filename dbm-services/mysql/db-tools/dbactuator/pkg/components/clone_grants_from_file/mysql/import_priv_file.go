package mysql

import (
	"context"
	"fmt"
	"io"
	"os"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/clone_grants_from_file/internal/checker"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/clone_grants_from_file/internal/importer"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/clone_grants_from_file/internal/mysql"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/clone_grants_from_file/internal/pkg"

	_ "github.com/go-sql-driver/mysql" // mysql 驱动

	"github.com/jmoiron/sqlx"
)

type ImportPrivFileParam struct {
	SystemUsers        []string `json:"system_users"`
	SourceIP           string   `json:"source_ip"`
	SourcePort         int      `json:"source_port"`
	SourceRawVersion   string   `json:"source_raw_version"`
	SourcePrivFilePath string   `json:"source_priv_file_path"`
	TargetIP           string   `json:"target_ip"`
	TargetPort         int      `json:"target_port"`
	IsSpider           bool     `json:"is_spider"`
	//SpiderSkipUser     string   `json:"spider_skip_user"`
}

type importPrivFileCtx struct {
	targetDB             *sqlx.DB
	targetConn           *sqlx.Conn
	srcVer               int64
	dstVer               int64
	sourcePrivFileCpPath string
}
type ImportPrivFileComponent struct {
	GeneralParam *components.GeneralParam `json:"general"`
	Param        *ImportPrivFileParam     `json:"extend"`
	importPrivFileCtx
}

func (c *ImportPrivFileComponent) Init() error {
	db, err := sqlx.Connect(
		"mysql",
		fmt.Sprintf(
			"%s:%s@tcp(%s:%d)/",
			c.GeneralParam.RuntimeAccountParam.AdminUser,
			c.GeneralParam.RuntimeAccountParam.AdminPwd,
			c.Param.TargetIP,
			c.Param.TargetPort,
		),
	)
	if err != nil {
		logger.Error("connect target mysql %s:%d err: %v", c.Param.TargetIP, c.Param.TargetPort, err)
		return err
	}
	logger.Info("connect target mysql %s:%d success", c.Param.TargetIP, c.Param.TargetPort)

	c.targetDB = db

	if err := c.initConn(); err != nil {
		logger.Error("get conn from target mysql %s:%d err: %v", c.Param.TargetIP, c.Param.TargetPort, err)
		return err
	}

	if err := c.parseVersion(); err != nil {
		logger.Error("parse version err: %v", err)
		return err
	}

	if err := c.copySourcePrivFile(); err != nil {
		logger.Error("copy source priv file err: %v", err)
		return err
	}
	return nil
}

func (c *ImportPrivFileComponent) initConn() error {
	conn, err := c.targetDB.Connx(context.Background())
	if err != nil {
		logger.Error("get connect from target mysql err: %v", err)
		return err
	}
	logger.Info("get connect from target mysql success")

	_, err = conn.ExecContext(context.Background(), `SET SESSION sql_log_bin = 0`)
	if err != nil {
		logger.Error("set sql_log_bin = 0 err: %v", err)
		_ = conn.Close()
		return err
	}
	logger.Info("set sql_log_bin = 0 success")
	c.targetConn = conn
	return nil
}

func (c *ImportPrivFileComponent) parseVersion() error {
	// 在 target 执行 select @@Version
	var rawVersion string
	if err := c.targetDB.Get(&rawVersion, "SELECT @@VERSION"); err != nil {
		logger.Error("get target raw version err: %v", err)
		return err
	}
	logger.Info("target raw version: %s", rawVersion)

	// 解析版本号
	if c.Param.IsSpider {
		c.dstVer = int64(cmutil.SpiderVersionParse(rawVersion))
		c.srcVer = int64(cmutil.SpiderVersionParse(c.Param.SourceRawVersion))
	} else {
		c.dstVer = int64(cmutil.MySQLVersionParse(rawVersion))
		c.srcVer = int64(cmutil.MySQLVersionParse(c.Param.SourceRawVersion))
	}

	logger.Info("source version: %d, target version: %d", c.srcVer, c.dstVer)
	return nil
}

// 把 sourcePrivFilePath 复制到当前路径下
func (c *ImportPrivFileComponent) copySourcePrivFile() error {
	sourceFile := c.Param.SourcePrivFilePath
	sourceFileCp := fmt.Sprintf(
		`./%s_%d_%s_%d.priv`,
		c.Param.SourceIP, c.Param.SourcePort, c.Param.TargetIP, c.Param.TargetPort,
	)

	// 打开源文件
	src, err := os.Open(sourceFile)
	if err != nil {
		logger.Error("open source file %s err: %v", sourceFile, err)
		return err
	}
	defer func() {
		_ = src.Close()
	}()

	// 创建目标文件
	dst, err := os.Create(sourceFileCp)
	if err != nil {
		logger.Error("create destination file %s err: %v", sourceFileCp, err)
		return err
	}
	defer func() {
		_ = dst.Close()
	}()

	// 复制文件内容
	if _, err := io.Copy(dst, src); err != nil {
		logger.Error("copy file from %s to %s err: %v", sourceFile, sourceFileCp, err)
		return err
	}
	// log warn 便于看到是在处理那个 priv 权限文件
	logger.Warn("copied file from %s to %s", sourceFile, sourceFileCp)

	c.sourcePrivFileCpPath = sourceFileCp
	return nil
}

func (c *ImportPrivFileComponent) ParseFile() (err error) {
	if c.Param.IsSpider {
		err := fmt.Errorf("ParseFile called with wrong IsSpider flag, mysql expects IsSpider=false, spider expects IsSpider=true")
		logger.Error(err.Error())
		return err
	}

	_, err = mysql.ParseFile(
		c.sourcePrivFileCpPath,
		c.srcVer,
		c.dstVer,
		c.Param.SourceIP,
		c.Param.TargetIP,
		c.Param.SystemUsers,
	)

	if err != nil {
		logger.Error("parse grants file err: %v", err)
		return err
	}

	return nil
}

func (c *ImportPrivFileComponent) flushPrivileges() {
	if _, err := c.targetConn.ExecContext(context.Background(), "FLUSH PRIVILEGES"); err != nil {
		logger.Error("flush privileges err: %v", err)
	} else {
		logger.Info("flush privileges success")
	}
}

func (c *ImportPrivFileComponent) PreCheckCreateUser() error {
	outFiles := pkg.OutputFilePaths(c.sourcePrivFileCpPath)
	if err := checker.PreCheckCreateUserFile(c.targetConn, outFiles.CreateUser, c.dstVer); err != nil {
		logger.Error("pre-check create user file %s err: %v", outFiles.CreateUser, err)
		return err
	}

	logger.Info("pre-check create user file success")
	return nil
}

func (c *ImportPrivFileComponent) ImportCreateUserFile() error {
	defer c.flushPrivileges()

	outFiles := pkg.OutputFilePaths(c.sourcePrivFileCpPath)
	if err := importer.ImportFile(c.targetConn, outFiles.CreateUser); err != nil {
		logger.Error("import file %s err: %v", outFiles.CreateUser, err)
		return err
	}

	logger.Info("import create user file success")
	return nil
}

func (c *ImportPrivFileComponent) ImportGrantPrivFile() error {
	defer c.flushPrivileges()

	outFiles := pkg.OutputFilePaths(c.sourcePrivFileCpPath)
	if err := importer.ImportFile(c.targetConn, outFiles.GrantPriv); err != nil {
		logger.Error("import file %s err: %v", outFiles.GrantPriv, err)
		return err
	}

	logger.Info("import grant priv file success")
	return nil
}

func (c *ImportPrivFileComponent) VerifyCreateUser() error {
	outFiles := pkg.OutputFilePaths(c.sourcePrivFileCpPath)
	if err := checker.VerifyCreateUserFile(c.targetConn, outFiles.CreateUser, c.dstVer); err != nil {
		logger.Error("verify create user file %s err: %v", outFiles.CreateUser, err)
		return err
	}

	logger.Info("verify create user file success")
	return nil
}

func (c *ImportPrivFileComponent) VerifyGrantPriv() error {
	outFiles := pkg.OutputFilePaths(c.sourcePrivFileCpPath)
	if err := checker.VerifyGrantPrivFile(c.targetConn, outFiles.GrantPriv, c.dstVer); err != nil {
		logger.Error("verify grant priv file %s err: %v", outFiles.GrantPriv, err)
		return err
	}

	logger.Info("verify grant priv file success")
	return nil
}

func (c *ImportPrivFileComponent) SrcVer() int64                { return c.srcVer }
func (c *ImportPrivFileComponent) DstVer() int64                { return c.dstVer }
func (c *ImportPrivFileComponent) SourcePrivFileCpPath() string { return c.sourcePrivFileCpPath }

func (c *ImportPrivFileComponent) Example() interface{} {
	return ImportPrivFileComponent{
		Param: &ImportPrivFileParam{
			SystemUsers:        []string{"fake_admin"},
			SourceIP:           "1.1.1.1",
			SourcePort:         1234,
			SourceRawVersion:   "5.5.24-tmysql-1.6-log",
			SourcePrivFilePath: "/path/to/file",
			TargetIP:           "2.2.2.2",
			TargetPort:         2345,
			IsSpider:           false,
		},
	}
}
