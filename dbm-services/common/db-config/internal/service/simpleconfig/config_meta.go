package simpleconfig

import (
	"fmt"

	"bk-dbconfig/internal/api"
	"bk-dbconfig/internal/pkg/errno"
	"bk-dbconfig/internal/repository/model"
	"bk-dbconfig/pkg/util"
	"bk-dbconfig/pkg/validate"

	"github.com/pkg/errors"
	"gorm.io/gorm"
)

// CheckConfNameAndValue godoc
// 检查配置项名字与值 是否合法
// 如果传递了 valueAllowed!="" 则检查传递的值，否则从db获取检查规则
// todo 去掉checkValue
func CheckConfNameAndValue(c *model.ConfigModel, checkValue bool, valueType, valueTypeSub, valueAllowed string) error {
	cn := model.ConfigNameDefModel{
		Namespace: c.Namespace,
		ConfType:  c.ConfType,
		ConfFile:  c.ConfFile,
		ConfName:  c.ConfName,
	}
	fd := api.BaseConfFileDef{Namespace: c.Namespace, ConfType: c.ConfType, ConfFile: c.ConfFile}
	checkName := true
	checkValue = true
	confFile, err := model.CacheGetConfigFile(fd)
	if err != nil {
		return err
	} else if confFile == nil { // 如果 db中没有该配置文件元数据，默认true
		checkValue = true
		checkName = true
	} else {
		checkValue = confFile.ConfValueValidate == 1
		checkName = confFile.ConfNameValidate == 1
	}
	sqlRes := model.DB.Self.Table(cn.TableName()).Where(cn.UniqueWhere()).Take(&cn)
	if checkName {
		if sqlRes.Error != nil {
			if errors.Is(sqlRes.Error, gorm.ErrRecordNotFound) {
				return errors.Errorf("illegal conf_name [%s] for %s %s", c.ConfName, c.Namespace, c.ConfType)
			}
			return sqlRes.Error
		}
		// 在 entity level 时，还是要允许编辑
		if cn.IsReadOnly() && !model.IsConfigLevelEntityVersioned(c.Namespace, c.ConfType, c.ConfFile, c.LevelName) {
			return errors.Errorf("conf_name %s is readonly", c.ConfName)
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
		err := validate.ValidateConfValue(cn.ValueDefault, cn.ValueType, cn.ValueTypeSub, cn.ValueAllowed)
		if err != nil {
			errors.WithMessage(err, c.ConfName)
		}
	} else {
		return nil
	}
	return nil
}

// QueryConfigNames TODO
func QueryConfigNames(r *api.QueryConfigNamesReq, isPub bool) (*api.QueryConfigNamesResp, error) {
	var confNames []*model.ConfigNameDefModel
	var err error
	if isPub {
		confNames, err = model.QueryConfigNamesPlat(r.Namespace, r.ConfType, r.ConfFile, r.ConfName)
	} else {
		confNames, err = model.QueryConfigNames(r.Namespace, r.ConfType, r.ConfFile, r.ConfName)
	}
	if err != nil {
		return nil, err
	}
	var resp = &api.QueryConfigNamesResp{
		ConfFile: r.ConfFile,
	}
	namesMap := make(map[string]*api.ConfNameDef)
	for _, c := range confNames {
		namesMap[c.ConfName] = &api.ConfNameDef{
			ConfName:     c.ConfName,
			ConfNameLC:   c.ConfNameLC,
			ValueType:    c.ValueType,
			ValueTypeSub: c.ValueTypeSub,
			ValueDefault: c.ValueDefault,
			ValueAllowed: c.ValueAllowed,
			NeedRestart:  c.NeedRestart,
			FlagDisable:  c.FlagDisable,
			FlagLocked:   c.FlagLocked,
			Description:  c.Description,
			FlagStatus:   c.FlagStatus,
		}
	}
	resp.ConfNames = namesMap
	return resp, nil
}

// QueryConfigTypeInfo TODO
func QueryConfigTypeInfo(r *api.QueryConfigTypeReq) (*api.QueryConfigTypeResp, error) {
	// query conf type info
	confTypes, err := model.QueryConfigFileDetail(r.Namespace, r.ConfType, r.ConfFile)
	if err != nil {
		return nil, err
	}
	// conf type info
	ct := confTypes[0]

	// conf_files
	confFiles := make(map[string]string)
	for _, confType := range confTypes {
		confFiles[confType.ConfFile] = confType.ConfFileLC
	}
	// conf_levels
	confLevels := make(map[string]string)
	levelNames := util.SplitAnyRune(ct.LevelNames, ", ")
	if levels, err := model.QueryConfigLevel(levelNames); err != nil {
		return nil, err
	} else {
		for _, l := range levels {
			confLevels[l.LevelName] = l.LevelNameCN
		}
	}

	var resp = &api.QueryConfigTypeResp{
		ConfTypeInfo: &api.ConfTypeDef{
			// ConfType:         ct.ConfType,
			// ConfTypeLC:       ct.ConfTypeLC,
			LevelVersioned:    ct.LevelVersioned,
			LevelNames:        ct.LevelNames,
			VersionKeepDays:   ct.VersionKeepDays,
			VersionKeepLimit:  ct.VersionKeepLimit,
			ConfNameValidate:  ct.ConfNameValidate,
			ConfValueValidate: ct.ConfValueValidate,
			ConfNameOrder:     ct.ConfNameOrder,
		},
		ConfFiles:  confFiles,
		ConfLevels: confLevels,
	}
	return resp, nil
}

// CheckValidConfType 检查 namespace, conf_type, conf_file, level_name 的合法性
// 如果 level_name = "" 不检查 level_name
// 如果 needVersioned >=2 不做版本化相关检查
func CheckValidConfType(namespace, confType, confFiles2, levelName string, needVersioned int8) error {
	confFiles := util.SplitAnyRuneTrim(confFiles2, ",")
	for _, confFile := range confFiles {
		errStr := fmt.Sprintf("namespace=%s, conf_type=%s, conf_file=%s", namespace, confType, confFile)
		fd := api.BaseConfFileDef{Namespace: namespace, ConfType: confType, ConfFile: confFile}
		if f, e := model.CacheGetConfigFile(fd); e != nil {
			return errors.Wrapf(errno.ErrConfFile, "NotFound: %s", errStr)
		} else if f == nil {
			return errors.Wrapf(errno.ErrNamespaceType, errStr)
		} else {
			if levelName != "" {
				if !util.StringsHas(f.LevelNameList, levelName) {
					return errors.Wrapf(errno.ErrLevelName, "allowed [%s] but given %s", f.LevelNames, levelName)
				}
			}
			if needVersioned < 2 {
				if needVersioned == 1 && f.LevelVersioned == "" {
					return errors.Errorf("conf_file is un-versionable for %s", errStr)
				} else if needVersioned == 0 && f.LevelVersioned != "" {
					return errors.Errorf("conf_file is versionable for %s", errStr)
				}
			}
		}
	}
	return nil
}

// checkVersionable 判断是否可以版本化
// 需先确认namespace confType 已合法
// 从 cache 中取，不涉及 DB 操作
func checkVersionable(namespace, confType string) bool {
	if namespaceInfo, ok := model.CacheNamespaceType[namespace]; ok {
		if typeInfo, ok := namespaceInfo[confType]; ok {
			if typeInfo.LevelVersioned != "" {
				return true
			}
		}
	}
	return false
}
