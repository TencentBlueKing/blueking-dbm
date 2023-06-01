package model

import (
	"fmt"

	"dbm-services/common/go-pubpkg/logger"
)

// TbDeviceSpec TODO
type TbDeviceSpec struct {
	ID            int    `gorm:"primaryKey;column:id;type:int(11);not null" json:"-"`
	ResourceType  string `gorm:"column:resource_type;type:int(11);not null" json:"resource_type"`
	DeviceClass   string `gorm:"unique;column:device_class;type:varchar(64);not null" json:"device_class"`
	CPUNum        int    `gorm:"column:cpu_num;type:int(11);not null" json:"cpu_num"`
	DramCap       int    `gorm:"column:dram_cap;type:int(11);not null" json:"dram_cap"`
	SsdCap        int    `gorm:"column:ssd_cap;type:int(11);not null" json:"ssd_cap"`
	SsdNum        int    `gorm:"column:ssd_num;type:int(11);not null" json:"ssd_num"`
	HddCap        int    `gorm:"column:hdd_cap;type:int(11);not null" json:"hdd_cap"`
	IsLocalStorge int    `gorm:"column:is_local_storge;type:int(11);not null" json:"is_local_storge"`
}

// TbDeviceSpecName TODO
func TbDeviceSpecName() string {
	return "tb_device_spec"
}

// GetDeviceSpecFromClass TODO
func GetDeviceSpecFromClass(deviceClass string) (m TbDeviceSpec, err error) {
	err = DB.Self.Table(TbDeviceSpecName()).Where("device_class = ? ", deviceClass).First(&m).Error
	if err != nil {
		logger.Error(fmt.Sprintf("Query DeviceSpec By DeviceClass Failed %s", err.Error()))
		return
	}
	return
}
