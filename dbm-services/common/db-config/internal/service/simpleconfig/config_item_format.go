package simpleconfig

import (
	"bk-dbconfig/internal/api"
	"bk-dbconfig/internal/repository/model"
	"bk-dbconfig/pkg/constvar"
	"bk-dbconfig/pkg/core/logger"
	"bk-dbconfig/pkg/util"
	"bk-dbconfig/pkg/validate"
	"encoding/json"
	"strings"

	"github.com/pkg/errors"
	"github.com/spf13/cast"
)

// FormatConfItemForResp TODO
// 返回配置项列表，可以根据 map / list 格式返回
// map后还可以跟 .#| 3个格式，作为分隔符，返回的格式会进一步
// 这里没有检查这一批 item 是否合法，比如重复的 conf_name
func FormatConfItemForResp(format string, configs []*model.ConfigModel) (map[string]interface{}, error) {
	confItems := make(map[string]interface{})
	if len(configs) == 0 {
		return confItems, nil
	}
	c0 := configs[0]
	fd := api.BaseConfFileDef{Namespace: c0.Namespace, ConfType: c0.ConfType, ConfFile: c0.ConfFile}
	cFile, err := model.CacheGetConfigFile(fd)
	if err != nil {
		return nil, err
	}
	if format == constvar.FormatMap {
		for _, c := range configs {
			confItems[c.ConfName] = CastValueType(c.ConfName, c.ConfValue, fd, cFile.ValueTypeStrict)
		}
	} else if strings.HasPrefix(format, constvar.FormatMap) {
		separator := strings.TrimPrefix(format, constvar.FormatMap)
		if separator == "" {
			for _, c := range configs {
				confItems[c.ConfName] = CastValueType(c.ConfName, c.ConfValue, fd, cFile.ValueTypeStrict)
			}
		} else {
			tmpContent := map[string]map[string]interface{}{}
			for _, c := range configs {
				confNames := strings.SplitN(c.ConfName, separator, 2) //  mysqld.max_connections
				if len(confNames) != 2 {
					// return nil, fmt.Errorf("confName error %s. format:%s", c.ConfName, format)
					confItems[c.ConfName] = CastValueType(c.ConfName, c.ConfValue, fd, cFile.ValueTypeStrict)
					continue
				}
				cSection := confNames[0]
				confName := confNames[1]
				if _, ok := tmpContent[cSection]; ok {
					tmpContent[cSection][confName] = CastValueType(c.ConfName, c.ConfValue, fd, cFile.ValueTypeStrict)
				} else {
					tmpContent[cSection] = make(map[string]interface{})
					tmpContent[cSection][confName] = CastValueType(c.ConfName, c.ConfValue, fd, cFile.ValueTypeStrict)
				}
			}
			for k, v := range tmpContent {
				confItems[k] = v
			}
		}
	} else if format == constvar.FormatList {
		for _, c := range configs {
			baseItem := NewBaseConfItemWithModel(c, "")
			confItems[c.ConfName] = baseItem
		}
	} else {
		return nil, errors.Errorf("illegal format %s", format)
	}
	return confItems, nil
}

// FormatConfItemOpForResp TODO
func FormatConfItemOpForResp(format string, configs []*model.ConfigModelOp) (map[string]interface{}, error) {
	confItems := make(map[string]interface{}, 0)
	if len(configs) == 0 {
		return confItems, nil
	}
	c0 := configs[0].Config
	fd := api.BaseConfFileDef{Namespace: c0.Namespace, ConfType: c0.ConfType, ConfFile: c0.ConfFile}
	confFile, err := model.CacheGetConfigFile(fd)
	if err != nil {
		return nil, err
	}
	if format == constvar.FormatMap {
		for _, config := range configs {
			c := config.Config
			confItems[c.ConfName] = CastValueType(c.ConfName, c.ConfValue, fd, confFile.ValueTypeStrict)
		}
	} else if format == constvar.FormatList {
		for _, config := range configs {
			c := config.Config
			baseItem := NewBaseConfItemWithModel(c, config.OPType)
			// OPType: config.OPType,
			confItems[c.ConfName] = baseItem
		}
	} else {
		return nil, errors.Errorf("illegal format %s", format)
	}
	return confItems, nil
}

// FormatConfigFileForResp TODO
// simple
func FormatConfigFileForResp(r *api.SimpleConfigQueryReq, configs []*model.ConfigModel) (*api.GenerateConfigResp,
	error) {
	simpleContent, err := FormatConfItemForResp(r.Format, configs)
	if err != nil {
		return nil, err
	}
	var resp = &api.GenerateConfigResp{
		BKBizID: r.BKBizID,
		BaseLevelDef: api.BaseLevelDef{
			LevelName:  r.LevelName,
			LevelValue: r.LevelValue,
		},
		ConfFile: r.ConfFile,
		Content:  simpleContent,
	}
	return resp, nil
}

// CastValueType 将 value string 转换成具体的类型
func CastValueType(confName string, confValue string, f api.BaseConfFileDef, valueTypeStrict int8) interface{} {
	if valueTypeStrict == 0 || util.ConfValueIsPlaceHolder(confValue) {
		return confValue
	}
	var valueType string
	var valueSubType string
	if nameDef, err := model.CacheGetConfigNameDef(f.Namespace, f.ConfType, f.ConfFile, confName); err != nil {
		logger.Error(errors.Wrapf(err, confName).Error())
	} else {
		valueType = nameDef.ValueType
		valueSubType = nameDef.ValueTypeSub
	}
	if valueType == "" {
		return confValue
	}
	if valueType == validate.DTypeInt {
		return cast.ToInt(confValue)
	} else if valueType == validate.DTypeFloat || valueType == validate.DTypeNumber {
		return cast.ToFloat32(confValue)
	} else if valueType == validate.DTypeBool {
		return util.ToBoolExt(confValue)
	} else if valueType == validate.DTypeString {
		if valueSubType == validate.DTypeSubList {
			newValue := util.SplitAnyRuneTrim(confValue, ",")
			return newValue
		} else if valueSubType == validate.DTypeSubMap {
			mapI := make(map[string]interface{})
			err := json.Unmarshal([]byte(confValue), &mapI)
			if err != nil {
				logger.Error("fail to unmarshal conf_value %s. err:%s", confValue, err.Error())
				return confValue
			}
			return mapI
		}
		return confValue
	} else {
		logger.Warn("%sun-support value_type %s to cast %s", f.ConfFile, valueType, confValue)
		return confValue
	}
}
