package add_priv

import (
	"dbm-services/mysql/priv-service/service"
	"dbm-services/mysql/priv-service/service/v2/internal"
	"dbm-services/mysql/priv-service/service/v2/internal/drs"
	"fmt"
	"log/slog"
	"strconv"
	"strings"

	"github.com/pkg/errors"
)

// versionRelatedInfo 从目标实例上一次探到的和版本相关的信息, 后续所有按版本分支的地方都从这里拿, 不再重复探测
//
//	RawVersion   @@version 原始字符串
//	Product      spider / mysql
//	VersionAsInt @@version 前缀的 base 版本编码 X*10000 + Y*100 + Z, mysql/spider 同一套
//	             (5.7.30-log -> 50730; 5.7.20-tspider-4.x -> 50720; 5.5.24-tspider-3.x -> 50524)
//	             建用户语法界就靠这个直接和 50700 比, 对齐 procedure.sql 里 SUBSTRING_INDEX(@@version, ".", 2) < 5.7
//	AuthColName  mysql.user 里存密码的列名, "password" 或 "authentication_string"
//	             tspider 的判据和 mysql 不同 (procedure.sql 里 check_password 是按 tspider-N 分的), 单独存一个字段
type versionRelatedInfo struct {
	RawVersion   string
	Product      string
	VersionAsInt int64
	AuthColName  string
}

//const (
//	productSpider = "spider"
//	productMySQL  = "mysql"
//)

func (c *PrivTaskPara) addOnMySQL(
	clientIps []string, workingInstances map[int64][]string,
	dbScopePrivs map[string][]string,
	longPSW string,
	shortPSW string,
) (reports map[string][]string, err error) {
	reports = make(map[string][]string)

	// 版本相关信息 (密码列、CREATE USER 语法界等) 顶层探一次, 下面 check / grant 都从这里读
	versionInfosByCloud := make(map[int64]map[string]versionRelatedInfo, len(workingInstances))
	for bkCloudId, addrs := range workingInstances {
		infos, err := queryVersionInfo(bkCloudId, addrs)
		if err != nil {
			return nil, err
		}
		versionInfosByCloud[bkCloudId] = infos
	}

	// Go 侧预检. 有报告说明发现冲突, 直接返回, 不再走 dba_grant 里存储过程的检查
	// existingUsers: addr -> clientIp set, 已存在的用户不再生成建用户语句
	checkReports, existingUsers, err := c.check(clientIps, workingInstances, versionInfosByCloud, dbScopePrivs, longPSW, shortPSW)
	if err != nil {
		return nil, err
	}
	if len(checkReports) > 0 {
		return checkReports, nil
	}

	if err := c.grant(clientIps, workingInstances, versionInfosByCloud, dbScopePrivs, longPSW, existingUsers, reports); err != nil {
		return nil, err
	}
	slog.Info(
		"add on mysql finish",
		slog.Any("reports", reports),
	)

	return reports, nil
}

/*
这个存储过程本身是有限制的
client ip 和 db list 最大只能 2000 长
db list不太可能超长, 因为前面把 dbname 单独循环了
client ip 有可能, 所以这里要切分下
*/
func (c *PrivTaskPara) addOneDtOnMySQL(
	clientIps []string,
	workingInstances map[int64][]string,
	accountAndRuleDetails *accountAndRule,
	psw *service.MultiPsw,
	dt *service.TbAccountRules,
	reports map[string][]string,
) error {
	var oneBatchClients []string
	for idx, ip := range clientIps {
		// 限长 100 代码会比较好些, 不往极限的 2000 搞
		oneBatchClients = append(oneBatchClients, ip)
		if len(oneBatchClients) > 100 || idx == len(clientIps)-1 {
			slog.Info("add one dt on mysql", slog.Any("one batch client", oneBatchClients))
			// 一次跑一批 client
			err := c.addOneDtOnMySQLForSplitClient(
				strings.Join(oneBatchClients, ","),
				workingInstances,
				accountAndRuleDetails,
				psw,
				dt,
				reports,
			)
			if err != nil {
				slog.Error("add on mysql", slog.String("err", err.Error()))
				return err
			}
			oneBatchClients = []string{}
		}
	}
	return nil
}

