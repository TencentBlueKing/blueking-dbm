package config

import (
	acst "dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"fmt"
	"log/slog"
	"os"
	"path/filepath"

	"github.com/go-playground/validator/v10"
	"github.com/gofrs/flock"
	"gopkg.in/yaml.v2"
)

var HeartBeatName = "mysql_monitor_heart_beat"
var HeartBeatSchedule = "@every 5m"
var MonitorConfig *Config
var ItemsConfig []*MonitorItem
var DBUpSchedule = "@every 10s"
var UpdateMonitorConfigSchedule = "@every 10m"

// InitConfig 配置初始化
func InitConfig(configPath string) error {
	fmt.Printf("config flag: %s\n", configPath)
	if !filepath.IsAbs(configPath) {
		cwd, err := os.Getwd()
		if err != nil {
			slog.Error("init config", slog.String("error", err.Error()))
			return err
		}

		configPath = filepath.Join(cwd, configPath)
	}
	fmt.Printf("config path: %s\n", configPath)

	lockFileName := fmt.Sprintf("%s.lock", filepath.Base(configPath))
	lockFileBasePath := filepath.Join(acst.MySQLMonitorInstallPath, "locks")
	err := os.MkdirAll(lockFileBasePath, os.ModePerm)
	if err != nil {
		slog.Error(
			"init config",
			slog.String("dir", lockFileBasePath),
			slog.String("err", err.Error()),
		)
		return err
	}
	lockFilePath := filepath.Join(lockFileBasePath, lockFileName)
	fl := flock.New(lockFilePath)

	// 共享锁
	err = fl.RLock()
	if err != nil {
		slog.Error("init config", slog.String("error", err.Error()))
		return err
	}
	defer func() {
		_ = fl.Unlock()
	}()

	content, err := os.ReadFile(configPath)
	if err != nil {
		slog.Error("init config", slog.String("error", err.Error()))
		return err
	}

	MonitorConfig = &Config{}
	err = yaml.Unmarshal(content, MonitorConfig)
	if err != nil {
		slog.Error("init config", slog.String("error", err.Error()))
		return err
	}

	validate := validator.New()
	err = validate.Struct(MonitorConfig)
	if err != nil {
		slog.Error("validate monitor config", slog.String("error", err.Error()))
		return err
	}

	return nil
}

// LoadMonitorItemsConfig 加载监控项配置
func LoadMonitorItemsConfig() error {
	ItemsConfig = make([]*MonitorItem, 0)

	content, err := os.ReadFile(MonitorConfig.ItemsConfigFile)
	if err != nil {
		slog.Error("load monitor items config", slog.String("error", err.Error()))
		return err
	}

	err = yaml.UnmarshalStrict(content, &ItemsConfig)
	if err != nil {
		slog.Error("unmarshal monitor items config", slog.String("error", err.Error()))
		return err
	}

	validate := validator.New()
	for _, ele := range ItemsConfig {
		err := validate.Struct(ele)
		if err != nil {
			slog.Error("validate monitor items config", slog.String("error", err.Error()))
			return err
		}
	}

	return nil
}

func InjectMonitorHeartBeatItem() {
	enable := true
	heartBeatItem := &MonitorItem{
		Name:        HeartBeatName,
		Enable:      &enable,
		Schedule:    &HeartBeatSchedule,
		MachineType: []string{MonitorConfig.MachineType},
		Role:        nil,
	}
	ItemsConfig = injectItem(heartBeatItem, ItemsConfig)
	slog.Info("inject hardcode", slog.String("item", HeartBeatName))
}

func InjectMonitorDbUpItem() {
	enable := true
	dbUpItem := &MonitorItem{
		Name:        "db-up",
		Enable:      &enable,
		Schedule:    &DBUpSchedule,
		MachineType: []string{MonitorConfig.MachineType},
		Role:        nil,
	}
	ItemsConfig = injectItem(dbUpItem, ItemsConfig)
	slog.Info("inject hardcode", slog.String("item", "db-up"))
}

func InjectUpdateMonitorConfigItem() {
	// 只有主备存储才需要更新配置中的角色
	if MonitorConfig.MachineType != "backend" && MonitorConfig.MachineType != "remote" {
		return
	}
	slog.Info(
		"inject hardcode",
		slog.String("machine_type", MonitorConfig.MachineType),
		slog.String("name", "update-monitor-config"),
	)

	enable := true
	item := &MonitorItem{
		Name:        "update-monitor-config",
		Enable:      &enable,
		Schedule:    &UpdateMonitorConfigSchedule,
		MachineType: []string{MonitorConfig.MachineType},
		Role:        nil,
	}
	ItemsConfig = injectItem(item, ItemsConfig)
	slog.Info("inject hardcode", slog.String("item", "update-monitor-config"))
}

func injectItem(item *MonitorItem, collect []*MonitorItem) (res []*MonitorItem) {
	for i, ele := range collect {
		if ele.Name == item.Name {
			// 如果已经在配置文件, 保留 enable 配置, 其他覆盖为默认配置
			res = append(collect[:i], collect[i+1:]...)
			item.Enable = ele.Enable
			return append(res, item)
		}
	}

	return append(collect, item)
}

// WriteMonitorItemsBack 回写监控项到文件
func WriteMonitorItemsBack() error {
	// 注入硬编码监控项后回写items文件
	content, err := yaml.Marshal(ItemsConfig)
	if err != nil {
		slog.Error("marshal items config", slog.String("error", err.Error()))
		return err
	}

	f, err := os.OpenFile(MonitorConfig.ItemsConfigFile, os.O_TRUNC|os.O_WRONLY, 0755)
	if err != nil {
		slog.Error("open items config file", slog.String("error", err.Error()))
		return err
	}

	_, err = f.Write(content)
	if err != nil {
		slog.Error("write items config file", slog.String("error", err.Error()))
		return err
	}
	return nil
}
