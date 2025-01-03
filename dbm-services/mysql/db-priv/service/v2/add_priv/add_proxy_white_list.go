package add_priv

import (
	"dbm-services/mysql/priv-service/service"
	"dbm-services/mysql/priv-service/service/v2/internal"
	"dbm-services/mysql/priv-service/service/v2/internal/drs"
	"errors"
	"fmt"
	"log/slog"
	//"github.com/pkg/errors"
)

func (c *PrivTaskPara) addWhiteList(targetMetaInfos []*service.Instance) (err error) {
	//if c.ClusterType == internal.ClusterTypeTenDBHA {
	//按 bk cloud id 分组
	// 这个二层循环的量不大
	workingProxies := make(map[int64][]string)
	for _, ele := range targetMetaInfos {
		if ele.BindTo == internal.MachineTypeProxy {
			for _, p := range ele.Proxies {
				if _, ok := workingProxies[ele.BkCloudId]; !ok {
					workingProxies[ele.BkCloudId] = make([]string, 0)
				}
				workingProxies[ele.BkCloudId] = append(
					workingProxies[ele.BkCloudId],
					fmt.Sprintf(`%s:%d`, p.IP, p.AdminPort),
				)
			}
		}
	}
	slog.Info(
		"add proxy white list",
		slog.Any("proxies", workingProxies),
	)

	if len(workingProxies) <= 0 {
		return nil
	}

	cmds := generateProxyCmds(c.SourceIPs, c.User)
	slog.Info(
		"add proxy white list",
		slog.Any("cmds", cmds),
	)

	// drs 执行多个 sql 是循环一个一个来的
	// 所以批量发送是可以的, 只是这么搞 drs 负载估计要炸
	// 这里搞并发的意义不大
	var errCollect error
	for bkCloudId, addresses := range workingProxies {
		slog.Info(
			"add proxy white list",
			slog.Int64("bk_cloud_id", bkCloudId),
			slog.Any("addresses", addresses),
		)
		drsRes, err := drs.RPCProxyAdmin(
			bkCloudId,
			addresses,
			cmds,
			false,
			0,
		)
		if err != nil {
			slog.Error("add proxy white list", slog.String("err", err.Error()))
			return err
		}

		// 错误要收集起来
		ec := collectErrors(drsRes)
		if ec != nil {
			slog.Error("add proxy white list", slog.String("err collection", ec.Error()))
			errCollect = errors.Join(errCollect, ec)
		} else {
			slog.Info(
				"add proxy white list success",
				slog.Int64("bk_cloud_id", bkCloudId),
			)
		}
	}
	if errCollect != nil {
		return errCollect
	}

	return nil
}

func collectErrors(res []*drs.OneAddressResult) (ec error) {
	for _, r := range res {
		if r.ErrorMsg != "" {
			err := fmt.Errorf(
				"add proxy white list on %s: %s", r.Address, r.ErrorMsg,
			)
			ec = errors.Join(ec, err)
			continue
		}
		if r.CmdResults[0].ErrorMsg != "" {
			err := fmt.Errorf(
				"add proxy white list on %s: %s", r.Address, r.CmdResults[0].ErrorMsg,
			)
			ec = errors.Join(ec, err)
			continue
		}
	}
	return ec
}

func generateProxyCmds(clientIps []string, username string) (cmds []string) {
	for _, clientIp := range clientIps {
		//clientIp 可能是 localhost, 要忽略
		if clientIp == "localhost" {
			continue
		}
		cmds = append(
			cmds,
			fmt.Sprintf(`refresh_users('%s@%s', '+')`,
				username, clientIp,
			))
	}
	return cmds
}
