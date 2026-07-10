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
	"sort"
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
	addSpiderRoleTdbctl = "spider_ctl"
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

// AddSpiderRoutingParam 添加节点路由的参数
//
// 字段含义:
//   - Host/Port:     中控 primary 节点的本机地址和 admin 端口 (用来本地直连中控执行 SQL)
//   - AddPort:       本次待加入节点的访问端口; 由上层调用方根据 AddSpiderRole 自行决定:
//     spider_* 角色 -> 业务端口; tdbctl 角色 -> 中控 admin 端口
//   - AddSpiders:    本次待加入的节点 IP 列表
//   - AddSpiderRole: 待加入节点的角色, 支持 spider_master / spider_slave / spider_mnt / tdbctl;
//     是否需要给 TDBCTL 节点加路由由上层调用方通过显式调用 (传入 AddSpiderRole=tdbctl) 来决定,
//     本组件不再做隐式的 spider_master 顺带加 tdbctl 的逻辑.
//
// 注意:
//
//	内置账号信息全部从 GeneralParam.RuntimeAccountParam 读取, 由上层单据流程统一注入,
//	不在 extend 中明文透传, 也避免活动节点重试时密码发生变化:
//	  - spider_* 角色: 使用 SpiderUser / SpiderPwd
//	  - tdbctl     角色: 使用 TdbctlUser / TdbctlPwd
type AddSpiderRoutingParam struct {
	Host          string   `json:"host" validate:"required,ip"`
	Port          int      `json:"port" validate:"required,lt=65536,gte=3306"`
	AddPort       int      `json:"add_port" validate:"required,lt=65536,gte=3306"`
	AddSpiders    []string `json:"add_spiders" validate:"required,min=1,dive,ip"`
	AddSpiderRole string   `json:"add_spider_role" validate:"required,oneof=spider_master spider_slave spider_mnt spider_ctl"`
}

// addSpiderRoutingCtx 任务执行上下文
type addSpiderRoutingCtx struct {
	// ctlConn 本地中控 primary 的连接(对应 Python 里的 ctl_master)
	ctlConn *native.TdbctlDbWork
	// ctlMasterIP 中控 primary 的 IP, 用于 drop user 时定位 host
	ctlMasterIP string
	// realAddSpiders 经过 F1/F2/F3 体检后, 真正需要本次新建路由的节点列表;
	// 已经"上一轮添加成功且体检通过"的节点不在此列表内
	realAddSpiders []string
}

