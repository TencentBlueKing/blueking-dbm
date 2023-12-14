package spiderctl

import (
	"fmt"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
)

// 处理tendb cluster 部署阶段时初始化 tendb、ctl、spider 节点之间的路由关系

// InitClusterRoutingComp TODO
type InitClusterRoutingComp struct {
	GeneralParam *components.GeneralParam `json:"general"`
	Params       *InitClusterRoutingParam `json:"extend"`
	InitCtx
}

// InitClusterRoutingParam TODO
type InitClusterRoutingParam struct {
	Host                 string          `json:"host" validate:"required,ip"`
	Port                 int             `json:"port" validate:"required,lt=65536,gte=3306"`
	MysqlInstanceTuples  []InstanceTuple `json:"mysql_instance_tuples" validate:"required"`
	SpiderInstances      []Instance      `json:"spider_instances" validate:"required"`
	CltInstances         []Instance      `json:"ctl_instances" validate:"required"`
	TdbctlUser           string          `json:"tdbctl_user" validate:"required"`
	TdbctlPass           string          `json:"tdbctl_pass" validate:"required"`
	NotFlushAll          bool            `json:"not_flush_all"`
	OnltInitCtl          bool            `json:"only_init_ctl"`
	SpiderSlaveInstances []Instance      `json:"spider_slave_instances"`
}

// Instance TODO
type Instance struct {
	Host    string `json:"host"  validate:"required,ip" `
	Port    int    `json:"port"  validate:"required,lt=65536,gte=3306"`
	ShardID int    `json:"shard_id"`
}

// InstanceTuple TODO
type InstanceTuple struct {
	Host      string `json:"host" validate:"required"`
	Port      int    `json:"port" validate:"required"`
	SlaveHost string `json:"slave_host" validate:"required"`
	ShardID   int    `json:"shard_id" validate:"required"`
}

// InitCtx 定义任务执行时需要的上下文
type InitCtx struct {
	dbConn     *native.DbWorker
	tdbCtlConn *native.TdbctlDbWork
}

// Example TODO
func (i *InitClusterRoutingComp) Example() interface{} {
	comp := InitClusterRoutingComp{
		Params: &InitClusterRoutingParam{
			Host: "x.x.x.x",
			Port: 26000,
			MysqlInstanceTuples: []InstanceTuple{
				{
					Host:      "x.x.x.x",
					Port:      20000,
					SlaveHost: "x.x.x.x",
					ShardID:   0,
				},
				{
					Host:      "x.x.x.x",
					Port:      20001,
					SlaveHost: "x.x.x.x",
					ShardID:   1,
				},
			},
			SpiderInstances: []Instance{
				{
					Host: "x.x.x.x",
					Port: 25000,
				},
				{
					Host: "x.x.x.x",
					Port: 25001,
				},
			},
			CltInstances: []Instance{
				{
					Host: "x.x.x.x",
					Port: 26000,
				},
				{
					Host: "x.x.x.x",
					Port: 26001,
				},
			},
		},
	}
	return comp
}

// Init 定义act的初始化内容
func (i *InitClusterRoutingComp) Init() (err error) {

	// 连接本地实例的db
	i.dbConn, err = native.InsObject{
		Host: i.Params.Host,
		Port: i.Params.Port,
		User: i.GeneralParam.RuntimeAccountParam.AdminUser,
		Pwd:  i.GeneralParam.RuntimeAccountParam.AdminPwd,
	}.Conn()
	if err != nil {
		logger.Error("Connect %d failed:%s", i.Params.Port, err.Error())
		return err
	}
	i.tdbCtlConn = &native.TdbctlDbWork{DbWorker: *i.dbConn}
	return nil
}

// InitMySQLServers 初始化mysql.servers表
// todo 发现tdbctl组件执行create node 会让tc_is_primary跳转，看看是不是bug
func (i *InitClusterRoutingComp) InitMySQLServers() (err error) {
	var execSQLs []string

	// 先清理mysql.servers 表，保证活动节点执行的幂等性。但这么粗暴地删除会不会有安全隐患？
	TruncateSQL := []string{"set tc_admin = 0; ", "truncate table mysql.servers;"}
	if _, err := i.dbConn.ExecMore(TruncateSQL); err != nil {
		logger.Error("truncate mysql.servers failed:[%s]", err.Error())
		return err
	}
	execSQLs = i.getFlushRouterSqls()
	execSQLs = append(execSQLs, "tdbctl enable primary;")
	execSQLs = append(execSQLs, "tdbctl flush routing;")
	if _, err := i.dbConn.ExecMore(execSQLs); err != nil {
		logger.Error("tdbctl create node failed:[%s]", err.Error())
		return err
	}
	return nil
}

