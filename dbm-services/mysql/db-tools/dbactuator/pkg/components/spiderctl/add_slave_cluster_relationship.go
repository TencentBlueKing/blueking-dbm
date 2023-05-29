package spiderctl

import (
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
	"dbm-services/mysql/db-tools/dbactuator/pkg/tools"
	"fmt"
)

// AddSlaveClusterRoutingComp TODO
type AddSlaveClusterRoutingComp struct {
	GeneralParam *components.GeneralParam     `json:"general"`
	Params       *AddSlaveClusterRoutingParam `json:"extend"`
	AddCtx
	tools *tools.ToolSet
}

// AddSlaveClusterRoutingParam TODO
type AddSlaveClusterRoutingParam struct {
	Host                 string     `json:"host" validate:"required,ip"`
	Port                 int        `json:"port" validate:"required,lt=65536,gte=3306"`
	SlaveInstances       []Instance `json:"slave_instances" validate:"required"`
	SpiderSlaveInstances []Instance `json:"spider_slave_instances" validate:"required"`
}

// AddCtx 定义任务执行时需要的上下文
type AddCtx struct {
	dbConn *native.DbWorker
}

// Example TODO
func (a *AddSlaveClusterRoutingComp) Example() interface{} {
	comp := AddSlaveClusterRoutingComp{
		Params: &AddSlaveClusterRoutingParam{
			Host: "1.1.1.1",
			Port: 26000,
			SlaveInstances: []Instance{
				{
					Host:    "3.3.3.3",
					Port:    20000,
					ShardID: 0,
				},
				{
					Host:    "3.3.3.3",
					Port:    20001,
					ShardID: 1,
				},
			},
			SpiderSlaveInstances: []Instance{
				{
					Host: "3.3.3.3",
					Port: 25000,
				},
				{
					Host: "3.3.3.3",
					Port: 25001,
				},
			},
		},
	}
	return comp
}

// Init 定义act的初始化内容
func (a *AddSlaveClusterRoutingComp) Init() (err error) {

	// 连接本地实例的db
	a.dbConn, err = native.InsObject{
		Host: a.Params.Host,
		Port: a.Params.Port,
		User: a.GeneralParam.RuntimeAccountParam.AdminUser,
		Pwd:  a.GeneralParam.RuntimeAccountParam.AdminPwd,
	}.Conn()
	if err != nil {
		logger.Error("Connect %d failed:%s", a.Params.Port, err.Error())
		return err
	}
	return nil
}

// PerCheck 临时方法，目前部分命令需要设置tc_admin后，新连接才能执行
func (a *AddSlaveClusterRoutingComp) PerCheck() (err error) {

	// 先把session级别tc_admin 设置为0，让show命令生效
	if _, err := a.dbConn.Exec("set tc_admin = 0"); err != nil {
		logger.Error("set tc_admin failed:[%s]", err.Error())
		return err
	}

	// 连接本地实例的db，查看是否从实例连接它，如果有，认为在主从关系里面它是主，如果没有，暂时不信任
	slaveHosts, err := a.dbConn.ShowSlaveHosts()
	if err != nil {
		logger.Error("exec show-slave-hosts failed:[%s]", err.Error())
		return err
	}
	if len(slaveHosts) == 0 {
		return fmt.Errorf("This instance is not currently the master, exit")
	}

	return nil
}

// AddSlaveRouting 在中控集群添加 remote-slave的域名关系
// with database 执行失败之后 tdbctl create node wrapper 无法幂等，目前需要手动清洗待spider
func (a *AddSlaveClusterRoutingComp) AddSlaveRouting() (err error) {

	tdbctlUser := a.GeneralParam.RuntimeAccountParam.TdbctlUser
	tdbctlPwd := a.GeneralParam.RuntimeAccountParam.TdbctlPwd

	// 首先添加 remote-slave 的路由信息，每添加一个slave，先判断信息是否存在, 然后执行加入
	for _, inst := range a.Params.SlaveInstances {
		var execSQLs []string
		err, isInsert := a.CheckInst(inst.Host, inst.Port)
		if err != nil {
			// 判断出现异常
			return err
		}
		if !isInsert {
			// 实例已存在，跳过,目前中控保证添加成功后 ，mysql.servers表会存在
			continue
		}
		// 组装添加remote-slave节点的路由SQL
		// 显性标记实例为主节点
		execSQLs = append(execSQLs, "set tc_admin=1;")
		execSQLs = append(execSQLs, "set global tc_is_primary=1;")
		execSQLs = append(
			execSQLs,
			fmt.Sprintf(
				"tdbctl create node wrapper 'mysql_slave' options(user '%s', password '%s', host '%s', port %d, number %d);",
				tdbctlUser, tdbctlPwd, inst.Host, inst.Port, inst.ShardID),
		)
		if _, err := a.dbConn.ExecMore(execSQLs); err != nil {
			logger.Error("tdbctl create node failed:[%s]", err.Error())
			return err
		}

	}
	// 然后添加spider-slave节点，每添加一个spider slave，需要判断是否已添加过
	for _, inst := range a.Params.SpiderSlaveInstances {

		var execSQLs []string

		err, isInsert := a.CheckInst(inst.Host, inst.Port)
		if err != nil {
			// 判断出现异常
			return err
		}
		if !isInsert {
			// 实例已存在，跳过
			continue
		}
		// 组装添加spider-slave节点的路由SQL
		// 显性标记实例为主节点
		execSQLs = append(execSQLs, "set tc_admin=1;")
		execSQLs = append(execSQLs, "set global tc_is_primary=1;")
		execSQLs = append(
			execSQLs,
			fmt.Sprintf(
				"tdbctl create node wrapper 'SPIDER_SLAVE' options(user '%s', password '%s', host '%s', port %d ) with database;",
				tdbctlUser, tdbctlPwd, inst.Host, inst.Port),
		)
		if _, err := a.dbConn.ExecMore(execSQLs); err != nil {
			logger.Error("tdbctl create node failed:[%s]", err.Error())
			return err
		}

	}

	// 最后flush整体集群的路由信息
	if _, err := a.dbConn.Exec("tdbctl flush routing;"); err != nil {
		logger.Error("tdbctl create node failed:[%s]", err.Error())
		return err
	}
	return nil
}

// CheckInst todo
// 检查添加的集群实例的路由信息之前是否添加完成
func (a *AddSlaveClusterRoutingComp) CheckInst(host string, port int) (err error, result bool) {
	var cnt int
	// 先把session级别tc_admin 设置为0，让show命令生效
	if _, err := a.dbConn.Exec("set tc_admin = 0"); err != nil {
		logger.Error("set tc_admin failed:[%s]", err.Error())
		return err, false
	}

	checkSQL := fmt.Sprintf("select count(0) from mysql.servers where Host = '%s' and Port = %d ", host, port)
	if err := a.dbConn.Queryxs(&cnt, checkSQL); err != nil {
		logger.Error("检查失败%s", err.Error())
		return err, false
	}
	if cnt != 0 {
		// 返回结果非0，则代表该实例已经写入路由表
		logger.Warn("实例【%s:%d】已经在中控实例录入到，这次选跳过", host, port)
		return nil, false

	}
	return nil, true
}
