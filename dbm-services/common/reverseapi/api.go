package reverseapi

import (
	"dbm-services/common/reverseapi/internal/common"
	"dbm-services/common/reverseapi/internal/mysql"
	"os"
	"path/filepath"

	"github.com/pkg/errors"
)

type ReverseApi struct {
	Common *common.Common
	MySQL  *mysql.MySQL
}

func NewReverseApi(bkCloudId int64) (*ReverseApi, error) {
	return NewReverseApiWithAddrsFile(bkCloudId, filepath.Join(DefaultCommonConfigDir, DefaultNginxProxyAddrsFileName))
}

func NewReverseApiWithAddr(bkCloudId int64, alterNginxAddrs ...string) *ReverseApi {
	return &ReverseApi{
		Common: common.NewCommon(bkCloudId, alterNginxAddrs...),
		MySQL:  mysql.NewMySQL(bkCloudId, alterNginxAddrs...),
	}
}

func NewReverseApiWithAddrsFile(bkCloudId int64, alterNginxAddrsFile string) (*ReverseApi, error) {
	if !filepath.IsAbs(alterNginxAddrsFile) {
		cwd, _ := os.Getwd()
		alterNginxAddrsFile = filepath.Join(cwd, alterNginxAddrsFile)
	}
	addrs, err := readNginxProxyAddrs(alterNginxAddrsFile)
	if err != nil {
		return nil, errors.Wrap(err, "failed to read nginx proxy addrs")
	}

	return NewReverseApiWithAddr(bkCloudId, addrs...), nil
}
