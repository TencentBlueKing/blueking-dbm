package model

import (
	"slices"

	"bk-dbconfig/internal/api"
	"bk-dbconfig/pkg/constvar"

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

func buildPlatConfigSql(whereMap map[string]interface{}, tableName string, columns []string) (string, error) {
	//m := &ConfigNameDefModel{}

	sb := sqlbuilder.NewSelectBuilder().Select(columns...).From(tableName)
	for k, v := range whereMap {
		sb.Where(sb.Equal(k, v))
	}
	sqlStr, sqlArgs := sb.Build()
	return sqlbuilder.MySQL.Interpolate(sqlStr, sqlArgs)
}

func queryPlat(namespace, confType, confFile string, o *api.QueryConfigOptions, db *gorm.DB) ([]*ConfigNameDefModel, error) {
	whereMap := map[string]interface{}{
		"namespace": namespace,
		"conf_type": confType,
		"conf_file": confFile,
		// "flag_visible": "1",
	}
	if o.ConfName != "" {
		//confNameList := strings.Split(o.ConfName, ",")
		//nameIn := strings.Join(confNameList, "','")
		whereMap["conf_name"] = o.ConfName
	}
	if o.ConfValue != "" {
		whereMap["value_default"] = o.ConfValue
	}
	sql1, err := buildPlatConfigSql(whereMap, ConfigNameDefModel{}.TableName(), []string{"*"})
	if err != nil {
		return nil, err
	}

	sql2, err := buildPlatConfigSql(whereMap, ConfigNamePlatModel{}.TableName(), []string{"*"})
	if err != nil {
		return nil, err
	}
	var namesDef []*ConfigNameDefModel
	if err := db.Debug().Raw(sql1).Scan(&namesDef).Error; err != nil {
		return nil, err
	}
	var namesPlat []*ConfigNamePlatModel
	if err := db.Debug().Raw(sql2).Scan(&namesPlat).Error; err != nil {
		return nil, err
	}
	namesDef = mergeConfNamePlat(namesDef, namesPlat)
	return namesDef, nil
}

// mergeConfNamePlat merge confNamesPlat to confNamesDef with overwrite
func mergeConfNamePlat(confNamesDef []*ConfigNameDefModel, confNamesPlat []*ConfigNamePlatModel) []*ConfigNameDefModel {
	for _, namePlat := range confNamesPlat {
		matched := false
		namePlat.ID = 0
		namePlat.CreateFrom = constvar.PlatTypePlat
		for i, nameDef := range confNamesDef {
			if nameDef.ConfName == namePlat.ConfName {
				namePlat.CreateFrom = constvar.PlatTypeDef // 配置定义在 plat/def 上都存在
				if namePlat.Deleted > 0 {
					confNamesDef = slices.Delete(confNamesDef, i, i+1)
				} else {
					converted := ConfigNameDefModel(*namePlat)
					confNamesDef[i] = &converted
				}
				matched = true
				break
			}
		}

		if !matched && namePlat.Deleted <= 0 {
			converted := ConfigNameDefModel(*namePlat)
			confNamesDef = append(confNamesDef, &converted)
		}
	}
	// 不在 plat 表里的，CreateFrom 为空，代表 def 且未被自定义
	return confNamesDef
}

func newConfigFromNameDef(nameDef *ConfigNameDefModel) *ConfigModel {
	var res *ConfigModel = &ConfigModel{
		Namespace:       nameDef.Namespace,
		ConfType:        nameDef.ConfType,
		ConfFile:        nameDef.ConfFile,
		ConfName:        nameDef.ConfName,
		ConfValue:       nameDef.ValueDefault,
		LevelName:       "plat",
		LevelValue:      "0",
		BKBizID:         "0",
		UpdatedRevision: "",
		Description:     nameDef.ConfNameLC,
		FlagDisable:     nameDef.FlagDisable,
		FlagLocked:      nameDef.FlagLocked,
	}
	return res
}

// GetSimpleConfig no  merge, all levels
func GetSimpleConfig(db *gorm.DB, r *api.BaseConfigNode, up *api.UpLevelInfo,
	o *api.QueryConfigOptions) ([]*ConfigModel, []*ConfigNameDefModel, error) {
	var allLevelConfigs []*ConfigModel

	upLevel, err := GetUpLevelInfo(r, up)
	if err != nil {
		return nil, nil, err
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
		"description",
		"created_at",
		"updated_at",
	}
	configsPlat, err := queryPlat(r.Namespace, r.ConfType, r.ConfFile, o, db)
	if err != nil {
		return nil, nil, err
	}
	for _, oneNameDef := range configsPlat {
		if oneNameDef.FlagVisible == 1 {
			allLevelConfigs = append(allLevelConfigs, newConfigFromNameDef(oneNameDef))
		}
	}
	//allLevelConfigs = append(allLevelConfigs, newConfigFromNameDef(configsPlat)...)

	tx := db.Transaction(func(tx *gorm.DB) error {
		for levelName, levelValue := range upLevel.LevelInfo {
			if levelName == constvar.LevelPlat {
				continue
			}
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
				return nil, nil, err
			}
		}
	}

	return allLevelConfigs, configsPlat, tx
}