func (c *PrivTaskPara) addOneDtOnMySQLForSplitClient(
	clientIpsStr string,
	workingInstances map[int64][]string,
	accountAndRuleDetails *accountAndRule,
	psw *service.MultiPsw,
	dt *service.TbAccountRules,
	reports map[string][]string,
) error {
	for bkCloudId, workingInstanceAddrs := range workingInstances {
		slog.Info(
			"add on mysql call procedure",
			slog.Any("addrs", workingInstanceAddrs),
			slog.String("user", accountAndRuleDetails.TbAccount.User),
			slog.String("ipstr", clientIpsStr),
			slog.String("dbname", dt.Dbname),
			slog.String("psw", psw.Psw),
			slog.String("old psw", psw.OldPsw),
			slog.String("priv", dt.DmlDdlPriv),
			slog.String("global priv", dt.GlobalPriv),
		)
		drsRes, err := drs.RPCMySQL(
			bkCloudId,
			workingInstanceAddrs,
			[]string{
				fmt.Sprintf(
					`CALL infodba_schema.dba_grant('%s', '%s', '%s', '%s', '%s', '%s', '%s')`,
					accountAndRuleDetails.TbAccount.User,
					clientIpsStr,
					dt.Dbname,
					psw.Psw,
					psw.OldPsw,
					dt.DmlDdlPriv,
					dt.GlobalPriv,
				),
			},
			true,
			600,
		)
		// 调用 api 有问题, 比如 request body
		if err != nil {
			slog.Error("add on mysql", slog.String("err", err.Error()))
			return err
		}
		// 这里其实有个没检查, 不过应该不太可能
		// len(workingInstanceAddrs) == len(drsRes)
		slog.Info("add on mysql", slog.String("response", fmt.Sprintf("%+v", drsRes)))
		readOneDtRes(bkCloudId, drsRes, reports)
	}

	return nil
}

func readOneDtRes(bkCloudId int64, res []*drs.OneAddressResult, reports map[string][]string) {
	for _, r := range res {
		// 和 addr 建立连接之类的有问题
		// 这个错误应该收集起来
		if r.ErrorMsg != "" {
			err := errors.New(r.ErrorMsg)
			slog.Error(
				"add on mysql",
				slog.String("err", err.Error()),
				slog.String("addr", r.Address),
			)
			reports[r.Address] = []string{r.ErrorMsg}
			continue
		}
		readOneAddrRes(bkCloudId, r, reports)
	}
}

func readOneAddrRes(bkCloudId int64, r *drs.OneAddressResult, reports map[string][]string) {
	errMsg := r.CmdResults[0].ErrorMsg
	if errMsg == "" {
		return
	}

	if _, ok := reports[r.Address]; !ok {
		reports[r.Address] = make([]string, 0)
	}

	_, sqlStat, msgText, isException := internal.ParseMySQLErrStr(errMsg)
	if !isException {
		reports[r.Address] = append(reports[r.Address], msgText)
		return
	}

	switch sqlStat {
	case 32401:
		reports[r.Address] = append(reports[r.Address], msgText)
	case 32402:
		// 冲突检测错误
		readConflictReport(msgText, bkCloudId, r.Address, reports)
	default:
		reports[r.Address] = append(reports[r.Address], msgText)
	}
}

