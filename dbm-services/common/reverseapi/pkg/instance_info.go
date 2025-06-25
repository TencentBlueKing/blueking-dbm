package pkg

import (
	"dbm-services/common/reverseapi/define"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"slices"
	"time"

	reversemysqldef "dbm-services/common/reverseapi/define/mysql"
)

// GetSelfInfo 获取本实例信息
// if instance_info.info is too old, will return error. because info may can not be trusted
func GetSelfInfo(host string, port int) (sii *reversemysqldef.StorageInstanceInfo, err error) {
	filePath := filepath.Join(
		define.DefaultCommonConfigDir,
		define.DefaultInstanceInfoFileName,
	)
	f, err := os.OpenFile(filePath, os.O_RDONLY, os.ModePerm)
	if err != nil {
		return nil, err
	}
	if fstat, err := f.Stat(); err != nil {
		return nil, err
	} else {
		if time.Now().Sub(fstat.ModTime()).Hours() > 24 {
			return nil, fmt.Errorf("file %s is too old", filePath)
		}
	}

	b, err := io.ReadAll(f)
	if err != nil {
		return nil, err
	}

	var siis []reversemysqldef.StorageInstanceInfo
	err = json.Unmarshal(b, &siis)
	if err != nil {
		return nil, err
	}

	idx := slices.IndexFunc(siis, func(ele reversemysqldef.StorageInstanceInfo) bool {
		return ele.Ip == host && ele.Port == port
	})
	if idx < 0 {
		return nil, fmt.Errorf("can't find %s:%d in %v", host, port, siis)
	}
	return &siis[idx], nil
}
