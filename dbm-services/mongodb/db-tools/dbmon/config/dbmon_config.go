package config

import (
	"os"
	"sync"

	"github.com/fsnotify/fsnotify"
	"github.com/jinzhu/copier"
	"github.com/pkg/errors"
	"github.com/spf13/viper"
	"go.uber.org/zap"
	"gopkg.in/yaml.v3"
)

// DbMonConfig 用于处理配置文件读取，更新
type DbMonConfig struct {
	ConfigFile string
	Config     *Configuration
	lock       *sync.RWMutex
	viper      *viper.Viper
}

func NewDbMonConfig(configFile string) (*DbMonConfig, error) {
	v := &DbMonConfig{
		ConfigFile: configFile,
		lock:       new(sync.RWMutex),
		viper:      viper.New(),
	}
	return v, nil
}

// LoadAndWatchConfig 读取配置文件, 并监控配置文件变化.
func (c *DbMonConfig) LoadAndWatchConfig(watch bool, logger *zap.Logger) error {
	err := c.LoadConfig()
	if err != nil {
		return err
	}
	if !watch {
		return nil
	}
	// 监控配置文件变化
	c.viper.WatchConfig()
	c.viper.OnConfigChange(func(in fsnotify.Event) {
		logger.Info("viper.OnConfigChange: start to reload config")
		c.lock.Lock()
		defer c.lock.Unlock()
		c2 := new(Configuration)
		if err := c.viper.Unmarshal(c2); err != nil {
			logger.Error("viper.OnConfigChange: unmarshal config error", zap.Error(err))
		} else {
			c2.SetDefault()
			c2.LoadCount = c.Config.LoadCount + 1
			c.Config = c2
			logger.Info("viper.OnConfigChange: config changed", zap.Any("config", c.Config))
		}
	})
	return nil
}

// LoadConfig LoadConfig from file
func (c *DbMonConfig) LoadConfig() error {
	c.viper.SetConfigFile(c.ConfigFile)
	err := c.viper.ReadInConfig()
	if err != nil { // 读取配置信息失败
		return err
	}
	c.Config = new(Configuration)
	if err = c.viper.Unmarshal(c.Config); err != nil {
		return err
	}
	c.Config.SetDefault()
	return nil
}

// GetCopy 获取配置文件的副本
func (c *DbMonConfig) GetCopy() (*Configuration, error) {
	c.lock.Lock()
	defer c.lock.Unlock()
	if c.Config == nil {
		return nil, errors.New("config is nil")
	}
	var val = &Configuration{}
	var err = copier.Copy(val, c.Config)
	if err != nil {
		return nil, errors.Wrap(err, "copy config error")
	}
	return val, nil
}

// WriteFile 写入配置文件 在act install_dbmon中也有调用
func (c *DbMonConfig) WriteFile(conf *Configuration) error {
	c.lock.Lock()
	defer c.lock.Unlock()

	if conf == nil {
		return errors.New("config is nil")
	}

	if c.ConfigFile == "" {
		return errors.New("config file is empty")
	}

	data, err := yaml.Marshal(conf)
	if err != nil {
		return errors.Wrap(err, "marshal config error")
	}
	return os.WriteFile(c.ConfigFile, data, 0644)
}
