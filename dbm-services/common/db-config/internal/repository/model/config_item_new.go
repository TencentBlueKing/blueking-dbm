package model

import (
	"bk-dbconfig/internal/api"

	sqlbuilder "github.com/huandu/go-sqlbuilder"
	"gorm.io/gorm"
)

func buildLevelConfigSql(whereMap map[string]interface{}, columns []string) (string, error) {
	m := &ConfigModel{}

	sb := sqlbuilder.NewSelectBuilder().Select(columns...).From(m.TableName())
	for k, v := range whereMap {
		sb.Where(sb.Equal(k, v))
	}
	sqlStr, sqlArgs := sb.Build()
	return sqlbuilder.MySQL.Interpolate(sqlStr, sqlArgs)
}

func buildPlatConfigSql(whereMap map[string]interface{}, columns []string) (string, error) {
	m := &ConfigNameDefModel{}

	sb := sqlbuilder.NewSelectBuilder().Select(columns...).From(m.TableName())
	for k, v := range whereMap {
		sb.Where(sb.Equal(k, v))
	}
	sqlStr, sqlArgs := sb.Build()
	return sqlbuilder.MySQL.Interpolate(sqlStr, sqlArgs)
}

func queryPlat(namespace, confType, confFile string, o *api.QueryConfigOptions, db *gorm.DB) ([]*ConfigNameDefModel, error) {
	whereMap := map[string]interface{}{
		"namespace":    namespace,
		"conf_type":    confType,
		"conf_file":    confFile,
		"flag_visible": "1",
	}
	if o.ConfName != "" {
		//confNameList := strings.Split(o.ConfName, ",")
		//nameIn := strings.Join(confNameList, "','")
		whereMap["conf_name"] = o.ConfName
	}
	if o.ConfValue != "" {
		whereMap["value_default"] = o.ConfValue
	}
	sql, err := buildPlatConfigSql(whereMap, []string{"*"})
	if err != nil {
		return nil, err
	}
	var res []*ConfigNameDefModel
	if err := db.Debug().Raw(sql).Scan(&res).Error; err != nil {
		return nil, err
	}
	return res, nil
}

func newConfigFromNameDef(names []*ConfigNameDefModel) []*ConfigModel {
	var res []*ConfigModel
	for _, name := range names {
		res = append(res, &ConfigModel{
			Namespace:       name.Namespace,
			ConfType:        name.ConfType,
			ConfFile:        name.ConfFile,
			ConfName:        name.ConfName,
			ConfValue:       name.ValueDefault,
			LevelName:       "plat",
			LevelValue:      "0",
			BKBizID:         "0",
			UpdatedRevision: "",
			Description:     name.ConfNameLC,
			FlagDisable:     name.FlagDisable,
			FlagLocked:      name.FlagLocked,
		})
	}
	return res
}

func GetSimpleConfig(db *gorm.DB, r *api.BaseConfigNode, up *api.UpLevelInfo,
	o *api.QueryConfigOptions) ([]*ConfigModel, error) {
	var allLevelConfigs []*ConfigModel

	upLevel, err := GetUpLevelInfo(r, up)
	if err != nil {
		return nil, err
	}
	upLevel.LevelInfo[r.LevelName] = r.LevelValue
	upLevel.LevelInfo["app"] = r.BKBizID

	fieldNames := []string{
		"id",
		"bk_biz_id",
		"namespace",
		"conf_type",
		"conf_file",
		"conf_name",
		"level_name",
		"level_value",
		"conf_value",
		"flag_locked",
		"flag_disable",
		"updated_revision",
		"stage",
		"description",
		"created_at",
		"updated_at",
	}
	configsPlat, err := queryPlat(r.Namespace, r.ConfType, r.ConfFile, o, db)
	if err != nil {
		return nil, err
	}
	allLevelConfigs = append(allLevelConfigs, newConfigFromNameDef(configsPlat)...)

	tx := db.Transaction(func(tx *gorm.DB) error {
		for levelName, levelValue := range upLevel.LevelInfo {
			whereLevel := map[string]interface{}{
				"namespace":   r.Namespace,
				"conf_type":   r.ConfType,
				"conf_file":   r.ConfFile,
				"bk_biz_id":   r.BKBizID,
				"level_name":  levelName,
				"level_value": levelValue,
			}
			if o.ConfName != "" {
				whereLevel["conf_name"] = o.ConfName
			}
			if o.ConfValue != "" {
				whereLevel["conf_value"] = o.ConfValue
			}
			queryLevel, err := buildLevelConfigSql(whereLevel, fieldNames)
			if err != nil {
				panic(err)
			}
			var levelRes []*ConfigModel
			if err := tx.Debug().Raw(queryLevel).Scan(&levelRes).Error; err != nil {
				return err
			}
			allLevelConfigs = append(allLevelConfigs, levelRes...)
		}

		return nil
	})
	if o.Decrypt {
		for _, c := range allLevelConfigs {
			err = c.MayDecrypt()
			if err != nil {
				return nil, err
			}
		}
	}
	return allLevelConfigs, tx
}
