package service

import (
	"errors"
	"fmt"
	"regexp"
	"strconv"
	"strings"
	"sync"
	"time"

	"golang.org/x/exp/slog"

	"dbm-services/common/go-pubpkg/errno"
	"dbm-services/mysql/db-partition/model"
	"dbm-services/mysql/db-partition/monitor"

	"github.com/spf13/viper"
)

// GetPartitionDbLikeTbLike TODO
func (config *PartitionConfig) GetPartitionDbLikeTbLike(dbtype string, splitCnt int) ([]InitSql, []string, []string,
	error) {
	var addSqls, dropSqls, errs Messages
	var initSqls InitMessages
	var err error
	initSqls.list = []InitSql{}
	addSqls.list = []string{}
	dropSqls.list = []string{}
	errs.list = []string{}

	tbs, errOuter := config.GetDbTableInfo()
	if errOuter != nil {
		slog.Error("GetDbTableInfo error", errOuter)
		return nil, nil, nil, fmt.Errorf("get database and table info failed：%s", errOuter.Error())
	}
	var sql string
	var needSize int
	wg := sync.WaitGroup{}
	tokenBucket := make(chan int, 10)
	for _, tb := range tbs {
		wg.Add(1)
		tokenBucket <- 0
		slog.Info(fmt.Sprintf("get init/add/drop partition for (domain:%s, dbname:%s, table_name:%s)", tb.ImmuteDomain,
			tb.DbName, tb.TbName))
		go func(tb ConfigDetail) {
			defer func() {
				<-tokenBucket
				wg.Done()
			}()
			if tb.Partitioned {
				sql, err = tb.GetAddPartitionSql()
				if err != nil {
					slog.Error("msg", "GetAddPartitionSql error", err)
					AddString(&errs, err.Error())
					return
				}
				AddString(&addSqls, sql)
				sql, err = tb.GetDropPartitionSql()
				if err != nil {
					slog.Error("msg", "GetDropPartitionSql error", err)
					AddString(&errs, err.Error())
					return
				}
				AddString(&dropSqls, sql)
			} else {
				sql, needSize, err = tb.GetInitPartitionSql(dbtype, splitCnt)
				if err != nil {
					slog.Error("msg", "GetInitPartitionSql error", err)
					AddString(&errs, err.Error())
					return
				}
				AddInit(&initSqls, InitSql{sql, needSize})
			}
			return
		}(tb)
	}
	wg.Wait()
	close(tokenBucket)
	if len(errs.list) > 0 {
		err := fmt.Errorf("partition rule: [dblike:`%s` tblike:`%s`] get partition sql error\n%s",
			config.DbLike, config.TbLike, strings.Join(errs.list, "\n"))
		slog.Error("msg", "GetPartitionDbLikeTbLike", err)
		return nil, nil, nil, err
	}
	return initSqls.list, addSqls.list, dropSqls.list, nil
}

// GetDbTableInfo TODO
func (config *PartitionConfig) GetDbTableInfo() (ptlist []ConfigDetail, err error) {
	address := fmt.Sprintf("%s:%d", config.ImmuteDomain, config.Port)
	slog.Info(fmt.Sprintf("get real partition info from (%s/%s,%s)", address, config.DbLike, config.TbLike))

	var output oneAddressResult
	sql := fmt.Sprintf(
		`select TABLE_SCHEMA,TABLE_NAME,CREATE_OPTIONS from information_schema.tables where TABLE_SCHEMA like '%s' and TABLE_NAME like '%s';`, config.DbLike, config.TbLike)
	var queryRequest = QueryRequest{[]string{address}, []string{sql}, true, 30, config.BkCloudId}
	output, err = OneAddressExecuteSql(queryRequest)
	if err != nil {
		return nil, err
	}
	if len(output.CmdResults[0].TableData) == 0 {
		return nil, errno.NoTableMatched.Add(
			fmt.Sprintf("db like: [%s] and table like: [%s]",
				strings.Replace(config.DbLike, "%", "%%", -1), config.TbLike))
	}
	for _, row := range output.CmdResults[0].TableData {
		var partitioned bool
		if strings.Contains(row["CREATE_OPTIONS"].(string), "partitioned") {
			partitioned = true
		}

		partitionTable := ConfigDetail{PartitionConfig: *config, DbName: row["TABLE_SCHEMA"].(string),
			TbName: row["TABLE_NAME"].(string), Partitioned: partitioned}
		ptlist = append(ptlist, partitionTable)
	}
	slog.Info("finish getting all partition info")
	return ptlist, nil
}

