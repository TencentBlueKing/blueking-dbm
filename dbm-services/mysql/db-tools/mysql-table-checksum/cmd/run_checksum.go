package cmd

import (
	"dbm-services/common/reverseapi"
	"dbm-services/common/reverseapi/define/mysql"
	"encoding/json"
	"fmt"
	"io"
	"log/slog"
	"os"
	"path/filepath"
	"slices"

	"dbm-services/mysql/db-tools/mysql-table-checksum/pkg/checker"
	"dbm-services/mysql/db-tools/mysql-table-checksum/pkg/config"

	"github.com/juju/fslock"
	"gopkg.in/yaml.v2"
)

func generateRun(mode config.CheckMode, configPath string) error {
	err := config.InitConfig(configPath)
	if err != nil {
		return err
	}

	// 只有 general 模式才会强制保持配置和实例信息一致
	if mode == config.GeneralMode {
		err = updateConfig(configPath)
		if err != nil {
			return err
		}
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

func updateConfig(configPath string) error {
	sii, err := getSelfInfo()
	if err != nil {
		slog.Error("init config", slog.String("error", err.Error()))
		return nil
	}
	slog.Info("init config", slog.Any("sii", sii))

	config.ChecksumConfig.InnerRole = config.InnerRoleEnum(sii.InstanceInnerRole)

	cf, err := os.OpenFile(configPath, os.O_WRONLY|os.O_CREATE|os.O_TRUNC, 0777)
	if err != nil {
		slog.Error("init config", slog.String("error", err.Error()))
		return err
	}
	defer func() {
		_ = cf.Close()
	}()

	b, err := yaml.Marshal(config.ChecksumConfig)
	if err != nil {
		slog.Error("init config", slog.String("error", err.Error()))
		return err
	}

	_, err = cf.WriteString(string(b) + "\n")
	if err != nil {
		slog.Error("init config", slog.String("error", err.Error()))
		return err
	}
	slog.Info("init config", slog.String("config", string(b)))
	return nil
}

func getSelfInfo() (sii *mysql.StorageInstanceInfo, err error) {
	filePath := filepath.Join(
		reverseapi.DefaultCommonConfigDir,
		reverseapi.DefaultInstanceInfoFileName,
	)
	f, err := os.OpenFile(filePath, os.O_RDONLY, os.ModePerm)
	if err != nil {
		slog.Error(
			"init config",
			slog.String("err", err.Error()),
			slog.String("filePath", filePath),
		)
		return nil, err
	}

	b, err := io.ReadAll(f)
	if err != nil {
		slog.Error(
			"init config",
			slog.String("err", err.Error()),
		)
		return nil, err
	}

	var siis []mysql.StorageInstanceInfo
	err = json.Unmarshal(b, &siis)
	if err != nil {
		slog.Error(
			"init config",
			slog.String("err", err.Error()),
		)
		return nil, err
	}
	slog.Info("init config", slog.String("instance info", string(b)))

	idx := slices.IndexFunc(siis, func(ele mysql.StorageInstanceInfo) bool {
		return ele.Ip == config.ChecksumConfig.Ip && ele.Port == config.ChecksumConfig.Port
	})
	if idx < 0 {
		err := fmt.Errorf("can't find %s:%d in %v", config.ChecksumConfig.Ip, config.ChecksumConfig.Port, siis)
		slog.Error(
			"init config",
			slog.String("err", err.Error()),
		)
		return nil, err
	}

	return &siis[idx], nil
}