// 这个函数的所有错误都要收集了, 不能 return
func readConflictReport(uuid string, bkCloudId int64, addr string, reports map[string][]string) {
	r, err := drs.RPCMySQL(
		bkCloudId,
		[]string{addr},
		[]string{
			fmt.Sprintf(`SELECT * FROM infodba_schema.dba_grant_result WHERE id = '%s'`, uuid),
		},
		false,
		600,
	)
	if err != nil {
		slog.Error("add on mysql read conflict report", slog.String("err", err.Error()))
		reports[addr] = append(reports[addr], err.Error())
		return
	}

	if r[0].ErrorMsg != "" {
		slog.Error("add on mysql read conflict report", slog.String("err", r[0].ErrorMsg))
		reports[addr] = append(reports[addr], r[0].ErrorMsg)
		return
	}

	if r[0].CmdResults[0].ErrorMsg != "" {
		slog.Error("add on mysql read conflict report", slog.String("err", r[0].CmdResults[0].ErrorMsg))
		reports[addr] = append(reports[addr], r[0].CmdResults[0].ErrorMsg)
		return
	}

	for _, row := range r[0].CmdResults[0].TableData {
		dbname, ok := row["dbname"].(string)
		var msg string
		if ok {
			msg = fmt.Sprintf(
				`apply %s@%s on %s: %s`,
				row["username"], row["client_ip"], dbname, row["msg"],
			)
		} else {
			msg = fmt.Sprintf(
				`apply %s@%s: %s`,
				row["username"], row["client_ip"], row["msg"],
			)
		}

		slog.Error("add on mysql read conflict report", slog.String("msg", msg))
		reports[addr] = append(reports[addr], msg)
	}
	return
}

// check 把 procedure.sql 的密码检查和库冲突检查搬到 Go 侧
// 在 addOnMySQL 入口一次性把所有 addr 的检查跑完, 有冲突就直接返回, 不再走 dba_grant 里的存储过程检查
// 同时收集 existingUsers (addr -> clientIp set), 供 grant 阶段跳过已有用户的建用户语句
// versionInfosByCloud 由调用方 (addOnMySQL) 顶层探一次后传入, 内部不重复探
func (c *PrivTaskPara) check(
	clientIps []string,
	workingInstances map[int64][]string,
	versionInfosByCloud map[int64]map[string]versionRelatedInfo,
	dbScopePrivs map[string][]string,
	longPSW string,
	shortPSW string,
) (map[string][]string, map[string]map[string]bool, error) {
	reports := make(map[string][]string)
	existingUsers := make(map[string]map[string]bool)

	// dbScopePrivs 的 key: 具体 dbname 表示 db 级权限, "*" 表示全局权限
	// 库冲突只关心 dbname 字面, 过滤掉 "*"
	dbs := make([]string, 0, len(dbScopePrivs))
	for db := range dbScopePrivs {
		if db == "*" {
			continue
		}
		dbs = append(dbs, db)
	}

	for bkCloudId, addrs := range workingInstances {
		addrVersionRelateInfos := versionInfosByCloud[bkCloudId]

		// spider 中控和 backend 可能不同版本, auth_col 不能假设一致
		// 按 auth_col 把 addr 拆开, 各自跑一次 SELECT
		addrsByAuthCol := make(map[string][]string)
		for addr, info := range addrVersionRelateInfos {
			addrsByAuthCol[info.AuthColName] = append(addrsByAuthCol[info.AuthColName], addr)
		}

		for pswCol, groupAddrs := range addrsByAuthCol {
			if err := checkPsw(
				bkCloudId, groupAddrs, c.User, clientIps,
				longPSW, shortPSW, pswCol, reports, existingUsers,
			); err != nil {
				return nil, nil, err
			}
		}

		// 库冲突检查跟 mysql.db 表结构相关, 各版本一致, 不用按 auth_col 分拨, 整批一次
		// 只有全局权限 (dbScopePrivs 只有 "*" key) 时 dbs 是空, 跳过
		if len(dbs) > 0 {
			if err := checkDbConflict(
				bkCloudId, addrs, c.User, clientIps, dbs, reports,
			); err != nil {
				return nil, nil, err
			}
		}
	}

	return reports, existingUsers, nil
}