// GetDropPartitionSql 生成删除分区的sql
func (m *ConfigDetail) GetDropPartitionSql() (string, error) {
	var sql, dropSql, fx string
	reserve := m.ReservedPartition * m.PartitionTimeInterval
	address := fmt.Sprintf("%s:%d", m.ImmuteDomain, m.Port)
	base0 := fmt.Sprintf(`select partition_name from INFORMATION_SCHEMA.PARTITIONS `+
		`where TABLE_SCHEMA='%s' and TABLE_NAME='%s' and PARTITION_DESCRIPTION<`, m.DbName, m.TbName)
	base1 := "order by PARTITION_DESCRIPTION asc;"
	switch m.PartitionType {
	case 0:
		fx = fmt.Sprintf(`(TO_DAYS(now())-%d) `, reserve-DiffOneDay)
	case 1:
		fx = fmt.Sprintf(`(TO_DAYS(now())-%d) `, reserve)
	case 3:
		fx = fmt.Sprintf(`DATE_FORMAT(date_sub(now(),interval %d day),'%%Y%%m%%d')`, reserve)
	case 101:
		fx = fmt.Sprintf(`DATE_FORMAT(date_sub(now(),interval %d day),'%%Y%%m%%d')`, reserve-DiffOneDay)
	case 4:
		fx = fmt.Sprintf(`DATE_FORMAT(date_sub(now(),interval %d day),'\'%%Y-%%m-%%d\'')`, reserve-DiffOneDay)
	case 5:
		fx = fmt.Sprintf(`UNIX_TIMESTAMP(date_sub(curdate(),INTERVAL %d DAY))`, reserve-DiffOneDay)
	default:
		return dropSql, errors.New("not supported partition type")
	}
	sql = fmt.Sprintf("%s %s %s", base0, fx, base1)
	var queryRequest = QueryRequest{Addresses: []string{address}, Cmds: []string{sql}, Force: true, QueryTimeout: 30,
		BkCloudId: m.BkCloudId}
	output, err := OneAddressExecuteSql(queryRequest)
	if err != nil {
		return dropSql, err
	}
	reg := regexp.MustCompile(fmt.Sprintf("^%s$", "p[0-9]{8}"))

	var expired []string
	for _, row := range output.CmdResults[0].TableData {
		name := row["partition_name"].(string)
		if reg.MatchString(name) {
			expired = append(expired, name)
		} else {
			return dropSql, fmt.Errorf("partition_name [%s] not like 'p20130101', "+
				"not created by partition system, can't be dropped", name)
		}
	}
	if len(expired) != 0 {
		dropSql = fmt.Sprintf("alter table `%s`.`%s` drop partition %s", m.DbName, m.TbName, strings.Join(expired, ","))
	}
	return dropSql, nil
}

