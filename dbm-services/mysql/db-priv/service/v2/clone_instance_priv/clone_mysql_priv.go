package clone_instance_priv

import (
	"dbm-services/mysql/priv-service/service/v2/clone_instance_priv/internal/mysql"
	"dbm-services/mysql/priv-service/service/v2/internal"
	"log/slog"
)

func (c *CloneInstancePrivPara) cloneMySQLPriv(isStorage bool) error {
	userList, err := mysql.QueryUserList(*c.BkCloudId, c.Source.Address, c.SystemUsers, c.Target.Address)
	if err != nil {
		return err
	}

	slog.Info(
		"clone mysql users",
		slog.Int("users count", len(userList)),
	)

	v, err := internal.QueryMySQLVersion(*c.BkCloudId, c.Source.Address)
	if err != nil {
		slog.Error(
			"clone mysql priv",
			slog.String("address", c.Source.Address),
			slog.String("error", err.Error()),
		)
		return err
	}
	c.sourceMySQLVersion = v
	slog.Info(
		"clone mysql priv",
		slog.Int("source mysql version", v),
	)

	v, err = internal.QueryMySQLVersion(*c.BkCloudId, c.Target.Address)
	if err != nil {
		slog.Error(
			"clone mysql priv",
			slog.String("address", c.Target.Address),
			slog.String("error", err.Error()),
		)
		return err
	}
	c.targetMySQLVersion = v
	slog.Info(
		"clone mysql priv",
		slog.Int("target mysql version", v),
	)

	privs, err := mysql.QueryUserPriv(*c.BkCloudId, c.Source.Address, userList, c.sourceMySQLVersion >= 57 && isStorage)
	if err != nil {
		slog.Error(
			"clone mysql priv",
			slog.String("address", c.Source.Address),
			slog.String("error", err.Error()),
		)
		return err
	}
	slog.Info(
		"clone mysql priv",
		slog.Int("user priv count", len(privs)),
	)

	// 这个函数其实不会失败
	// 只会生成一些奇怪的 sql
	// 最后会在 import 的时候失败
	privs, err = mysql.ProcessGrantSql(
		privs, c.Source.Address, c.Target.Address, c.sourceMySQLVersion, c.targetMySQLVersion, isStorage,
	)
	if err != nil {
		slog.Error(
			"clone mysql priv",
			slog.String("address", c.Target.Address),
			slog.String("error", err.Error()),
		)
		return err
	}
	slog.Info("clone mysql priv priv process success")

	err = mysql.ImportPriv(*c.BkCloudId, c.Target.Address, privs)
	if err != nil {
		slog.Error(
			"clone mysql priv",
			slog.String("address", c.Target.Address),
			slog.String("error", err.Error()),
		)
		return err
	}

	slog.Info("clone mysql priv finish")
	return nil
}
