package simpleconfig

import (
	"bk-dbconfig/internal/pkg/cst"
	"bk-dbconfig/internal/pkg/errno"
	"bk-dbconfig/internal/repository/model"
	"bk-dbconfig/pkg/constvar"
	"bk-dbconfig/pkg/core/logger"
	"bk-dbconfig/pkg/util"
	"fmt"
	"strings"

	"github.com/pkg/errors"
)

// ConfigLevelCompare TODO
func ConfigLevelCompare(a, b *model.ConfigModel) (int, error) {
	ConfigLevelMap := cst.GetConfigLevelMap("")
	logger.Info("ConfigLevelCompare LevelName=%s", b.LevelName)
	if aLevel, ok := ConfigLevelMap[a.LevelName]; ok {
		if bLevel, ok := ConfigLevelMap[b.LevelName]; ok {
			if aLevel > bLevel {
				return 1, nil
			} else if aLevel < bLevel {
				return -1, nil
			} else {
				// app#conf_type#conf_name#namespace=>level should be unique
				return 0, errors.WithMessage(errno.ErrConfigLevel, a.ConfName)
			}
		} else {
			return 0, errors.Errorf("unknown configLevel1 %s", b.LevelName)
		}
	} else {
		return 0, errors.Errorf("unknown configLevel2 %s", a.LevelName)
	}
}

// MergeConfig TODO
// view = merge.xxx
func MergeConfig(configs []*model.ConfigModel, view string) ([]*model.ConfigModel, error) {
	// ConfigLevelKeys := ConfigLevelMap
	// ConfigUniqueKeys := []string{"bk_biz_id", "conf_type", "conf_name", "namespace"}
	// viewTmp := strings.Split(view, ".")
	configMergeMap := make(map[string]*model.ConfigModel)
	for _, config := range configs {
		configKey := ""

		if view == constvar.ViewRaw {
			configKey = fmt.Sprintf("%s|%s|%s|%s|%s|%s|%s",
				config.BKBizID, config.Namespace, config.ConfType, config.ConfFile,
				config.ConfName, config.LevelName, config.LevelValue)
		} else if strings.HasPrefix(view, constvar.ViewMerge) {
			configKey = fmt.Sprintf("%s|%s|%s|%s",
				config.Namespace, config.ConfType, config.ConfFile, config.ConfName)
		} else {
			return nil, errors.New("no view given")
		}
		logger.Debugf("service.MergeConfig merge: %s", configKey)
		if _, ok := configMergeMap[configKey]; !ok {
			configMergeMap[configKey] = config
		} else {
			if r, e := ConfigLevelCompare(config, configMergeMap[configKey]); e == nil {
				if r > 0 {
					logger.Warnf("service.MergeConfig replace: %+v", config)
					configMergeMap[configKey] = config
				}
			} else {
				return nil, e
			}
		}
	}
	// convert configMergeMap values to slice
	logger.Debugf("service.GetConfig configMergeMap: %+v", configMergeMap)
	configItems := make([]*model.ConfigModel, 0)
	for _, config := range configMergeMap {
		configItems = append(configItems, config)
	}
	return configItems, nil
}