// GetInitPartitionSql 首次分区,自动分区
func (m *ConfigDetail) GetInitPartitionSql(dbtype string, splitCnt int) (string, int, error) {
	var sqlPartitionDesc []string
	var pkey, descKey, descFormat, initSql string
	var needSize, diff int
	var err error
	slog.Info(fmt.Sprintf("GetInitPartitionSql ConfigDetail: %v", m))
	switch m.PartitionType {
	case 0:
		pkey = fmt.Sprintf("RANGE (TO_DAYS(%s))", m.PartitionColumn)
		descKey = "less than"
		descFormat = "to_days('2006-01-02')"
		diff = DiffOneDay
	case 1:
		pkey = fmt.Sprintf("LIST (TO_DAYS(%s))", m.PartitionColumn)
		descKey = "in"
		descFormat = "to_days('2006-01-02')"
		diff = 0
	case 3:
		pkey = fmt.Sprintf("LIST (%s)", m.PartitionColumn)
		descKey = "in"
		descFormat = "20060102"
		diff = 0
	case 4:
		pkey = fmt.Sprintf("RANGE COLUMNS(%s)", m.PartitionColumn)
		descKey = "less than"
		descFormat = "'2006-01-02'"
		diff = DiffOneDay
	case 5:
		pkey = fmt.Sprintf("RANGE (UNIX_TIMESTAMP(%s))", m.PartitionColumn)
		descKey = "less than"
		descFormat = "UNIX_TIMESTAMP('2006-01-02')"
		diff = DiffOneDay
	case 101:
		pkey = fmt.Sprintf("RANGE (%s)", m.PartitionColumn)
		descKey = "less than"
		descFormat = "20060102"
		diff = 0
	default:
		return initSql, needSize, errors.New("不支持的分区类型")
	}

	for i := -m.ReservedPartition; i < 15; i++ {
		pname := time.Now().AddDate(0, 0, i*m.PartitionTimeInterval).Format("p20060102")
		pdesc := time.Now().AddDate(0, 0, i*m.PartitionTimeInterval+diff).Format(descFormat)
		palter := fmt.Sprintf(" partition %s values %s (%s)", pname, descKey, pdesc)
		sqlPartitionDesc = append(sqlPartitionDesc, palter)
	}
	// nohup /usr/bin/perl /data/dbbak/percona-toolkit-3.2.0/bin/pt-online-schema-change -uxxx -pxxx -S /data1/mysqldata/mysql.sock
	// --charset=utf8 --recursion-method=NONE --alter-foreign-keys-method=auto --alter "partition by xxx"
	// D=leagues_server_HN1,t=league_audit --max-load Threads_running=100 --critical-load=Threads_running:80 --no-drop-old-table
	// --pause-file=/tmp/partition_osc_pause_xxxx --set-vars lock_wait_timeout=5 --execute >> /data/dbbak/xxx.out 2>&1 &

	if dbtype == "TDBCTL" {
		initSql = fmt.Sprintf("alter table `%s`.`%s` partition by %s (%s)", m.DbName, m.TbName, pkey,
			strings.Join(sqlPartitionDesc, ","))
	} else {
		needSize, err = m.CheckTableSize(splitCnt)
		if err != nil {
			return initSql, needSize, err
		}
		options := fmt.Sprintf(
			"--charset=utf8 --recursion-method=NONE --alter-foreign-keys-method=auto --max-load Threads_running=%d "+
				"--critical-load=Threads_running=%d --set-vars lock_wait_timeout=%d --print --pause-file=/tmp/partition_osc_pause_%s_%s --execute ",
			viper.GetInt("pt.max_load.threads_running"),
			viper.GetInt("pt.critical_load.threads_running"), viper.GetInt("pt.lock_wait_timeout"), m.DbName, m.TbName)
		initSql = fmt.Sprintf(` D=%s,t=%s --alter "partition by %s (%s)" %s`, m.DbName, m.TbName, pkey,
			strings.Join(sqlPartitionDesc, ","), options)
	}
	return initSql, needSize, nil
}

// CheckTableSize TODO
func (m *ConfigDetail) CheckTableSize(splitCnt int) (int, error) {
	var needSize int
	address := fmt.Sprintf("%s:%d", m.ImmuteDomain, m.Port)
	sql := fmt.Sprintf(
		"select TABLE_ROWS,(DATA_LENGTH+INDEX_LENGTH) as BYTES from information_schema.tables where TABLE_SCHEMA='%s' and TABLE_NAME='%s'", m.DbName, m.TbName)
	var queryRequest = QueryRequest{Addresses: []string{address}, Cmds: []string{sql}, Force: true, QueryTimeout: 30,
		BkCloudId: m.BkCloudId}
	output, err := OneAddressExecuteSql(queryRequest)
	if err != nil {
		return needSize, err
	}
	rows, _ := strconv.Atoi(output.CmdResults[0].TableData[0]["TABLE_ROWS"].(string))
	bytes, _ := strconv.Atoi(output.CmdResults[0].TableData[0]["BYTES"].(string))
	if bytes < viper.GetInt("pt.max_size") && rows < viper.GetInt("pt.max_rows") {
		needSize = 3 * bytes * splitCnt // 预留空间：3倍于表大小的空间用于做pt-osc，如果是spider remote，再乘以这台机器上的分片数量
		return needSize, nil
	} else {
		return needSize, fmt.Errorf(
			"table %s.%s is not a partition table,and can not do auto alter partition, "+
				"because large than 100MB size or large than 1000000 rows", m.DbName, m.TbName)
	}
}

