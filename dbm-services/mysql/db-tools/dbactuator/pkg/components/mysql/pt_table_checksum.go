package mysql

import (
	"bytes"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/peripheraltools/checksum"
	"dbm-services/mysql/db-tools/mysql-table-checksum/pkg/config"
	"fmt"
	"os"
	"os/exec"
	"path"
	"strings"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql/common"
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
	"dbm-services/mysql/db-tools/dbactuator/pkg/tools"

	_ "github.com/go-sql-driver/mysql" // mysql 驱动
	"github.com/jmoiron/sqlx"
	"gopkg.in/yaml.v2"
)

// PtTableChecksumComp 数据校验基本结构
type PtTableChecksumComp struct {
	GeneralParam *components.GeneralParam `json:"general"`
	Params       *PtTableChecksumParam    `json:"extend"`
	PtTableChecksumCtx
	tools *tools.ToolSet
}

// PtTableChecksumParam godoc
type PtTableChecksumParam struct {
	BkBizId                   int         `json:"bk_biz_id"`                    // 业务 id
	ClusterId                 int         `json:"cluster_id"`                   // 集群 id
	ImmuteDomain              string      `json:"immute_domain"`                // 集群域名
	MasterIp                  string      `json:"master_ip"`                    // 执行校验的 db ip
	MasterPort                int         `json:"master_port"`                  // 执行校验的 db port
	InnerRole                 string      `json:"inner_role"`                   // 执行校验的 db inner role, 应该是[master, repeater]
	MasterAccessSlaveUser     string      `json:"master_access_slave_user"`     // 从 db 访问 slave 的用户名
	MasterAccessSlavePassword string      `json:"master_access_slave_password"` // 从 db 访问 slave 的密码
	DbPatterns                []string    `json:"db_patterns"`                  // 库表过滤选项
	IgnoreDbs                 []string    `json:"ignore_dbs"`                   // 库表过滤选项
	TablePatterns             []string    `json:"table_patterns"`               // 库表过滤选项
	IgnoreTables              []string    `json:"ignore_tables"`                // 库表过滤选项
	RuntimeHour               int         `json:"runtime_hour"`                 // 校验运行时长
	ReplicateTable            string      `json:"replicate_table"`              // 结果表, 带库前缀
	Slaves                    []SlaveInfo `json:"slaves"`                       // slave 列表
	SystemDbs                 []string    `json:"system_dbs"`                   // 系统表
	StageDBHeader             string      `json:"stage_db_header"`
	RollbackDBTail            string      `json:"rollback_db_tail"`
}

// SlaveInfo slave 描述
type SlaveInfo struct {
	Id   int    `json:"id"`   // slave id
	Ip   string `json:"ip"`   // slave ip
	Port int    `json:"port"` // slave port
}

// PtTableChecksumCtx 上下文信息
type PtTableChecksumCtx struct {
	uid     string
	cfgFile string
	dbh     *sqlx.DB
}

// Precheck 预检查
// master, slaves 连接
// 依赖文件存在
func (c *PtTableChecksumComp) Precheck() (err error) {
	_, err = native.InsObject{
		Host: c.Params.MasterIp,
		Port: c.Params.MasterPort,
		User: c.GeneralParam.RuntimeAccountParam.MonitorUser,
		Pwd:  c.GeneralParam.RuntimeAccountParam.MonitorPwd,
	}.Conn()
	if err != nil {
		logger.Error("connect %s:%d failed:%s", c.Params.MasterIp, c.Params.MasterPort, err.Error())
		return err
	}

	for _, slave := range c.Params.Slaves {
		_, err = native.InsObject{
			Host: slave.Ip,
			Port: slave.Port,
			User: c.Params.MasterAccessSlaveUser,
			Pwd:  c.Params.MasterAccessSlavePassword,
		}.Conn()
		if err != nil {
			logger.Error("connect slave %s:%d failed:%s", slave.Ip, slave.Port, err.Error())
			return err
		}
	}

	c.tools, err = tools.NewToolSetWithPick(tools.ToolMysqlTableChecksum, tools.ToolPtTableChecksum)
	if err != nil {
		logger.Error("init toolset failed: %s", err.Error())
		return err
	}

	return nil
}

// Init 连接 master
func (c *PtTableChecksumComp) Init(uid string) (err error) {
	c.uid = uid

	dsn := fmt.Sprintf(
		`%s:%s@tcp(%s:%d)/test`,
		c.GeneralParam.RuntimeAccountParam.MonitorUser,
		c.GeneralParam.RuntimeAccountParam.MonitorPwd,
		c.Params.MasterIp,
		c.Params.MasterPort,
	)
	c.dbh, err = sqlx.Connect("mysql", dsn)
	if err != nil {
		logger.Error("connect %s failed: %s", dsn, err.Error())
		return err
	}

	return nil
}

