package slave_status

import (
	"context"
	"database/sql"
	"fmt"

	"dbm-services/mysql/db-tools/mysql-monitor/pkg/config"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/monitor_item_interface"

	"github.com/pkg/errors"
	"golang.org/x/exp/slog"
)

var ctlReplicateName = "ctl-replicate"

type ctlReplicateChecker struct {
	slaveStatusChecker
}

// Run TODO
func (c *ctlReplicateChecker) Run() (msg string, err error) {
	isPrimary, err := c.isPrimary()
	if err != nil {
		return "", err
	}

	if !isPrimary {
		return "", nil
	}

	err = c.fetchSlaveStatus()
	if err != nil {
		return "", err
	}

	if c.slaveStatus == nil || len(c.slaveStatus) == 0 {
		return "empty slave status", nil
	}

	if !c.isOk() {
		slaveErr, err := c.collectError()
		if err != nil {
			return "", err
		}
		return fmt.Sprintf("IO/SQL thread not running: %s", slaveErr), nil

	}
	return "", nil
}

func (c *ctlReplicateChecker) isPrimary() (bool, error) {
	ctx, cancel := context.WithTimeout(context.Background(), config.MonitorConfig.InteractTimeout)
	defer cancel()

	var tcIsPrimary sql.NullInt32
	err := c.db.GetContext(ctx, &tcIsPrimary, `SELECT @@tc_is_primary`)
	if err != nil {
		slog.Error("select @@tc_is_primary", err)
		return false, err
	}

	if !tcIsPrimary.Valid {
		err := errors.Errorf("invalide tc_is_primary: %v", tcIsPrimary)
		slog.Error("select @@tc_is_primary", err)
		return false, err
	}

	return tcIsPrimary.Int32 == 1, nil
}

// Name TODO
func (c *ctlReplicateChecker) Name() string {
	return ctlReplicateName
}

// NewCtlReplicateChecker TODO
func NewCtlReplicateChecker(cc *monitor_item_interface.ConnectionCollect) monitor_item_interface.MonitorItemInterface {
	return &ctlReplicateChecker{slaveStatusChecker{
		db:          cc.CtlDB,
		slaveStatus: make(map[string]interface{}),
	}}
}

// RegisterCtlReplicateChecker TODO
func RegisterCtlReplicateChecker() (string, monitor_item_interface.MonitorItemConstructorFuncType) {
	return ctlReplicateName, NewCtlReplicateChecker
}