// GetAddPartitionSql 生成增加分区的sql
func (m *ConfigDetail) GetAddPartitionSql() (string, error) {
	var vsql, addSql, descKey, name, fx string
	var wantedDesc, wantedName, wantedDescIfOld, wantedNameIfOld string
	var diff, desc int
	var begin int
	address := fmt.Sprintf("%s:%d", m.ImmuteDomain, m.Port)
	switch m.PartitionType {
	case 0:
		diff = DiffOneDay
		descKey = "less than"
		fx = fmt.Sprintf(`(TO_DAYS(now())+%d) `, diff)
		wantedDesc = "partition_description as WANTED_DESC,"
		wantedName = fmt.Sprintf(`DATE_FORMAT(from_days(PARTITION_DESCRIPTION-%d),'%%Y%%m%%d')  as WANTED_NAME`, diff)
		wantedDescIfOld = fmt.Sprintf(`(TO_DAYS(now())+%d) as WANTED_DESC,`, diff)
		wantedNameIfOld = "DATE_FORMAT(now(),'%Y%m%d')  as wanted_name"
	case 1:
		descKey = "in"
		fx = "TO_DAYS(now())"
		wantedDesc = "partition_description as WANTED_DESC,"
		wantedName = "DATE_FORMAT(from_days(PARTITION_DESCRIPTION),'%Y%m%d')  as WANTED_NAME"
		wantedDescIfOld = "(TO_DAYS(now())) as WANTED_DESC,`"
		wantedNameIfOld = "DATE_FORMAT(now(),'%Y%m%d')  as WANTED_NAME"
	case 3:
		descKey = "in"
		fx = "DATE_FORMAT(now(),'%Y%m%d')"
		wantedName = "partition_description as WANTED_NAME"
		wantedNameIfOld = "DATE_FORMAT(now(),'%Y%m%d')  as WANTED_NAME"
	case 101:
		diff = DiffOneDay
		descKey = "less than"
		fx = fmt.Sprintf(`DATE_FORMAT(date_add(now(),interval %d day),'%%Y%%m%%d')`, diff)
		wantedName = "partition_description as WANTED_NAME"
		wantedNameIfOld = "DATE_FORMAT(now(),'%Y%m%d')  as WANTED_NAME"
	case 4:
		diff = DiffOneDay
		descKey = "less than"
		fx = fmt.Sprintf(`DATE_FORMAT(date_add(now(),interval %d day),'\'%%Y-%%m-%%d\'')`, diff)
		wantedName = fmt.Sprintf(
			`DATE_FORMAT(date_sub(replace(partition_description,'\'',''),interval %d day),'%%Y%%m%%d') as WANTED_NAME`, diff)
		wantedNameIfOld = "DATE_FORMAT(now(),'%Y%m%d')  as WANTED_NAME"
	case 5:
		diff = DiffOneDay
		descKey = "less than"
		fx = fmt.Sprintf(`UNIX_TIMESTAMP(date_add(curdate(),INTERVAL %d DAY))`, diff)
		wantedDesc = "partition_description as WANTED_DESC,"
		wantedName = fmt.Sprintf(
			`DATE_FORMAT(date_sub(from_unixtime(partition_description),interval %d day),'%%Y%%m%%d') as WANTED_NAME`, diff)
		wantedDescIfOld = fmt.Sprintf(`UNIX_TIMESTAMP(DATE_ADD(curdate(),INTERVAL %d DAY)) as WANTED_DESC,`, diff)
		wantedNameIfOld = "DATE_FORMAT(now(),'%Y%m%d')  as WANTED_NAME"
	default:
		return addSql, errors.New("不支持的分区类型")
	}

	vsql = fmt.Sprintf(
		"select count(*) as COUNT from INFORMATION_SCHEMA.PARTITIONS where TABLE_SCHEMA='%s' and TABLE_NAME='%s' "+
			"and PARTITION_DESCRIPTION> %s", m.DbName, m.TbName, fx)
	var queryRequest = QueryRequest{Addresses: []string{address}, Cmds: []string{vsql}, Force: true, QueryTimeout: 30,
		BkCloudId: m.BkCloudId}
	output, err := OneAddressExecuteSql(queryRequest)
	if err != nil {
		return addSql, err
	}
	cnt, _ := strconv.Atoi(output.CmdResults[0].TableData[0]["COUNT"].(string))
	// 是否需要添加分区
	if cnt >= m.ExtraPartition {
		return addSql, nil
	}
	need := m.ExtraPartition - cnt
	// 先获取当前最大的分区PARTITION_DESCRIPTION和PARTITION_NAME
	vsql = fmt.Sprintf(`select %s %s from INFORMATION_SCHEMA.PARTITIONS where TABLE_SCHEMA ='%s' and TABLE_NAME='%s' `+
		`and partition_description >= %s `+
		`order by PARTITION_DESCRIPTION desc limit 1;`, wantedDesc, wantedName, m.DbName, m.TbName, fx)
	queryRequest = QueryRequest{Addresses: []string{address}, Cmds: []string{vsql}, Force: true, QueryTimeout: 30,
		BkCloudId: m.BkCloudId}
	output, err = OneAddressExecuteSql(queryRequest)
	if err != nil {
		return addSql, err
	}
	// 表是分区表，但是已有的分区过旧，以至于不能包含今天或者未来的分区，添加能包含今天数据的分区
	if len(output.CmdResults[0].TableData) == 0 {
		begin = -1
		vsql = fmt.Sprintf(`select %s %s from INFORMATION_SCHEMA.PARTITIONS limit 1;`, wantedDescIfOld, wantedNameIfOld)
		queryRequest = QueryRequest{Addresses: []string{address}, Cmds: []string{vsql}, Force: true, QueryTimeout: 30,
			BkCloudId: m.BkCloudId}
		output, err = OneAddressExecuteSql(queryRequest)
		if err != nil {
			return addSql, err
		}
		slog.Warn(fmt.Sprintf(
			"%s.%s is a partitioned table, but existed partitions are too old, do not contain today's data.", m.DbName,
			m.TbName))
	}
	name = output.CmdResults[0].TableData[0]["WANTED_NAME"].(string)
	switch m.PartitionType {
	case 0, 1, 5:
		desc, _ = strconv.Atoi(output.CmdResults[0].TableData[0]["WANTED_DESC"].(string))
		addSql, err = m.NewPartitionNameDescType0Type1Type5(begin, need, name, desc, descKey)
	case 3, 101:
		addSql, err = m.NewPartitionNameDescType3Type101(begin, need, name, descKey)
	case 4:
		addSql, err = m.NewPartitionNameDescType4(begin, need, name, descKey)
	default:
		return addSql, errors.New("不支持的分区类型")
	}
	addSql = fmt.Sprintf("alter table `%s`.`%s`  add partition( %s", m.DbName, m.TbName, addSql)
	return addSql, nil
}

