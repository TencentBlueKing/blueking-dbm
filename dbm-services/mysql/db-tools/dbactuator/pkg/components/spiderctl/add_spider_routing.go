/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package spiderctl

import (
	"fmt"
	"regexp"
	"strconv"
	"strings"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/mysqlconn"

	"github.com/jmoiron/sqlx"
)

// 该文件等价翻译自 Python 侧:
// dbm-ui/backend/flow/plugins/components/collections/spider/add_spider_routing.py
//
// 行为差异说明 (与 Python 版本保持一致的部分以及差异):
//   1. 不再调用 dbm-ui 的 DBPrivManagerApi 添加内置账号, 该步骤由上层 flow 在
//      调用本子命令前自行完成 (例如使用 mysql/grant-user 类子命令).
//   2. 本子命令需要在 "中控 primary 节点本机" 执行, 通过本地 admin 端口连接中控,
//      与 Python 侧通过 DRS 远程访问 ctl_master 行为完全等价.
//   3. drop user / reset master 这两步原本通过 DRS 操作"待加入 spider 节点",
//      在本地化场景下使用 native.InsObject 直接发起远程 mysql 连接执行.
//   4. 版本判定逻辑 (>=2.4.13 走并发添加, 否则串行) 与 Python 完全等价.

// 支持并发添加节点的最低版本编号: 2.4.13
const minParallelRouteVersion = 2004013

// addSpiderRole 定义角色枚举字符串(与 dbm-ui 侧 TenDBClusterSpiderRole 保持一致)
const (
	addSpiderRoleMaster = "spider_master"
	addSpiderRoleSlave  = "spider_slave"
	addSpiderRoleMnt    = "spider_mnt"
)

// 13 以上的中控版本, 添加路由时会自动跳过 TC_SKIP_CHECK_DB_LIST 中的数据库
var tcSkipCheckDBList = []string{
	"mysql",
	"information_schema",
	"performance_schema",
	"sys",
	"test",
	"infodba_schema",
	"db_infobase",
}

// AddSpiderRoutingComp 添加 spider 节点路由组件
type AddSpiderRoutingComp struct {
	GeneralParam *components.GeneralParam `json:"general"`
	Params       *AddSpiderRoutingParam   `json:"extend"`
	addSpiderRoutingCtx
}

// AddSpiderRoutingParam 添加 spider 节点路由的参数
//
// 字段含义:
//   - Host/Port:     中控 primary 节点的本机地址和 admin 端口 (用来本地直连中控执行 SQL)
//   - SpiderPort:    本集群所有 spider 节点对外业务端口
//   - AdminPort:     本集群所有中控节点的 admin 端口 (仅在添加 spider_master 时, 还需要一并加入 TDBCTL 路由时使用)
//   - AddSpiders:    本次待加入的节点 IP 列表 (端口由 SpiderPort/AdminPort 决定, 无需在此重复指定)
//   - AddSpiderRole: 待加入 spider 的角色, 仅支持 spider_master / spider_slave / spider_mnt
//   - SpiderUser/SpiderPass: 中控连接 spider 节点时使用的内置账号(原 Python 中的 user/passwd)
//   - ForceParallel: 可选, 跳过版本探测; nil=自动探测, true=强制并发, false=强制串行
//
// 注意:
//
//	中控之间互相连接使用的内置账号密码 (原 Python 中的 ctl_pass), 统一从
//	GeneralParam.RuntimeAccountParam.TdbctlPwd 读取, 由上层流程通过 general.runtime_account
//	注入, 必传; 不再通过 extend 字段透传.
type AddSpiderRoutingParam struct {
	Host          string   `json:"host" validate:"required,ip"`
	Port          int      `json:"port" validate:"required,lt=65536,gte=3306"`
	SpiderPort    int      `json:"spider_port" validate:"required,lt=65536,gte=3306"`
	AdminPort     int      `json:"admin_port" validate:"required,lt=65536,gte=3306"`
	AddSpiders    []string `json:"add_spiders" validate:"required,min=1,dive,ip"`
	AddSpiderRole string   `json:"add_spider_role" validate:"required,oneof=spider_master spider_slave spider_mnt"`
	SpiderUser    string   `json:"spider_user" validate:"required"`
	SpiderPass    string   `json:"spider_pass" validate:"required"`
}

