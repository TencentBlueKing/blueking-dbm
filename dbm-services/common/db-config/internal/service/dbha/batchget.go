package dbha

import (
	"bk-dbconfig/internal/api"
	"bk-dbconfig/internal/repository/model"
	"bk-dbconfig/pkg/util"
)

// BatchGetConfigItem TODO
func BatchGetConfigItem(r *api.BatchGetConfigItemReq) (resp *api.BatchGetConfigItemResp, err error) {
	configs := make([]*model.ConfigModel, 0)
	confNames := util.SplitAnyRuneTrim(r.ConfName, ",")
	if configs, err = model.BatchGetConfigItem(r, confNames); err != nil {
		return nil, err
	}
	resp = &api.BatchGetConfigItemResp{
		BaseConfFileDef: api.BaseConfFileDef{
			Namespace: r.Namespace,
			ConfType:  r.ConfType,
			ConfFile:  r.ConfFile,
		},
		LevelName: r.LevelName,
		ConfName:  r.ConfName,
	}
	var content = map[string]map[string]string{}
	for _, conf := range configs {
		if _, ok := content[conf.LevelValue]; ok {
			content[conf.LevelValue][conf.ConfName] = conf.ConfValue
		} else {
			content[conf.LevelValue] = map[string]string{conf.ConfName: conf.ConfValue}
		}
	}
	resp.Content = content
	return resp, nil
}