func (i *InitClusterRoutingComp) getFlushRouterSqls() (execSQLs []string) {
	// 显性标记实例为主节点
	execSQLs = append(execSQLs, "set tc_admin=1;")

	// 拼接create node 语句
	execSQLs = append(execSQLs, i.getRemoteRouterSqls()...)
	execSQLs = append(execSQLs, i.getSpiderRouterSqls()...)
	execSQLs = append(execSQLs, i.getTdbctlRouterSqls()...)
	return execSQLs
}
func (i *InitClusterRoutingComp) getSpiderRouterSqls() (execSQLs []string) {
	for _, inst := range i.Params.SpiderInstances {
		execSQLs = append(
			execSQLs,
			fmt.Sprintf(
				"tdbctl create node wrapper 'SPIDER' options(user '%s', password '%s', host '%s', port %d);",
				i.Params.TdbctlUser, i.Params.TdbctlPass, inst.Host, inst.Port,
			),
		)
	}
	for _, inst := range i.Params.SpiderSlaveInstances {
		execSQLs = append(
			execSQLs,
			fmt.Sprintf(
				"tdbctl create node wrapper 'SPIDER_SLAVE' options(user '%s', password '%s', host '%s', port %d);",
				i.Params.TdbctlUser, i.Params.TdbctlPass, inst.Host, inst.Port,
			),
		)
	}
	return execSQLs
}

func (i *InitClusterRoutingComp) getRemoteRouterSqls() (execSQLs []string) {
	for _, inst := range i.Params.MysqlInstanceTuples {
		execSQLs = append(
			execSQLs,
			fmt.Sprintf(
				"tdbctl create node wrapper 'mysql' options(user '%s', password '%s', host '%s', port %d, number %d );",
				i.Params.TdbctlUser, i.Params.TdbctlPass, inst.Host, inst.Port, inst.ShardID,
			),
		)
		execSQLs = append(
			execSQLs,
			fmt.Sprintf(
				"tdbctl create node wrapper 'mysql_slave' options(user '%s', password '%s', host '%s', port %d, number %d );",
				i.Params.TdbctlUser, i.Params.TdbctlPass, inst.SlaveHost, inst.Port, inst.ShardID,
			),
		)
	}
	return execSQLs
}

func (i *InitClusterRoutingComp) getTdbctlRouterSqls() (execSQLs []string) {
	for _, inst := range i.Params.CltInstances {
		execSQLs = append(
			execSQLs,
			fmt.Sprintf(
				"tdbctl create node wrapper 'TDBCTL' options(user '%s', password '%s', host '%s', port %d);",
				i.Params.TdbctlUser, i.Params.TdbctlPass, inst.Host, inst.Port,
			),
		)
	}
	return execSQLs
}

// OnlyInitTdbctl 只刷新中控路由
func (i *InitClusterRoutingComp) OnlyInitTdbctl() (err error) {
	var execSQLs []string
	execSQLs = append(execSQLs, "set tc_admin=1;")
	execSQLs = append(execSQLs, i.getTdbctlRouterSqls()...)
	execSQLs = append(execSQLs, "tdbctl enable primary;")
	if _, err := i.tdbCtlConn.ExecMore(execSQLs); err != nil {
		logger.Error("tdbctl create node failed:[%s]", err.Error())
		return err
	}
	servers, err := i.tdbCtlConn.SelectServers()
	if err != nil {
		logger.Error("get local mysql servers failed %s", err.Error())
		return err
	}
	var tdbctlSvrCount int
	for _, server := range servers {
		if !native.SvrNameIsTdbctl(server.ServerName) {
			continue
		}
		tdbctlSvrCount++
		logger.Info("start flush %s router", server.ServerName)
		flushSql := fmt.Sprintf(" TDBCTL FLUSH SERVER %s ROUTING;", server.ServerName)
		logger.Info("make debug flush sql %s", flushSql)
		_, err = i.tdbCtlConn.Exec(flushSql)
		if err != nil {
			logger.Error("flush router to %s failed %s", server.ServerName, err.Error())
			return err
		}

	}
	if tdbctlSvrCount < 1 {
		return fmt.Errorf("not found  tdbctl in mysql.servers")
	}
	return nil
}

// AddAppendDeployInitRouter 无中控迁移到有中控后，中控需要初始化的路由信息
func (i *InitClusterRoutingComp) AddAppendDeployInitRouter() (err error) {
	var execSQLs []string
	execSQLs = append(execSQLs, "set tc_admin=1;")
	execSQLs = append(execSQLs, i.getRemoteRouterSqls()...)
	execSQLs = append(execSQLs, i.getSpiderRouterSqls()...)
	execSQLs = append(execSQLs, "tdbctl enable primary;")
	if _, err := i.tdbCtlConn.ExecMore(execSQLs); err != nil {
		logger.Error("tdbctl create node failed:[%s]", err.Error())
		return err
	}
	servers, err := i.tdbCtlConn.SelectServers()
	if err != nil {
		logger.Error("get local mysql servers failed %s", err.Error())
		return err
	}
	var tdbctlSvrCount int
	for _, server := range servers {
		if !native.SvrNameIsTdbctl(server.ServerName) {
			continue
		}
		tdbctlSvrCount++
		logger.Info("start flush %s router", server.ServerName)
		flushSql := fmt.Sprintf(" TDBCTL FLUSH SERVER %s ROUTING;", server.ServerName)
		_, err = i.tdbCtlConn.Exec(flushSql)
		if err != nil {
			logger.Error("flush router to %s failed %s", server.ServerName, err.Error())
			return err
		}

	}
	if tdbctlSvrCount < 1 {
		return fmt.Errorf("not found  tdbctl in mysql.servers")
	}
	return nil
}
