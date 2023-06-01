package items_collect

import (
	"fmt"

	"dbm-services/mysql/db-tools/mysql-monitor/pkg/items_collect/character_consistency"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/items_collect/definer"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/items_collect/engine"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/items_collect/ext3_check"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/items_collect/ibd_statistic"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/items_collect/master_slave_heartbeat"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/items_collect/mysql_config_diff"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/items_collect/mysql_connlog"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/items_collect/mysql_errlog"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/items_collect/mysql_processlist"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/items_collect/proxy_backend"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/items_collect/proxy_user_list"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/items_collect/rotate_slowlog"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/items_collect/slave_status"
	mi "dbm-services/mysql/db-tools/mysql-monitor/pkg/monitor_item_interface"

	"golang.org/x/exp/slog"
)

// ToDo 加点说明字符串似乎能让list命令更好用
var registeredItemConstructor map[string]func(*mi.ConnectionCollect) mi.MonitorItemInterface

func registerItemConstructor(
	name string, f func(*mi.ConnectionCollect) mi.MonitorItemInterface,
) error {
	if _, ok := registeredItemConstructor[name]; ok {
		err := fmt.Errorf("%s already registered", name)
		slog.Error("register item creator", err)
		return err
	}
	registeredItemConstructor[name] = f
	return nil
}

// RegisteredItemConstructor TODO
func RegisteredItemConstructor() map[string]func(*mi.ConnectionCollect) mi.MonitorItemInterface {
	return registeredItemConstructor
}

func init() {
	registeredItemConstructor = make(map[string]func(*mi.ConnectionCollect) mi.MonitorItemInterface)
	/*
		注册监控项
	*/
	_ = registerItemConstructor(character_consistency.Register())
	_ = registerItemConstructor(definer.RegisterCheckTriggerDefiner())
	_ = registerItemConstructor(definer.RegisterCheckViewDefiner())
	_ = registerItemConstructor(definer.RegisterCheckRoutineDefiner())
	_ = registerItemConstructor(engine.Register())
	_ = registerItemConstructor(ext3_check.Register())
	_ = registerItemConstructor(master_slave_heartbeat.Register())
	_ = registerItemConstructor(slave_status.RegisterSlaveStatusChecker())
	_ = registerItemConstructor(mysql_errlog.RegisterMySQLErrNotice())
	_ = registerItemConstructor(mysql_errlog.RegisterMySQLErrCritical())
	_ = registerItemConstructor(mysql_errlog.RegisterSpiderErrNotice())
	_ = registerItemConstructor(mysql_errlog.RegisterSpiderErrWarn())
	_ = registerItemConstructor(mysql_errlog.RegisterSpiderErrCritical())
	_ = registerItemConstructor(mysql_processlist.RegisterMySQLLock())
	_ = registerItemConstructor(mysql_processlist.RegisterMySQLInject())
	_ = registerItemConstructor(rotate_slowlog.RegisterRotateSlowLog())
	_ = registerItemConstructor(mysql_connlog.RegisterMySQLConnLogSize())
	_ = registerItemConstructor(mysql_connlog.RegisterMySQLConnLogRotate())
	_ = registerItemConstructor(mysql_connlog.RegisterMySQLConnLogReport())
	_ = registerItemConstructor(mysql_config_diff.Register())
	_ = registerItemConstructor(proxy_user_list.Register())
	_ = registerItemConstructor(proxy_backend.Register())
	_ = registerItemConstructor(ibd_statistic.Register())
	_ = registerItemConstructor(slave_status.RegisterCtlReplicateChecker())
}
