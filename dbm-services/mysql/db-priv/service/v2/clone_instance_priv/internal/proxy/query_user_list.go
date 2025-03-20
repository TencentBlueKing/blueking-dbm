package proxy

import (
	"dbm-services/mysql/priv-service/service/v2/internal/drs"
	"errors"
	"fmt"
	"log/slog"
	"strconv"
	"strings"

	pe "github.com/pkg/errors"
)

func QueryUserList(bkCloudId int64, addr string) ([]string, error) {
	adminAddr := adminAddr(addr)

	drsRes, err := drs.RPCProxyAdmin(
		bkCloudId,
		[]string{adminAddr},
		[]string{"SELECT * FROM USER"},
		false,
		600,
	)
	if err != nil {
		slog.Error(
			"query proxy user list",
			slog.String("address", adminAddr),
			slog.String("error", err.Error()),
		)
		return nil, pe.Wrap(err, "failed to query proxy user list")
	}

	if drsRes[0].ErrorMsg != "" {
		slog.Error(
			"query proxy user list",
			slog.String("address", adminAddr),
			slog.String("error", drsRes[0].ErrorMsg),
		)
		return nil, errors.New(drsRes[0].ErrorMsg)
	}

	if drsRes[0].CmdResults[0].ErrorMsg != "" {
		slog.Error(
			"failed to query proxy user list",
			slog.String("address", adminAddr),
			slog.String("error", drsRes[0].ErrorMsg),
		)
		return nil, errors.New(drsRes[0].ErrorMsg)
	}

	var res []string
	for _, row := range drsRes[0].CmdResults[0].TableData {
		res = append(res, row["user@ip"].(string))
	}

	return res, nil
}

func adminAddr(addr string) string {
	splitAddr := strings.Split(addr, ":")
	port, _ := strconv.Atoi(splitAddr[1])
	adminAddr := fmt.Sprintf("%s:%d", splitAddr[0], port+1000)
	return adminAddr
}
