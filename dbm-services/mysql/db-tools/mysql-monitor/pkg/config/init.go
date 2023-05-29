package config

import (
	"fmt"
	"os"
	"path/filepath"

	"github.com/go-playground/validator/v10"
	"golang.org/x/exp/slog"
	"gopkg.in/yaml.v2"
)

// HeartBeatName TODO
var HeartBeatName = "mysql_monitor_heart_beat"

// MonitorConfig TODO
var MonitorConfig *monitorConfig

// ItemsConfig TODO
var ItemsConfig []*MonitorItem

// HardCodeSchedule TODO
var HardCodeSchedule = "@every 10s"

// InitConfig TODO
func InitConfig(configPath string) error {
	fmt.Printf("config flag: %s\n", configPath)
	if !filepath.IsAbs(configPath) {
		cwd, err := os.Getwd()
		if err != nil {
			slog.Error("init config", err)
			return err
		}

		configPath = filepath.Join(cwd, configPath)
	}
	fmt.Printf("config path: %s\n", configPath)

	content, err := os.ReadFile(configPath)
	if err != nil {
		slog.Error("init config", err)
		return err
	}

	MonitorConfig = &monitorConfig{}
	err = yaml.UnmarshalStrict(content, MonitorConfig)
	if err != nil {
		slog.Error("init config", err)
		return err
	}

	validate := validator.New()
	err = validate.Struct(MonitorConfig)
	if err != nil {
		slog.Error("validate monitor config", err)
		return err
	}

	return nil
}

// LoadMonitorItemsConfig TODO
func LoadMonitorItemsConfig() error {
	ItemsConfig = make([]*MonitorItem, 0)

	content, err := os.ReadFile(MonitorConfig.ItemsConfigFile)
	if err != nil {
		slog.Error("load monitor items config", err)
		return err
	}

	err = yaml.UnmarshalStrict(content, &ItemsConfig)
	if err != nil {
		slog.Error("unmarshal monitor items config", err)
		return err
	}

	validate := validator.New()
	for _, ele := range ItemsConfig {
		err := validate.Struct(ele)
		if err != nil {
			slog.Error("validate monitor items config", err)
			return err
		}
	}

	return nil
}

// InjectHardCodeItem TODO
func InjectHardCodeItem() {
	enable := true
	dbUpItem := &MonitorItem{
		Name:        "db-up",
		Enable:      &enable,
		Schedule:    &HardCodeSchedule, // &MonitorConfig.DefaultSchedule,
		MachineType: []string{MonitorConfig.MachineType},
		Role:        nil,
	}
	heartBeatItem := &MonitorItem{
		Name:        HeartBeatName,
		Enable:      &enable,
		Schedule:    &HardCodeSchedule, // &MonitorConfig.DefaultSchedule,
		MachineType: []string{MonitorConfig.MachineType},
		Role:        nil,
	}
	slog.Debug("load monitor item", slog.Any("items", ItemsConfig))

	ItemsConfig = injectItem(dbUpItem, ItemsConfig)
	slog.Debug("inject hardcode", slog.Any("items", ItemsConfig))

	ItemsConfig = injectItem(heartBeatItem, ItemsConfig)
	slog.Debug("inject hardcode", slog.Any("items", ItemsConfig))
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

// WriteMonitorItemsBack TODO
func WriteMonitorItemsBack() error {
	// 注入硬编码监控项后回写items文件
	content, err := yaml.Marshal(ItemsConfig)
	if err != nil {
		slog.Error("marshal items config", err)
		return err
	}

	f, err := os.OpenFile(MonitorConfig.ItemsConfigFile, os.O_TRUNC|os.O_WRONLY, 0755)
	if err != nil {
		slog.Error("open items config file", err)
		return err
	}

	_, err = f.Write(content)
	if err != nil {
		slog.Error("write items config file", err)
		return err
	}
	return nil
}