// MergeConfigView TODO
func MergeConfigView(configs []*model.ConfigModelView, view string) ([]*model.ConfigModelView, error) {
	configMergeMap := make(map[string]*model.ConfigModelView)
	for _, config := range configs {
		configKey := ""
		if view == constvar.ViewRaw {
			configKey = fmt.Sprintf("%s#1-#%s#2-#%s#3-#%s#4-#%s#5-#%s#6%s",
				config.BKBizID, config.Namespace, config.ConfType, config.ConfName, config.LevelName, config.LevelValue,
				config.Cluster)
		} else if strings.HasPrefix(view, constvar.ViewMerge) {
			// configKey = fmt.Sprintf("%s=%s#1#%s#2#%s#3#%s", viewTmp[1], config.LevelValue, config.Namespace, config.ConfType, config.ConfName)
			if config.Cluster != "" {
				configKey = fmt.Sprintf("#1#%s#2#%s#3#%s#c4%s", config.Namespace, config.ConfType, config.ConfName, config.Cluster)
			} else if config.Module != "" {
				configKey = fmt.Sprintf("#1#%s#2#%s#3#%s#m4%s", config.Namespace, config.ConfType, config.ConfName, config.Module)
			} else {
				configKey = fmt.Sprintf("#1#%s#2#%s#3#%sa4%s", config.Namespace, config.ConfType, config.ConfName, config.BKBizID)
			}

		} else {
			return nil, fmt.Errorf("no view given")
		}
		logger.Debugf("service.MergeConfig merge: %s", configKey)
		if _, ok := configMergeMap[configKey]; !ok {
			configMergeMap[configKey] = config
		} else {
			if r, e := ConfigVLevelCompare(config, configMergeMap[configKey]); e == nil {
				if r > 0 {
					logger.Warnf("service.MergeConfig replace: %+v", config)
					configMergeMap[configKey] = config
				}
			} else {
				return nil, e
			}
		}
	}
	// convert configMergeMap values to slice
	logger.Debugf("service.GetConfig configMergeMap: %+v", configMergeMap)
	configItems := make([]*model.ConfigModelView, 0)
	for _, config := range configMergeMap {
		configItems = append(configItems, config)
	}
	return configItems, nil
}

// ConfigVLevelCompare TODO
func ConfigVLevelCompare(a, b *model.ConfigModelView) (int, error) {
	ConfigLevelMap := cst.GetConfigLevelMap("")
	if aLevel, ok := ConfigLevelMap[a.LevelName]; ok {
		if bLevel, ok := ConfigLevelMap[b.LevelName]; ok {
			if aLevel > bLevel {
				return 1, nil
			} else if aLevel < bLevel {
				return -1, nil
			} else {
				// app#conf_type#conf_name#namespace=>level should be unique
				return 0, errors.WithMessage(errno.ErrConfigLevel, a.ConfName)
			}
		} else {
			return 0, errors.New("unknown configLevel")
		}
	} else {
		return 0, errors.New("unknown configLevel")
	}
}

// ProcessConfig TODO
func ProcessConfig(configs []*model.ConfigModel) []*model.ConfigModel {
	for _, c := range configs {
		if c.ConfType == "user" || c.ConfFile == "notifier" {
			// split by ", ;"
			userList := util.SplitAnyRune(util.ReplaceBlank(c.ConfValue), ",;")
			userListUnique := util.SliceUniqMap(userList) // keep original order
			c.ConfValue = strings.Join(userListUnique, ",")
		}
	}
	return configs
}

// ProcessConfigV TODO
func ProcessConfigV(configs []*model.ConfigModelView) []*model.ConfigModelView {
	for _, c := range configs {
		if c.ConfType == "user" || c.ConfFile == "notifier" {
			// split by ", ;"
			userList := util.SplitAnyRune(util.ReplaceBlank(c.ConfValue), ",;")
			userListUnique := util.SliceUniqMap(userList) // keep original order
			c.ConfValue = strings.Join(userListUnique, ",")
		}
	}
	return configs
}

// FormatConfNameValueSimple TODO
func FormatConfNameValueSimple(configs []*model.ConfigModel) map[string]map[string]string {
	confValues := make(map[string]map[string]string, 0)
	for _, c := range configs {
		NSConfFile := ""
		if c.Namespace == "" {
			NSConfFile = c.ConfFile
		} else {
			NSConfFile = fmt.Sprintf("%s|%s", c.Namespace, c.ConfFile)
		}
		if _, ok := confValues[NSConfFile]; !ok {
			confValues[NSConfFile] = make(map[string]string, 0)
		}
		confValues[NSConfFile][c.ConfName] = c.ConfValue
	}
	return confValues
}
