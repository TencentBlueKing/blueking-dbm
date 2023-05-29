package model

import (
	"fmt"

	"bk-dbconfig/pkg/core/logger"
	"bk-dbconfig/pkg/util/serialize"

	"github.com/coocood/freecache"
	"github.com/pkg/errors"
	"gorm.io/gorm"
)

// CacheGetLevelNode godoc
// 根据 node_id 查询 namespace,bk_biz_id,conf_type,conf_file,level_name,level_value
func CacheGetLevelNode(nodeID uint64) (*ConfigFileNodeModel, error) {
	cacheKey := []byte(fmt.Sprintf("LN.%d", nodeID))

	if cacheVal, err := CacheLocal.Get(cacheKey); err != nil {
		if errors.Is(err, freecache.ErrNotFound) {
			return CacheSetAndGetLevelNode(nodeID)
		}
		return nil, err
	} else {
		cacheValStr := string(cacheVal)
		if cacheValStr == NotFoundInDB || cacheVal == nil {
			logger.Info("CacheGetLevelNode not_found_in_db key=%s", cacheKey)
			return nil, nil
		}
		fileNode := &ConfigFileNodeModel{}
		// @TODO 可以做性能优化，不必每次都反序列化
		serialize.UnSerializeString(cacheValStr, &fileNode, true)
		return fileNode, nil
	}
}

// CacheSetAndGetLevelNode TODO
func CacheSetAndGetLevelNode(nodeID uint64) (*ConfigFileNodeModel, error) {
	cacheKey := []byte(fmt.Sprintf("LN.%d", nodeID))
	fn := ConfigFileNodeModel{ID: nodeID}
	fileNode, err := fn.Detail(DB.Self)
	if err != nil {
		if errors.Is(err, gorm.ErrRecordNotFound) { // not in db
			logger.Info("CacheSetAndGetLevelNode not_found_in_db key=%s", cacheKey)
			CacheLocal.Set(cacheKey, []byte(NotFoundInDB), 60)
			return nil, nil
		}
		return nil, err
	}
	if fileNode == nil {
		return nil, freecache.ErrNotFound
	} else {
		logger.Info("CacheSetAndGetLevelNode to cache: %+v", fileNode)
		cacheVal, _ := serialize.SerializeToString(fileNode, true)
		CacheLocal.Set(cacheKey, []byte(cacheVal), 300)
		return fileNode, nil
	}
}
