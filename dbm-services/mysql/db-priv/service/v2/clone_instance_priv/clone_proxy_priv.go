package clone_instance_priv

import (
	"dbm-services/mysql/priv-service/service/v2/clone_instance_priv/internal/proxy"
	"log/slog"
)

func (c *CloneInstancePrivPara) cloneProxyPriv() error {
	userList, err := proxy.QueryUserList(*c.BkCloudId, c.Source.Address)
	if err != nil {
		return err
	}

	slog.Info(
		"clone proxy users",
		slog.Int("users count", len(userList)),
	)
	// ToDo 这里想加一个正确性验证, 把非法的白名单排除掉, 就可以慢慢纠正白名单的诡异错误

	err = proxy.ImportUserList(*c.BkCloudId, c.Target.Address, userList)
	if err != nil {
		return err
	}

	slog.Info("clone proxy users import finish")
	return nil
}
