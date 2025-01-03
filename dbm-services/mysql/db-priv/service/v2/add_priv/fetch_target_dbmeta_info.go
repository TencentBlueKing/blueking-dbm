package add_priv

import (
	"dbm-services/mysql/priv-service/service"
	"dbm-services/mysql/priv-service/util"
	"encoding/json"
	"fmt"
	"log/slog"
	"net/http"
)

// 这个函数的 python api 是个循环, 这里没有啥控制的必要
func (c *PrivTaskPara) fetchTargetDBMetaInfo() ([]*service.Instance, error) {
	url := fmt.Sprintf(
		"/apis/proxypass/dbmeta/priv_manager/mysql/%s/bulk_cluster_instances/",
		c.ClusterType,
	)
	slog.Info(
		"fetch target db meta info",
		slog.String("url", url),
	)

	result, err := util.DbmetaClient.Do(
		http.MethodPost,
		url,
		struct {
			EntryNames []string `json:"entry_names" url:"entry_names"`
		}{
			EntryNames: c.TargetInstances,
		},
	)
	if err != nil {
		slog.Error(
			"fetch target detail",
			slog.Any("entry_names", c.TargetInstances),
			slog.String("err", err.Error()),
		)
		return nil, err
	}
	slog.Info("fetch target db meta info", slog.Any("result", result))

	res := make([]*service.Instance, 0)
	err = json.Unmarshal(result.Data, &res)
	if err != nil {
		slog.Error(
			"fetch target detail failed",
			slog.String("err", err.Error()),
		)
		return nil, err
	}
	slog.Info(
		"fetch target detail",
		slog.String("res", fmt.Sprintf("%+v", res)),
	)
	return res, nil
}
