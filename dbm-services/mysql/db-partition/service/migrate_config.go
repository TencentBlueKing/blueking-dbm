package service

import (
	"dbm-services/mysql/db-partition/model"
	"dbm-services/mysql/priv-service/util"
	"fmt"
	"log/slog"
	"strings"
)

// MigrateConfig 从scr迁移分区配置
func (m *MigratePara) MigrateConfig() ([]int, []int, []int, []int, error) {
	GcsDb = &model.Database{
		Self: model.OpenDB(m.GcsDb.User, m.GcsDb.Psw, fmt.Sprintf("%s:%s", m.GcsDb.Host, m.GcsDb.Port), m.GcsDb.Name),
	}
	defer func() {
		sqlDB, _ := GcsDb.Self.DB()
		sqlDB.Close()
	}()
	// 检查迁移的入参
	apps, err := m.CheckPara()
	if err != nil {
		return nil, nil, nil, nil, err
	}
	var appWhere string
	var clusters []Cluster
	for app, bkBizId := range apps {
		appWhere = fmt.Sprintf("%s,'%s'", appWhere, app)
		// 获取业务的集群信息，为了获取cluster_id
		c, errInner := GetAllClustersInfo(BkBizId{bkBizId})
		if errInner != nil {
			return nil, nil, nil, nil, fmt.Errorf("从dbm biz_clusters获取集群信息失败: %s", errInner.Error())
		}
		clusters = append(clusters, c...)
	}
	// 生成集群域名和cluster_id的对应关系
	domainBkbizIdMap := make(map[string]int64, len(clusters))
	for _, item := range clusters {
		domainBkbizIdMap[item.ImmuteDomain] = item.Id
	}
	// app过滤条件
	appWhere = strings.TrimPrefix(appWhere, ",")
	// 检查是否可以迁移
	err = Check(appWhere)
	if err != nil {
		return nil, nil, nil, nil, err
	}

	// 区分迁移范围
	if m.Range == "mysql" {
		// 从scr迁移成功的mysql分区配置、从scr迁移失败的mysql分区配置
		mysqlIdFromScr, mysqlMigrateFail, errs := Migrate(appWhere, apps, domainBkbizIdMap, "mysql")
		if len(errs) > 0 {
			return mysqlIdFromScr, mysqlMigrateFail, nil, nil,
				fmt.Errorf("errors: %s", strings.Join(errs, "\n"))
		}
		return mysqlIdFromScr, mysqlMigrateFail, nil, nil, nil
	} else if m.Range == "spider" {
		// 从scr迁移成功的spider分区配置、从scr迁移失败的spider分区配置
		spiderIdFromScr, spiderMigrateFail, errs := Migrate(appWhere, apps, domainBkbizIdMap, "spider")
		if len(errs) > 0 {
			return nil, nil, spiderIdFromScr, spiderMigrateFail,
				fmt.Errorf("errors: %s", strings.Join(errs, "\n"))
		}
		return nil, nil, spiderIdFromScr, spiderMigrateFail, nil
	} else if m.Range == "all" {
		// 从scr迁移成功的mysql分区配置、从scr迁移失败的mysql分区配置
		mysqlIdFromScr, mysqlMigrateFail, errs := Migrate(appWhere, apps, domainBkbizIdMap, "mysql")
		spiderIdFromScr, spiderMigrateFail, errs1 := Migrate(appWhere, apps, domainBkbizIdMap, "spider")
		errs = append(errs, errs1...)
		if len(errs) > 0 {
			return mysqlIdFromScr, mysqlMigrateFail, spiderIdFromScr, spiderMigrateFail,
				fmt.Errorf("errors: %s", strings.Join(errs, "\n"))
		}
		return mysqlIdFromScr, mysqlMigrateFail, spiderIdFromScr, spiderMigrateFail, nil
	} else {
		return nil, nil, nil, nil, fmt.Errorf("not support range")
	}
}

