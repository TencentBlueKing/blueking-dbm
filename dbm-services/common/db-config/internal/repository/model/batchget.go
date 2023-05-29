package model

import "bk-dbconfig/internal/api"

// BatchGetConfigItem TODO
func BatchGetConfigItem(r *api.BatchGetConfigItemReq, confNames []string) (configs []*ConfigModel, err error) {
	where := &ConfigModel{
		Namespace: r.Namespace,
		ConfType:  r.ConfType,
		ConfFile:  r.ConfFile,
		LevelName: r.LevelName,
		// ConfName:  r.ConfName, // in
	}
	sqlRes := DB.Self.Model(&ConfigModel{}).
		Where(where).Where("level_value in ?", r.LevelValues).Where("conf_name in ?", confNames).
		Select("id", "level_value", "conf_name", "conf_value").Find(&configs)
	if err := sqlRes.Error; err != nil {
		return nil, err
	}
	for _, c := range configs {
		err = c.MayDecrypt()
		if err != nil {
			return nil, err
		}
	}
	return configs, nil
}
