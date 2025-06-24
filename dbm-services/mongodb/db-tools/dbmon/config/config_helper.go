package config

import (
	"dbm-services/mongodb/db-tools/dbactuator/pkg/util"
	"os"
	"strconv"
	"time"

	"github.com/pkg/errors"
	"go.uber.org/zap"
	"gopkg.in/yaml.v2"
)

type ClusterConfigHelper struct {
	configFile string
	conf       *ClusterConfigConf
}

func NewClusterConfigHelper(configFile string) *ClusterConfigHelper {
	return &ClusterConfigHelper{
		configFile: configFile,
	}
}

func (c *ClusterConfigHelper) RewriteConfigFile() error {
	data, err := yaml.Marshal(c.conf)
	if err != nil {
		return err
	}
	return os.WriteFile(c.configFile, data, 0644)
}

// UpdateOne update one config item. in instance scope.
// set, cluster 级别的配置还不支持. 因为目前还不支持回写集群配置.
// 控制本地配置，可以用--port=0来表示控制所有实例
func (c *ClusterConfigHelper) UpdateOne(svr *ConfServerItem, segment, key string, value string) (string, error) {
	oldValue, err := c.GetOne(svr, segment, key)
	if err != nil {
		return "", err
	}

	// update instance config
	for i, _ := range c.conf.InstanceConfig {
		item := c.conf.InstanceConfig[i]
		if item.Instance == svr.Addr() && item.Segment == segment && item.Key == key {
			c.conf.InstanceConfig[i].Value = value
			return oldValue, nil
		}
	}

	// add new instance config
	c.conf.InstanceConfig = append(c.conf.InstanceConfig, InstanceConfigItem{
		Instance: svr.Addr(),
		ClusterConfigItem: ClusterConfigItem{
			ClusterId: svr.GetClusterIdStr(),
			Segment:   segment,
			Key:       key,
			Value:     value,
			Mtime:     int(time.Now().Unix()),
		}})

	return oldValue, nil
}

func (c *ClusterConfigHelper) GetOne(svr *ConfServerItem, segment, key string) (string, error) {
	// default value
	defaultValue := ""
	// Get from registered config
	if v, ok := registeredConfig.Load(segment + "." + key); ok {
		defaultValue = v.(string)
	} else {
		return "", errors.New("Unregistered-config")
	}

	// todo realod config file
	var err error
	c.conf, err = _loadClusterConfigFile(c.configFile, c.conf)

	if err != nil {
		return "", errors.Wrap(err, "load cluster config failed")
	}

	// instance config
	for _, item := range c.conf.InstanceConfig {
		if item.Instance == svr.Addr() && item.Segment == segment && item.Key == key {
			return item.Value, nil
		}
	}

	// set config
	for _, item := range c.conf.SetConfig {
		if item.ClusterId == svr.GetClusterIdStr() && item.SetId == svr.SetName &&
			item.Segment == segment && item.Key == key {
			return item.Value, nil
		}
	}

	// cluster config
	for _, item := range c.conf.ClusterConfig {
		if item.ClusterId == svr.GetClusterIdStr() &&
			item.Segment == segment && item.Key == key {
			return item.Value, nil
		}
	}

	return defaultValue, nil
}

func (c *ClusterConfigHelper) GetInt64(svr *ConfServerItem, segment, key string, defaultVal int64) (int64, error) {
	v, err := c.GetOne(svr, segment, key)
	if err != nil {
		return defaultVal, errors.Wrap(err, "get one failed, return default value")
	}
	intv, err := strconv.ParseInt(v, 10, 64)
	if err != nil {
		return defaultVal, err
	}
	return intv, nil
}

func (c *ClusterConfigHelper) GetBool(svr *ConfServerItem, segment, key string, defaultValue bool) (bool, error) {
	return true, nil
}

var ClusterConfig *ClusterConfigHelper

// mkClusterConfigFile create a cluster config file if not exists
func mkClusterConfigFile(fileName string) error {
	if fileName == "" {
		panic("cluster config file name is empty")
	}
	if util.FileExists(fileName) {
		return nil
	}
	conf := ClusterConfigConf{
		CreateTime: time.Now(),
	}
	data, err := yaml.Marshal(conf)
	if err != nil {
		panic("init cluster config failed")
	}
	err = os.WriteFile(fileName, data, 0644)
	if err != nil {
		panic("init cluster config failed")
	}
	return nil
}

func InitClusterConfigHelper(clusterConfigFile string, logger *zap.Logger) {
	mkClusterConfigFile(clusterConfigFile)
	ClusterConfig = NewClusterConfigHelper(clusterConfigFile)
	var err error
	ClusterConfig.conf, err = _loadClusterConfigFile(clusterConfigFile, nil)
	if err != nil {
		panic("load cluster config failed")
	}

	logger.Info("init cluster config success", zap.String("file", clusterConfigFile))
}
