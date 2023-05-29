package tools

import (
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/osutil"

	"github.com/pkg/errors"
)

func (s *ToolSet) validate() error {
	for k, v := range s.maps {
		if _, ok := defaultPath[k]; !ok {
			return errors.Errorf("tool %s is not regiestered", k)
		}
		if !osutil.FileExist(v) {
			err := errors.Errorf("%s: %s not found", k, v)
			return err
		}
	}
	return nil
}

// Get 获得工具路径
func (s *ToolSet) Get(tool ExternalTool) (string, error) {
	if p, ok := s.maps[tool]; ok {
		return p, nil
	}
	err := errors.Errorf("%s not registered or picked", tool)
	return "", err
}

// MustGet 必须获得
func (s *ToolSet) MustGet(tool ExternalTool) string {
	if p, ok := s.maps[tool]; ok {
		return p
	}
	err := errors.Errorf("%s not registered or picked", tool)
	panic(err)
}
