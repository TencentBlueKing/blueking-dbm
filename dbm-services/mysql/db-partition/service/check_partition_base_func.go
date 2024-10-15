package service

import (
	"errors"
	"fmt"
	"log/slog"
	"regexp"
	"strconv"
	"strings"
	"sync"
	"time"

	"dbm-services/common/go-pubpkg/errno"
	"dbm-services/mysql/db-partition/model"

	"github.com/spf13/viper"
)

// GetPartitionDbLikeTbLike TODO
func (config *PartitionConfig) GetPartitionDbLikeTbLike(dbtype string, splitCnt int, fromCron bool, host Host) (
	[]InitSql, []string, []string,
	error) {
	var addSqls, dropSqls, errs Messages
	var initSqls InitMessages
	var err error
	initSqls.list = []InitSql{}
	addSqls.list = []string{}
	dropSqls.list = []string{}
	errs.list = []string{}

	tbs, errOuter := config.GetDbTableInfo(fromCron, host)
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
		slog.Info(fmt.Sprintf("get init/add/drop partition for (domain:%s, dbname:%s, "+
			"table_name:%s, partitioned:%t, has_unique_key:%t)", tb.ImmuteDomain,
			tb.DbName, tb.TbName, tb.Partitioned, tb.HasUniqueKey))
		go func(tb ConfigDetail) {
			defer func() {
				<-tokenBucket
				wg.Done()
			}()
			if tb.Partitioned {
				sql, err = tb.GetAddPartitionSql(host)
				if err != nil {
					slog.Error("msg", "GetAddPartitionSql error", err)
					AddString(&errs, err.Error())
					return
				}
				AddString(&addSqls, sql)
				if tb.Phase == online {
					// 启用的分区规则，会执行删除历史分区
					// 禁用的分区规则，会新增分区，但是不会删除历史分区
					sql, err = tb.GetDropPartitionSql(host)
					if err != nil {
						slog.Error("msg", "GetDropPartitionSql error", err)
						AddString(&errs, err.Error())
						return
					}
					AddString(&dropSqls, sql)
				}
			} else {
				sql, needSize, err = tb.GetInitPartitionSql(dbtype, splitCnt, host)
				if err != nil {
					slog.Error("msg", "GetInitPartitionSql error", err)
					AddString(&errs, err.Error())
					return
				}
				AddInit(&initSqls, InitSql{sql, needSize, tb.HasUniqueKey})
			}
			return
		}(tb)
	}
	wg.Wait()
	close(tokenBucket)
	if len(errs.list) > 0 {
		err = fmt.Errorf("partition rule: [dblike:`%s` tblike:`%s`] get partition sql error\n%s",
			config.DbLike, config.TbLike, strings.Join(errs.list, "\n"))
		slog.Error("msg", "GetPartitionDbLikeTbLike", err)
		return nil, nil, nil, err
	}
	return initSqls.list, addSqls.list, dropSqls.list, nil
}

