package model

import (
	"fmt"

	"bk-dbconfig/pkg/core/logger"
	"bk-dbconfig/pkg/util/serialize"

	"github.com/coocood/freecache"
	"github.com/pkg/errors"
	"gorm.io/gorm"
)

// CacheGetConfigNameDef godoc
// 存放 conf_name 定义
// key: confname|tendbha|dbconf|MySQL-5.7
// value: map[conf_name]ConfigNameDefModel
func CacheGetConfigNameDef(namespace, confType, confFile, confName string) (*ConfigNameDefModel, error) {
	cacheKey := []byte(fmt.Sprintf("confname|%s|%s|%s", namespace, confType, confFile))

	if cacheVal, err := CacheLocal.Get(cacheKey); err != nil {
		if errors.Is(err, freecache.ErrNotFound) {
			return CacheSetAndGetConfigName(namespace, confType, confFile, confName)
		}
		return nil, err
	} else {
		cacheValStr := string(cacheVal)
		if cacheValStr == NotFoundInDB || cacheVal == nil {
			logger.Info("CacheGetConfigNameDef not_found_in_db key=%s", cacheKey)
			return nil, nil
		}
		f := make(map[string]*ConfigNameDefModel, 0)
		// @TODO 可以做性能优化，不必每次都反序列化
		serialize.UnSerializeString(cacheValStr, &f, true)
		if v, ok := f[confName]; ok {
			// logger.Info("CacheGetConfigNameDef from cache: %+v", v)
			return v, nil
		} else {
			return CacheSetAndGetConfigName(namespace, confType, confFile, confName)
		}
	}
}

// CacheSetAndGetConfigName TODO
func CacheSetAndGetConfigName(namespace, confType, confFile, confName string) (*ConfigNameDefModel, error) {
	cacheKey := []byte(fmt.Sprintf("confname|%s|%s|%s", namespace, confType, confFile))

	confFiles, err := QueryConfigNamesPlat(namespace, confType, confFile, "")
	if err != nil {
		if errors.Is(err, gorm.ErrRecordNotFound) { // not in db
			logger.Info("SetAndGetCacheConfigName not_found_in_db key=%s", cacheKey)
			CacheLocal.Set(cacheKey, []byte(NotFoundInDB), 60)
			return nil, nil
		}
		return nil, err
	}
	f := confFiles
	// logger.Info("SetAndGetCacheConfigName to cache: %+v", f)

	fmap := make(map[string]*ConfigNameDefModel, 0)
	for _, v := range f {
		fmap[v.ConfName] = v
	}

	cacheVal, _ := serialize.SerializeToString(fmap, true)
	CacheLocal.Set(cacheKey, []byte(cacheVal), 300)
	if n, ok := fmap[confName]; ok {
		return n, nil
	}
	return nil, freecache.ErrNotFound
}
