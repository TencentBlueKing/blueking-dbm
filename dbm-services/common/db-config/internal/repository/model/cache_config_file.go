package model

import (
	"fmt"

	"bk-dbconfig/internal/api"

	"github.com/coocood/freecache"
	"github.com/pkg/errors"
	"gorm.io/gorm"

	"bk-dbconfig/pkg/core/logger"
	"bk-dbconfig/pkg/util/serialize"
)

// NotFoundInDB TODO
const NotFoundInDB = "1"

// IsConfigLevelEntityVersioned TODO
func IsConfigLevelEntityVersioned(namespace, confType, conFile, levelName string) bool {
	fd := api.BaseConfFileDef{Namespace: namespace, ConfType: confType, ConfFile: conFile}
	if fileDef, err := CacheGetConfigFile(fd); err == nil {
		if fileDef.LevelVersioned == levelName {
			return true
		}
	}
	return false
}

// CacheGetConfigFile godoc
// return nil,nil 表示db中不存在
func CacheGetConfigFile(fd api.BaseConfFileDef) (*ConfigFileDefModel, error) {
	cacheKey := []byte(fmt.Sprintf("%s|%s|%s", fd.Namespace, fd.ConfType, fd.ConfFile))

	if cacheVal, err := CacheLocal.Get(cacheKey); err != nil {
		if errors.Is(err, freecache.ErrNotFound) {
			return CacheSetAndGetConfigFile(fd)
			// return CacheGetConfigFile(namespace, confType, confFile)
		}
		return nil, err
	} else {
		cacheValStr := string(cacheVal)
		if cacheValStr == NotFoundInDB || cacheVal == nil {
			logger.Info("GetConfigFile not_found_in_db key=%s", cacheKey)
			return nil, nil
		}
		f := ConfigFileDefModel{}
		serialize.UnSerializeString(cacheValStr, &f, false)
		logger.Info("GetConfigFile from cache: %+v", f)
		return &f, nil
	}
}

// CacheSetAndGetConfigFile godoc
// 从 DB 里查询 plat config file，如果db中不存在 返回 nil, nil. 并cache不存在信息60s
func CacheSetAndGetConfigFile(fd api.BaseConfFileDef) (*ConfigFileDefModel, error) {
	cacheKey := []byte(fmt.Sprintf("%s|%s|%s", fd.Namespace, fd.ConfType, fd.ConfFile))

	confFiles, err := QueryConfigFileDetail(fd.Namespace, fd.ConfType, fd.ConfFile)
	if err != nil {
		if errors.Is(err, gorm.ErrRecordNotFound) { // not in db
			logger.Info("CacheSetAndGetConfigFile not_found_in_db key=%s", cacheKey)
			CacheLocal.Set(cacheKey, []byte(NotFoundInDB), 60)
			return nil, nil
		}
		return nil, err
	}
	f := confFiles[0]
	// logger.Info("CacheSetAndGetConfigFile to cache: %+v", f)

	cacheVal, _ := serialize.SerializeToString(f, false)
	CacheLocal.Set(cacheKey, []byte(cacheVal), 300)
	if f.Namespace == fd.Namespace && f.ConfType == fd.ConfType && f.ConfFile == fd.ConfFile {
		return f, nil
	} else {
		return nil, errors.Errorf("found in db but set cache failed %s", fd.ConfFile)
	}
}

// ConfTypeInfo TODO
type ConfTypeInfo struct {
	ConfFiles         []string `json:"conf_files"`
	ConfNameValidate  int8     `json:"conf_name_validate"`
	ConfValueValidate int8     `json:"conf_value_validate"`
	ValueTypeStrict   int8     `json:"value_type_strict"`
	LevelVersioned    string   `json:"level_versioned"`
	LevelNames        string   `json:"level_names"`
}

// ConfTypeFile TODO
type ConfTypeFile = map[string]ConfTypeInfo

// CacheNamespaceList TODO
var CacheNamespaceList []string

// CacheNamespaceType TODO
var CacheNamespaceType map[string]ConfTypeFile

