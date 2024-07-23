package cmutil

import (
	"fmt"

	"github.com/hashicorp/go-version"
)

func MustNewVersion(ver string) *version.Version {
	verObj, err := version.NewVersion(ver)
	if err != nil {
		panic(fmt.Errorf("parse version %s", ver))
	}
	return verObj
}