// NewPartitionNameDescType0Type1Type5 TODO
func (m *ConfigDetail) NewPartitionNameDescType0Type1Type5(begin int, need int, name string, desc int,
	descKey string) (string, error) {
	var newdesc, ratio int
	var newname, sql string
	ratio = 1
	if m.PartitionType == 5 {
		ratio = 86400
	}
	for i := begin; i < need; i++ {
		// 生成分区description
		newdesc = desc + (i+1)*m.PartitionTimeInterval*ratio
		// 生成分区名
		formatDate, err := time.Parse("20060102", name)
		if err != nil {
			return sql, errors.New("err partition name: " + name)
		}
		newname = formatDate.AddDate(0, 0, (i+1)*m.PartitionTimeInterval).Format("20060102")
		sql = fmt.Sprintf("%s partition `p%s`  values %s (%d),", sql, newname, descKey, newdesc)
	}
	sql = sql[0:len(sql)-1] + ")"
	return sql, nil
}

// NewPartitionNameDescType3Type101 TODO
func (m *ConfigDetail) NewPartitionNameDescType3Type101(begin int, need int, name string, descKey string) (string,
	error) {
	var newname, sql string
	for i := begin; i < need; i++ {
		formatDate, err := time.Parse("20060102", name)
		if err != nil {
			return sql, errors.New("err partition name: " + name)
		}
		newname = formatDate.AddDate(0, 0, (i+1)*m.PartitionTimeInterval).Format("20060102")
		sql = fmt.Sprintf("%s partition `p%s` values %s (%s),", sql, newname, descKey, newname)
	}
	sql = sql[0:len(sql)-1] + ")"
	return sql, nil
}

