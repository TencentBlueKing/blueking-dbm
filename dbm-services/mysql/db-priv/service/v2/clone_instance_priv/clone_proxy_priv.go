package clone_instance_priv

import (
	"dbm-services/mysql/priv-service/service/v2/clone_instance_priv/internal/proxy"
	"log/slog"
)

func (c *CloneInstancePrivPara) cloneProxyPriv() error {
	userList, err := proxy.QueryUserList(*c.BkCloudId, c.Source.Address, c.logger)
	if err != nil {
		c.logger.Error(
			"query user list failed",
			slog.String("error", err.Error()),
			slog.String("address", c.Source.Address),
		)
		return err
	}

	c.logger.Info(
		"query proxy user list",
		slog.Int("users count", len(userList)),
	)
	// ToDo 这里想加一个正确性验证, 把非法的白名单排除掉, 就可以慢慢纠正白名单的诡异错误

	err = proxy.ImportUserList(*c.BkCloudId, c.Target.Address, userList, c.logger)
	if err != nil {
		c.logger.Info(
			"import proxy user list",
			slog.String("error", err.Error()),
			slog.String("address", c.Target.Address),
		)
		return err
	}

	c.logger.Info("clone proxy users import finish")
	return nil
}