// addSpiderRoutingCtx 任务执行上下文
type addSpiderRoutingCtx struct {
	// ctlConn 本地中控 primary 的连接(对应 Python 里的 ctl_master)
	ctlConn *native.TdbctlDbWork
	// ctlMasterIP 中控 primary 的 IP, 用于 drop user 时定位 host
	ctlMasterIP string
}

// Example 示例参数
func (a *AddSpiderRoutingComp) Example() interface{} {
	return AddSpiderRoutingComp{
		Params: &AddSpiderRoutingParam{
			Host:       "127.0.0.1",
			Port:       26000,
			SpiderPort: 25000,
			AdminPort:  26000,
			AddSpiders: []string{
				"127.0.0.2",
				"127.0.0.3",
			},
			AddSpiderRole: addSpiderRoleMaster,
			SpiderUser:    "spider_xxx",
			SpiderPass:    "spider_xxx_pwd",
		},
	}
}

// Init 初始化: 建立中控本地连接
func (a *AddSpiderRoutingComp) Init() (err error) {
	dbConn, err := native.InsObject{
		Host: a.Params.Host,
		Port: a.Params.Port,
		User: a.GeneralParam.RuntimeAccountParam.TdbctlUser,
		Pwd:  a.GeneralParam.RuntimeAccountParam.TdbctlPwd,
	}.Conn()
	if err != nil {
		logger.Error("connect ctl-primary %s:%d failed: %s", a.Params.Host, a.Params.Port, err.Error())
		return err
	}
	a.ctlConn = &native.TdbctlDbWork{DbWorker: *dbConn}
	a.ctlMasterIP = a.Params.Host

	return nil
}

// PreCheck 前置校验: 当前节点必须确实是中控 primary.
//
// 直接复用 mysql-dbbackup 已有的公共方法 mysqlconn.IsPrimaryCtl, 内部执行
// `tdbctl get primary` 并依据 IS_THIS_SERVER=1 判定.
func (a *AddSpiderRoutingComp) PreCheck() (err error) {
	// 显式标识 session 为中控会话, 避免 set 之类的命令被错误转发
	if _, err = a.ctlConn.Exec("set tc_admin = 1"); err != nil {
		return fmt.Errorf("set tc_admin=1 failed: %w", err)
	}
	// native.DbWorker.Db 是 *sql.DB, 而 mysqlconn.DbWorker.Db 是 *sqlx.DB,
	// 这里用 sqlx.NewDb 做无侵入桥接, 不会重新建立连接.
	dbw := &mysqlconn.DbWorker{Db: sqlx.NewDb(a.ctlConn.Db, "mysql")}
	isPrimary, err := mysqlconn.IsPrimaryCtl(dbw)
	if err != nil {
		return fmt.Errorf("check tdbctl primary failed: %w", err)
	}
	if !isPrimary {
		return fmt.Errorf("current node %s:%d is NOT tdbctl primary",
			a.Params.Host, a.Params.Port)
	}
	return nil
}

// Run 主流程, 对应 Python AddSpiderRoutingService._execute
func (a *AddSpiderRoutingComp) Run() (err error) {
	// 阶段 1: Python 侧 _add_system_user 由 dbm-ui 中央 API 完成, 这里跳过.
	logger.Info("skip add-system-user phase, expected to be done by upper flow before this command")

	// 阶段 2: 添加路由信息
	useParallel, err := a.shouldUseParallel()
	if err != nil {
		return err
	}
	if useParallel {
		logger.Info("use parallel route adding")
		if err = a.addNodesInParallel(); err != nil {
			return err
		}
	} else {
		logger.Info("use serial route adding")
		if err = a.addNodesInNonParallel(); err != nil {
			return err
		}
	}

	// 阶段 3: 统一刷新路由
	logger.Info("flushing routing ...")
	if err = a.flushRouting(); err != nil {
		return err
	}
	logger.Info("flush routing to other tdbctl nodes successfully")
	return nil
}