// ConfFileInfo TODO
type ConfFileInfo struct {
	ConfFile          string `json:"conf_file"`
	ConfFileLC        string `json:"conf_file_lc"`
	LevelNames        string `json:"level_names"`
	LevelVersioned    string `json:"level_versioned"`
	ConfNameValidate  int8   `json:"conf_name_validate"`
	ConfValueValidate int8   `json:"conf_value_validate"`
}

// CacheNamespaceType2 key: namespace.dbconf, value: file_list
var CacheNamespaceType2 map[string]ConfFileInfo

// CacheGetConfigFileList TODO
//
//	{
//	   "namespace1": {
//	       "conf_type1": {"conf_files": ["f1", "f2"], "conf_name_validate":1, "level_name":""},
//	       "conf_type2": {"conf_files": ["f1", "f2"]}
//	   },
//	   "namespace1": {
//	       "conf_type3": {"conf_files": ["f1", "f2"]},
//	       "conf_type4": {"conf_files": ["f1", "f2"]}
//	   }
//	}
func CacheGetConfigFileList(namespace, confType, confFile string) (map[string]ConfTypeFile, error) {
	cacheKey := []byte("namespace|conf_type")
	if cacheVal, err := CacheLocal.Get(cacheKey); err != nil {
		if errors.Is(err, freecache.ErrNotFound) {
			return CacheSetAndGetConfigFileList(namespace, confType, confFile)
		}
		return nil, err
	} else {
		namespaceType := map[string]ConfTypeFile{}
		cacheValStr := string(cacheVal)
		serialize.UnSerializeString(cacheValStr, &namespaceType, false)
		logger.Info("CacheGetConfigFileList from cache: %+v", namespaceType)

		return namespaceType, nil
	}
}

// CacheSetAndGetConfigFileList TODO
func CacheSetAndGetConfigFileList(namespace, confType, confFile string) (map[string]ConfTypeFile, error) {
	namespaceType := map[string]ConfTypeFile{}

	confFiles, err := GetConfigFileList(namespace, confType, confFile)
	if err != nil {
		return nil, err
	}
	for _, tf := range confFiles {
		if _, ok := namespaceType[tf.Namespace]; ok {
			if confTypeInfo, ok := namespaceType[tf.Namespace][tf.ConfType]; !ok {
				// confTypeInfo.ConfFiles = append(confTypeInfo.ConfFiles, tf.ConfFile)
				confTypeInfo = ConfTypeInfo{
					ConfFiles:         []string{tf.ConfFile},
					ConfNameValidate:  tf.ConfNameValidate,
					ConfValueValidate: tf.ConfValueValidate,
					ValueTypeStrict:   tf.ValueTypeStrict,
					LevelVersioned:    tf.LevelVersioned,
				}
				namespaceType[tf.Namespace][tf.ConfType] = confTypeInfo
			} else {
				confTypeInfo.ConfFiles = append(confTypeInfo.ConfFiles, tf.ConfFile)
				namespaceType[tf.Namespace][tf.ConfType] = confTypeInfo
				// should not reach here
			}
		} else {
			namespaceType[tf.Namespace] = ConfTypeFile{ // key:conf_type, value:ConfTypeInfo
				tf.ConfType: ConfTypeInfo{
					ConfFiles:         []string{tf.ConfFile},
					ConfNameValidate:  tf.ConfNameValidate,
					ConfValueValidate: tf.ConfValueValidate,
					ValueTypeStrict:   tf.ValueTypeStrict,
					LevelVersioned:    tf.LevelVersioned,
				},
			}
		}
	}
	// logger.Info("CacheSetAndGetConfigFileList to cache: %+v", namespaceType)

	cacheKey := []byte("namespace|conf_type")
	cacheVal, _ := serialize.SerializeToString(namespaceType, false)
	CacheLocal.Set(cacheKey, []byte(cacheVal), 300)

	CacheNamespaceList = nil
	for k, _ := range namespaceType {
		CacheNamespaceList = append(CacheNamespaceList, k)
	}
	CacheNamespaceType = namespaceType
	return namespaceType, nil
}
