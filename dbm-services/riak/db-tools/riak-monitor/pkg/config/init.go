package config

import (
	"os"
	"path/filepath"

	"github.com/go-playground/validator"
	"golang.org/x/exp/slog"
	"gopkg.in/yaml.v2"
)

var HeartBeatName = "riak_monitor_heart_beat"
var MonitorConfig *monitorConfig
var ItemsConfig []*MonitorItem
var HardCodeSchedule = "@every 10s"

// InitConfig 配置初始化
func InitConfig(configPath string) error {
	slog.Info("msg", "config path", configPath)
	if !filepath.IsAbs(configPath) {
		cwd, err := os.Getwd()
		if err != nil {
			slog.Error("init config", err)
			return err
		}

		configPath = filepath.Join(cwd, configPath)
	}
	slog.Info("msg", "absolute config path", configPath)

	content, err := os.ReadFile(configPath)
	if err != nil {
		slog.Error("init config", err)
		return err
	}

	slog.Info("msg", "content", string(content))
	MonitorConfig = &monitorConfig{}
	slog.Info("msg", "MonitorConfig", MonitorConfig)
	err = yaml.UnmarshalStrict(content, MonitorConfig)
	if err != nil {
		slog.Error("config file content", string(content))
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

// LoadMonitorItemsConfig 加载监控项配置
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

// InjectHardCodeItem 注入硬编码的心跳和db-up监控
func InjectHardCodeItem() {
	enable := true
	dbUpItem := &MonitorItem{
		Name:        "db-up",
		Enable:      &enable,
		Schedule:    &HardCodeSchedule, //&MonitorConfig.DefaultSchedule,
		MachineType: []string{MonitorConfig.MachineType},
	}
	heartBeatItem := &MonitorItem{
		Name:        HeartBeatName,
		Enable:      &enable,
		Schedule:    &HardCodeSchedule, //&MonitorConfig.DefaultSchedule,
		MachineType: []string{MonitorConfig.MachineType},
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

// WriteMonitorItemsBack 回写监控项到文件
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
