package pkg

import (
	"dbm-services/common/reverseapi/define"
	"dbm-services/common/reverseapi/define/mysql"
	"encoding/json"
	"errors"
	"io"
	"log/slog"
	"os"
	"path/filepath"
)

func GetBkBizId() (int, error) {
	filePath := filepath.Join(
		define.DefaultCommonConfigDir,
		define.DefaultInstanceInfoFileName,
	)
	f, err := os.OpenFile(filePath, os.O_RDONLY, os.ModePerm)
	if err != nil {
		slog.Error("bk_biz_id updater job", slog.String("err", err.Error()))
		return 0, err
	}
	defer func() {
		_ = f.Close()
	}()

	b, err := io.ReadAll(f)
	if err != nil {
		slog.Error("bk_biz_id updater job", slog.String("err", err.Error()))
		return 0, err
	}

	var commInfos []mysql.ProxyInstanceInfo
	err = json.Unmarshal(b, &commInfos)
	if err != nil {
		slog.Error("bk_biz_id updater job", slog.String("err", err.Error()))
		return 0, err
	}

	if len(commInfos) == 0 {
		slog.Error("bk_biz_id updater job", slog.String("err", "no instance info"))
		return 0, errors.New("no instance info")
	}

	bkBizId := commInfos[0].BkBizId

	return bkBizId, nil
}
