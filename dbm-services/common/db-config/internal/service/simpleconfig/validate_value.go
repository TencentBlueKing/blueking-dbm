package simpleconfig

import (
	"errors"

	"bk-dbconfig/internal/api"
	"bk-dbconfig/internal/repository/model"
	"bk-dbconfig/pkg/util"
	"bk-dbconfig/pkg/validatestruct"

	errors2 "github.com/pkg/errors"
	"gorm.io/gorm"
)

// ValidateValueForClient 给前端调用
// 实际保存到 db 的时候，还会根据 db里的值进行校验
func ValidateValueForClient(items []*api.UpsertConfNames) error {
	var errs error
	for _, c := range items {
		var err error
		if c.ValueType == "" {
			errs = errors.Join(errs, errors2.Errorf("conf_name %s value_type is empty", c.ConfName))
		}
		if c.FlagLocked == 1 || c.FlagReadonly == 1 {
			errs = errors.Join(errs, errors2.Errorf("conf_name %s is readonly", c.ConfName))
		}
		if c.OPType == "remove" || util.ConfValueIsPlaceHolder(c.ValueDefault) {
			continue
		}

		if err = validatestruct.ValidateConfValue(c.ValueDefault, c.ValueType, c.ValueTypeSub, c.ValueAllowed); err != nil {
			errs = errors.Join(errs, err)
		}
	}
	return errs
}

// ValidateValue godoc
// 检查配置项名字与值 是否合法
// 如果传递了 valueAllowed!="" 则检查传递的值，否则从db获取检查规则
// todo 去掉checkValue
func ValidateValue(c *model.ConfigModel, valueType, valueTypeSub, valueAllowed string) error {
	cn := model.ConfigNameDefModel{
		Namespace: c.Namespace,
		ConfType:  c.ConfType,
		ConfFile:  c.ConfFile,
		ConfName:  c.ConfName,
	}
	fd := api.BaseConfFileDef{Namespace: c.Namespace, ConfType: c.ConfType, ConfFile: c.ConfFile}
	checkName := true
	checkValue := true
	confFile, err := model.CacheGetConfigFile(fd)
	if err != nil {
		return err
	} else {
		checkValue = confFile.ConfValueValidate == 1
		checkName = confFile.ConfNameValidate == 1
	}
	sqlRes := model.DB.Self.Table(cn.TableName()).Where(cn.UniqueWhere()).Take(&cn)
	if checkName {
		if sqlRes.Error != nil {
			if errors.Is(sqlRes.Error, gorm.ErrRecordNotFound) {
				return errors2.Errorf("illegal conf_name [%s] for %s %s", c.ConfName, c.Namespace, c.ConfType)
			}
			return sqlRes.Error
		}
		// 在 entity level 时，还是要允许编辑
		if cn.FlagLocked == 1 || cn.FlagReadonly == 1 {
			return errors2.Errorf("conf_name %s is readonly", c.ConfName)
		}
	}
	if checkValue && !util.ConfValueIsPlaceHolder(c.ConfValue) { // 如果 value 以 {{ 开头表示值待定
		if valueAllowed == "" {
			// 如果给了 valueAllowed 说明是检查平台配置, 平台配置有可能来自页面的修改，以页面的 valueType 和 valueAllowed 为准
			cn.ValueAllowed = valueAllowed
			cn.ValueType = valueType
			cn.ValueTypeSub = valueTypeSub
		}
		cn.ValueDefault = c.ConfValue
		// 如果不校验 conf_name， 那么 conf_name 可能在 name_def 里没定义，value_type, value_type_sub, value_allowed 都为空
		err = validatestruct.ValidateConfValue(cn.ValueDefault, cn.ValueType, cn.ValueTypeSub, cn.ValueAllowed)
		if err != nil {
			return errors2.WithMessage(err, c.ConfName)
		}
	} else {
		return nil
	}
	return nil
}
