package config

import (
	"log"
	"strings"

	"github.com/spf13/viper"
)

var (
	// Get TODO
	Get = viper.Get
	// GetBool TODO
	GetBool = viper.GetBool
	// GetDuration TODO
	GetDuration = viper.GetDuration
	// GetFloat64 TODO
	GetFloat64 = viper.GetFloat64
	// GetInt TODO
	GetInt = viper.GetInt
	// GetInt32 TODO
	GetInt32 = viper.GetInt32
	// GetInt64 TODO
	GetInt64 = viper.GetInt64
	// GetIntSlice TODO
	GetIntSlice = viper.GetIntSlice
	// GetString TODO
	GetString = viper.GetString
	// GetStringMap TODO
	GetStringMap = viper.GetStringMap
	// GetStringMapString TODO
	GetStringMapString = viper.GetStringMapString
	// GetStringMapStringSlice TODO
	GetStringMapStringSlice = viper.GetStringMapStringSlice
	// GetStringSlice TODO
	GetStringSlice = viper.GetStringSlice
	// GetTime TODO
	GetTime = viper.GetTime
	// GetUint TODO
	GetUint = viper.GetUint
	// GetUint32 TODO
	GetUint32 = viper.GetUint32
	// GetUint64 TODO
	GetUint64 = viper.GetUint64
	// SetDefault TODO
	SetDefault = viper.SetDefault
)

// InitConfig TODO
func InitConfig(fileName string) {
	viper.AddConfigPath("conf")
	viper.SetConfigType("yaml")
	viper.SetConfigName(fileName)
	viper.AutomaticEnv() // read in environment variables that match
	// viper.SetEnvPrefix("ACCOUNT")
	replacer := strings.NewReplacer(".", "_")
	viper.SetEnvKeyReplacer(replacer)
	if err := viper.MergeInConfig(); err != nil {
		log.Fatal(err)
	}
}