// GetDbTableInfo TODO
func (config *PartitionConfig) GetDbTableInfo(fromCron bool, host Host) (ptlist []ConfigDetail, err error) {
	address := fmt.Sprintf("%s:%d", host.Ip, host.Port)
	slog.Info(fmt.Sprintf("get real partition info from (%s/%s,%s)", address, config.DbLike, config.TbLike))

	var output oneAddressResult
	sql := fmt.Sprintf(
		`select TABLE_SCHEMA as TABLE_SCHEMA,TABLE_NAME as TABLE_NAME,CREATE_OPTIONS as CREATE_OPTIONS `+
			` from information_schema.tables where TABLE_SCHEMA like '%s' and TABLE_NAME like '%s';`,
		config.DbLike, config.TbLike)
	var queryRequest = QueryRequest{[]string{address}, []string{sql}, true, 30,
		int(host.BkCloudId)}
	output, err = OneAddressExecuteSql(queryRequest)
	if err != nil {
		slog.Error("GetDbTableInfo", sql, err.Error())
		return nil, err
	}
	if len(output.CmdResults[0].TableData) == 0 {
		return nil, errno.NoTableMatched.Add(
			fmt.Sprintf("db like: [%s] and table like: [%s]",
				strings.Replace(config.DbLike, "%", "%%", -1), config.TbLike))
	}
	uniqueKeySql := fmt.Sprintf(
		`select distinct TABLE_SCHEMA as TABLE_SCHEMA,TABLE_NAME as TABLE_NAME `+
			` from information_schema.TABLE_CONSTRAINTS `+
			` where TABLE_SCHEMA like '%s' and TABLE_NAME like '%s' and `+
			` CONSTRAINT_TYPE in ('UNIQUE','PRIMARY KEY');`,
		config.DbLike, config.TbLike)
	queryRequest = QueryRequest{[]string{address}, []string{uniqueKeySql}, true,
		30, int(host.BkCloudId)}
	hasUniqueKey, err := OneAddressExecuteSql(queryRequest)
	if err != nil {
		slog.Error("get", sql, err.Error())
		return nil, err
	}

	for _, row := range output.CmdResults[0].TableData {
		var partitioned bool
		db := row["TABLE_SCHEMA"].(string)
		tb := row["TABLE_NAME"].(string)
		if strings.Contains(row["CREATE_OPTIONS"].(string), "partitioned") {
			partitioned = true
			//check分区字段、分区间隔
			sql = fmt.Sprintf("select PARTITION_EXPRESSION"+
				" as PARTITION_EXPRESSION,PARTITION_METHOD as PARTITION_METHOD,PARTITION_NAME"+
				" as PARTITION_NAME from "+
				" information_schema.PARTITIONS where TABLE_SCHEMA like '%s' and TABLE_NAME like '%s' "+
				" order by PARTITION_DESCRIPTION asc limit 2;",
				db, tb)
			queryRequest = QueryRequest{[]string{address}, []string{sql}, true, 30,
				int(host.BkCloudId)}
			output, err = OneAddressExecuteSql(queryRequest)
			if err != nil {
				slog.Error("GetDbTableInfo", sql, err.Error())
				return nil, err
			}
			// (1)兼容【分区字段为空】的历史问题，对于某些特殊的分区类型，旧系统已经不在页面上支持，所以旧系统有意将分区字段留空，
			// 		使其无法在页面编辑，避免改变了其他所属分区类别，因此无法核对比较，但不影响新增和删除分区。
			// (2)兼容web、dnf业务的特殊定制类型，分区字段类型为int，但是系统记录为timestamp，因此无法核对比较，但不影响新增和删除分区。
			// (3)兼容minigame业务的特殊定制类型，分区类型为0，但是实际定义与分区类型存在差异，因此无法核对比较，但不影响新增和删除分区。
			webCustomization := config.BkBizId == 159 && config.PartitionColumn == "Fcreate_time"
			minigameCustomization := config.BkBizId == 121 && config.ImmuteDomain == "gamedb.game-record.minigame.db"
			dnfCustomization := config.BkBizId == 105 && config.PartitionColumn == "occ_date"
			if config.PartitionColumn != "" && !webCustomization && !minigameCustomization && !dnfCustomization {
				// 分区表至少会有一个分区
				for _, v := range output.CmdResults[0].TableData {
					// 如果发现分区字段、分区间隔与规则不符合，需要重新做分区，页面调整了分区规则
					ok, errInner := CheckPartitionExpression(v["PARTITION_EXPRESSION"].(string),
						v["PARTITION_METHOD"].(string),
						config.PartitionColumn, config.PartitionType)
					if errInner != nil {
						slog.Error("CheckPartitionExpression", "error", errInner.Error())
						return nil, errInner
					} else if !ok {
						// 如果页面调整了分区规则，允许在页面手动执行执行分区。定时任务不对已经分区过的表做初始化，风险高
						if fromCron {
							tips := fmt.Sprintf("partition crontab task not init partitioned table " +
								"when partition expression in db not consistent with config in system, " +
								"please confirm, you can execute from web")
							slog.Error("CheckPartitionExpression", "tips", tips,
								"db", db, "tb", tb)
							return nil, fmt.Errorf("db like: [%s] and table like: [%s]: %s", db, tb, tips)
						} else {
							partitioned = false
							break
						}
					}
				}
			}
			if partitioned == true && len(output.CmdResults[0].TableData) == 2 {
				ok, errInner := CalculateInterval(output.CmdResults[0].TableData[0]["PARTITION_NAME"].(string),
					output.CmdResults[0].TableData[1]["PARTITION_NAME"].(string), config.PartitionTimeInterval)
				if errInner != nil {
					slog.Error("CalculateInterval", "error", errInner.Error())
					return nil, errInner
				} else if !ok {
					if fromCron {
						tips := fmt.Sprintf("partition crontab task not init partitioned table " +
							"when partition interval in db not consistent with config in system, " +
							"please confirm, you can execute from web")
						slog.Error("CalculateInterval", "tips", tips,
							"db", db, "tb", tb)
						return nil, fmt.Errorf("db like: [%s] and table like: [%s]: %s", db, tb, tips)
					} else {
						partitioned = false
					}
				}
			}
		}
		uniqueKeyFlag := false
		for _, unique := range hasUniqueKey.CmdResults[0].TableData {
			if db == unique["TABLE_SCHEMA"].(string) && tb == unique["TABLE_NAME"].(string) {
				uniqueKeyFlag = true
			}
		}
		partitionTable := ConfigDetail{PartitionConfig: *config, DbName: db,
			TbName: tb, Partitioned: partitioned, HasUniqueKey: uniqueKeyFlag}
		ptlist = append(ptlist, partitionTable)
	}
	slog.Info("finish getting all partition info")
	return ptlist, nil
}

