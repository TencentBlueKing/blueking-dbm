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
	// 从scr迁移成功的mysql分区配置
	var mysqlIdFromScr []int
	// 从scr迁移成功的spider分区配置
	var spiderIdFromScr []int
	// 从scr迁移失败的mysql分区配置
	var mysqlMigrateFail []int
	// 从scr迁移失败的spider分区配置
	var spiderMigrateFail []int
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
		return mysqlIdFromScr, spiderIdFromScr, mysqlMigrateFail, spiderMigrateFail, err
	}
	var appWhere string
	var clusters []Cluster
	for app, bkBizId := range apps {
		appWhere = fmt.Sprintf("%s,'%s'", appWhere, app)
		// 获取业务的集群信息，为了获取cluster_id
		c, errInner := GetAllClustersInfo(BkBizId{bkBizId})
		if errInner != nil {
			return mysqlIdFromScr, spiderIdFromScr, mysqlMigrateFail, spiderMigrateFail,
				fmt.Errorf("从dbm biz_clusters获取集群信息失败: %s", errInner.Error())
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
		return mysqlIdFromScr, spiderIdFromScr, mysqlMigrateFail, spiderMigrateFail, err
	}
	// mysql分区配置
	mysqlConfig := make([]*PartitionConfigWithApp, 0)
	// spider分区配置
	spiderConfig := make([]*PartitionConfigWithApp, 0)
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
		MysqlPartitionConfigScr, appWhere)
	getSpiderConfig := fmt.Sprintf("%s from %s where app in (%s)", getConfigColumns,
		SpiderPartitionConfigScr, appWhere)
	// 获取配置信息
	err = GcsDb.Self.Debug().Raw(getMysqlConfig).Scan(&mysqlConfig).Error
	if err != nil {
		slog.Error(getMysqlConfig, "execute error", err)
		return mysqlIdFromScr, spiderIdFromScr, mysqlMigrateFail, spiderMigrateFail, err
	}
	err = GcsDb.Self.Debug().Raw(getSpiderConfig).Scan(&spiderConfig).Error
	if err != nil {
		slog.Error(getSpiderConfig, "execute error", err)
		return mysqlIdFromScr, spiderIdFromScr, mysqlMigrateFail, spiderMigrateFail, err
	}
	var errs []string
	// 迁移mysql分区配置
	for k, item := range mysqlConfig {
		id := item.ID
		// 清洗数据
		// app换成bk_biz_id

		// app没有对应的bk_biz_id
		if apps[item.App] == 0 {
			mysqlMigrateFail = append(mysqlMigrateFail, id)
			errs = append(errs, fmt.Sprintf("not find bk_biz_id for app: %s", item.App))
			continue
		} else {
			mysqlConfig[k].BkBizId = apps[item.App]
		}
		// 补充cluster_id
		// 域名没有对应的cluster_id
		if domainBkbizIdMap[item.ImmuteDomain] == 0 {
			mysqlMigrateFail = append(mysqlMigrateFail, id)
			errs = append(errs, fmt.Sprintf("not find cluster id for cluster: %s", item.ImmuteDomain))
			continue
		} else {
			mysqlConfig[k].ClusterId = int(domainBkbizIdMap[item.ImmuteDomain])
		}
		// 自增
		mysqlConfig[k].ID = 0
		partitionConfig := item.PartitionConfig
		// 插入分区规则，后台定时任务会执行
		err = model.DB.Self.Table(MysqlPartitionConfig).Create(&partitionConfig).Error
		if err != nil {
			mysqlMigrateFail = append(mysqlMigrateFail, id)
			errs = append(errs, err.Error())
		} else {
			// 记录从scr迁移的id
			mysqlIdFromScr = append(mysqlIdFromScr, id)
			// 记录日志
			CreateManageLog(MysqlPartitionConfig, MysqlManageLogsTable, partitionConfig.ID,
				"Insert", "migrator")
		}
	}

	// 迁移spider分区配置
	for k, item := range spiderConfig {
		id := item.ID
		// app换成bk_biz_id
		if apps[item.App] == 0 {
			spiderMigrateFail = append(spiderMigrateFail, id)
			errs = append(errs, fmt.Sprintf("not find bk_biz_id for app: %s", item.App))
			continue
		} else {
			spiderConfig[k].BkBizId = apps[item.App]
		}
		// 补充cluster_id
		if domainBkbizIdMap[item.ImmuteDomain] == 0 {
			spiderMigrateFail = append(spiderMigrateFail, id)
			errs = append(errs, fmt.Sprintf("not find cluster id for cluster: %s", item.ImmuteDomain))
			continue
		} else {
			spiderConfig[k].ClusterId = int(domainBkbizIdMap[item.ImmuteDomain])
		}
		spiderConfig[k].ID = 0
		partitionConfig := item.PartitionConfig
		// 插入分区规则，后台定时任务会执行
		err = model.DB.Self.Table(SpiderPartitionConfig).Create(&partitionConfig).Error
		if err != nil {
			spiderMigrateFail = append(spiderMigrateFail, id)
			errs = append(errs, err.Error())
		} else {
			// 记录从scr迁移的id
			spiderIdFromScr = append(spiderIdFromScr, id)
			// 记录日志
			CreateManageLog(SpiderPartitionConfig, SpiderManageLogsTable, partitionConfig.ID,
				"Insert", "migrator")
		}
	}
	if len(errs) > 0 {
		return mysqlIdFromScr, spiderIdFromScr, mysqlMigrateFail, spiderMigrateFail,
			fmt.Errorf("errors: %s", strings.Join(errs, "\n"))
	}
	return mysqlIdFromScr, spiderIdFromScr, mysqlMigrateFail, spiderMigrateFail, nil
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