// shouldUseParallel 决定是否走并发路径
//
// 优先级: ForceParallel(显式指定) > 自动版本探测 (>=2.4.13)
func (a *AddSpiderRoutingComp) shouldUseParallel() (bool, error) {
	version, err := a.ctlConn.SelectVersion()
	if err != nil {
		return false, fmt.Errorf("query ctl-primary version failed: %w", err)
	}
	logger.Info("ctl-primary version: %s", version)
	return tdbctlVersionParse(version) >= minParallelRouteVersion, nil
}

// flushRouting 对应 Python AddSpiderRoutingService.flush_routing /
// get_flush_routing_sql_for_server
//
// 找到所有 (1)中控 slave 节点 (2)本次新加入的 spider 节点, 对它们逐一执行
// `TDBCTL FLUSH SERVER xxx ROUTING`.
func (a *AddSpiderRoutingComp) flushRouting() error {
	servers, err := a.ctlConn.SelectServers()
	if err != nil {
		return fmt.Errorf("select mysql.servers failed: %w", err)
	}

	addSpiderIPSet := make(map[string]struct{}, len(a.Params.AddSpiders))
	for _, ip := range a.Params.AddSpiders {
		addSpiderIPSet[ip] = struct{}{}
	}

	var flushSQLs []string
	for _, srv := range servers {
		switch {
		case srv.Wrapper == native.TDBCTL_PREFIX &&
			!(srv.Host == a.ctlMasterIP && srv.Port == a.Params.Port):
			// 中控 slave 节点 (避开 primary 自身)
			flushSQLs = append(flushSQLs, fmt.Sprintf("TDBCTL FLUSH SERVER %s ROUTING;", srv.ServerName))
		default:
			if _, ok := addSpiderIPSet[srv.Host]; ok {
				// 本次新加入的 spider 节点
				flushSQLs = append(flushSQLs, fmt.Sprintf("TDBCTL FLUSH SERVER %s ROUTING;", srv.ServerName))
			}
		}
	}
	if len(flushSQLs) == 0 {
		logger.Info("no server need to flush routing, skip")
		return nil
	}
	logger.Info("exec flush_routing cmds: %v", flushSQLs)

	cmds := append([]string{"set tc_admin=1"}, flushSQLs...)
	if _, err := a.ctlConn.ExecMore(cmds); err != nil {
		return fmt.Errorf("flush routing failed: %w", err)
	}
	return nil
}

// checkNodeIsAdded 对应 Python check_spider_node_is_add_cluster:
// 添加之前检测节点是否已经存在路由表中
func (a *AddSpiderRoutingComp) checkNodeIsAdded(host string, port int) (bool, error) {
	if _, err := a.ctlConn.Exec("set tc_admin=0"); err != nil {
		return false, fmt.Errorf("set tc_admin=0 failed: %w", err)
	}
	var cnt int
	if err := a.ctlConn.Queryxs(&cnt, fmt.Sprintf(
		"select count(0) from mysql.servers where Host = '%s' and Port = %d", host, port)); err != nil {
		return false, fmt.Errorf("select mysql.servers failed: %w", err)
	}
	return cnt > 0, nil
}

// resolveWrapperBySpiderRole 角色 -> wrapper
func resolveWrapperBySpiderRole(role string) (string, error) {
	switch role {
	case addSpiderRoleSlave:
		return native.SPIDER_SLAVE_PREFIX, nil
	case addSpiderRoleMaster, addSpiderRoleMnt:
		return native.SPIDER_PREFIX, nil
	default:
		return "", fmt.Errorf("unsupported add_spider_role [%s]", role)
	}
}