// queryVersionInfo 一次探完目标实例上版本相关的所有信息, 供后续所有按版本分支的地方复用
// 判定尽量推给 db 自己算, Go 只拿结果直接拼下一条 SQL
//
// 密码列判据 (完全对齐 procedure.sql 的 check_password):
//
//	tspider-1 / tspider-2 -> password
//	tspider-3 / tspider-4 -> authentication_string
//	其它 tspider           -> 不支持, 直接报错 (对齐 procedure.sql 的 SIGNAL '32401')
//	MySQL < 5.7           -> password
//	MySQL >= 5.7          -> authentication_string
//
// 任一 addr 探测报错(网络/RPC/SQL 执行/结果为空/版本不支持)直接返回错误, 不吞
func queryVersionInfo(bkCloudId int64, addrs []string) (map[string]versionRelatedInfo, error) {
	query := `SELECT
		@@version AS raw_version,
		CASE WHEN @@version LIKE '%tspider%' THEN 'spider' ELSE 'mysql' END AS product,
		CAST(SUBSTRING_INDEX(@@version, '.', 1) AS UNSIGNED) * 10000 +
		CAST(SUBSTRING_INDEX(SUBSTRING_INDEX(@@version, '.', 2), '.', -1) AS UNSIGNED) * 100 +
		CAST(SUBSTRING_INDEX(SUBSTRING_INDEX(@@version, '.', 3), '.', -1) AS UNSIGNED) AS version_as_int,
		CASE
			WHEN @@version LIKE '%tspider-1%' OR @@version LIKE '%tspider-2%' OR @@version LIKE '%tspider-3%' THEN 'password'
			WHEN @@version LIKE '%tspider-4%' THEN 'authentication_string'
			WHEN @@version LIKE '%tspider%' THEN ''
			WHEN CAST(SUBSTRING_INDEX(@@version, '.', 1) AS UNSIGNED) * 10000 +
			     CAST(SUBSTRING_INDEX(SUBSTRING_INDEX(@@version, '.', 2), '.', -1) AS UNSIGNED) * 100 < 50700 THEN 'password'
			ELSE 'authentication_string'
		END AS auth_col_name`

	res, err := drs.RPCMySQL(bkCloudId, addrs, []string{query}, false, 600)
	if err != nil {
		return nil, err
	}

	ret := make(map[string]versionRelatedInfo, len(addrs))
	for _, r := range res {
		if r.ErrorMsg != "" {
			return nil, errors.Errorf("query version info on %s: %s", r.Address, r.ErrorMsg)
		}
		cr := r.CmdResults[0]
		if cr.ErrorMsg != "" {
			return nil, errors.Errorf("query version info on %s: %s", r.Address, cr.ErrorMsg)
		}
		if len(cr.TableData) == 0 {
			return nil, errors.Errorf("query version info on %s: empty result", r.Address)
		}
		row := cr.TableData[0]

		raw, _ := row["raw_version"].(string)
		product, _ := row["product"].(string)
		col, _ := row["auth_col_name"].(string)
		if col == "" {
			return nil, errors.Errorf("not support spider version on %s: %s", r.Address, raw)
		}
		vintStr, _ := row["version_as_int"].(string)
		vint, _ := strconv.ParseInt(vintStr, 10, 64)
		ret[r.Address] = versionRelatedInfo{
			RawVersion:   raw,
			Product:      product,
			VersionAsInt: int64(vint),
			AuthColName:  col,
		}
	}
	return ret, nil
}