// NewPartitionNameDescType4 TODO
func (m *ConfigDetail) NewPartitionNameDescType4(begin int, need int, name string, descKey string) (string, error) {
	var newname, newdesc, sql string
	for i := begin; i < need; i++ {
		formatDate, err := time.Parse("20060102", name)
		if err != nil {
			return sql, errors.New("err partition name: " + name)
		}
		newname = formatDate.AddDate(0, 0, (i+1)*m.PartitionTimeInterval).Format("20060102")
		newdesc = formatDate.AddDate(0, 0, (i+2)*m.PartitionTimeInterval).Format("'2006-01-02'")
		sql = fmt.Sprintf("%s partition `p%s`  values %s (%s),", sql, newname, descKey, newdesc)
	}
	sql = sql[0:len(sql)-1] + ")"
	return sql, nil
}

// GetSpiderBackends TODO
func GetSpiderBackends(address string, bkCloudId int) (tableDataType, int, error) {
	var splitCnt int
	var tdbctlPrimary string
	// 查询tdbctl
	dbctlSql := "select HOST,PORT,server_name as SPLIT_NUM, SERVER_NAME, WRAPPER from mysql.servers " +
		"where wrapper='TDBCTL' and server_name like 'TDBCTL%' ;"
	getTdbctlPrimary := "tdbctl get primary;"
	queryRequest := QueryRequest{Addresses: []string{address}, Cmds: []string{dbctlSql}, Force: true, QueryTimeout: 30,
		BkCloudId: bkCloudId}
	output, err := OneAddressExecuteSql(queryRequest)
	if err != nil {
		return nil, splitCnt, fmt.Errorf("execute [%s] get spider info error: %s", dbctlSql, err.Error())
	} else if len(output.CmdResults[0].TableData) == 0 {
		return nil, splitCnt, fmt.Errorf("no spider tdbctl found")
	}

	// 查询tdbctl主节点
	for _, item := range output.CmdResults[0].TableData {
		tdbctl := fmt.Sprintf("%s:%s", item["HOST"].(string), item["PORT"].(string))
		queryRequest = QueryRequest{Addresses: []string{tdbctl}, Cmds: []string{getTdbctlPrimary}, Force: true,
			QueryTimeout: 30, BkCloudId: bkCloudId}
		primary, err := OneAddressExecuteSql(queryRequest)
		if err != nil {
			slog.Warn(fmt.Sprintf("execute [%s] error: %s", getTdbctlPrimary, err.Error()))
			continue
		}
		if len(primary.CmdResults[0].TableData) == 0 {
			slog.Error(fmt.Sprintf("execute [%s] nothing return", getTdbctlPrimary))
			return nil, splitCnt, fmt.Errorf("execute [%s] nothing return", getTdbctlPrimary)
		}
		slog.Info("data:", primary.CmdResults[0].TableData)
		tdbctlPrimary = primary.CmdResults[0].TableData[0]["SERVER_NAME"].(string)
		break
	}
	if tdbctlPrimary == "" {
		slog.Error(fmt.Sprintf("execute [%s] SERVER_NAME is null", getTdbctlPrimary))
		return nil, splitCnt, fmt.Errorf("execute [%s] SERVER_NAME is null", getTdbctlPrimary)
	}
	// 查询remote master各分片实例和tdbctl主节点
	splitSql := fmt.Sprintf("select HOST,PORT,replace(server_name,'SPT','') as SPLIT_NUM, SERVER_NAME, WRAPPER "+
		"from mysql.servers where wrapper in ('mysql','TDBCTL') and "+
		"(server_name like 'SPT%%' or server_name like '%s')", tdbctlPrimary)
	queryRequest = QueryRequest{Addresses: []string{address}, Cmds: []string{splitSql}, Force: true, QueryTimeout: 30,
		BkCloudId: bkCloudId}
	output, err = OneAddressExecuteSql(queryRequest)
	if err != nil {
		return nil, splitCnt, fmt.Errorf("execute [%s] get spider remote and tdbctl master error: %s", splitSql, err.Error())
	}
	// 查询一台remote机器上有多少个实例，用于评估存储空间
	cntSql := "select count(*) as COUNT from mysql.servers where WRAPPER='mysql' and " +
		"SERVER_NAME like 'SPT%' group by host order by 1 desc limit 1;"
	queryRequest = QueryRequest{Addresses: []string{address}, Cmds: []string{cntSql}, Force: true, QueryTimeout: 30,
		BkCloudId: bkCloudId}
	output1, err := OneAddressExecuteSql(queryRequest)
	if err != nil {
		return nil, splitCnt, fmt.Errorf("execute [%s] get spider split count error: %s", cntSql, err.Error())
	}
	splitCnt, _ = strconv.Atoi(output1.CmdResults[0].TableData[0]["COUNT"].(string))
	return output.CmdResults[0].TableData, splitCnt, nil
}

