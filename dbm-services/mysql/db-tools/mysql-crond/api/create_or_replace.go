package api

import (
	"encoding/json"
	"log/slog"

	"github.com/pkg/errors"
)

// JobDefine TODO
type JobDefine struct {
	Name     string   `json:"name" validate:"required"`
	Command  string   `json:"command" validate:"required"`
	Args     []string `json:"args"`
	Schedule string   `json:"schedule" validate:"required"`
	Creator  string   `json:"creator"`
	Enable   bool     `json:"enable"`
	WorkDir  string   `json:"work_dir"`
	Overlap  bool     `json:"overlap"`
}

// CreateOrReplace TODO
func (m *Manager) CreateOrReplace(job JobDefine, permanent bool) (int, error) {
	body := struct {
		Job       JobDefine `json:"job"`
		Permanent bool      `json:"permanent"`
	}{
		Job:       job,
		Permanent: permanent,
	}
	slog.Info("CreateOrReplace", slog.Any("job", job))

	resp, err := m.do("/create_or_replace", "POST", body)
	if err != nil {
		return 0, errors.Wrap(err, "manager call /create_or_replace")
	}

	res := struct {
		EntryId int `json:"entry_id"`
	}{}
	err = json.Unmarshal(resp, &res)
	if err != nil {
		return 0, errors.Wrap(err, "manager unmarshal /create_or_replace response")
	}

	return res.EntryId, nil
}
