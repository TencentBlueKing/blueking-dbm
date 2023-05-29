package model

import (
	"log"

	"github.com/coocood/freecache"
)

// CacheLocal TODO
var CacheLocal *freecache.Cache

// InitCache TODO
func InitCache() {
	cacheSize := 10 * 1024 * 1024
	CacheLocal = freecache.NewCache(cacheSize)
}

// LoadCache TODO
func LoadCache() {
	// 加载Cache失败，panic
	if err := AutoRefreshCache(); err != nil {
		log.Panicln("Init start loading cache failed", err)
	}
}