// checkPsw 密码一致性检查 + 收集已存在的 user@host
// existingUsers: addr -> clientIp set, 记录该 addr 上已存在的用户, 供 grant 阶段跳过建用户语句
// mismatch 的行写入 reports, 上层通过 len(reports) > 0 判断是否中止
func checkPsw(
	bkCloudId int64,
	addrs []string,
	user string,
	clientIps []string,
	longPsw string,
	shortPsw string,
	pswCol string,
	reports map[string][]string,
	existingUsers map[string]map[string]bool,
) error {
	sql := buildPswCheckSQL(user, clientIps, longPsw, shortPsw, pswCol)
	slog.Info("check psw", slog.Any("addrs", addrs), slog.String("sql", sql))

	res, err := drs.RPCMySQL(bkCloudId, addrs, []string{sql}, false, 600)
	if err != nil {
		return err
	}

	for _, r := range res {
		if r.ErrorMsg != "" {
			reports[r.Address] = append(reports[r.Address], fmt.Sprintf("[%s] %s", r.Address, r.ErrorMsg))
			continue
		}
		cr := r.CmdResults[0]
		if cr.ErrorMsg != "" {
			reports[r.Address] = append(reports[r.Address], fmt.Sprintf("[%s] %s", r.Address, cr.ErrorMsg))
			continue
		}
		for _, row := range cr.TableData {
			clientIp, _ := row["client_ip"].(string)
			status, _ := row["status"].(string)

			if existingUsers[r.Address] == nil {
				existingUsers[r.Address] = make(map[string]bool)
			}
			existingUsers[r.Address][clientIp] = true

			if status == "mismatch" {
				reports[r.Address] = append(
					reports[r.Address],
					fmt.Sprintf("[%s] apply %s@%v: password not match", r.Address, user, clientIp),
				)
			}
		}
	}
	return nil
}

// checkDbConflict 库模式冲突检查
// 对入参 addrs 发一次 RPC 跑一条 SELECT, 返回 (host, apply_db, applied_db) 三元组:
// 申请库和已授权库模式相互匹配上但字面又不等, 需要人肉判一下
func checkDbConflict(
	bkCloudId int64,
	addrs []string,
	user string,
	clientIps []string,
	dbs []string,
	reports map[string][]string,
) error {
	sql := buildDbConflictSQL(user, clientIps, dbs)
	slog.Info("check db conflict", slog.Any("addrs", addrs), slog.String("sql", sql))

	res, err := drs.RPCMySQL(bkCloudId, addrs, []string{sql}, false, 600)
	if err != nil {
		return err
	}

	for _, r := range res {
		if r.ErrorMsg != "" {
			reports[r.Address] = append(reports[r.Address], fmt.Sprintf("[%s] %s", r.Address, r.ErrorMsg))
			continue
		}
		cr := r.CmdResults[0]
		if cr.ErrorMsg != "" {
			reports[r.Address] = append(reports[r.Address], fmt.Sprintf("[%s] %s", r.Address, cr.ErrorMsg))
			continue
		}
		for _, row := range cr.TableData {
			reports[r.Address] = append(
				reports[r.Address],
				fmt.Sprintf(
					"[%s] apply %s@%v on %v: conflict with applied db [%v]",
					r.Address, user, row["client_ip"], row["apply_db"], row["applied_db"],
				),
			)
		}
	}
	return nil
}

// buildPswCheckSQL 返回所有已存在的 user@host 及密码匹配状态
// 返回列: client_ip, status ('ok' | 'mismatch')
// 不存在的 host 不出现在结果集, grant 阶段需要为其生成建用户语句
//
// pswCol == "password": 老版本 mysql / tspider-1,2, longPsw 或 shortPsw 任一匹配即 ok
// pswCol == 其它 (即 authentication_string): 5.7+ / tspider-3,4, 只比 longPsw
func buildPswCheckSQL(user string, clientIps []string, longPsw, shortPsw, pswCol string) string {
	var matchExpr string
	if pswCol == "password" {
		matchExpr = fmt.Sprintf(
			`CASE WHEN CONVERT(%s USING utf8) COLLATE utf8_bin IN ('%s','%s') THEN 'ok' ELSE 'mismatch' END`,
			pswCol, longPsw, shortPsw,
		)
	} else {
		matchExpr = fmt.Sprintf(
			`CASE WHEN CONVERT(%s USING utf8) COLLATE utf8_bin = '%s' THEN 'ok' ELSE 'mismatch' END`,
			pswCol, longPsw,
		)
	}

	return fmt.Sprintf(
		`SELECT host AS client_ip, %s AS status FROM mysql.user `+
			`WHERE user = CONVERT('%s' USING utf8) COLLATE utf8_bin `+
			`AND host IN (%s)`,
		matchExpr,
		user,
		quoteJoin(clientIps),
	)
}

