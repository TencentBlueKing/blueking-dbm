package test

import (
	"testing"

	"dbm-services/common/dbha/ha-module/log"
)

func TestLog(t *testing.T) {
	i := 0
	for {
		log.Logger.Debugf("debug %d", i)
		log.Logger.Infof("info %d", i)
		log.Logger.Warnf("warn %d", i)
		log.Logger.Errorf("error %d", i)
		i++
	}
}
