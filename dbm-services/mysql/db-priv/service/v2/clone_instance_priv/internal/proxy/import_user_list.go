package proxy

import (
	"dbm-services/mysql/priv-service/service/v2/internal/drs"
	"errors"
	"fmt"
	"log/slog"
	"strings"

	pe "github.com/pkg/errors"
)

const proxyUserImportBuckSize = 1000

func ImportUserList(bkCloudId int64, addr string, userList []string, logger *slog.Logger) error {
	adminAddr := adminAddr(addr)

	var oneBuckUsers []string
	var errCollect error

	logger.Info(
		fmt.Sprintf("import proxy users, buck size: %d, total users: %d", proxyUserImportBuckSize, len(userList)),
	)

	leftCount := len(userList)
	for _, user := range userList {
		oneBuckUsers = append(oneBuckUsers, user)
		if len(oneBuckUsers) >= proxyUserImportBuckSize {
			refreshSql := fmt.Sprintf(
				"refresh_users('%s', '+')",
				strings.Join(oneBuckUsers, ","),
			)

			err := doProxyUserImport(bkCloudId, adminAddr, refreshSql, logger)
			if err != nil {
				slog.Error(
					fmt.Sprintf("clone proxy users one buck, err: %s", err.Error()),
				)
				errCollect = errors.Join(errCollect, err)
			}

			leftCount -= proxyUserImportBuckSize
			logger.Info(
				fmt.Sprintf("clone proxy users one buck success, user left: %d", leftCount),
			)
			oneBuckUsers = []string{}
		}
	}
	if len(oneBuckUsers) > 0 {
		refreshSql := fmt.Sprintf(
			"refresh_users('%s', '+')",
			strings.Join(oneBuckUsers, ","),
		)
		err := doProxyUserImport(bkCloudId, adminAddr, refreshSql, logger)
		if err != nil {
			logger.Error(
				fmt.Sprintf("clone proxy users last buck, err: %s", err.Error()),
			)
			errCollect = errors.Join(errCollect, err)
		}

		// leftCount -= len(oneBuckUsers) 不用计数了
		logger.Info(
			"clone proxy users last buck success",
		)
	}

	/*
		这个检查没有必要
		if leftCount > 0 {
		}
	*/

	return errCollect
}

func doProxyUserImport(bkCloudId int64, address string, sql string, logger *slog.Logger) error {
	drsRes, err := drs.RPCProxyAdmin(
		bkCloudId,
		[]string{address},
		[]string{sql},
		false,
		600,
	)
	if err != nil {
		logger.Error(
			fmt.Sprintf("import proxy user, address: %s, sql: %s, err: %s", address, sql, err),
		)
		return pe.Wrap(err, "failed to import proxy user")
	}
	if drsRes[0].ErrorMsg != "" {
		logger.Error(
			fmt.Sprintf("import proxy user, address: %s, sql: %s, err: %s", address, sql, drsRes[0].ErrorMsg),
		)
		return errors.New(drsRes[0].ErrorMsg)
	}
	if drsRes[0].CmdResults[0].ErrorMsg != "" {
		logger.Error(
			fmt.Sprintf(
				"import proxy user, address: %s, sql: %s, err: %s",
				address, sql, drsRes[0].CmdResults[0].ErrorMsg),
		)
		return errors.New(drsRes[0].CmdResults[0].ErrorMsg)
	}
	return nil
}