// CreatePartitionTicket TODO
func CreatePartitionTicket(check Checker, objects []PartitionObject, zoneOffset int, date string, scheduler string) {
	zone := fmt.Sprintf("%+03d:00", zoneOffset)
	ticketType := "MYSQL_PARTITION"
	if check.ClusterType == Tendbcluster {
		ticketType = "SPIDER_PARTITION"
	}
	ticket := Ticket{BkBizId: check.BkBizId, TicketType: ticketType, Remark: "auto partition",
		Details: Detail{Infos: []Info{{check.ConfigId, check.ClusterId, check.ImmuteDomain, *check.BkCloudId, objects}}}}
	id, err := CreateDbmTicket(ticket)
	if err != nil {
		dimension := monitor.NewPartitionEventDimension(check.BkBizId, *check.BkCloudId, check.ImmuteDomain)
		content := fmt.Sprintf("partition error. create ticket fail: %s", err.Error())
		monitor.SendEvent(monitor.PartitionEvent, dimension, content, "0.0.0.0")
		slog.Error("msg", fmt.Sprintf("create ticket fail: %v", ticket), err)
		_ = AddLog(check.ConfigId, check.BkBizId, check.ClusterId, *check.BkCloudId,
			0, check.ImmuteDomain, zone, date, scheduler,
			content, CheckFailed, check.ClusterType)
		return
	}
	_ = AddLog(check.ConfigId, check.BkBizId, check.ClusterId, *check.BkCloudId, id, check.ImmuteDomain,
		zone, date, scheduler, "", ExecuteAsynchronous, check.ClusterType)
}