func CheckPartitionExpression(expression, method, column string, partitionType int) (bool, error) {
	columnWithBackquote := fmt.Sprintf("`%s`", column)
	switch partitionType {
	case 0:
		if (expression == fmt.Sprintf("to_days(%s)", column) || expression ==
			fmt.Sprintf("to_days(%s)", columnWithBackquote) ||
			expression == fmt.Sprintf("TO_DAYS(%s)", column) ||
			expression == fmt.Sprintf("TO_DAYS(%s)", columnWithBackquote)) && method == "RANGE" {
			return true, nil
		}
	case 1:
		if (expression == fmt.Sprintf("to_days(%s)", column) || expression ==
			fmt.Sprintf("to_days(%s)", columnWithBackquote) ||
			expression == fmt.Sprintf("TO_DAYS(%s)", column) ||
			expression == fmt.Sprintf("TO_DAYS(%s)", columnWithBackquote)) && method == "LIST" {
			return true, nil
		}
	case 3:
		if (expression == column || expression == columnWithBackquote) && method == "LIST" {
			return true, nil
		}
	case 101:
		if (expression == column || expression == columnWithBackquote) && method == "RANGE" {
			return true, nil
		}
	case 4:
		if (expression == column || expression == columnWithBackquote) && method == "RANGE COLUMNS" {
			return true, nil
		}
	case 5:
		if (expression == fmt.Sprintf("unix_timestamp(%s)", column) || expression ==
			fmt.Sprintf("unix_timestamp(%s)", columnWithBackquote) ||
			expression == fmt.Sprintf("UNIX_TIMESTAMP(%s)", column) ||
			expression == fmt.Sprintf("UNIX_TIMESTAMP(%s)", columnWithBackquote)) && method == "RANGE" {
			return true, nil
		}
	default:
		return true, errno.NotSupportedPartitionType
	}
	return false, nil
}

func CalculateInterval(firstName, secondName string, interval int) (bool, error) {
	reg := regexp.MustCompile(fmt.Sprintf("^%s$", "p[0-9]{8}"))
	name := firstName
	if !reg.MatchString(name) {
		slog.Error("msg", "wrong name format", errno.WrongPartitionNameFormat.AddBefore(name))
		return true, errno.WrongPartitionNameFormat.AddBefore(name)
	}
	name = secondName
	if !reg.MatchString(name) {
		slog.Error("msg", "wrong name format", errno.WrongPartitionNameFormat.AddBefore(name))
		return true, errno.WrongPartitionNameFormat.AddBefore(name)
	}

	firstName = strings.Replace(firstName, "p", "", -1)
	secondName = strings.Replace(secondName, "p", "", -1)
	t1, err := time.Parse("20060102", firstName)
	if err != nil {
		slog.Error("msg", "time parse error", err)
		return true, err
	}
	t2, err := time.Parse("20060102", secondName)
	if err != nil {
		slog.Error("msg", "time parse error", err)
		return true, err
	}
	if int(t2.Sub(t1).Hours()/24) != interval {
		return false, nil
	}
	return true, nil
}

