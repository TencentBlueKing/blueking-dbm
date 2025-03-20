package config

import (
	"time"

	"github.com/pkg/errors"
)

// AlarmConfig handle alarm config, including shield alarm, unblock alarm, and check if alarm is shielded
// 实际上是对ClusterConfigHelper的封装
type AlarmConfig struct {
	c *ClusterConfigHelper
}

func NewAlarmConfig(c *ClusterConfigHelper) *AlarmConfig {
	return &AlarmConfig{
		c: c,
	}
}

// Shield server. If endTime is empty, shield forever, otherwise shield until endTime.
func (a *AlarmConfig) Shield(server *ConfServerItem, endTime string) error {
	_, err := a.c.UpdateOne(server, "alarm", "shield", "true")
	if err != nil {
		return err
	}
	_, err = a.c.UpdateOne(server, "alarm", ShieldEndTimeKey, endTime)
	if err != nil {
		return err
	}
	return nil
}

// Unblock shield server
func (a *AlarmConfig) Unblock(server *ConfServerItem) error {
	_, err := a.c.UpdateOne(server, "alarm", "shield", "false")
	if err != nil {
		return err
	}
	_, err = a.c.UpdateOne(server, "alarm", ShieldEndTimeKey, "")
	if err != nil {
		return err
	}
	return nil
}

// GetOne get one config item
func (a *AlarmConfig) GetOne(svr *ConfServerItem) (alarmShield string, endTime string, isShielded bool, err error) {
	alarmShield, err = a.c.GetOne(svr, "alarm", "shield")
	if err != nil {
		return
	}
	endTime, err = a.c.GetOne(svr, "alarm", ShieldEndTimeKey)
	if err != nil {
		return
	}

	isShielded = alarmShield == "true"

	if endTime == "" {
		return
	} else {
		endTimeVal, err2 := time.Parse(ShieldEndTimeFormat, endTime)
		if err2 != nil {
			return "", "",
				false, errors.Wrap(err2, "parse shield end time failed")
		}
		if time.Now().Before(endTimeVal) {
			isShielded = true
			return
		} else {
			isShielded = false
			return
		}
	}
}

// IsAlarmShield check if alarm shielded
func (a *AlarmConfig) IsAlarmShield(svr *ConfServerItem) (bool, error) {
	_, _, isShielded, err := a.GetOne(svr)
	if err != nil {
		return false, err
	}
	return isShielded, nil
}
