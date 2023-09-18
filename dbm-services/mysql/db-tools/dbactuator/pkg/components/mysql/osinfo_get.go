package mysql

import (
	"encoding/json"
	"fmt"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
)

// OSInfoGetComp TODO
type OSInfoGetComp struct {
	Params        OSInfoParam `json:"extend"`
	result        OSInfoResult
	defaultParams bool
}

// OSInfoParam TODO
type OSInfoParam struct {
	// Directory default [/ /data /data1 /data2]
	Directory     []string `json:"directory"`
	NoCheckDevice bool     `json:"no_check_device"`
}

type OSInfoResult struct {
	Mem  *cmutil.MemoryInfo     `json:"mem"`
	Cpu  *cmutil.CPUInfo        `json:"cpu"`
	Disk []*cmutil.DiskPartInfo `json:"disk"`
}

// Example TODO
func (s *OSInfoGetComp) Example() interface{} {
	comp := OSInfoGetComp{
		Params: OSInfoParam{
			Directory:     []string{"/data/dbbak", "/data1/dbbak"},
			NoCheckDevice: false,
		},
	}
	return comp
}

// String 用于打印
func (s *OSInfoGetComp) String() string {
	str, _ := json.Marshal(s)
	return string(str)
}

// Start TODO
func (s *OSInfoGetComp) Start() (err error) {
	res := OSInfoResult{}
	res.Mem, err = cmutil.GetMemoryInfo()
	if err != nil {
		return err
	}
	res.Cpu, err = cmutil.GetCPUInfo()
	if err != nil {
		return err
	}
	if len(s.Params.Directory) == 0 {
		s.defaultParams = true
		s.Params.Directory = []string{"/", "/data", "/data1", "/data2"}
	}
	for _, dir := range s.Params.Directory {
		disk, err := cmutil.GetDiskPartInfo(dir, s.Params.NoCheckDevice)
		if err != nil {
			if s.defaultParams {
				continue
			}
			return err
		}
		res.Disk = append(res.Disk, disk)
	}
	s.result = res
	return nil
}

// WaitDone TODO
func (s *OSInfoGetComp) WaitDone() error {
	return nil
}

// OutputCtx TODO
func (s *OSInfoGetComp) OutputCtx() error {
	ss, err := components.WrapperOutput(s.result)
	if err != nil {
		return err
	}
	fmt.Println(ss)
	return nil
}