// GetDropPartitionSql 生成删除分区的sql
func (m *ConfigDetail) GetDropPartitionSql(host Host) (string, error) {
	var sql, dropSql, fx string
	// 保留时间+1天，考虑时区差异引起的时间计算不稳定
	reserve := m.ReservedPartition*m.PartitionTimeInterval + 1
	address := fmt.Sprintf("%s:%d", host.Ip, host.Port)
	base0 := fmt.Sprintf(`select PARTITION_NAME as PARTITION_NAME from INFORMATION_SCHEMA.PARTITIONS `+
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
		// 101类型分区，分区名和desc不相差一天，但是用了less than
		fx = fmt.Sprintf(`DATE_FORMAT(date_sub(now(),interval %d day),'%%Y%%m%%d')`, reserve-DiffOneDay)
	case 4:
		fx = fmt.Sprintf(`DATE_FORMAT(date_sub(now(),interval %d day),'\'%%Y-%%m-%%d\'')`, reserve-DiffOneDay)
	case 5:
		fx = fmt.Sprintf(`UNIX_TIMESTAMP(date_sub(curdate(),INTERVAL %d DAY))`, reserve-DiffOneDay)
	default:
		return dropSql, errno.NotSupportedPartitionType
	}
	sql = fmt.Sprintf("%s %s %s", base0, fx, base1)
	var queryRequest = QueryRequest{Addresses: []string{address}, Cmds: []string{sql}, Force: true, QueryTimeout: 30,
		BkCloudId: int(host.BkCloudId)}
	output, err := OneAddressExecuteSql(queryRequest)
	if err != nil {
		return dropSql, err
	}
	reg := regexp.MustCompile(fmt.Sprintf("^%s$", "p[0-9]{8}"))

	var expired []string
	for _, row := range output.CmdResults[0].TableData {
		name := row["PARTITION_NAME"].(string)
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
func (m *ConfigDetail) GetInitPartitionSql(dbtype string, splitCnt int, host Host) (string, int, error) {
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
		return initSql, needSize, errno.NotSupportedPartitionType
	}
	// 兼容历史遗留的PARTITION p20230325 VALUES LESS THAN (20230325)的格式，虽然是less than但是分区名和desc是同一天
	if m.PartitionType == 101 {
		for i := -m.ReservedPartition + 1; i < m.ExtraPartition+1; i++ {
			pname := time.Now().AddDate(0, 0, i*m.PartitionTimeInterval).Format("p20060102")
			pdesc := time.Now().AddDate(0, 0, i*m.PartitionTimeInterval+diff).Format(descFormat)
			palter := fmt.Sprintf(" partition %s values %s (%s)", pname, descKey, pdesc)
			sqlPartitionDesc = append(sqlPartitionDesc, palter)
		}
	} else {
		for i := -m.ReservedPartition; i < m.ExtraPartition; i++ {
			pname := time.Now().AddDate(0, 0, i*m.PartitionTimeInterval).Format("p20060102")
			pdesc := time.Now().AddDate(0, 0, i*m.PartitionTimeInterval+diff).Format(descFormat)
			palter := fmt.Sprintf(" partition %s values %s (%s)", pname, descKey, pdesc)
			sqlPartitionDesc = append(sqlPartitionDesc, palter)
		}
	}
	// nohup /usr/bin/perl /data/dbbak/percona-toolkit-3.2.0/bin/pt-online-schema-change -uxxx -pxxx -S /data1/mysqldata/mysql.sock
	// --charset=utf8 --recursion-method=NONE --alter-foreign-keys-method=auto --alter "partition by xxx"
	// D=leagues_server_HN1,t=league_audit --max-load Threads_running=100 --critical-load=Threads_running:80 --no-drop-old-table
	// --pause-file=/tmp/partition_osc_pause_xxxx --set-vars lock_wait_timeout=5 --execute >> /data/dbbak/xxx.out 2>&1 &

	if dbtype == "TDBCTL" {
		initSql = fmt.Sprintf("alter table `%s`.`%s` partition by %s (%s)", m.DbName, m.TbName, pkey,
			strings.Join(sqlPartitionDesc, ","))
	} else {
		needSize, err = m.CheckTableSize(splitCnt, host)
		if err != nil {
			return initSql, needSize, err
		}
		if m.HasUniqueKey {
			options := fmt.Sprintf(
				"--charset=utf8 --recursion-method=NONE --alter-foreign-keys-method=auto --max-load Threads_running=%d "+
					"--critical-load=Threads_running=%d --set-vars lock_wait_timeout=%d --print --pause-file=/tmp/partition_osc_pause_%s_%s --execute ",
				viper.GetInt("pt.max_load.threads_running"),
				viper.GetInt("pt.critical_load.threads_running"), viper.GetInt("pt.lock_wait_timeout"), m.DbName, m.TbName)
			initSql = fmt.Sprintf(` D=%s,t=%s --alter "partition by %s (%s)" %s`, m.DbName, m.TbName, pkey,
				strings.Join(sqlPartitionDesc, ","), options)
		} else {
			initSql = fmt.Sprintf("alter table `%s`.`%s` partition by %s (%s)", m.DbName, m.TbName, pkey,
				strings.Join(sqlPartitionDesc, ","))
		}
	}
	return initSql, needSize, nil
}

// CheckTableSize TODO
func (m *ConfigDetail) CheckTableSize(splitCnt int, host Host) (int, error) {
	var needSize int
	address := fmt.Sprintf("%s:%d", host.Ip, host.Port)
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
				"because large than %d size or large than %d rows", m.DbName, m.TbName,
			viper.GetInt("pt.max_size"), viper.GetInt("pt.max_rows"))
	}
}