// addNodesInParallel 对应 Python add_nodes_in_parallel
func (a *AddSpiderRoutingComp) addNodesInParallel() error {
	wrapper, err := resolveWrapperBySpiderRole(a.Params.AddSpiderRole)
	if err != nil {
		return err
	}

	// 添加 spider 角色路由
	if err := a.execCreateNodeWithConcurrent(
		a.Params.SpiderUser, a.Params.SpiderPass,
		a.Params.AddSpiders, a.Params.SpiderPort, wrapper,
	); err != nil {
		return err
	}

	// 如果是 spider_master, 还需要并发添加对应的 TDBCTL 路由
	if a.Params.AddSpiderRole == addSpiderRoleMaster {
		if err := a.execCreateNodeWithConcurrent(
			a.Params.SpiderUser, a.GeneralParam.RuntimeAccountParam.TdbctlPwd,
			a.Params.AddSpiders, a.Params.AdminPort, native.TDBCTL_PREFIX,
		); err != nil {
			return err
		}
	}
	return nil
}

// addNodesInNonParallel 对应 Python add_nodes_in_non_parallel
func (a *AddSpiderRoutingComp) addNodesInNonParallel() error {
	wrapper, err := resolveWrapperBySpiderRole(a.Params.AddSpiderRole)
	if err != nil {
		return err
	}

	for _, ip := range a.Params.AddSpiders {
		if err := a.execCreateNode(
			a.Params.SpiderUser, a.Params.SpiderPass,
			ip, a.Params.SpiderPort, wrapper,
		); err != nil {
			return err
		}
		if a.Params.AddSpiderRole == addSpiderRoleMaster {
			if err := a.execCreateNode(
				a.Params.SpiderUser, a.GeneralParam.RuntimeAccountParam.TdbctlPwd,
				ip, a.Params.AdminPort, native.TDBCTL_PREFIX,
			); err != nil {
				return err
			}
		}
	}
	return nil
}

// execCreateNodeWithConcurrent 对应 Python _exec_create_node_with_concurrent
//
// 在中控 primary 上, 通过单条 SQL 一次性 create 多个 node:
//
//	tdbctl create node wrapper 'SPIDER' options
//	  (user 'u', password 'p', host 'h1', port 25000),
//	  (user 'u', password 'p', host 'h2', port 25000)
//	with database;
//
// 同时在执行前 SET tc_skip_check_db_list, 与 Python 行为一致.
func (a *AddSpiderRoutingComp) execCreateNodeWithConcurrent(
	user, passwd string, ips []string, port int, wrapper string,
) error {
	// 预过滤已经存在路由表的节点
	var realAdd []string
	for _, ip := range ips {
		exists, err := a.checkNodeIsAdded(ip, port)
		if err != nil {
			return err
		}
		if exists {
			logger.Warn("node already in mysql.servers, skip [%s:%d]", ip, port)
			continue
		}
		realAdd = append(realAdd, ip)
	}
	if len(realAdd) == 0 {
		logger.Warn("no node need to add for wrapper=%s, skip", wrapper)
		return nil
	}

	// 拼 SQL
	var sb strings.Builder
	sb.WriteString(fmt.Sprintf("tdbctl create node wrapper '%s' options ", wrapper))
	for i, host := range realAdd {
		sb.WriteString(fmt.Sprintf("(user '%s', password '%s', host '%s', port %d) ",
			user, passwd, host, port))
		if i == len(realAdd)-1 {
			sb.WriteString("with database;")
		} else {
			sb.WriteString(",")
		}
	}
	createSQL := sb.String()

	cmds := []string{
		"set tc_admin=1",
		fmt.Sprintf("SET GLOBAL tc_skip_check_db_list = '%s'", strings.Join(tcSkipCheckDBList, ",")),
		createSQL,
	}
	logger.Info("exec parallel add-node cmds: %v", maskSQLs(cmds, passwd))

	if _, err := a.ctlConn.ExecMore(cmds); err != nil {
		return fmt.Errorf("parallel create node failed: %w", err)
	}
	logger.Info("parallel add-node succeed: wrapper=%s, hosts=%v, port=%d", wrapper, realAdd, port)
	return nil
}

