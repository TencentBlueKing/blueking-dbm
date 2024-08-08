package rename_dbs

import (
	"bufio"
	"bytes"
	"context"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/rename_dbs/pkg"
	"fmt"
	"os"
	"os/exec"
	"strings"

	_ "github.com/go-sql-driver/mysql" // mysql 驱动

	"github.com/jmoiron/sqlx"
)

type ViaCtlParam struct {
	Host     string          `json:"host" valid:"required, ip"`
	Port     int             `json:"port" valid:"required"`
	Requests []renameRequest `json:"requests" valid:"required"`
}

type ViaCtlComponent struct {
	GeneralParam *components.GeneralParam `json:"general"`
	Param        *ViaCtlParam             `json:"extend"`
	viaCtlCtx
}

type viaCtlCtx struct {
	dbConn   *sqlx.Conn
	dbTables map[string][]string
	uid      string
}

func (c *ViaCtlComponent) Init(uid string) error {
	db, err := sqlx.Connect(
		"mysql",
		fmt.Sprintf("%s:%s@tcp(%s:%d)/",
			c.GeneralParam.RuntimeAccountParam.AdminUser, c.GeneralParam.RuntimeAccountParam.AdminPwd,
			c.Param.Host, c.Param.Port,
		),
	)
	if err != nil {
		return err
	}

	conn, err := db.Connx(context.Background())
	if err != nil {
		return err
	}
	c.dbConn = conn

	c.uid = uid
	c.dbTables = make(map[string][]string)
	return nil
}

func (c *ViaCtlComponent) ListTables() error {
	for _, req := range c.Param.Requests {
		tables, err := pkg.ListDBTables(c.dbConn, req.FromDatabase)
		if err != nil {
			logger.Error("list tables failed: %s", err.Error())
			return err
		}
		logger.Info("list tables: %v", tables)
		c.dbTables[req.FromDatabase] = tables
	}
	logger.Info("list all tables: %v", c.dbTables)
	return nil
}

func (c *ViaCtlComponent) CreateToDB() error {
	for _, req := range c.Param.Requests {
		err := pkg.CreateDB(c.dbConn, req.ToDatabase)
		if err != nil {
			logger.Error("create db: %s failed: %s", req.ToDatabase, err.Error())
			return err
		}
		logger.Info("create db: %s success", req.ToDatabase)
	}
	logger.Info("create all to db success")
	return nil
}

func (c *ViaCtlComponent) CreateSchemaInToDB() error {
	for _, req := range c.Param.Requests {
		backupFilePath, err := pkg.DumpDBSchema(
			c.Param.Host, c.Param.Port,
			c.GeneralParam.RuntimeAccountParam.AdminUser, c.GeneralParam.RuntimeAccountParam.AdminPwd,
			req.FromDatabase, c.uid,
			true,
		)
		if err != nil {
			return err
		}

		// dump 出来的 sql 文件有 USE ${DB}, 需要删除
		sedCmd := exec.Command("sed", "-i", `/^USE.*;/d`, backupFilePath)
		var stderr bytes.Buffer
		sedCmd.Stderr = &stderr
		err = sedCmd.Run()
		if err != nil {
			logger.Error("sed backup file %s failed: %s: %s", backupFilePath, err, stderr.String())
			return err
		}
		logger.Info("sed backup file %s success", backupFilePath)

		err = pkg.ImportDBSchema(
			c.Param.Host, c.Param.Port,
			c.GeneralParam.RuntimeAccountParam.AdminUser, c.GeneralParam.RuntimeAccountParam.AdminPwd,
			req.ToDatabase, backupFilePath,
		)
		if err != nil {
			return err
		}

		// 为了幂等重试, 忽略导入的 already exists 错误
		importErrFilePath := fmt.Sprintf("%s.%s.err", backupFilePath, req.ToDatabase)
		ief, err := os.Open(importErrFilePath)
		if err != nil {
			return err
		}
		logger.Info("open %s success", importErrFilePath)

		var importErrors []string
		scanner := bufio.NewScanner(ief)
		for scanner.Scan() {
			line := scanner.Text()
			if !strings.HasPrefix(line, "ERROR 1050") /*table view*/ &&
				!strings.HasPrefix(line, "ERROR 1304") /*procedure function*/ &&
				!strings.HasPrefix(line, "ERROR 1537") /*event*/ &&
				!strings.HasPrefix(line, "ERROR 1359") /*trigger*/ &&
				!strings.HasPrefix(line, "ERROR 1840") {
				importErrors = append(importErrors, line)
			}
		}
		if err := scanner.Err(); err != nil {
			return err
		}

		if len(importErrors) > 0 {
			errStr := strings.Join(importErrors, "\n")
			return fmt.Errorf(errStr)
		}
	}
	return nil
}

func (c *ViaCtlComponent) DropFromDB() error {
	for _, req := range c.Param.Requests {
		err := pkg.DropDB(c.dbConn, req.FromDatabase, req.ToDatabase, false)
		if err != nil {
			return err
		}
	}
	return nil
}

func (c *ViaCtlComponent) Example() interface{} {
	return ViaCtlComponent{
		Param: &ViaCtlParam{
			Host: "127.0.0.1",
			Port: 12345,
			Requests: []renameRequest{
				{
					FromDatabase: "old_db1",
					ToDatabase:   "new_db1",
				},
				{
					FromDatabase: "old_db2",
					ToDatabase:   "new_db2",
				},
			},
		},
	}
}
