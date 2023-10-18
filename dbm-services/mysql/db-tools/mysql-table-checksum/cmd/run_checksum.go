package cmd

import (
	"fmt"
	"log/slog"
	"os"

	"dbm-services/mysql/db-tools/mysql-table-checksum/pkg/checker"
	"dbm-services/mysql/db-tools/mysql-table-checksum/pkg/config"

	"github.com/juju/fslock"
)

func generateRun(mode config.CheckMode, configPath string) /*func(cmd *cobra.Command, args []string)*/ error {
	// return func(cmd *cobra.Command, args []string) error {
	err := config.InitConfig(configPath)
	if err != nil {
		return err
	}

	initLogger(config.ChecksumConfig.Log, mode)

	ck, err := checker.NewChecker(mode)
	if err != nil {
		return err
	}

	lockFilePath := fmt.Sprintf(".%s_%d_%s.lock", ck.Config.Ip, ck.Config.Port, ck.Mode)
	lock := fslock.New(lockFilePath)
	defer func() {
		_ = os.Remove(lockFilePath)
	}()

	switch ck.Config.InnerRole {
	case config.RoleMaster:
		err = lock.TryLock()
		if err != nil {
			slog.Error("another checksum already running", slog.String("error", err.Error()))
			return err
		}
		slog.Info("run checksum on master start")
		err = ck.Run()
		if err != nil {
			slog.Error("run checksum on master", slog.String("error", err.Error()))
			return err
		}
		slog.Info("run checksum on master finish")
		return nil
	case config.RoleRepeater:
		err = lock.TryLock()
		if err != nil {
			slog.Error("another checksum already running", slog.String("error", err.Error()))
			return err
		}

		slog.Info("run checksum on repeater start")
		err = ck.Run()
		if err != nil {
			slog.Error("run checksum on repeater", slog.String("error", err.Error()))
			return err
		}
		if ck.Mode == config.GeneralMode {
			slog.Info("run checksum on repeater to report start")
			err = ck.Report()
			if err != nil {
				slog.Error("run report on repeater", slog.String("error", err.Error()))
				return err
			}
			slog.Info("run checksum on repeater to report finish")
		}
		slog.Info("run checksum on repeater finish")
		return nil
	case config.RoleSlave:
		slog.Info("run checksum on slave")
		if ck.Mode == config.DemandMode {
			err = fmt.Errorf("checksum bill should not run on slave")
			slog.Error("role is slave", slog.String("error", err.Error()))
			return err
		}
		slog.Info("run checksum on slave to report start")
		err = ck.Report()
		if err != nil {
			slog.Error("run report on slave", slog.String("error", err.Error()))
			return err
		}
		slog.Info("run checksum on slave to report finish")
		return nil
	default:
		err := fmt.Errorf("unknown instance inner role: %s", ck.Config.InnerRole)
		slog.Error("general run", slog.String("error", err.Error()))
		return err
	}
}