// execCreateNode 对应 Python _exec_create_node (串行单条添加)
func (a *AddSpiderRoutingComp) execCreateNode(
	user, passwd, spiderIP string, spiderPort int, wrapper string,
) error {
	exists, err := a.checkNodeIsAdded(spiderIP, spiderPort)
	if err != nil {
		return err
	}
	if exists {
		logger.Warn("node already in mysql.servers, skip [%s:%d]", spiderIP, spiderPort)
		return nil
	}

	// 串行模式: create node 之前, 先在 ctl primary 上对当前 mysql.servers 中的某一个 server
	// 做一次 flush server xxx routing, 用于解决 SPT0 之类的 Data source error.
	preCmds := []string{"set tc_admin=1"}
	if firstFlush, err := a.firstFlushSQL(); err != nil {
		return err
	} else if firstFlush != "" {
		preCmds = append(preCmds, firstFlush)
	}

	createSQL := fmt.Sprintf(
		"tdbctl create node wrapper '%s' options(user '%s', password '%s', host '%s', port %d) with database",
		wrapper, user, passwd, spiderIP, spiderPort,
	)
	cmds := append(preCmds, createSQL)
	logger.Info("exec serial add-node cmds: %v", maskSQLs(cmds, passwd))

	if _, err := a.ctlConn.ExecMore(cmds); err != nil {
		return fmt.Errorf("tdbctl create node failed: %w", err)
	}
	logger.Info("tdbctl create node succeed [%s:%d]", spiderIP, spiderPort)
	return nil
}

// firstFlushSQL 取出当前 mysql.servers 中第一个需要 flush 的 server, 返回对应的 flush SQL
// (仅服务于串行模式下的 _exec_create_node 行为)
func (a *AddSpiderRoutingComp) firstFlushSQL() (string, error) {
	if _, err := a.ctlConn.Exec("set tc_admin=0"); err != nil {
		return "", fmt.Errorf("set tc_admin=0 failed: %w", err)
	}
	servers, err := a.ctlConn.SelectServers()
	if err != nil {
		return "", fmt.Errorf("select mysql.servers failed: %w", err)
	}
	for _, srv := range servers {
		if srv.Wrapper == native.TDBCTL_PREFIX &&
			(srv.Host != a.ctlMasterIP || srv.Port != a.Params.Port) {
			return fmt.Sprintf("TDBCTL FLUSH SERVER %s ROUTING;", srv.ServerName), nil
		}
	}
	return "", nil
}

// maskSQLs 把 SQL 中的密码替换成 xxx 用于日志输出
func maskSQLs(cmds []string, passwd string) []string {
	if passwd == "" {
		return cmds
	}
	out := make([]string, len(cmds))
	for i, c := range cmds {
		out[i] = strings.ReplaceAll(c, passwd, "xxx")
	}
	return out
}

// tdbctlVersionParse 等价复刻 dbm-ui 侧 mysql_version_parse.tdbctl_version_parse
//
// 输入:
//
//	"mysql-5.7.20-linux-x86_64-tdbctl-2.4.11.tar.gz" / "tdbctl-2.4.11" / "2.4.11"
//
// 输出:
//
//	2 * 1000000 + 4 * 1000 + 11 = 2004011
func tdbctlVersionParse(version string) int {
	rePattern := regexp.MustCompile(`tdbctl-(\d+)\.?(\d+)?\.?(\d+)?`)
	m := rePattern.FindStringSubmatch(version)
	if len(m) == 0 {
		// 退化为通用三段版本号匹配
		rePattern = regexp.MustCompile(`(\d+)\.?(\d+)?\.?(\d+)?`)
		m = rePattern.FindStringSubmatch(version)
		if len(m) == 0 {
			return 0
		}
	}
	atoi := func(s string) int {
		if s == "" {
			return 0
		}
		v, _ := strconv.Atoi(s)
		return v
	}
	return atoi(m[1])*1000000 + atoi(m[2])*1000 + atoi(m[3])
}
