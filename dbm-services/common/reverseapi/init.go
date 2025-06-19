package reverseapi

import (
	"dbm-services/common/reverseapi/define"
	"dbm-services/common/reverseapi/internal/core"
	"dbm-services/common/reverseapi/pkg"
	"os"
	"path/filepath"

	"github.com/pkg/errors"
)

func NewCore(bkCloudId int64) (*core.Core, error) {
	return NewCoreWithAddrsFile(
		bkCloudId,
		filepath.Join(define.DefaultCommonConfigDir, define.DefaultNginxProxyAddrsFileName),
	)
}

func NewCoreWithAddr(bkCloudId int64, alterNginxAddrs ...string) *core.Core {
	return core.NewCore(bkCloudId, alterNginxAddrs...)
}

func NewCoreWithAddrsFile(bkCloudId int64, alterNginxAddrsFile string) (*core.Core, error) {
	if !filepath.IsAbs(alterNginxAddrsFile) {
		cwd, _ := os.Getwd()
		alterNginxAddrsFile = filepath.Join(cwd, alterNginxAddrsFile)
	}
	addrs, err := pkg.ReadNginxProxyAddrs(alterNginxAddrsFile)
	if err != nil {
		return nil, errors.Wrap(err, "failed to read nginx proxy addrs")
	}
	return NewCoreWithAddr(bkCloudId, addrs...), nil
}
