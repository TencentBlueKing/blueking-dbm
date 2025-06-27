package reverseapi

import (
	"fmt"
	"os"
	"path/filepath"
	"strconv"
	"strings"

	"dbm-services/common/reverseapi/define"
	"dbm-services/common/reverseapi/internal/core"
	"dbm-services/common/reverseapi/pkg"

	"github.com/pkg/errors"
)

// NewCore
/*
根据 nginx addrs file 的内容格式不同, bkCloudId 不是必要的参数
1. 格式是 IP:PORT 时, bkCloudId 必须是正确的, 有意义的
2. 格式是 BK_CLOUD_ID:IP:PORT 时, bkCloudId 可以随便写一个, 会被文件内容覆盖
*/
func NewCore(bkCloudId int64) (*core.Core, error) {
	return NewCoreWithAddrsFile(
		bkCloudId,
		filepath.Join(define.DefaultCommonConfigDir, define.DefaultNginxProxyAddrsFileName),
	)
}

// NewCoreWithAddr
/*
根据 nginx addrs 的内容格式不同, bkCloudId 不是必要的参数
1. 格式是 IP:PORT 时, bkCloudId 必须是正确的, 有意义的
2. 格式是 BK_CLOUD_ID:IP:PORT 时, bkCloudId 可以随便写一个, 会被文件内容覆盖
*/
func NewCoreWithAddr(bkCloudId int64, alterNginxAddrs ...string) (*core.Core, error) {
	return newCore(bkCloudId, alterNginxAddrs...)
}

// NewCoreWithAddrsFile
/*
根据 nginx addrs file 的内容格式不同, bkCloudId 不是必要的参数
1. 格式是 IP:PORT 时, bkCloudId 必须是正确的, 有意义的
2. 格式是 BK_CLOUD_ID:IP:PORT 时, bkCloudId 可以随便写一个, 会被文件内容覆盖
*/
func NewCoreWithAddrsFile(bkCloudId int64, alterNginxAddrsFile string) (*core.Core, error) {
	if !filepath.IsAbs(alterNginxAddrsFile) {
		cwd, _ := os.Getwd()
		alterNginxAddrsFile = filepath.Join(cwd, alterNginxAddrsFile)
	}
	lines, err := pkg.ReadNginxProxyAddrs(alterNginxAddrsFile)
	if err != nil {
		return nil, errors.Wrap(err, "failed to read nginx proxy addrs")
	}

	return newCore(bkCloudId, lines...)
}

func newCore(bkCloudId int64, mixAddrs ...string) (*core.Core, error) {
	var err error
	var addrs []string
	var bkCloudIdMap = make(map[int64]int64) // case 3 时判断是不是一样的 bk cloud id

	for _, line := range mixAddrs {
		var addr string
		splitLine := strings.Split(line, ":")
		switch len(splitLine) {
		case 2:
			bkCloudIdMap[bkCloudId] = 0

			_, err = strconv.ParseInt(splitLine[1], 10, 64)
			if err != nil {
				return nil, errors.Wrapf(err, "bad nginx proxy port: %s", line)
			}

			addr = fmt.Sprintf("%s:%s", splitLine[0], splitLine[1])
		case 3:
			bkCloudId, err = strconv.ParseInt(splitLine[0], 10, 64)
			if err != nil {
				return nil, errors.Wrapf(err, "bad nginx bk cloud id: %s", line)
			}

			_, err = strconv.ParseInt(splitLine[2], 10, 64)
			if err != nil {
				return nil, errors.Wrapf(err, "bad nginx proxy port: %s", line)
			}

			bkCloudIdMap[bkCloudId] = 0
			addr = fmt.Sprintf("%s:%s", splitLine[1], splitLine[2])
		default:
			return nil, errors.Wrapf(err, "failed to parse line from %s", line)
		}
		addrs = append(addrs, addr)
	}

	if len(bkCloudIdMap) > 1 {
		return nil, errors.Errorf("different bk_cloud_id from %v", mixAddrs)
	}

	return core.NewCore(bkCloudId, addrs...), nil
}