// NeedPartition TODO
func NeedPartition(cronType string, clusterType string, zoneOffset int, cronDate string) ([]*Checker, error) {
	var configTb, logTb string
	var all, doNothing []*Checker
	switch clusterType {
	case Tendbha, Tendbsingle:
		configTb = MysqlPartitionConfig
		logTb = MysqlPartitionCronLogTable
	case Tendbcluster:
		configTb = SpiderPartitionConfig
		logTb = SpiderPartitionCronLogTable
	default:
		return nil, errors.New("不支持的db类型")
	}
	vzone := fmt.Sprintf("%+03d:00", zoneOffset)
	vsql := fmt.Sprintf(
		"select id as config_id, bk_biz_id, cluster_id, immute_domain, port, bk_cloud_id,"+
			" '%s' as cluster_type from `%s`.`%s` where time_zone='%s' and phase='online' order by 2,3;",
		clusterType, viper.GetString("db.name"), configTb, vzone)
	slog.Info(vsql)
	err := model.DB.Self.Raw(vsql).Scan(&all).Error
	if err != nil {
		slog.Error(vsql, "execute err", err)
		return nil, err
	}
	slog.Info("all", all)
	if cronType == "daily" {
		return all, nil
	}
	vsql = fmt.Sprintf("select conf.id as config_id from `%s`.`%s` as conf,"+
		"`%s`.`%s` as log where conf.id=log.config_id "+
		"and conf.time_zone='%s' and log.cron_date='%s' and log.status like '%s'",
		viper.GetString("db.name"), configTb, viper.GetString("db.name"),
		logTb, vzone, cronDate, CheckSucceeded)
	slog.Info(vsql)
	err = model.DB.Self.Raw(vsql).Scan(&doNothing).Error
	if err != nil {
		slog.Error(vsql, "execute err", err)
		return nil, err
	}
	var need []*Checker
	for _, item := range all {
		retryFlag := true
		for _, ok := range doNothing {
			if (*item).ConfigId == (*ok).ConfigId {
				retryFlag = false
				break
			}
		}
		if retryFlag == true {
			need = append(need, item)
		}
	}
	return need, nil
}

// GetMaster TODO
func GetMaster(configs []*PartitionConfig, immuteDomain, clusterType string) ([]*PartitionConfig, error) {
	newconfigs := make([]*PartitionConfig, len(configs))
	clusterInfo, err := GetCluster(Domain{immuteDomain}, clusterType)
	if err != nil {
		slog.Error("msg", "GetCluster err", err)
		return nil, fmt.Errorf("GetCluster err: %s", err.Error())
	}
	var masterIp string
	var masterPort int
	for _, storage := range clusterInfo.Storages {
		if storage.InstanceRole == Orphan || storage.InstanceRole == BackendMaster {
			masterIp = storage.IP
			masterPort = storage.Port
			break
		}
	}

	for k, v := range configs {
		newconfig := *v
		newconfig.ImmuteDomain = masterIp
		newconfig.Port = masterPort
		newconfigs[k] = &newconfig
	}
	return newconfigs, nil
}

// AddLog TODO
func AddLog(configId, bkBizId, clusterId, bkCloudId, ticketId int, immuteDomain, zone, date, scheduler,
	info, checkStatus, clusterType string) error {
	tx := model.DB.Self.Begin()
	tb := MysqlPartitionCronLogTable
	if clusterType == Tendbcluster {
		tb = SpiderPartitionCronLogTable
	}
	log := &PartitionCronLog{ConfigId: configId, BkBizId: bkBizId, ClusterId: clusterId, TicketId: ticketId,
		ImmuteDomain: immuteDomain, BkCloudId: bkCloudId, TimeZone: zone, CronDate: date, Scheduler: scheduler,
		CheckInfo: info, Status: checkStatus}
	err := tx.Debug().Table(tb).Create(log).Error
	if err != nil {
		tx.Rollback()
		slog.Error("msg", "add cron log failed", err)
		return err
	}
	tx.Commit()
	return nil
}

// AddInit TODO
func AddInit(m *InitMessages, s InitSql) {
	if s.Sql != "" {
		(*m).mu.Lock()
		(*m).list = append((*m).list, s)
		(*m).mu.Unlock()
	}
	return
}

// AddString TODO
func AddString(m *Messages, s string) {
	if s != "" {
		(*m).mu.Lock()
		(*m).list = append((*m).list, s)
		(*m).mu.Unlock()
	}
	return
}
