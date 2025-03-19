package clone_instance_priv

import (
	"dbm-services/mysql/priv-service/service/v2/clone_instance_priv/internal/mysql"
	"dbm-services/mysql/priv-service/service/v2/internal"
	"log/slog"
)

func (c *CloneInstancePrivPara) cloneMySQLPriv(isStorage bool) error {
	userList, err := mysql.QueryUserList(*c.BkCloudId, c.Source.Address, c.SystemUsers, c.Target.Address, c.logger)
	if err != nil {
		return err
	}

	c.logger.Info(
		"query mysql user list",
		slog.Int("users count", len(userList)),
	)

	v, err := internal.QueryMySQLVersion(*c.BkCloudId, c.Source.Address)
	if err != nil {
		c.logger.Error(
			"query source mysql version",
			slog.String("address", c.Source.Address),
			slog.String("error", err.Error()),
		)
		return err
	}
	c.sourceMySQLVersion = v
	c.logger.Info(
		"",
		slog.Int("source mysql version", v),
	)

	v, err = internal.QueryMySQLVersion(*c.BkCloudId, c.Target.Address)
	if err != nil {
		c.logger.Error(
			"query target mysql version",
			slog.String("address", c.Target.Address),
			slog.String("error", err.Error()),
		)
		return err
	}
	c.targetMySQLVersion = v
	c.logger.Info(
		"",
		slog.Int("target mysql version", v),
	)

	privs, err := mysql.QueryUserPriv(
		*c.BkCloudId, c.Source.Address, userList, c.sourceMySQLVersion >= 57 && isStorage, c.logger)
	if err != nil {
		c.logger.Error(
			"query users priv",
			slog.String("address", c.Source.Address),
			slog.String("error", err.Error()),
		)
		return err
	}
	c.logger.Info(
		"query users priv",
		slog.Int("user priv count", len(privs)),
	)

	// 这个函数其实不会失败
	// 只会生成一些奇怪的 sql
	// 最后会在 import 的时候失败
	privs, err = mysql.ProcessGrantSql(
		privs, c.Source.Address, c.Target.Address, c.sourceMySQLVersion, c.targetMySQLVersion, isStorage, c.logger,
	)
	if err != nil {
		c.logger.Error(
			"process grant sql",
			slog.String("address", c.Target.Address),
			slog.String("error", err.Error()),
		)
		return err
	}
	c.logger.Info("grant sql process success", slog.Int("priv count", len(privs)))

	err = mysql.ImportPriv(*c.BkCloudId, c.Target.Address, privs, c.logger)
	if err != nil {
		c.logger.Error(
			"import priv",
			slog.String("address", c.Target.Address),
			slog.String("error", err.Error()),
		)
		return err
	}

	c.logger.Info("clone mysql priv finish")
	return nil
}