// Example 示例参数
func (a *AddSpiderRoutingComp) Example() interface{} {
	return AddSpiderRoutingComp{
		Params: &AddSpiderRoutingParam{
			Host:    "127.0.0.1",
			Port:    26000,
			AddPort: 25000,
			AddSpiders: []string{
				"127.0.0.2",
				"127.0.0.3",
			},
			AddSpiderRole: addSpiderRoleMaster,
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

	// 阶段 2.0: 节点体检, 对每个待加入节点做 F1/F2/F3 三层校验,
	// 统一收集结果, 对 mismatch 节点集中抛错, 对 matched 节点直接 skip,
	// 对 absent 节点放进 realAddSpiders 走后续 create node 流程.
	if err = a.preInspectNodes(); err != nil {
		return err
	}

	// 阶段 2: 添加路由信息
	if len(a.realAddSpiders) == 0 {
		logger.Warn("all nodes are already added & inspected ok, skip create node phase")
	} else {
		useParallel, err := a.shouldUseParallel()
		if err != nil {
			return err
		}
		if useParallel {
			// 启动并发添加路由信息的通道
			logger.Info("use parallel route adding for %v", a.realAddSpiders)
			if err = a.addNodesInParallel(); err != nil {
				return err
			}
		} else {
			// 启动串行添加路由信息的通道
			logger.Info("use serial route adding for %v", a.realAddSpiders)
			if err = a.addNodesInNonParallel(); err != nil {
				return err
			}
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

// getCredByRole 根据角色返回创建路由时使用的账号 (user, passwd).
//
// 账号一律来自 general.runtime_account, 不在 extend 中透传:
//   - spider_* 角色: SpiderUser / SpiderPwd
//   - tdbctl     角色: TdbctlUser / TdbctlPwd
func (a *AddSpiderRoutingComp) getCredByRole() (user, passwd string, err error) {
	acc := a.GeneralParam.RuntimeAccountParam
	if a.Params.AddSpiderRole == addSpiderRoleTdbctl {
		if acc.TdbctlUser == "" || acc.TdbctlPwd == "" {
			return "", "", fmt.Errorf("tdbctl_user/tdbctl_pwd is required in general.runtime_account for role=tdbctl")
		}
		return acc.TdbctlUser, acc.TdbctlPwd, nil
	}
	if acc.SpiderUser == "" || acc.SpiderPwd == "" {
		return "", "", fmt.Errorf(
			"spider_user/spider_pwd is required in general.runtime_account for role=%s", a.Params.AddSpiderRole)
	}
	return acc.SpiderUser, acc.SpiderPwd, nil
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

// ===== 节点体检: F1 / F2 / F3 =====

// nodeRouteState ctl primary 上 mysql.servers 中, 待加入节点的三态.
type nodeRouteState int

const (
	// nodeRouteAbsent 路由不存在, 应当走 create node 新建
	nodeRouteAbsent nodeRouteState = iota
	// nodeRouteMatched 路由存在且与本次目标完全一致, 视为上一轮已加入, 进入 F2/F3 体检
	nodeRouteMatched
	// nodeRouteMismatch 路由存在但 wrapper / username / password 与本次不一致;
	// 必须由运维人工先 DROP NODE 再清环境, 不允许程序自动覆盖
	nodeRouteMismatch
)

// nodeMismatchInfo F1 mismatch 的详细信息, 用于聚合后给运维输出修复指引
type nodeMismatchInfo struct {
	IP           string
	Port         int
	ExistServer  native.Server // 当前 mysql.servers 中查到的实际记录(多条时取第一条做样本)
	WantWrapper  string
	WantUsername string
	// Reason 触发 mismatch 的原因, 让运维能一眼区分"字段不一致"还是"同主键有多条脏路由"
	//   - "field-mismatch": (host,port) 唯一一条, 但 wrapper/username/password 不一致
	//   - "duplicate-rows": (host,port) 出现 >1 条记录, 视为脏数据
	Reason string
	// DupCount 仅 Reason=duplicate-rows 时有效, 表示重复条数
	DupCount int
}

// preInspectNodes 在真正 create node 之前, 对 a.Params.AddSpiders 做体检:
//
//	F1: 在 ctl primary 的 mysql.servers 中按 (host, port) 查询,
//	    根据 wrapper / username / password 三元素判定 absent / matched / mismatch.
//	F2: 对 matched 节点, 远程登录该节点本机 mysql.servers, 校验最小路由集.
//	F3: 对 matched 节点, 远程登录该节点, 比对 information_schema 中的业务表数量.
//
// 任意 mismatch 节点存在 -> 收集成清单一次性抛错, 附带人工修复步骤;
// matched 节点全部体检通过 -> 不进入 realAddSpiders, 后续 create node 自然 skip;
// absent 节点 -> 进入 realAddSpiders, 后续 create node.
func (a *AddSpiderRoutingComp) preInspectNodes() error {
	wantWrapper, err := resolveWrapperBySpiderRole(a.Params.AddSpiderRole)
	if err != nil {
		return err
	}
	wantUser, wantPwd, err := a.getCredByRole()
	if err != nil {
		return err
	}

	// 在循环开始前统一设置一次tc_admin=0，避免批量场景下的重复设置
	if _, err := a.ctlConn.Exec("set tc_admin=0"); err != nil {
		return fmt.Errorf("set tc_admin=0 failed: %w", err)
	}

	var (
		mismatched []nodeMismatchInfo
		matched    []string
		absent     []string
	)

	for _, ip := range a.Params.AddSpiders {
		state, srv, err := a.classifyNodeRoute(ip, a.Params.AddPort, wantWrapper, wantUser, wantPwd)
		if err != nil {
			return err
		}
		switch state {
		case nodeRouteAbsent:
			absent = append(absent, ip)
		case nodeRouteMatched:
			logger.Info("F1 ok: node already routed correctly [%s:%d] (server=%s)",
				ip, a.Params.AddPort, srv.ServerName)
			matched = append(matched, ip)
		case nodeRouteMismatch:
			reason := "field-mismatch"
			dupCount := 0
			// 通过再次 count 的方式拿 DupCount 成本太高, 这里直接复用 classifyNodeRoute 的判定:
			// 当 srv 是从 len(rows)>1 分支返回时, 我们没有 dupCount 字段, 但可以通过再查一次 count 拿到.
			// 为了避免复杂的多返回值改造, 在 mismatch 收集阶段补一次 count.
			cnt, cerr := a.countServerRowsAt(ip, a.Params.AddPort)
			if cerr != nil {
				return cerr
			}
			if cnt > 1 {
				reason = "duplicate-rows"
				dupCount = cnt
			}
			mismatched = append(mismatched, nodeMismatchInfo{
				IP:           ip,
				Port:         a.Params.AddPort,
				ExistServer:  *srv,
				WantWrapper:  wantWrapper,
				WantUsername: wantUser,
				Reason:       reason,
				DupCount:     dupCount,
			})
		}
	}

	// F1 mismatch 一次性聚合抛错
	if len(mismatched) > 0 {
		return fmt.Errorf("%s", buildMismatchManualFixHint(mismatched))
	}

	// F2 + F3: 对 matched 节点继续做更深一层的体检
	for _, ip := range matched {
		if err := a.deepInspectMatchedNode(ip); err != nil {
			return fmt.Errorf("deep inspect node [%s:%d] failed: %w",
				ip, a.Params.AddPort, err)
		}
	}

	a.realAddSpiders = absent
	logger.Info("preInspectNodes done. matched(skip)=%v, absent(toAdd)=%v",
		matched, absent)
	return nil
}

// classifyNodeRoute 在 ctl primary 的 mysql.servers 中按 (host, port) 找记录,
// 与本次目标 (wantWrapper / wantUser / wantPwd) 比对, 给出三态判定.
//
// 注意:
//   - 若同 (host, port) 出现多条记录, 判为 mismatch (异常状态, 让人工处理).
//   - 比较密码时使用全字符串相等; mysql.servers.Password 字段存放的就是 create node 时
//     传入的明文密码, 与本组件持有的 RuntimeAccountParam 来源一致, 可直接比较.
func (a *AddSpiderRoutingComp) classifyNodeRoute(
	host string, port int, wantWrapper, wantUser, wantPwd string,
) (nodeRouteState, *native.Server, error) {
	// 移除重复的tc_admin=0设置，已在preInspectNodes入口处统一设置
	var rows []native.Server
	if err := a.ctlConn.Queryx(&rows,
		"select Server_name, Host, Db, Username, Password, Port, Wrapper "+
			"from mysql.servers where Host = ? and Port = ?", host, port); err != nil {
		return nodeRouteAbsent, nil, fmt.Errorf("select mysql.servers failed: %w", err)
	}
	if len(rows) == 0 {
		return nodeRouteAbsent, nil, nil
	}
	if len(rows) > 1 {
		// 视为异常脏数据: (host,port) 维度本应只有 1 条记录, 出现多条说明历史单据残留或人工误操作.
		// 此处必须把所有重复行的明细打到日志, 上层 mismatch 错误清单只能携带一条样本,
		// 没有日志辅助的话运维很难定位"重复"这一根因.
		logger.Warn(
			"F1 duplicate-rows detected on primary mysql.servers for [%s:%d], total=%d, dump all rows below:",
			host, port, len(rows))
		for i, r := range rows {
			logger.Warn(
				"  dup[%d/%d] server_name=%s host=%s port=%d wrapper=%s username=%s db=%s",
				i+1, len(rows), r.ServerName, r.Host, r.Port, r.Wrapper, r.Username, r.Db)
		}
		return nodeRouteMismatch, &rows[0], nil
	}
	srv := rows[0]
	if srv.Wrapper == wantWrapper && srv.Username == wantUser && srv.Password == wantPwd {
		return nodeRouteMatched, &srv, nil
	}
	return nodeRouteMismatch, &srv, nil
}

// countServerRowsAt 统计 ctl primary 的 mysql.servers 中 (host,port) 维度的记录条数,
// 用于区分 mismatch 是 field-mismatch 还是 duplicate-rows 场景.
func (a *AddSpiderRoutingComp) countServerRowsAt(host string, port int) (int, error) {
	// 移除重复的tc_admin=0设置，已在preInspectNodes入口处统一设置
	var cnt int
	if err := a.ctlConn.Get(&cnt,
		"select count(0) from mysql.servers where Host = ? and Port = ?",
		host, port); err != nil {
		return 0, fmt.Errorf("count mysql.servers failed: %w", err)
	}
	return cnt, nil
}

// buildMismatchManualFixHint 把 F1 mismatch 节点列表组装成一段可读的错误信息,
// 内含每个实例的现状与人工清理步骤; 上层捕获后会原样落到 dbactuator stderr/日志, 便于排障.
func buildMismatchManualFixHint(infos []nodeMismatchInfo) string {
	var sb strings.Builder
	sb.WriteString(fmt.Sprintf(
		"found %d node(s) already routed with conflicts (field-mismatch or duplicate-rows), "+
			"refuse to overwrite. please manually clean them and retry:\n",
		len(infos)))
	for i, info := range infos {
		switch info.Reason {
		case "duplicate-rows":
			sb.WriteString(fmt.Sprintf(
				"  [%d] %s:%d  reason=duplicate-rows dup_count=%d sample{server_name=%s, wrapper=%s, username=%s} "+
					"want{wrapper=%s, username=%s}  -- see dbactuator log for full dup list\n",
				i+1, info.IP, info.Port, info.DupCount,
				info.ExistServer.ServerName, info.ExistServer.Wrapper, info.ExistServer.Username,
				info.WantWrapper, info.WantUsername))
		default:
			sb.WriteString(fmt.Sprintf(
				"  [%d] %s:%d  reason=field-mismatch exist{server_name=%s, wrapper=%s, username=%s} "+
					"want{wrapper=%s, username=%s}\n",
				i+1, info.IP, info.Port,
				info.ExistServer.ServerName, info.ExistServer.Wrapper, info.ExistServer.Username,
				info.WantWrapper, info.WantUsername))
		}
	}
	sb.WriteString("manual fix steps (run on tdbctl primary):\n")
	sb.WriteString("  1) set tc_admin=1;\n")
	for _, info := range infos {
		// duplicate-rows 场景 server_name 只是其中一条样本, 提醒运维按 host/port 全量清理
		if info.Reason == "duplicate-rows" {
			sb.WriteString(fmt.Sprintf(
				"  2) clean ALL %d duplicate rows for host=%s port=%d "+
					"(e.g. TDBCTL DROP NODE IF EXISTS <each-server-name>);\n",
				info.DupCount, info.IP, info.Port))
		} else {
			sb.WriteString(fmt.Sprintf(
				"  2) TDBCTL DROP NODE IF EXISTS %s;   -- for %s:%d\n",
				info.ExistServer.ServerName, info.IP, info.Port))
		}
	}
	sb.WriteString("  3) TDBCTL FLUSH ROUTING;\n")
	sb.WriteString("then on each affected instance:\n")
	sb.WriteString("  4) set ddl_execute_by_ctl = 0; --if spider_version >3.x \n")
	sb.WriteString("  5) drop all business databases (keep system dbs: ")
	sb.WriteString(strings.Join(tcSkipCheckDBList, ","))
	sb.WriteString(");\n")
	sb.WriteString("after manual cleanup, retry this ticket.\n")
	return sb.String()
}

// deepInspectMatchedNode 对 F1 matched 节点做 F2/F3 深度体检.
//
// F2: 节点本地 mysql.servers 应至少包含本角色所需的最小路由条目;
// F3: 节点的业务表数量分布应与"同角色另一节点"完全一致.
func (a *AddSpiderRoutingComp) deepInspectMatchedNode(ip string) error {
	user, pwd, err := a.getCredByRole()
	if err != nil {
		return err
	}
	nodeConn, err := native.InsObject{
		Host: ip, Port: a.Params.AddPort, User: user, Pwd: pwd,
	}.Conn()
	if err != nil {
		return fmt.Errorf("F2/F3 connect node [%s:%d] failed: %w",
			ip, a.Params.AddPort, err)
	}
	defer nodeConn.Db.Close()

	// F2: 节点本地 mysql.servers 路由健康检测
	if err := a.inspectLocalRouting(ip, nodeConn); err != nil {
		return err
	}
	// F3: 业务表数量与对照节点一致
	if err := a.inspectBusinessTableConsistency(ip, nodeConn); err != nil {
		return err
	}
	return nil
}

// inspectLocalRouting F2: 待加入节点本机 mysql.servers 必须与 ctl primary 的路由集严格一致.
//
// 角色到比较范围:
//   - spider_master / spider_mnt: 比较 Wrapper='mysql'        子集
//   - spider_slave              : 比较 Wrapper='mysql_slave'  子集
//   - spider_ctl                : 比较整个 mysql.servers 集合
//
// 比较口径(按 ServerName/Host/Port/Wrapper 四元组集合):
//
//	primary 子集 == node 子集  且  node 中必须包含 "primary 自身这条 TDBCTL 路由".
//
// 后者用于证明节点确实订阅了 ctl primary 的路由广播, 而不是"凑巧本地有一份残留".
func (a *AddSpiderRoutingComp) inspectLocalRouting(ip string, nodeConn *native.DbWorker) error {
	primaryServers, err := a.ctlConn.SelectServers()
	if err != nil {
		return fmt.Errorf("F2 select primary mysql.servers failed: %w", err)
	}
	var nodeServers []native.Server
	if err := nodeConn.Queryx(&nodeServers,
		"select Server_name, Host, Db, Username, Password, Port, Wrapper from mysql.servers"); err != nil {
		return fmt.Errorf("F2 query local mysql.servers failed on [%s]: %w", ip, err)
	}

	// 1) 路由集合按角色比对
	var compareWrappers []string
	switch a.Params.AddSpiderRole {
	case addSpiderRoleMaster, addSpiderRoleMnt:
		compareWrappers = []string{"mysql"}
	case addSpiderRoleSlave:
		compareWrappers = []string{"mysql_slave"}
	case addSpiderRoleTdbctl:
		// nil 表示比较全集
		compareWrappers = nil
	default:
		return fmt.Errorf("F2 unsupported role: %s", a.Params.AddSpiderRole)
	}
	primarySub := filterServersByWrapper(primaryServers, compareWrappers)

	// spider_slave 角色特殊处理:
	// slave spider 节点本机看到的对端路由是 wrapper='mysql' / ServerName='SPT{N}' 形态,
	// 而 primary 上同一份对端的登记是 wrapper='mysql_slave' / ServerName='SPT_SLAVE{N}'.
	// 直接用 primary 的 mysql_slave 子集去比节点本机会永远不等, 所以这里把 primary 子集
	// 做一次语义归一化, 然后节点子集按 wrapper='mysql' 取, 即可走通用的集合相等判定.
	nodeWrappers := compareWrappers
	if a.Params.AddSpiderRole == addSpiderRoleSlave {
		primarySub = normalizeSlaveSubAsMaster(primarySub)
		nodeWrappers = []string{"mysql"}
	}
	nodeSub := filterServersByWrapper(nodeServers, nodeWrappers)

	if len(primarySub) == 0 {
		// 极端兜底: primary 上同 wrapper 一条都没有, 说明集群本身就不健康, 直接报错让人排查
		return fmt.Errorf(
			"F2 failed on [%s]: primary mysql.servers has 0 record for wrappers=%v, cluster routing unhealthy",
			ip, compareWrappers)
	}
	miss := diffServerKeys(primarySub, nodeSub)
	extra := diffServerKeys(nodeSub, primarySub)
	if len(miss) > 0 || len(extra) > 0 {
		return fmt.Errorf(
			"F2 failed on [%s]: local routing not equivalent to primary for wrappers=%v, "+
				"miss(in primary not in node)=%v, extra(in node not in primary)=%v",
			ip, compareWrappers, miss, extra)
	}

	// 2) 节点本机必须包含"primary 自身的 TDBCTL 路由", 证明它仍订阅着 primary 的路由广播
	primaryTdbctl, ok := a.pickPrimaryTdbctlServer(primaryServers)
	if !ok {
		return fmt.Errorf(
			"F2 failed on [%s]: cannot locate primary's TDBCTL self-record (host=%s port=%d) on primary",
			ip, a.ctlMasterIP, a.Params.Port)
	}
	if !containsServerKey(nodeServers, primaryTdbctl) {
		return fmt.Errorf(
			"F2 failed on [%s]: primary TDBCTL route [%s] missing in node's mysql.servers, "+
				"node may have lost subscription to primary",
			ip, serverKey(primaryTdbctl))
	}

	logger.Info("F2 ok: node [%s] local routing equals primary for role=%s wrappers=%v, "+
		"and primary's tdbctl self-record [%s] is present",
		ip, a.Params.AddSpiderRole, compareWrappers, serverKey(primaryTdbctl))
	return nil
}

// filterServersByWrapper 按 wrapper 白名单过滤 servers; wrappers 为 nil 时返回全集.
func filterServersByWrapper(servers []native.Server, wrappers []string) []native.Server {
	if wrappers == nil {
		return servers
	}
	set := make(map[string]struct{}, len(wrappers))
	for _, w := range wrappers {
		set[w] = struct{}{}
	}
	out := make([]native.Server, 0, len(servers))
	for _, s := range servers {
		if _, ok := set[s.Wrapper]; ok {
			out = append(out, s)
		}
	}
	return out
}

// normalizeSlaveSubAsMaster 把 primary 上 wrapper='mysql_slave' 的路由记录,
// 在语义上等价转换成 slave spider 节点本机看到的 wrapper='mysql' / ServerName='SPT{N}' 形态:
//   - Wrapper    : mysql_slave -> mysql
//   - ServerName : SPT_SLAVE   -> SPT  (仅替换首次出现的前缀, 避免极端中缀场景被多次替换)
//
// 仅用于 spider_slave 角色的 F2 比对; Host/Port/Db/Username/Password 等其它字段保持不变.
func normalizeSlaveSubAsMaster(servers []native.Server) []native.Server {
	out := make([]native.Server, 0, len(servers))
	for _, s := range servers {
		s.Wrapper = "mysql"
		s.ServerName = strings.Replace(s.ServerName, "SPT_SLAVE", "SPT", 1)
		out = append(out, s)
	}
	return out
}

// pickPrimaryTdbctlServer 从 primary 的 mysql.servers 中识别出
// "代表 ctl primary 自身的那条 TDBCTL 记录", 用于 F2 的存在性断言.
func (a *AddSpiderRoutingComp) pickPrimaryTdbctlServer(
	primaryServers []native.Server,
) (native.Server, bool) {
	for _, s := range primaryServers {
		if s.Wrapper == native.TDBCTL_PREFIX &&
			s.Host == a.ctlMasterIP && s.Port == a.Params.Port {
			return s, true
		}
	}
	return native.Server{}, false
}

// containsServerKey 在 servers 中查找是否存在与 target 同 (ServerName/Host/Port/Wrapper) 的记录.
func containsServerKey(servers []native.Server, target native.Server) bool {
	want := serverKey(target)
	for _, s := range servers {
		if serverKey(s) == want {
			return true
		}
	}
	return false
}

// diffServerKeys 返回 a 中存在但 b 中不存在的 (ServerName/Host/Port/Wrapper) 四元组.
func diffServerKeys(a, b []native.Server) []string {
	bSet := make(map[string]struct{}, len(b))
	for _, s := range b {
		bSet[serverKey(s)] = struct{}{}
	}
	var out []string
	for _, s := range a {
		k := serverKey(s)
		if _, ok := bSet[k]; !ok {
			out = append(out, k)
		}
	}
	sort.Strings(out)
	return out
}

func serverKey(s native.Server) string {
	return fmt.Sprintf("%s|%s|%d|%s", s.ServerName, s.Host, s.Port, s.Wrapper)
}

// inspectBusinessTableConsistency F3: 节点的业务表数量分布应与同集群已有的 spider_master 对照节点一致.
//
//   - 业务表数量来源: information_schema.TABLES 中 TABLE_TYPE='BASE TABLE' 的记录,
//     按 TABLE_SCHEMA 分组计数, 系统库使用 tcSkipCheckDBList 过滤;
//   - 对照节点选取规则:
//     在 primary mysql.servers 全集中挑选第一个满足 Wrapper='SPIDER' 且 Host 不在
//     a.Params.AddSpiders 内的节点 (即排除本批所有节点, 取已稳定运行的 spider_master 作为基准).
//     找不到则 warn 跳过, 不阻塞流程 (常见于全新集群首批扩容、或集群当前没有可用 spider_master 路由).
//
// 连接对端账号: 直接复用 RuntimeAccountParam.SpiderUser/SpiderPwd 登录对端 spider 业务端口.
func (a *AddSpiderRoutingComp) inspectBusinessTableConsistency(
	ip string, nodeConn *native.DbWorker,
) error {
	peer, ok, err := a.pickPeerForCompare()
	if err != nil {
		return fmt.Errorf("F3 pick peer failed: %w", err)
	}
	if !ok {
		logger.Warn("F3 skipped on [%s]: no peer node with Wrapper='SPIDER' found outside this batch (AddSpiders=%v)",
			ip, a.Params.AddSpiders)
		return nil
	}

	peerConn, err := native.InsObject{
		Host: peer.Host, Port: peer.Port,
		User: peer.Username, Pwd: peer.Password,
	}.Conn()
	if err != nil {
		return fmt.Errorf("F3 connect peer [%s:%d] failed: %w",
			peer.Host, peer.Port, err)
	}
	defer peerConn.Db.Close()

	nodeStat, err := queryBusinessTableCount(nodeConn)
	if err != nil {
		return fmt.Errorf("F3 query node [%s] table count failed: %w", ip, err)
	}
	peerStat, err := queryBusinessTableCount(peerConn)
	if err != nil {
		return fmt.Errorf("F3 query peer [%s:%d] table count failed: %w",
			peer.Host, peer.Port, err)
	}

	if diff := diffTableStat(nodeStat, peerStat); diff != "" {
		return fmt.Errorf(
			"F3 failed on [%s]: business table count mismatch with peer [%s:%d]\n%s",
			ip, peer.Host, peer.Port, diff)
	}
	logger.Info("F3 ok: node [%s] business table distribution equals peer [%s:%d]",
		ip, peer.Host, peer.Port)
	return nil
}

// pickPeerForCompare 从 primary mysql.servers 全集中挑选 F3 对照节点:
//   - Wrapper = 'SPIDER'
//   - Host 不在 a.Params.AddSpiders 内 (排除本批所有节点, 仅以已存在的 spider_master 为基准)
//   - 取第一个满足条件的记录
//
// 找不到时返回 ok=false, 由调用方 warn 跳过.
func (a *AddSpiderRoutingComp) pickPeerForCompare() (native.Server, bool, error) {
	servers, err := a.ctlConn.SelectServers()
	if err != nil {
		return native.Server{}, false, err
	}
	batchHosts := make(map[string]struct{}, len(a.Params.AddSpiders))
	for _, ip := range a.Params.AddSpiders {
		batchHosts[ip] = struct{}{}
	}
	for _, s := range servers {
		if s.Wrapper != native.SPIDER_PREFIX {
			continue
		}
		if _, inBatch := batchHosts[s.Host]; inBatch {
			continue
		}
		return s, true, nil
	}
	return native.Server{}, false, nil
}

// queryBusinessTableCount 统计某节点上 (排除系统库后) 每个 db 的 BASE TABLE 数量.
func queryBusinessTableCount(conn *native.DbWorker) (map[string]int, error) {
	// IN (?, ?, ?, ...) 占位符, 防注入也防字符串拼接出错
	placeholders := make([]string, len(tcSkipCheckDBList))
	args := make([]interface{}, len(tcSkipCheckDBList))
	for i, db := range tcSkipCheckDBList {
		placeholders[i] = "?"
		args[i] = db
	}
	sqlStr := fmt.Sprintf(
		"select TABLE_SCHEMA, count(*) as cnt from information_schema.TABLES "+
			"where TABLE_TYPE = 'BASE TABLE' and TABLE_SCHEMA not in (%s) "+
			"group by TABLE_SCHEMA",
		strings.Join(placeholders, ","),
	)
	rows, err := conn.Db.Query(sqlStr, args...)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	out := make(map[string]int)
	for rows.Next() {
		var db string
		var cnt int
		if err := rows.Scan(&db, &cnt); err != nil {
			return nil, err
		}
		out[db] = cnt
	}
	if err := rows.Err(); err != nil {
		return nil, err
	}
	return out, nil
}

// diffTableStat 返回两份业务表分布的差异描述; 完全一致则返回空串.
func diffTableStat(node, peer map[string]int) string {
	var lines []string
	// node 中存在的 db
	dbs := make([]string, 0, len(node)+len(peer))
	seen := make(map[string]struct{})
	for db := range node {
		if _, ok := seen[db]; !ok {
			dbs = append(dbs, db)
			seen[db] = struct{}{}
		}
	}
	for db := range peer {
		if _, ok := seen[db]; !ok {
			dbs = append(dbs, db)
			seen[db] = struct{}{}
		}
	}
	sort.Strings(dbs)
	for _, db := range dbs {
		nc, np := node[db], peer[db]
		if nc != np {
			lines = append(lines,
				fmt.Sprintf("  db=%s node_tables=%d peer_tables=%d", db, nc, np))
		}
	}
	if len(lines) == 0 {
		return ""
	}
	return "table count diff:\n" + strings.Join(lines, "\n")
}

// resolveWrapperBySpiderRole 角色 -> wrapper
func resolveWrapperBySpiderRole(role string) (string, error) {
	switch role {
	case addSpiderRoleSlave:
		return native.SPIDER_SLAVE_PREFIX, nil
	case addSpiderRoleMaster, addSpiderRoleMnt:
		return native.SPIDER_PREFIX, nil
	case addSpiderRoleTdbctl:
		return native.TDBCTL_PREFIX, nil
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
	user, passwd, err := a.getCredByRole()
	if err != nil {
		return err
	}
	return a.execCreateNodeWithConcurrent(
		user, passwd,
		a.realAddSpiders, a.Params.AddPort, wrapper,
	)
}

// addNodesInNonParallel 对应 Python add_nodes_in_non_parallel
func (a *AddSpiderRoutingComp) addNodesInNonParallel() error {
	wrapper, err := resolveWrapperBySpiderRole(a.Params.AddSpiderRole)
	if err != nil {
		return err
	}
	user, passwd, err := a.getCredByRole()
	if err != nil {
		return err
	}
	for _, ip := range a.realAddSpiders {
		if err := a.execCreateNode(
			user, passwd,
			ip, a.Params.AddPort, wrapper,
		); err != nil {
			return err
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
	// 节点是否需要新建在 preInspectNodes 阶段已判定, 这里直接使用 ips 即可
	if len(ips) == 0 {
		logger.Warn("no node need to add for wrapper=%s, skip", wrapper)
		return nil
	}

	// 拼 SQL
	var sb strings.Builder
	sb.WriteString(fmt.Sprintf("tdbctl create node wrapper '%s' options ", wrapper))
	for i, host := range ips {
		sb.WriteString(fmt.Sprintf("(user '%s', password '%s', host '%s', port %d) ",
			user, passwd, host, port))
		if i == len(ips)-1 {
			sb.WriteString("with database;")
		} else {
			sb.WriteString(",")
		}
	}
	createSQL := sb.String()

	cmds := []string{
		"set tc_admin=1",
		"SET tc_use_internal_backup_tool = OFF",
		"SET GLOBAL tc_use_internal_backup_tool = OFF",
		fmt.Sprintf("SET GLOBAL tc_skip_check_db_list = '%s'", strings.Join(tcSkipCheckDBList, ",")),
		createSQL,
	}
	logger.Info("exec parallel add-node cmds: %v", maskSQLs(cmds, passwd))

	if _, err := a.ctlConn.ExecMore(cmds); err != nil {
		return fmt.Errorf("parallel create node failed: %w", err)
	}
	logger.Info("parallel add-node succeed: wrapper=%s, hosts=%v, port=%d", wrapper, ips, port)
	return nil
}

// execCreateNode 对应 Python _exec_create_node (串行单条添加)
func (a *AddSpiderRoutingComp) execCreateNode(
	user, passwd, spiderIP string, spiderPort int, wrapper string,
) error {
	// 节点是否需要新建在 preInspectNodes 阶段已判定, 这里直接执行
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