// buildDbConflictSQL 返回申请库和已授权库模式相互匹配、但字面不等的三元组
// 已授权库来自 mysql.db, 申请库来自 UNION ALL 拼的临时表
func buildDbConflictSQL(user string, clientIps []string, dbs []string) string {
	unions := make([]string, 0, len(dbs))
	for _, db := range dbs {
		unions = append(unions, fmt.Sprintf("SELECT '%s' AS db", db))
	}

	return fmt.Sprintf(
		`SELECT d.host AS client_ip, r.db AS apply_db, d.db AS applied_db `+
			`FROM mysql.db d `+
			`JOIN (%s) r ON 1 = 1 `+
			`WHERE d.user = CONVERT('%s' USING utf8) COLLATE utf8_bin `+
			`AND d.host IN (%s) `+
			`AND CONVERT(r.db USING utf8) COLLATE utf8_bin <> d.db `+
			`AND (CONVERT(r.db USING utf8) COLLATE utf8_bin LIKE d.db `+
			`OR d.db LIKE CONVERT(r.db USING utf8) COLLATE utf8_bin)`,
		strings.Join(unions, " UNION ALL "),
		user,
		quoteJoin(clientIps),
	)
}

func quoteJoin(ss []string) string {
	quoted := make([]string, 0, len(ss))
	for _, s := range ss {
		quoted = append(quoted, fmt.Sprintf("'%s'", s))
	}
	return strings.Join(quoted, ",")
}

// grant 把 procedure.sql 里 dba_grant_one_ip / dba_grant_one_ip_db 的建用户和授权搬到 Go 侧
//
// existingUsers (addr -> clientIp set) 来自上游 check 阶段:
//   - 已存在的用户不再生成建用户语句 (CREATE USER / GRANT USAGE ... IDENTIFIED BY PASSWORD)
//     避免 < 5.7 的 GRANT USAGE 把 old_password 升级成 native_password
//   - >= 5.7 同样跳过, CREATE USER IF NOT EXISTS 虽然幂等但跳过更干净
//   - 权限 GRANT 语句对所有 clientIps 都生成 (已有用户需要追加新库权限)
//
// 按 (bkCloudId, VersionAsInt < 50700) 分两组, 每组一次 RPC 把 SET + 建用户 + GRANT 一把梭
// versionInfosByCloud 由调用方 (addOnMySQL) 顶层探一次后传入, 内部不重复探
func (c *PrivTaskPara) grant(
	clientIps []string,
	workingInstances map[int64][]string,
	versionInfosByCloud map[int64]map[string]versionRelatedInfo,
	dbScopePrivs map[string][]string,
	longPSW string,
	existingUsers map[string]map[string]bool,
	reports map[string][]string,
) error {
	for bkCloudId := range workingInstances {
		infos := versionInfosByCloud[bkCloudId]

		var createUserAddrs, grantUsageAddrs []string
		for addr, info := range infos {
			if info.VersionAsInt < 50700 {
				grantUsageAddrs = append(grantUsageAddrs, addr)
			} else {
				createUserAddrs = append(createUserAddrs, addr)
			}
		}

		// >= 5.7: CREATE USER IF NOT EXISTS
		if len(createUserAddrs) > 0 {
			sqls := buildGrantSQLs(c.User, clientIps, dbScopePrivs, longPSW, true, existingUsers, createUserAddrs)
			if err := runGrant(bkCloudId, createUserAddrs, sqls, reports); err != nil {
				return err
			}
		}

		// < 5.7: GRANT USAGE ... IDENTIFIED BY PASSWORD
		if len(grantUsageAddrs) > 0 {
			sqls := buildGrantSQLs(c.User, clientIps, dbScopePrivs, longPSW, false, existingUsers, grantUsageAddrs)
			if err := runGrant(bkCloudId, grantUsageAddrs, sqls, reports); err != nil {
				return err
			}
		}
	}
	return nil
}

