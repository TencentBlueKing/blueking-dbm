package simpleconfig

import (
	"bk-dbconfig/internal/api"
	"bk-dbconfig/internal/repository/model"

	"github.com/jinzhu/copier"
)

func QueryConfNameChanges(req *api.ConfNameChangesQueryReq) (resp []*api.ConfNameChangesQueryRowResp, err error) {
	changes, err := model.QueryConfNameChanges(model.DB.Self, req)
	if err != nil {
		return nil, err
	}
	// 这里返回的 changes 可能包含多个 conf_file
	// 分别在下面补齐 conf_file_lc 的信息
	for _, change := range changes {
		baseFileDesc := api.ConfigFileDesc{}
		baseFile := api.BaseConfFileDef{
			Namespace: change.Namespace,
			ConfType:  change.ConfType,
			ConfFile:  change.ConfFile,
		}
		if fileModel, err := model.CacheGetConfigFile(baseFile); err == nil && fileModel != nil {
			baseFileDesc = api.ConfigFileDesc{
				ConfFileLC: fileModel.ConfFileLC,
				ConfTypeLC: fileModel.ConfTypeLC,
			}
		}
		var rowChange = api.ConfNameChangesQueryRowResp{
			ConfigFileDesc: baseFileDesc,
		}
		_ = copier.Copy(&rowChange, change)
		resp = append(resp, &rowChange)
	}
	return resp, nil
}