// GenerateConfigFile 生成 mysql-table-checksum 配置文件
func (c *PtTableChecksumComp) GenerateConfigFile() (err error) {
	logDir := path.Join(cst.ChecksumInstallPath, "logs")

	cfg := checksum.NewRuntimeConfig(
		c.Params.BkBizId, c.Params.ClusterId, c.Params.MasterPort,
		c.Params.InnerRole, "", c.Params.ImmuteDomain, c.Params.MasterIp,
		c.GeneralParam.RuntimeAccountParam.MonitorUser, c.GeneralParam.RuntimeAccountParam.MonitorPwd,
		"http://127.0.0.1:9999", logDir, c.tools)

	cfg.PtChecksum.Replicate = c.Params.ReplicateTable

	var ignoreDbs []string
	ignoreDbs = append(ignoreDbs, c.Params.SystemDbs...)
	ignoreDbs = append(ignoreDbs, []string{
		fmt.Sprintf(`%s%%`, c.Params.StageDBHeader),
		`bak_%`,
		fmt.Sprintf(`%%%s`, c.Params.RollbackDBTail),
	}...)

	cfg.SetFilter(c.Params.DbPatterns, ignoreDbs, c.Params.TablePatterns, c.Params.IgnoreTables)

	for _, slave := range c.Params.Slaves {
		cfg.Slaves = append(
			cfg.Slaves, config.Host{
				User:     c.Params.MasterAccessSlaveUser,
				Password: c.Params.MasterAccessSlavePassword,
				Ip:       slave.Ip,
				Port:     slave.Port,
			},
		)
	}

	yamlData, err := yaml.Marshal(&cfg)
	if err != nil {
		logger.Error("generate yaml config failed: %s", err.Error())
		return err
	}

	c.cfgFile = path.Join("/tmp", fmt.Sprintf("checksum_%d_%s.yaml", c.Params.MasterPort, c.uid))
	err = os.WriteFile(c.cfgFile, yamlData, 0644)
	if err != nil {
		logger.Error("write config failed: %s", err.Error())
		return err
	}

	logger.Info("mysql-table-checksum config: %s", cfg)
	return nil
}

// DoChecksum 执行校验
func (c *PtTableChecksumComp) DoChecksum() (err error) {
	mysqlTableChecksumPath, err := c.tools.Get(tools.ToolMysqlTableChecksum)
	if err != nil {
		logger.Error("get %s failed: %s", tools.ToolMysqlTableChecksum, err.Error())
		return err
	}
	command := exec.Command(
		mysqlTableChecksumPath, []string{
			"demand",
			"--config", c.cfgFile,
			"--uuid", c.uid,
		}...,
	)
	logger.Info("command: %s", command)
	var stdout, stderr bytes.Buffer
	command.Stdout = &stdout
	command.Stderr = &stderr

	err = command.Run()
	if err != nil {
		logger.Error("execute check command failed: %s, %s", err.Error(), stderr.String())
		return err
	}

	fmt.Println(components.WrapperOutputString(strings.TrimSpace(stdout.String())))
	return nil
}

// Example 样例
func (c *PtTableChecksumComp) Example() interface{} {
	comp := PtTableChecksumComp{
		GeneralParam: &components.GeneralParam{
			RuntimeAccountParam: components.RuntimeAccountParam{
				MySQLAccountParam: common.AccountMonitorExample,
			},
		},
		Params: &PtTableChecksumParam{
			BkBizId:                   1,
			ClusterId:                 1,
			ImmuteDomain:              "example.db.com",
			MasterIp:                  "127.0.0.1",
			MasterPort:                20000,
			InnerRole:                 "master",
			MasterAccessSlaveUser:     "dummyuser",
			MasterAccessSlavePassword: "dummypassword",
			DbPatterns:                []string{"db1%", "db2%"},
			IgnoreDbs:                 []string{"db11", "db22"},
			TablePatterns:             []string{},
			IgnoreTables:              []string{"table_user_%", "table_mail_%"},
			RuntimeHour:               2,
			ReplicateTable:            fmt.Sprintf("%s.checksum", native.INFODBA_SCHEMA),
			Slaves: []SlaveInfo{
				{
					Id:   11,
					Ip:   "127.0.0.2",
					Port: 20000,
				},
				{
					Id:   12,
					Ip:   "127.0.0.3",
					Port: 20000,
				},
			},
			SystemDbs: []string{native.INFODBA_SCHEMA, native.TEST_DB, "mysql"},
		},
		PtTableChecksumCtx: PtTableChecksumCtx{},
	}
	return comp
}