// buildGrantSQLs 拼一组同版本 addr 上要顺序执行的 SQL 列表
//
//	useCreateUser = true  -> CREATE USER IF NOT EXISTS ... IDENTIFIED WITH mysql_native_password AS (mysql >= 5.7)
//	useCreateUser = false -> GRANT USAGE ON *.* ... IDENTIFIED BY PASSWORD                          (mysql <  5.7)
//
// existingUsers 中已存在的 user@host 不生成建用户语句, 只生成 GRANT 权限语句
// 因为同一批 addrs 共享一组 SQL, 只有在所有 addrs 上都已存在的 clientIp 才能跳过
//
// SQL 顺序: SET sql_log_bin -> N × 建用户 -> N × M × GRANT
// dbScopePrivs 的 key "*" -> ON *.*, 其它 -> ON `dbname`.*
func buildGrantSQLs(
	user string, clientIps []string, dbScopePrivs map[string][]string, longPSW string, useCreateUser bool,
	existingUsers map[string]map[string]bool, addrs []string,
) []string {
	sqls := []string{"SET SESSION sql_log_bin = 0"}

	for _, ip := range clientIps {
		if needCreateUser(ip, existingUsers, addrs) {
			if useCreateUser {
				sqls = append(
					sqls, fmt.Sprintf(
						`CREATE USER IF NOT EXISTS '%s'@'%s' IDENTIFIED WITH mysql_native_password AS '%s'`,
						user, ip, longPSW,
					),
				)
			} else {
				sqls = append(
					sqls, fmt.Sprintf(
						`GRANT USAGE ON *.* TO '%s'@'%s' IDENTIFIED BY PASSWORD '%s'`,
						user, ip, longPSW,
					),
				)
			}
		}
	}

	for db, privs := range dbScopePrivs {
		if len(privs) == 0 {
			continue
		}
		privStr := strings.Join(privs, ",")
		var onClause string
		if db == "*" {
			onClause = "*.*"
		} else {
			onClause = fmt.Sprintf("`%s`.*", db)
		}
		for _, ip := range clientIps {
			sqls = append(
				sqls, fmt.Sprintf(
					`GRANT %s ON %s TO '%s'@'%s'`,
					privStr, onClause, user, ip,
				),
			)
		}
	}

	sqls = append(sqls, "FLUSH PRIVILEGES")
	return sqls
}

// needCreateUser 判断是否需要为 ip 生成建用户语句
// 只有当该 ip 在所有目标 addrs 上都已存在时才跳过
func needCreateUser(ip string, existingUsers map[string]map[string]bool, addrs []string) bool {
	for _, addr := range addrs {
		if !existingUsers[addr][ip] {
			return true
		}
	}
	return false
}

// runGrant 对一组同版本 addr 发一次 RPC, 逐 addr 逐 cmd 收错到 reports
// 单条 SQL 出错不影响其它 addr / 其它 SQL, 全部收集后由上层统一处理
func runGrant(bkCloudId int64, addrs []string, sqls []string, reports map[string][]string) error {
	slog.Info("grant", slog.Any("addrs", addrs), slog.Any("sqls", sqls))

	res, err := drs.RPCMySQL(bkCloudId, addrs, sqls, true, 600)
	if err != nil {
		return err
	}

	for _, r := range res {
		if r.ErrorMsg != "" {
			reports[r.Address] = append(reports[r.Address], r.ErrorMsg)
			continue
		}
		for _, cr := range r.CmdResults {
			if cr.ErrorMsg != "" {
				reports[r.Address] = append(
					reports[r.Address],
					fmt.Sprintf("%s: %s", cr.Cmd, cr.ErrorMsg),
				)
			}
		}
	}
	return nil
}