// GetAddPartitionSql 生成增加分区的sql
func (m *ConfigDetail) GetAddPartitionSql(host Host) (string, error) {
	var vsql, addSql, descKey, name, fx string
	var wantedDesc, wantedName, wantedDescIfOld, wantedNameIfOld string
	var diff, desc int
	var begin int
	address := fmt.Sprintf("%s:%d", host.Ip, host.Port)
	switch m.PartitionType {
	case 0:
		diff = DiffOneDay
		descKey = "less than"
		fx = fmt.Sprintf(`(TO_DAYS(now())+%d) `, diff)
		wantedDesc = "partition_description as WANTED_DESC,"
		wantedName = fmt.Sprintf(`DATE_FORMAT(from_days(PARTITION_DESCRIPTION-%d),'%%Y%%m%%d')  as WANTED_NAME`, diff)
		wantedDescIfOld = fmt.Sprintf(`(TO_DAYS(now())+%d) as WANTED_DESC,`, diff)
		wantedNameIfOld = "DATE_FORMAT(now(),'%Y%m%d')  as WANTED_NAME"
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
		// 101类型分区，分区名和desc不相差一天，但是desc为今天，不能算在预留分区个数中，因为【less than 今天】存储的是历史数据，所以diff为1
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
		return addSql, errno.NotSupportedPartitionType
	}

	// 可存储今日数据的分区是一个预留分区
	vsql = fmt.Sprintf(
		"select count(*) as COUNT from INFORMATION_SCHEMA.PARTITIONS where TABLE_SCHEMA='%s' and TABLE_NAME='%s' "+
			"and partition_description>= %s", m.DbName, m.TbName, fx)
	var queryRequest = QueryRequest{Addresses: []string{address}, Cmds: []string{vsql}, Force: true, QueryTimeout: 30,
		BkCloudId: int(host.BkCloudId)}
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
	vsql = fmt.Sprintf(`select %s %s ,PARTITION_NAME as PARTITION_NAME from INFORMATION_SCHEMA.PARTITIONS `+
		`where TABLE_SCHEMA ='%s' and TABLE_NAME='%s' `+
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
			BkCloudId: int(host.BkCloudId)}
		output, err = OneAddressExecuteSql(queryRequest)
		if err != nil {
			return addSql, err
		}
		slog.Warn(fmt.Sprintf(
			"%s.%s is a partitioned table, but existed partitions are too old, do not contain today's data.", m.DbName,
			m.TbName))
		name = output.CmdResults[0].TableData[0]["WANTED_NAME"].(string)
	} else {
		name = output.CmdResults[0].TableData[0]["WANTED_NAME"].(string)
		current := strings.TrimPrefix(output.CmdResults[0].TableData[0]["PARTITION_NAME"].(string), "p")
		formatDate, err := time.Parse("20060102", name)
		if err != nil {
			return addSql, err
		}
		// drs访问db无法保证时区与db时区一致，如果计算出希望创建的分区名比当前分区的名称还要小1天，如果分区间隔又只有1天，分区名会重复
		if formatDate.AddDate(0, 0, 1).Format("20060102") == current {
			name = current
		}
	}
	switch m.PartitionType {
	case 0, 1, 5:
		desc, _ = strconv.Atoi(output.CmdResults[0].TableData[0]["WANTED_DESC"].(string))
		addSql, err = m.NewPartitionNameDescType0Type1Type5(begin, need, name, desc, descKey)
	case 3, 101:
		addSql, err = m.NewPartitionNameDescType3Type101(begin, need, name, descKey)
	case 4:
		addSql, err = m.NewPartitionNameDescType4(begin, need, name, descKey)
	default:
		return addSql, errno.NotSupportedPartitionType
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

// CreatePartitionTicket 创建分区定时任务的单据
func CreatePartitionTicket(flows []Info, ClusterType string, domain string, vdate string) error {
	var ticketType string
	var ticket Ticket
	if ClusterType == Tendbha {
		ticketType = "MYSQL_PARTITION_CRON"
	} else if ClusterType == Tendbcluster {
		ticketType = "TENDBCLUSTER_PARTITION_CRON"
	} else {
		return errno.NotSupportedClusterType
	}
	ticket = Ticket{BkBizId: viper.GetInt("dba.bk_biz_id"),
		TicketType: ticketType, Remark: "auto partition", IgnoreDuplication: true,
		Details: Detail{Infos: flows, CronDate: vdate, ImmuteDomain: domain}}
	slog.Info("msg", "ticket info", fmt.Sprintf("%v", ticket))
	_, err := CreateDbmTicket(ticket)
	if err != nil {
		return err
	}
	return nil
}

// NeedPartition 获取需要实施的分区规则
func NeedPartition(cronType string, clusterType string, zoneOffset int, cronDate string) ([]*PartitionConfig, error) {
	var configTb, logTb string
	var doNothing []*Checker

	switch clusterType {
	case Tendbha, Tendbsingle:
		configTb = MysqlPartitionConfig
		logTb = MysqlPartitionCronLogTable
	case Tendbcluster:
		configTb = SpiderPartitionConfig
		logTb = SpiderPartitionCronLogTable
	default:
		return nil, errno.NotSupportedClusterType
	}
	vzone := fmt.Sprintf("%+03d:00", zoneOffset)
	// 集群被offline时，其分区规则也被禁用，规则不会被定时任务执行
	var all, need []*PartitionConfig
	err := model.DB.Self.Table(configTb).Where("time_zone = ? and phase in (?,?)", vzone, online, offline).Scan(&all).
		Error
	if err != nil {
		slog.Error("msg", fmt.Sprintf("query %s err", configTb), err)
		return nil, err
	}
	if cronType == "daily" {
		return all, nil
	}

	vsql := fmt.Sprintf("select conf.id as config_id from `%s`.`%s` as conf,"+
		"`%s`.`%s` as log where conf.id=log.config_id "+
		"and conf.time_zone='%s' and log.cron_date='%s' and log.status like '%s'",
		viper.GetString("db.name"), configTb, viper.GetString("db.name"),
		logTb, vzone, cronDate, Success)
	slog.Info(vsql)
	err = model.DB.Self.Raw(vsql).Scan(&doNothing).Error
	if err != nil {
		slog.Error(vsql, "execute err", err)
		return nil, err
	}
	for _, item := range all {
		retryFlag := true
		for _, ok := range doNothing {
			if (*item).ID == (*ok).ConfigId {
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

// GetMaster 获取主库
func GetMaster(immuteDomain, clusterType string) (Host, error) {
	var host Host
	cluster, err := GetCluster(Domain{immuteDomain}, clusterType)
	if err != nil {
		slog.Error("msg", "GetCluster err", err)
		return host, fmt.Errorf("GetCluster err: %s", err.Error())
	}
	for _, storage := range cluster.Storages {
		if storage.InstanceRole == Orphan || storage.InstanceRole == BackendMaster {
			return Host{Ip: storage.IP, Port: storage.Port, BkCloudId: cluster.BkCloudId}, nil
		}
	}
	return host, fmt.Errorf("not found master")
}

// AddLogBatch 批量添加日志
func AddLogBatch(configs []IdLog, date, scheduler, status, clusterType string, sameLog string) error {
	tx := model.DB.Self.Begin()
	tb := MysqlPartitionCronLogTable
	if clusterType == Tendbcluster {
		tb = SpiderPartitionCronLogTable
	}
	if sameLog != "" {
		for _, config := range configs {
			log := &PartitionCronLog{ConfigId: config.ConfigId, CronDate: date, Scheduler: scheduler,
				CheckInfo: sameLog, Status: status}
			err := tx.Debug().Table(tb).Create(log).Error
			if err != nil {
				tx.Rollback()
				slog.Error("msg", "add cron log failed", err)
				return err
			}
		}
	} else {
		for _, config := range configs {
			log := &PartitionCronLog{ConfigId: config.ConfigId, CronDate: date, Scheduler: scheduler,
				CheckInfo: config.Log, Status: status}
			err := tx.Debug().Table(tb).Create(log).Error
			if err != nil {
				tx.Rollback()
				slog.Error("msg", "add cron log failed", err)
				return err
			}
		}
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