// Migrate 迁移指定数据库类型和业务的分区规则
func Migrate(appWhere string, apps map[string]int64,
	domainBkbizIdMap map[string]int64, dbType string) ([]int, []int, []string) {
	var scrTable, dbmTable, logTable string
	if dbType == "mysql" {
		scrTable = MysqlPartitionConfigScr
		dbmTable = MysqlPartitionConfig
		logTable = MysqlManageLogsTable
	} else if dbType == "spider" {
		scrTable = SpiderPartitionConfigScr
		dbmTable = SpiderPartitionConfig
		logTable = SpiderManageLogsTable
	} else {
		return nil, nil, []string{fmt.Sprintf("not support %s dbtype", dbType)}
	}
	// 从scr迁移成功的分区配置
	var idFromScr []int
	// 从scr迁移失败的分区配置
	var migrateFail []int
	config := make([]*PartitionConfigWithApp, 0)
	var errs []string
	// 国内时区默认东八区、直连区域
	getConfigColumns := "select ID as id, app as app, Ip as immute_domain,Port as port, " +
		"0 as bk_cloud_id, DbLike as dblike, PartitionTableName as tblike, " +
		"PartitionColumn as  partition_column, PartitionColumnType as partition_column_type, " +
		"ReservedPartition as reserved_partition, ExtraPartition as extra_partition, " +
		"PartitionTimeInterval as partition_time_interval, PartitionType as partition_type, " +
		"ReservedPartition*PartitionTimeInterval as expire_time, '+08:00' as time_zone, 'online' as phase, " +
		"Creator as creator, Updator as updator, CreateTime as create_time, " +
		"UpdateTime as update_time "
	getMysqlConfig := fmt.Sprintf("%s from %s where app in (%s)", getConfigColumns,
		scrTable, appWhere)
	// 获取配置信息
	err := GcsDb.Self.Debug().Raw(getMysqlConfig).Scan(&config).Error
	if err != nil {
		slog.Error(getMysqlConfig, "dbType", dbType, "execute error", err, "sql", getMysqlConfig)
		return idFromScr, migrateFail, []string{fmt.Sprintf("dbtype[%s] %s", dbType, err.Error())}
	}
	// 迁移mysql分区配置
	for k, item := range config {
		id := item.ID
		// 清洗数据
		// app换成bk_biz_id
		// app没有对应的bk_biz_id
		if apps[item.App] == 0 {
			migrateFail = append(migrateFail, id)
			errs = append(errs, fmt.Sprintf("not find bk_biz_id for app: %s", item.App))
			continue
		} else {
			config[k].BkBizId = apps[item.App]
		}
		// 补充cluster_id
		// 域名没有对应的cluster_id
		if domainBkbizIdMap[item.ImmuteDomain] == 0 {
			migrateFail = append(migrateFail, id)
			errs = append(errs, fmt.Sprintf("dbtype[%s] not find cluster id for cluster: %s",
				dbType, item.ImmuteDomain))
			continue
		} else {
			config[k].ClusterId = int(domainBkbizIdMap[item.ImmuteDomain])
		}
		// 自增
		config[k].ID = 0
		partitionConfig := item.PartitionConfig
		// 插入分区规则，后台定时任务会执行
		err = model.DB.Self.Table(dbmTable).Create(&partitionConfig).Error
		if err != nil {
			migrateFail = append(migrateFail, id)
			errs = append(errs, err.Error())
			slog.Error("msg", "insert rule", err)
		} else {
			// 记录从scr迁移的id
			idFromScr = append(idFromScr, id)
			// 记录日志
			CreateManageLog(dbmTable, logTable, partitionConfig.ID,
				"Insert", "migrator")
		}
	}
	return idFromScr, migrateFail, errs
}

// CheckPara 检查迁移分区配置的参数
func (m *MigratePara) CheckPara() (map[string]int64, error) {
	if m.Foreign == nil {
		return nil, fmt.Errorf("not input [foreign] parameter, not support foreign platform")
	}
	if *m.Foreign {
		return nil, fmt.Errorf("not support foreign platform")
	}

	tips := "请设置需要迁移的app列表，多个app用逗号间隔，格式如\nAPPS='{\"test\":1, \"test2\":2}',名称区分大小写"
	rangeTips := "range可选值：all、mysql、spider"
	if m.Apps == "" {
		slog.Error(tips)
		return nil, fmt.Errorf("apps为空，%s", tips)
	}
	apps, err := util.JsonToMap(m.Apps)
	if err != nil {
		slog.Error("apps格式错误", "err", err, "tips", tips)
		return nil, fmt.Errorf(tips)
	}
	if len(apps) == 0 {
		slog.Error(tips)
		return nil, fmt.Errorf("apps为空，%s", tips)
	}
	if m.Range == "" {
		return nil, fmt.Errorf("%s，不能为空", rangeTips)
	}
	if !(m.Range == "all" || m.Range == "mysql" || m.Range == "spider") {
		return nil, fmt.Errorf("，不支持[%s]", m.Range)
	}
	return apps, nil
}

// Check 分区迁移检查检查
func Check(appWhere string) error {
	mysqlMonth := make([]*PartitionConfigWithApp, 0)
	spiderMonth := make([]*PartitionConfigWithApp, 0)
	// 分区间隔的单位是月不再支持
	cols := "select ID as id, app as app, Ip as immute_domain,Port as port, DbLike as dblike, " +
		"PartitionTableName as tblike, " +
		"PartitionColumn as partition_column, PartitionColumnType as partition_column_type, " +
		"ReservedPartition as reserved_partition, ExtraPartition as extra_partition, " +
		"PartitionTimeInterval as partition_time_interval, PartitionType as partition_type, " +
		"Creator as creator, Updator as updator, CreateTime as create_time, " +
		"UpdateTime as update_time "
	mysqlSelect := fmt.Sprintf("%s from %s where app in (%s) and PartitionTimeWay like 'MONTH';",
		cols, MysqlPartitionConfigScr, appWhere)
	err := GcsDb.Self.Debug().Raw(mysqlSelect).Scan(&mysqlMonth).Error
	if err != nil {
		slog.Error(mysqlSelect, "execute error", err)
		return err
	}
	spiderSelect := fmt.Sprintf("%s from %s where app in (%s) and PartitionTimeWay like 'MONTH';",
		cols, SpiderPartitionConfigScr, appWhere)
	err = GcsDb.Self.Debug().Raw(spiderSelect).Scan(&spiderMonth).Error
	if err != nil {
		slog.Error(mysqlSelect, "execute error", err)
		return err
	}
	if len(spiderMonth) > 0 || len(mysqlMonth) > 0 {
		slog.Error("msg", "check not pass", "value of PartitionType is month, can not be migrated")
		slog.Error("msg", "mysql PartitionType month", fmt.Sprintf("%v", mysqlMonth))
		slog.Error("msg", "spider PartitionType month", fmt.Sprintf("%v", spiderMonth))
		return fmt.Errorf("check not pass, value of PartitionType is month, can not be migrated, check logs")
	}
	slog.Info("check pass")
	return nil
}
