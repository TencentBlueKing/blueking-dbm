package mysql

import (
	"dbm-services/mysql/priv-service/service/v2/internal/drs"
	"errors"
	"fmt"
	"log/slog"
	"sync"

	"golang.org/x/exp/maps"
)

func QueryUserPriv(bkCloudId int64, address string, userList []string, withShowCreate bool) (privs []string, err error) {
	var limiterChan = make(chan struct{}, 5)
	var wg sync.WaitGroup

	var resChan = make(chan []string)
	var errChan = make(chan error)
	var quitChan = make(chan struct{})

	go func() {
		for {
			select {
			case r := <-resChan:
				privs = append(privs, r...)
				wg.Done()
			case e := <-errChan:
				err = errors.Join(err, e)
				wg.Done()
			case <-quitChan:
				return
			default:
			}
		}
	}()

	var bulkUsers []string
	for _, user := range userList {
		bulkUsers = append(bulkUsers, user)

		if len(bulkUsers) >= 500 {
			limiterChan <- struct{}{}
			wg.Add(1)

			go func(users []string) {
				defer func() {
					<-limiterChan
				}()

				res, err := queryUserPriv(bkCloudId, address, users, withShowCreate)
				if err != nil {
					errChan <- err
					return
				}
				resChan <- res
			}(bulkUsers)

			bulkUsers = []string{}
		}
	}

	wg.Wait()
	//close(limiterChan)
	//close(errChan)
	//close(resChan)
	quitChan <- struct{}{}

	if len(bulkUsers) > 0 {
		res, e := queryUserPriv(bkCloudId, address, bulkUsers, withShowCreate)
		if err != nil {
			err = errors.Join(err, e)
		} else {
			privs = append(privs, res...)
		}
	}

	return
}

func queryUserPriv(bkCloudId int64, address string, userList []string, withShowCreate bool) (privs []string, err error) {
	var cmds []string
	for _, user := range userList {
		if withShowCreate {
			cmds = append(cmds, fmt.Sprintf("SHOW CREATE USER %s", user))
		}
		cmds = append(cmds, fmt.Sprintf("SHOW GRANTS FOR %s", user))
	}

	drsRes, err := drs.RPCMySQL(
		bkCloudId,
		[]string{address},
		cmds,
		true,
		600,
	)
	if err != nil {
		slog.Error(
			"query mysql user priv",
			slog.String("address", address),
			slog.String("error", err.Error()),
		)
		return nil, err
	}
	if drsRes[0].ErrorMsg != "" {
		slog.Error(
			"query mysql user priv",
			slog.String("address", address),
			slog.String("error", drsRes[0].ErrorMsg),
		)
		return nil, errors.New(drsRes[0].ErrorMsg)
	}

	for _, cr := range drsRes[0].CmdResults {
		if cr.ErrorMsg != "" {
			slog.Error(
				"query mysql user priv",
				slog.String("address", address),
				slog.String("error", cr.ErrorMsg),
				slog.String("cmd", cr.Cmd),
			)
			err = errors.Join(err, errors.New(cr.ErrorMsg))
			continue
		}
		for _, row := range cr.TableData {
			for _, p := range maps.Values(row) {
				privs = append(privs, p.(string))
			}
		}
	}
	return
}
